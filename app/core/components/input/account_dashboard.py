"""Account dashboard component

This component handles displaying the account dashboard with proper validation.
Also handles initial state setup after login.
"""

import logging
from typing import Any

from core.components.base import InputComponent
from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.messaging.types import InteractiveType, MessageType, Section

logger = logging.getLogger(__name__)

# Account template
ACCOUNT_DASHBOARD = """*💳 {account}*
💳 {handle}

*💰 Secured Balances*
💰 {secured_balances}

*📊 Net Assets*
📊 {net_assets}{tier_limit_display}{pending_offer_message}"""


class AccountDashboard(InputComponent):
    """Handles account dashboard display and initial state"""

    def __init__(self):
        super().__init__("account_dashboard")

    def validate_display(self, value: Any) -> ValidationResult:
        """Validate display and handle menu selection"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "account_dashboard"}
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
                        details={"component": "account_dashboard"}
                    )

                # Get active account ID set by flow
                active_account_id = self.state_manager.get_state_value("active_account_id")
                if not active_account_id:
                    return ValidationResult.failure(
                        message="No active account set",
                        field="active_account",
                        details={"component": "account_dashboard"}
                    )

                # Find active account
                accounts = dashboard.get("accounts", [])
                active_account = next(
                    (acc for acc in accounts if acc.get("accountID") == active_account_id),
                    None
                )
                if not active_account:
                    return ValidationResult.failure(
                        message="Active account not found",
                        field="accounts",
                        details={"component": "account_dashboard"}
                    )

                # Format header data
                account = active_account.get("accountName", "")
                handle = active_account.get("accountHandle", "")

                # Format secured balances
                secured_balances = active_account.get("balanceData", {}).get("securedNetBalancesByDenom", [])
                secured_balances_str = "\n💰 ".join(secured_balances) if secured_balances else "0.00 USD"

                # Format net assets
                try:
                    net_assets_str = active_account.get("balanceData", {}).get("netCredexAssetsInDefaultDenom", "0.00")
                    # Split into value and denomination
                    parts = net_assets_str.split()
                    if len(parts) == 2:
                        net_value = float(parts[0])
                        denom = parts[1]
                    else:
                        # If no denomination in string, use account default
                        net_value = float(net_assets_str)
                        denom = active_account.get("defaultDenom", "USD")
                    net_assets = f"  {net_value:.2f} {denom}"
                except (ValueError, TypeError, AttributeError):
                    net_assets = f"- 0.00 {active_account.get('defaultDenom', 'USD')}"

                # Format tier limit display
                member = dashboard.get("member", {})
                tier_limit_display = ""
                if member and member.get("memberTier", 0) < 3:
                    try:
                        amount_remaining = float(member.get("remainingAvailableUSD", "0.00"))
                        tier_limit_display = f"\n\n⏳ *Daily Open Tier Limit*\n⏳  {amount_remaining:.2f} USD"
                    except (ValueError, TypeError):
                        tier_limit_display = "\n\n⏳ *Daily Open Tier Limit*\n0.00 USD"

                # Get pending counts from active account
                pending_in = len(active_account.get("pendingInData", []))
                pending_out = len(active_account.get("pendingOutData", []))

                # Format pending offer message
                pending_offer_message = f"\n\n💸 {pending_in} offers to accept" if pending_in > 0 else ""

                # Format final display data
                formatted_data = {
                    "account": account,
                    "handle": handle,
                    "secured_balances": secured_balances_str,
                    "net_assets": net_assets,
                    "tier_limit_display": tier_limit_display,
                    "pending_offer_message": pending_offer_message
                }

                # Get account info text
                account_info = ACCOUNT_DASHBOARD.format(**formatted_data)

                logger.info(f"Active account pendingOutData in dashboard: {active_account.get('pendingOutData')}")
                logger.info(f"Pending out count: {pending_out}")

                # Define sections for menu options
                sections = []

                # Credex Actions section
                credex_options = []
                credex_options.append({"id": "offer_secured", "title": "💸 Offer Secured Credex 💸", "description": "Send a credex backed by currency or gold from your Secured Balances"})
                if pending_in > 0:
                    credex_options.append({"id": "accept_offer", "title": "✅ Accept Offers ✅", "description": f"You have {pending_in} offers waiting"})
                    credex_options.append({"id": "decline_offer", "title": "❌ Decline Offers ❌", "description": f"You have {pending_in} offers waiting"})
                if pending_out > 0:
                    credex_options.append({"id": "cancel_offer", "title": "🚫 Cancel Offers 🚫", "description": f"You have {pending_out} offers pending"})

                if credex_options:
                    sections.append(Section(
                        title="Credex Actions",
                        rows=credex_options
                    ))

                # Account Actions section
                account_options = []
                # Commented out for now
                # account_options.append({"id": "view_ledger", "title": "📊 View account ledger", "description": "View account ledger"})

                if account_options:
                    sections.append(Section(
                        title="Account Actions",
                        rows=account_options
                    ))

                # Member Actions section - only show if there are member actions
                member_options = []
                if member.get("memberTier") == 1:
                    member_options.append({"id": "upgrade_membertier", "title": "🌟 Hustler Tier 💫", "description": "$1/month *First 10,000 Hustlers: $1 for the first year* 🔥💥💥"})

                if member_options:
                    sections.append(Section(
                        title="Member Actions",
                        rows=member_options
                    ))

                try:
                    # Set component to await input before sending menu
                    self.set_awaiting_input(True)

                    # Pass properly structured menu data to messaging service
                    self.state_manager.messaging.send_interactive(
                        body=account_info,
                        sections=sections,
                        button_text="Actions 🪄"
                    )

                    return ValidationResult.success(formatted_data)
                except Exception as e:
                    raise ComponentException(
                        message=f"Failed to send menu message: {str(e)}",
                        component=self.type,
                        field="messaging",
                        value=str(account_info),
                        validation=self.validation_state
                    )

            # Input Phase - When we get a response
            component_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = component_data.get("incoming_message", {})

            # For interactive messages, extract selection ID
            if incoming_message.get("type") == MessageType.INTERACTIVE.value:
                text = incoming_message.get("text", {})
                if text.get("interactive_type") == InteractiveType.LIST.value:
                    selection = text.get("list_reply", {}).get("id")
                    if selection:
                        # Validate selection matches expected flow paths
                        valid_paths = [
                            "offer_secured",
                            "accept_offer",
                            "decline_offer",
                            "cancel_offer",
                            "view_ledger",
                            "upgrade_membertier"
                        ]
                        if selection in valid_paths:
                            # Tell headquarters which path to take and release input wait
                            self.set_result(selection)
                            self.set_awaiting_input(False)
                            return ValidationResult.success(True)

            # Invalid selection, return failure but stay on component
            return ValidationResult.failure(
                message="Invalid selection. Please choose from the available options.",
                field="selection",
                details={"component": self.type}
            )

        except Exception as e:
            return ValidationResult.failure(
                message=str(e),
                field="display",
                details={
                    "component": "account_dashboard",
                    "error": str(e)
                }
            )
