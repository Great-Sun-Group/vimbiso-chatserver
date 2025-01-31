"""Multi-account dashboard component

This component handles displaying the multi-account dashboard for memberTier=5 users.
Allows selection of accounts to transition into specific account flows.
"""

import logging
from typing import Any

from core.components.base import InputComponent
from core.error.types import ValidationResult
from core.messaging.types import InteractiveType, MessageType, Section

logger = logging.getLogger(__name__)

# Multi-account template
MULTI_ACCOUNT_DASHBOARD = """*👋 Hie {firstname}*"""


class MultiAccountDashboard(InputComponent):
    """Handles multi-account dashboard display and account selection"""

    def __init__(self):
        super().__init__("multi_account_dashboard")

    def validate_display(self, value: Any) -> ValidationResult:
        """Validate display and handle account selection"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "multi_account_dashboard"}
            )

        try:
            # Display Phase - When not awaiting input
            if not self.state_manager.is_awaiting_input():
                # Get and validate dashboard data
                dashboard = self.state_manager.get_state_value("dashboard")
                if not dashboard:
                    return ValidationResult.failure(
                        message="No dashboard data found",
                        field="dashboard",
                        details={"component": "multi_account_dashboard"}
                    )

                # Get member info
                member = dashboard.get("member", {})
                firstname = member.get("firstname", "")

                # Get accounts
                accounts = dashboard.get("accounts", [])
                if not accounts:
                    return ValidationResult.failure(
                        message="No accounts found",
                        field="accounts",
                        details={"component": "multi_account_dashboard"}
                    )

                # Format header with member name
                header = MULTI_ACCOUNT_DASHBOARD.format(firstname=firstname)

                # Create account selection options
                account_options = []
                for account in accounts:
                    if account.get("isOwnedAccount"):
                        account_id = account.get("accountID")
                        account_name = account.get("accountName", "")
                        account_handle = account.get("accountHandle", "")

                        # WhatsApp's 24 char limit for title
                        # "💳 " takes 4 chars, leaving 20 chars
                        max_name_length = 20
                        truncated_handle = (
                            account_handle[:max_name_length]
                            if len(account_handle) > max_name_length
                            else account_handle
                        )

                        # Get net assets in default denomination
                        net_assets = account.get("balanceData", {}).get("netCredexAssetsInDefaultDenom", "0.00")

                        try:
                            # Build concise description (under 72 chars)
                            description = f"{account_name}: {net_assets}"
                        except Exception as e:
                            logger.error(f"Failed to build description: {str(e)}")
                            # Provide a fallback description
                            description = f"Type: {account.get('accountType')}"

                        account_options.append({
                            "id": account_id,
                            "title": f"💳 {truncated_handle}",
                            "description": description
                        })

                if not account_options:
                    return ValidationResult.failure(
                        message="No owned accounts found",
                        field="accounts",
                        details={"component": "multi_account_dashboard"}
                    )

                # Create sections for menu
                sections = [
                    Section(
                        title="Your Accounts",
                        rows=account_options
                    )
                ]

                try:
                    # Set component to await input before sending menu
                    self.set_awaiting_input(True)

                    # Send interactive menu
                    self.state_manager.messaging.send_interactive(
                        body=header,
                        sections=sections,
                        button_text="Select Account 💳"
                    )

                    return ValidationResult.success(True)
                except Exception as e:
                    return ValidationResult.failure(
                        message=f"Failed to send menu message: {str(e)}",
                        field="display",
                        details={
                            "component": "multi_account_dashboard",
                            "error": str(e),
                            "type": "validation"
                        }
                    )

            # Input Phase - When we get a response
            component_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = component_data.get("incoming_message", {})

            # For interactive messages, extract selection ID
            if incoming_message.get("type") == MessageType.INTERACTIVE.value:
                text = incoming_message.get("text", {})
                if text.get("interactive_type") == InteractiveType.LIST.value:
                    selected_account_id = text.get("list_reply", {}).get("id")
                    if selected_account_id:
                        # Set the selected account as active
                        self.state_manager.update_state({
                            "active_account_id": selected_account_id
                        })
                        # Tell headquarters to transition to account dashboard
                        self.set_result("account_selected")
                        self.set_awaiting_input(False)
                        return ValidationResult.success(True)

            # Invalid selection, return failure but stay on component
            return ValidationResult.failure(
                message="Invalid selection. Please choose an account from the list.",
                field="selection",
                details={"component": self.type}
            )

        except Exception as e:
            return ValidationResult.failure(
                message=str(e),
                field="display",
                details={
                    "component": "multi_account_dashboard",
                    "error": str(e)
                }
            )
