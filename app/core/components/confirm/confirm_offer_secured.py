"""Confirm offer secured component

This component handles confirming secured offer creation:
- Gets offer details from component_data
- Gets target account from action state
- Gets active account from dashboard state
- Shows confirmation with both account details
"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.messaging.types import Button
from core.utils.utils import format_denomination

from . import ConfirmBase

# Offer confirmation template
OFFER_CONFIRMATION = """*💰 {amount}*
💰 Secured Credex Offer

_From:_
💳 *{active_account_name}*
💳 {active_account_handle}

_To:_
💳 *{target_account_name}*
💳 {target_account_handle}"""


class ConfirmOfferSecured(ConfirmBase):
    """Handles secured offer confirmation"""

    def __init__(self):
        super().__init__("confirm_offer_secured")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def validate(self, value: Any) -> ValidationResult:
        """Override parent validate to handle confirmation flow"""
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        awaiting_input = current_data.get("awaiting_input", False)

        # Initial activation - let parent handle it only if not already awaiting input
        if value is None and not awaiting_input:
            return super().validate(value)

        # Process confirmation if we have an incoming message
        if current_data.get("incoming_message"):
            # Process the confirmation
            return self.handle_confirmation(value)

        # Already awaiting input but no message to process
        return ValidationResult.success(None)

    def _send(self) -> None:
        """Send confirmation message with buttons"""
        logger = logging.getLogger(__name__)
        logger.info("Preparing confirmation message")

        # Get offer data from component_data.data
        logger.debug("Getting offer details from component data")
        offer_data = self.state_manager.get_state_value("component_data", {}).get("data", {})
        amount = offer_data.get("amount")
        denom = offer_data.get("denom")
        handle = offer_data.get("handle")

        if not amount or not denom or not handle:
            raise ComponentException(
                message="Missing offer details",
                component=self.type,
                field="offer_data",
                details={
                    "missing_fields": [
                        "amount" if not amount else None,
                        "denom" if not denom else None,
                        "handle" if not handle else None
                    ]
                }
            )

        # Get and validate target account details from action state
        logger.debug("Getting target account from action state")
        action = self.state_manager.get_state_value("action", {})
        logger.debug(f"Action state: {action}")
        target_account = action.get("details", {})
        logger.debug(f"Target account details: {target_account}")
        if not target_account or not target_account.get("accountName"):
            raise ComponentException(
                message="Missing target account details",
                component=self.type,
                field="target_account",
                value=str(action)
            )

        # Get and validate active account details from dashboard state
        logger.debug("Getting active account from dashboard state")
        dashboard = self.state_manager.get_state_value("dashboard", {})
        logger.debug(f"Dashboard state: {dashboard}")
        active_account_id = self.state_manager.get_state_value("active_account_id")
        logger.debug(f"Active account ID: {active_account_id}")
        if not active_account_id:
            raise ComponentException(
                message="No active account selected",
                component=self.type,
                field="active_account_id",
                value=str(dashboard)
            )

        active_account = next(
            (acc for acc in dashboard.get("accounts", [])
             if acc.get("accountID") == active_account_id),
            None
        )
        if not active_account or not active_account.get("accountName"):
            raise ComponentException(
                message="Missing active account details",
                component=self.type,
                field="active_account",
                value=str(dashboard)
            )

        # Format amount with denomination
        try:
            formatted_amount = format_denomination(float(amount), denom)
        except (ValueError, TypeError):
            raise ComponentException(
                message="Invalid amount format",
                component=self.type,
                field="amount",
                details={"amount": amount, "denom": denom}
            )

        # Format and send confirmation message
        logger.debug(
            f"Sending confirmation for amount {formatted_amount} from "
            f"{active_account.get('accountName')} to {target_account.get('accountName')}"
        )
        confirmation_message = OFFER_CONFIRMATION.format(
            amount=formatted_amount,
            active_account_name=active_account.get("accountName", ""),
            active_account_handle=active_account.get("accountHandle", ""),
            target_account_name=target_account.get("accountName", ""),
            target_account_handle=handle
        )

        self.state_manager.messaging.send_interactive(
            body=confirmation_message,
            buttons=[
                Button(id="confirm", title="📝 Sign and Send 💸"),
                Button(id="cancel", title="❌ Cancel ❌")
            ]
        )
        self.set_awaiting_input(True)

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle secured offer confirmation"""
        logger = logging.getLogger(__name__)
        logger.info("Processing confirmation response")

        # Validate state manager is set
        logger.debug("Checking state manager")
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "confirm_offer_secured"}
            )

        # Get offer data from component data
        logger.debug("Getting offer data from component data")
        offer_data = self.state_manager.get_state_value("component_data", {}).get("data", {})
        if not offer_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="component_data",
                details={"component": "confirm_offer_secured"}
            )
        amount = offer_data.get("amount")
        denom = offer_data.get("denom")
        handle = offer_data.get("handle")

        if not amount or not denom or not handle:
            return ValidationResult.failure(
                message="Missing offer details",
                field="offer_data",
                details={
                    "missing_fields": [
                        "amount" if not amount else None,
                        "denom" if not denom else None,
                        "handle" if not handle else None
                    ]
                }
            )

        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})

        # Process button response
        logger.debug("Processing button response")
        incoming_message = current_data.get("incoming_message", {})
        if incoming_message.get("type") != "interactive":
            return ValidationResult.failure(
                message="Please use the Confirm or Cancel button",
                field="type",
                details={"message": incoming_message}
            )

        # Get button info
        text = incoming_message.get("text", {})
        if text.get("interactive_type") != "button":
            return ValidationResult.failure(
                message="Please use the Confirm or Cancel button",
                field="interactive_type",
                details={"text": text}
            )

        # Check button ID
        button = text.get("button", {})
        button_id = button.get("id")

        logger.debug(f"Button ID: {button_id}")
        if button_id == "cancel":
            logger.info("Offer cancelled")
            # Store confirmation status and set component result for flow control
            self.update_data({"confirmed": False})
            self.state_manager.set_component_result("cancelled")

            # Send cancellation message
            self.state_manager.messaging.send_text("Ok, no problem. It's cancelled.")

            # Release input wait
            self.set_awaiting_input(False)
            return ValidationResult.success({"confirmed": False})

        if button_id != "confirm":
            return ValidationResult.failure(
                message="Please use the Confirm or Cancel button",
                field="button",
                details={"button": button}
            )

        # Store confirmation status
        logger.info("Offer confirmed")
        self.update_data({"confirmed": True})

        # Release input wait
        self.set_awaiting_input(False)
        return ValidationResult.success({"confirmed": True})

    def get_rejection_message(self) -> str:
        """Get message for when offer is rejected"""
        return "Secured offer creation cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data"""
        return {
            "confirmed": value.get("confirmed", False)
        }
