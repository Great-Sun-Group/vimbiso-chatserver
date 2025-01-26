"""Upgrade member tier API call component

Handles upgrading a member's tier through the API:
- Gets required data from state (member, account)
- Makes API call to upgrade tier
- Updates state with response
- Sets component_result for flow control
"""

import logging
from typing import Any, Dict, Optional, Tuple

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

from ..base import ApiComponent

logger = logging.getLogger(__name__)


class UpgradeMembertierApiCall(ApiComponent):
    """Processes member tier upgrade and manages state"""

    def __init__(self):
        super().__init__("upgrade_membertier_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing state data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process member tier upgrade and update state"""
        # Validate state manager is set
        if not self.state_manager:
            return ValidationResult.failure(
                message="State manager not set",
                field="state_manager",
                details={"component": "upgrade_membertier_api"}
            )

        try:
            # Get confirmation data from component_data
            component_data = self.state_manager.get_state_value("component_data", {})
            confirmation_data = component_data.get("data", {})
            if not confirmation_data:
                return ValidationResult.failure(
                    message="No confirmation data found",
                    field="component_data.data",
                    details={"component": self.type}
                )

            # Get and validate required fields
            member_id = confirmation_data.get("member_id")
            if not member_id:
                return ValidationResult.failure(
                    message="Missing member ID",
                    field="member_id",
                    details={"component": self.type}
                )

            logger.info(
                f"Creating tier 3 subscription for member {member_id}"
            )

            # Make API call
            result = self._make_api_call(member_id)
            if not result.valid:
                return result

            # Clear confirmation data after successful operation
            self.update_data({})

            # Process response and update state
            return self._process_response(result.value)

        except Exception as e:
            logger.error(f"Error in upgrade member tier API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to upgrade member: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _get_required_data(self) -> Tuple[Optional[str], Optional[int]]:
        """Get required data from state"""
        try:
            # Get member data from dashboard
            dashboard = self.state_manager.get_state_value("dashboard", {})
            member = dashboard.get("member", {})
            member_id = member.get("memberID")
            current_tier = member.get("memberTier")

            return member_id, current_tier

        except Exception as e:
            logger.error(f"Error getting required data: {str(e)}")
            return None, None

    def _make_api_call(self, member_id: str) -> ValidationResult:
        """Make API call to create tier 3 subscription"""
        try:
            # Get source account ID from state
            source_account_id = self.state_manager.get_state_value("active_account_id")
            if not source_account_id:
                return ValidationResult.failure(
                    message="No active account selected",
                    field="api_call",
                    details={"error": "Missing active_account_id in state"}
                )

            # Construct proper payload dictionary
            payload = {
                "personalAccountID": source_account_id
            }

            response = make_api_request(
                url="hustler10k",
                payload=payload,
                method="POST",
                state_manager=self.state_manager
            )

            # Process response
            try:
                result, error = handle_api_response(
                    response=response,
                    state_manager=self.state_manager
                )
                if error:
                    logger.error(f"Failed to create tier 3 subscription: {error}")
                    return ValidationResult.failure(
                        message=f"Failed to create subscription: {error}",
                        field="api_call",
                        details={"error": error}
                    )
            except AttributeError as e:
                # Handle case where response is not properly structured
                logger.error(f"Invalid API response structure: {str(e)}")
                return ValidationResult.failure(
                    message="Invalid API response received",
                    field="api_call",
                    details={"error": str(e)}
                )

            return ValidationResult.success(result)

        except Exception as e:
            logger.error(f"Error making API call: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to upgrade member tier: {str(e)}",
                field="api_call",
                details={"error": str(e)}
            )

    def _process_response(self, response: Dict) -> ValidationResult:
        """Process API response and update state"""
        try:
            # Get action from state after API call
            action = self.state_manager.get_state_value("action", {})
            action_type = action.get("type")

            # Handle different action types and errors
            if action_type == "HUSTLER_10K_ENROLLED":
                logger.info("Tier 3 subscription created successfully")
                self.state_manager.messaging.send_text("Hustle hard 💥")
            elif action_type == "RECURRING_CREATED":
                logger.info("Tier 3 subscription created successfully")
                self.state_manager.messaging.send_text("Hustle hard 💥")
            elif action_type == "ERROR_VALIDATION":
                error_details = action.get("details", {})
                error_code = error_details.get("code")
                error_reason = error_details.get("reason", "Unknown error occurred")

                if error_code == "INSUFFICIENT_SECURED_BALANCE":
                    logger.info(f"Insufficient balance for upgrade: {error_reason}")
                    self.state_manager.messaging.send_text(
                        f"❌ Unable to upgrade: {error_reason}\n\n"
                        "💡 Please ensure you have sufficient secured balance before trying again."
                    )
                else:
                    logger.error(f"Validation error during upgrade: {error_reason}")
                    self.state_manager.messaging.send_text(f"❌ Failed to upgrade member tier: {error_reason}")
            elif action_type == "ERROR":
                error_message = action.get("details", {}).get("message", "Unknown error occurred")
                logger.error(f"Upgrade failed with error: {error_message}")
                self.state_manager.messaging.send_text(f"❌ Failed to upgrade member tier: {error_message}")
            else:
                logger.warning(f"Unexpected action type: {action_type}")
                self.state_manager.messaging.send_text("❌ Failed to upgrade member tier - please try again later")

            # Tell headquarters to return to dashboard
            self.set_result("send_dashboard")

            # Get tier info from action details
            details = action.get("details", {})
            previous_tier = details.get("previousTier")
            new_tier = details.get("newTier")

            return ValidationResult.success({
                "action": action,
                "upgraded": action_type in ["HUSTLER_10K_ENROLLED", "RECURRING_CREATED"],
                "previous_tier": previous_tier,
                "new_tier": new_tier
            })

        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return ValidationResult.failure(
                message=f"Failed to process response: {str(e)}",
                field="response",
                details={"error": str(e)}
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Dashboard/action data is handled by handle_api_response.
        We just track upgrade status here.
        """
        return {
            "upgrade_complete": value.get("upgraded", False),
            "previous_tier": value.get("previous_tier"),
            "new_tier": value.get("new_tier"),
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
