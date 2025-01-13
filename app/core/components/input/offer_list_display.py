"""Offer list display component

This component handles displaying a list of Credex offers and processing offer selection.
"""

import logging
from typing import Any, Dict, List

from core.components.base import InputComponent
from core.error.types import ValidationResult
from core.messaging.types import Button

logger = logging.getLogger(__name__)

# Title template
TITLE = """*Accept An Offer*"""


class OfferListDisplay(InputComponent):
    """Handles displaying a list of Credex offers and processing selection"""

    def __init__(self):
        super().__init__("offer_list_display")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate offer display and selection

        Args:
            value: None for initial display, or incoming message for selection
        """
        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = current_data.get("incoming_message")

            # Initial activation - display offer list
            if not current_data.get("awaiting_input"):
                return self._display_offers()

            # Process offer selection
            if not incoming_message:
                return ValidationResult.success(None)

            # Validate interactive message
            if incoming_message.get("type") != "interactive":
                return ValidationResult.failure(
                    message="Please select an offer using the buttons provided",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get button info
            text = incoming_message.get("text", {})
            if text.get("interactive_type") != "button":
                return ValidationResult.failure(
                    message="Please select an offer using the buttons provided",
                    field="interactive_type",
                    details={"text": text}
                )

            # Get button ID (credex_id)
            button = text.get("button", {})
            credex_id = button.get("id")
            if not credex_id:
                return ValidationResult.failure(
                    message="Invalid offer selection",
                    field="button",
                    details={"button": button}
                )

            # Handle return to dashboard
            if credex_id == "return_to_dashboard":
                self.update_component_data(
                    component_result="return_to_dashboard",
                    awaiting_input=False
                )
                return ValidationResult.success(None)

            # Validate credex_id exists in available offers
            if not self._is_valid_offer(credex_id):
                return ValidationResult.failure(
                    message="Invalid offer selection. Please choose from the available offers.",
                    field="credex_id",
                    details={"credex_id": credex_id}
                )

            # Store credex_id and continue to API
            self.update_component_data(
                data={"credex_id": credex_id},
                component_result="process_offer",
                awaiting_input=False
            )
            return ValidationResult.success(None)

        except Exception as e:
            logger.error(f"Error in offer list display: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="offer_list",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def _display_offers(self) -> ValidationResult:
        """Display offer list with selection buttons"""
        try:
            # Get dashboard data
            dashboard = self.state_manager.get_state_value("dashboard")
            if not dashboard:
                return ValidationResult.failure(
                    message="No dashboard data found",
                    field="dashboard",
                    details={"component": self.type}
                )

            # Get context and offers
            context = self.state_manager.get_path()
            offers = self._get_offers_for_context(context, dashboard)
            if not offers:
                # Send error message to user
                error_msg = f"❌ No {context.replace('_', ' ')}s available at this time."
                self.state_manager.messaging.send_text(error_msg)

                # Return to dashboard
                self.update_component_data(
                    component_result="return_to_dashboard",
                    awaiting_input=False
                )
                return ValidationResult.success(None)

            # Sort offers chronologically (oldest first)
            sorted_offers = sorted(offers, key=lambda x: x.get("timestamp", "0"))

            # Create buttons for up to 9 offers + dashboard button
            buttons = []

            # Add offer buttons (up to 9)
            for offer in sorted_offers[:9]:
                buttons.append(Button(
                    id=str(offer["credexID"]),
                    title=f"{offer['formattedInitialAmount']} from {offer['counterpartyAccountName']} ✅"
                ))

            # Add return to dashboard button
            buttons.append(Button(
                id="return_to_dashboard",
                title="Return to Dashboard 🏠"
            ))

            # Send title and buttons
            self.state_manager.messaging.send_interactive(
                body=TITLE,
                buttons=buttons
            )
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

        except Exception as e:
            logger.error(f"Error displaying offers: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="display",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def _get_offers_for_context(self, context: str, dashboard: Dict) -> List[Dict]:
        """Get relevant offers based on context"""
        # Get active account
        active_account_id = self.state_manager.get_state_value("active_account_id")
        if not active_account_id:
            return []

        # Find active account
        accounts = dashboard.get("accounts", [])
        active_account = next(
            (acc for acc in accounts if acc.get("accountID") == active_account_id),
            None
        )
        if not active_account:
            return []

        # Get offers based on context
        if context in {"accept_offer", "decline_offer"}:
            return active_account.get("pendingInData", [])
        if context == "cancel_offer":
            return active_account.get("pendingOutData", [])
        return []

    def _is_valid_offer(self, credex_id: str) -> bool:
        """Check if credex_id exists in available offers"""
        try:
            # Get dashboard and context
            dashboard = self.state_manager.get_state_value("dashboard", {})
            context = self.state_manager.get_path()

            # Get relevant offers
            offers = self._get_offers_for_context(context, dashboard)

            # Check if credex_id exists
            return any(str(offer.get("credexID")) == credex_id for offer in offers)

        except Exception as e:
            logger.error(f"Error validating offer: {str(e)}")
            return False

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified offer selection"""
        return {
            "credex_id": value
        }
