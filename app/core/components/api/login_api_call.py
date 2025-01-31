"""Login API call component

Handles the login flow for both new and existing members:
- For new users: Sets component_result="start_onboarding"
- For existing users: Sets component_result="send_dashboard"
"""

import logging
from typing import Any

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class LoginApiCall(ApiComponent):
    """Processes login API calls and manages member state"""

    def __init__(self):
        super().__init__("LoginApiCall")

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process login API call and set component_result for flow control"""
        try:
            # Get channel info
            channel = self.state_manager.get_state_value("channel")
            if not channel or not channel.get("identifier"):
                return ValidationResult.failure(
                    message="No channel identifier found",
                    field="channel",
                    details={"error": "missing_channel"}
                )

            logger.info(f"Making login API call for channel: {channel['identifier']}")

            # Make API call and inject response into state
            result = make_api_request(
                url="login",
                payload={"phone": channel["identifier"]},
                method="POST",
                retry_auth=False,
                state_manager=self.state_manager
            )

            # Process response
            result, error = handle_api_response(
                response=result,
                state_manager=self.state_manager
            )
            if error:
                return ValidationResult.failure(
                    message=f"Login failed: {error}",
                    field="api_call",
                    details={"error": error}
                )

            # Check action state to determine flow
            action = self.state_manager.get_state_value("action", {})
            if action.get("type") == "ERROR_NOT_FOUND":
                logger.info("New member detected - starting onboarding flow")
                # Tell headquarters to start onboarding
                self.set_result("start_onboarding")
                return ValidationResult.success(None)

            # For existing members, check tier and handle routing
            try:
                dashboard = self.state_manager.get_state_value("dashboard", {})
                member = dashboard.get("member", {})
                member_tier = member.get("memberTier")

                # For tier 5, show multi-account dashboard
                if member_tier == 5:
                    self.set_result("send_multi_dashboard")
                    return ValidationResult.success(result)

                # For other tiers, set personal account as active
                accounts = dashboard.get("accounts", [])
                personal_account = next(
                    (acc for acc in accounts if acc.get("accountType") == "PERSONAL"),
                    None
                )
                if not personal_account:
                    return ValidationResult.failure(
                        message="Login failed: No personal account found",
                        field="accounts",
                        details={"error": "missing_personal_account"}
                    )

                self.state_manager.update_state({
                    "active_account_id": personal_account["accountID"]
                })

                # Tell headquarters to show dashboard
                self.set_result("send_dashboard")
                return ValidationResult.success(result)
            except Exception as e:
                logger.error(f"Failed to process dashboard data: {e}")
                return ValidationResult.failure(
                    message="Login failed: Invalid dashboard data",
                    field="dashboard",
                    details={"error": str(e)}
                )

        except Exception as e:
            logger.error(f"Error in login API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Login failed: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )
