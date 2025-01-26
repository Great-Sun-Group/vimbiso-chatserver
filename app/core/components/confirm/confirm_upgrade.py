"""Confirm upgrade component

This component handles confirming member tier upgrade:
- Gets member details from dashboard state
- Shows confirmation with current/next tier
- Handles confirmation button interaction
"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.messaging.types import Button

from . import ConfirmBase

logger = logging.getLogger(__name__)

# Upgrade confirmation template
UPGRADE_CONFIRMATION = """📈 *Member Tier Upgrade*

👤 Member: {member_name}
🌟 Current Tier: Open (Free)
💫 Next Tier: Hustler ($1 USD/month)

🔥 If you are hustling hard to make a dollar in the markets of Mbare or anywhere in Zimbabwe's informal economy, be one of the first 10,000 VimbisoPay Hustlers and get a full year for $1 💥💥💥"""


class ConfirmUpgrade(ConfirmBase):
    """Handles member tier upgrade confirmation"""

    def __init__(self):
        super().__init__("confirm_upgrade")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data"""
        super().set_state_manager(state_manager)

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
        logger.info("Preparing upgrade confirmation message")

        try:
            # Get member details from dashboard
            logger.debug("Getting member details from dashboard")
            dashboard = self.state_manager.get_state_value("dashboard", {})
            member = dashboard.get("member", {})

            if not member:
                raise ComponentException(
                    message="No member data found",
                    component=self.type,
                    field="member",
                    value=str(dashboard)
                )

            # Get member details
            member_name = f"{member.get('firstname', '')} {member.get('lastname', '')}".strip()
            current_tier = member.get("memberTier")
            next_tier = current_tier + 1 if current_tier is not None else None

            if not all([member_name, current_tier is not None, next_tier is not None]):
                raise ComponentException(
                    message="Missing member details",
                    component=self.type,
                    field="member_details",
                    value=str(member)
                )

            # Format confirmation message
            logger.debug("Formatting confirmation message")
            confirmation_message = UPGRADE_CONFIRMATION.format(
                member_name=member_name,
                current_tier=current_tier,
                next_tier=next_tier
            )

            # Send message with buttons
            self.state_manager.messaging.send_interactive(
                body=confirmation_message,
                buttons=[
                    Button(id="confirm", title="💫 Upgrade Tier 📈"),
                    Button(id="cancel", title="❌ No Thanks ❌")
                ]
            )
            self.set_awaiting_input(True)

        except Exception as e:
            logger.error(f"Error preparing confirmation: {str(e)}")
            raise ComponentException(
                message=f"Failed to prepare confirmation: {str(e)}",
                component=self.type,
                field="confirmation",
                value=str(e)
            )

    def handle_confirmation(self, value: bool) -> ValidationResult:
        """Handle member tier upgrade confirmation"""
        logger.info("Processing upgrade confirmation")

        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = current_data.get("incoming_message", {})

            # Validate interactive message
            if incoming_message.get("type") != "interactive":
                return ValidationResult.failure(
                    message="Please use the Upgrade or Cancel button",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get button info
            text = incoming_message.get("text", {})
            if text.get("interactive_type") != "button":
                return ValidationResult.failure(
                    message="Please use the Upgrade or Cancel button",
                    field="interactive_type",
                    details={"text": text}
                )

            # Check button ID
            button = text.get("button", {})
            button_id = button.get("id")

            logger.debug(f"Button ID: {button_id}")
            if button_id == "cancel":
                logger.info("Upgrade rejected")
                # Store confirmation status
                self.update_data({"confirmed": False})

                # Release input wait
                self.set_awaiting_input(False)
                return ValidationResult.success({"confirmed": False})

            if button_id != "confirm":
                return ValidationResult.failure(
                    message="Please use the Upgrade or Cancel button",
                    field="button",
                    details={"button": button}
                )

            # Get required data for upgrade
            dashboard = self.state_manager.get_state_value("dashboard", {})
            member_id = dashboard.get("member", {}).get("memberID")
            active_account_id = self.state_manager.get_state_value("active_account_id")

            if not all([member_id, active_account_id]):
                return ValidationResult.failure(
                    message="Missing required data for upgrade",
                    field="member_data",
                    details={
                        "member_id": bool(member_id),
                        "account_id": bool(active_account_id)
                    }
                )

            # Store confirmation status and required data
            logger.info("Upgrade confirmed")
            self.update_data({
                "confirmed": True,
                "member_id": member_id,
                "account_id": active_account_id
            })

            # Release input wait
            self.set_awaiting_input(False)
            return ValidationResult.success({
                "confirmed": True,
                "member_id": member_id,
                "account_id": active_account_id
            })

        except Exception as e:
            logger.error(f"Error processing confirmation: {str(e)}")
            return ValidationResult.failure(
                message=str(e),
                field="confirmation",
                details={
                    "component": self.type,
                    "error": str(e)
                }
            )

    def get_rejection_message(self) -> str:
        """Get message for when upgrade is rejected"""
        return "Member tier upgrade cancelled"

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified confirmation data"""
        return {
            "confirmed": value.get("confirmed", False),
            "member_id": value.get("member_id"),
            "account_id": value.get("account_id")
        }
