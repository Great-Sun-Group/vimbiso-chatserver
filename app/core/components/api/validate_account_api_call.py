"""Validate account API call component

Validates account exists and gets account details:
- Validates account via API
- handle_api_response stores details in state.action
- Returns success/failure based on action type
"""
import logging
from typing import Any, Dict

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

from ..base import ApiComponent


class ValidateAccountApiCall(ApiComponent):
    """Validates account exists and gets details"""

    def __init__(self):
        super().__init__("validate_account_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing account data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Validate account exists and get details

        Makes API call to validate account and stores details in state:
        1. Calls getAccountByHandle endpoint
        2. handle_api_response stores account details in state.action
        3. Verifies ACCOUNT_FOUND action type
        4. Returns success/failure with appropriate error details

        Args:
            value: Ignored - handle is always retrieved from component_data

        Returns:
            ValidationResult with:
            - success(None) if account found
            - failure with error details for:
              - ERROR_VALIDATION (invalid handle format)
              - ERROR_NOT_FOUND (account doesn't exist)
              - Other errors (API/internal errors)
        """
        logger = logging.getLogger(__name__)

        # Get handle from component data
        component_data = self.state_manager.get_state_value("component_data", {})
        handle = component_data.get("data", {}).get("handle")
        if not handle:
            return ValidationResult.failure(
                message="No handle provided",
                field="handle",
                details={"component": self.type}
            )

        logger.info(f"Validating account handle: {handle}")

        # Make API call
        logger.debug("Making API call to getAccountByHandle")
        url = "getAccountByHandle"
        payload = {
            "accountHandle": handle
        }

        # Make request and let handle_api_response store action in state
        response = make_api_request(
            url=url,
            payload=payload,
            state_manager=self.state_manager
        )

        # Let handle_api_response store action in state
        logger.debug("Processing API response")
        response_data, error = handle_api_response(
            response=response,
            state_manager=self.state_manager
        )

        if error:
            return ValidationResult.failure(
                message=f"Account validation failed: {error}",
                field="api_call",
                details={"error": error}
            )

        # Get action from response and verify account found
        data = response_data.get("data", {})
        action = data.get("action", {})
        action_type = action.get("type")
        logger.debug(f"Checking action type: {action_type}")
        logger.debug(f"Response data: {response_data}")
        logger.debug(f"Action data: {action}")
        logger.debug(f"Account data: {data.get('account')}")

        # Check for validation error
        if action_type == "ERROR_VALIDATION":
            details = action.get("details", {})
            return ValidationResult.failure(
                message=f"Invalid account handle: {details.get('reason')}",
                field=details.get("field", "handle"),
                details={"error": "INVALID_HANDLE"}
            )

        # Check for not found error
        if action_type == "ERROR_NOT_FOUND":
            # Send friendly error message
            self.state_manager.messaging.send_text(
                text="❌ Oops, that 💳accountHandle doesn't exist. Please try again."
            )
            # Clear invalid handle but preserve other data like amount
            component_data = self.state_manager.get_state_value("component_data", {})
            data = component_data.get("data", {})
            data["handle"] = None
            self.update_data({"data": data})

            # Return to handle input component
            self.set_result("return_to_handle")
            self.set_awaiting_input(False)

            return ValidationResult.failure(
                message="Account not found",
                field="handle",
                details={"error": "ACCOUNT_NOT_FOUND", "retry": True}
            )

        # Check for success
        if action_type != "ACCOUNT_FOUND":
            return ValidationResult.failure(
                message="Account validation failed",
                field="api_call",
                details={"action_type": action_type}
            )

        # Success - account details are in state.action.details
        return ValidationResult.success(None)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Account details are handled by handle_api_response.
        We just track validation status here.
        """
        return {
            "validated": True  # We only get here on success
        }
