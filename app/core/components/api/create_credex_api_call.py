"""Create Credex API call component

Handles creating a new Credex offer through the API:
- Gets offer data from component_data.data (unvalidated)
- Creates new Credex offer via API
- Updates state with schema-validated dashboard data
"""
from ..base import ApiComponent

import logging
from typing import Any, Dict

from core.api.base import handle_api_response, make_api_request
from core.error.types import ValidationResult

logger = logging.getLogger(__name__)


class CreateCredexApiCall(ApiComponent):
    """Handles creating a new Credex offer and managing state"""

    def __init__(self):
        super().__init__("create_credex_api")
        self.state_manager = None

    def set_state_manager(self, state_manager: Any) -> None:
        """Set state manager for accessing offer data"""
        self.state_manager = state_manager

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process offer creation and update state with transaction tracking

        - Gets offer data (amount, handle) from flow state
        - Checks if a similar transaction has already been completed
        - Creates new Credex offer via API with idempotency key
        - Updates state with dashboard data via handle_api_response
        - Returns success status
        """
        # Get offer data from component data
        component_data = self.state_manager.get_state_value("component_data", {})
        offer_data = component_data.get("data", {})
        if not offer_data:
            return ValidationResult.failure(
                message="No offer data found",
                field="component_data.data",
                details={"component": self.type}
            )
        # Get and validate required fields
        amount = offer_data.get("amount")
        denom = offer_data.get("denom")

        if not amount or not denom:
            return ValidationResult.failure(
                message="Missing required offer fields",
                field="offer_data",
                details={
                    "component": self.type,
                    "missing_fields": {
                        "amount": not amount,
                        "denom": not denom
                    }
                }
            )

        # Get member data from dashboard
        dashboard = self.state_manager.get_state_value("dashboard")
        if not dashboard:
            return ValidationResult.failure(
                message="No dashboard data found",
                field="dashboard",
                details={"component": self.type}
            )

        member_id = dashboard.get("member", {}).get("memberID")
        if not member_id:
            return ValidationResult.failure(
                message="No member ID found in dashboard",
                field="member_id",
                details={"component": self.type}
            )

        # Get active account ID from state
        active_account_id = self.state_manager.get_state_value("active_account_id")
        if not active_account_id:
            return ValidationResult.failure(
                message="No active account selected",
                field="active_account",
                details={"component": self.type}
            )

        # Get recipient account ID from action state
        action = self.state_manager.get_state_value("action", {})
        recipient_account = action.get("details", {})
        if not recipient_account or not recipient_account.get("accountID"):
            return ValidationResult.failure(
                message="Missing recipient account details",
                field="action",
                details={"component": self.type}
            )

        # Create transaction data for deduplication
        transaction_data = {
            "amount": amount,
            "denom": denom,
            "issuer_account_id": active_account_id,
            "receiver_account_id": recipient_account.get("accountID"),
            "member_id": member_id,
            "credex_type": "PURCHASE",
            "offers_or_requests": "OFFERS",
            "secured_credex": True
        }

        # Check if this transaction has already been processed
        if self.state_manager.is_transaction_completed("create_credex", transaction_data):
            self.state_manager.messaging.send_text("✅ Secured credex already offered")
            self.update_data({})
            self.set_result("show_dashboard")
            return ValidationResult.success({
                "status": "success",
                "action": {"type": "CREDEX_CREATED"}
            })

        # Start a new transaction
        transaction_id = self.state_manager.start_transaction("create_credex", transaction_data)

        try:
            # Make API call
            url = "createCredex"
            payload = {
                "receiverAccountID": recipient_account["accountID"],
                "issuerAccountID": active_account_id,
                "Denomination": offer_data.get("denom"),
                "InitialAmount": amount,
                "credexType": "PURCHASE",
                "OFFERSorREQUESTS": "OFFERS",
                "securedCredex": True,
            }

            # Make request with idempotency key and store response
            response = make_api_request(
                url=url,
                payload=payload,
                state_manager=self.state_manager,
                idempotency_key=transaction_id
            )

            # Store response data in state
            response_data, error = handle_api_response(
                response=response,
                state_manager=self.state_manager
            )

            # Handle 403 error specifically
            if response.status_code == 403:
                error_message = response_data.get("message", "Failed to offer secured credex")
                self.state_manager.messaging.send_text(f"❌ {error_message}")
                self.update_data({})
                self.set_result("show_dashboard")

                # Mark transaction as failed
                self.state_manager.fail_transaction(transaction_id, error_message)

                return ValidationResult.success({
                    "status": "error",
                    "action": {"type": "ERROR_UNAUTHORIZED"}
                })

            # Validate response has required data
            if not response_data.get("data", {}).get("action", {}).get("type") == "CREDEX_CREATED":
                error_message = error or "Failed to offer secured credex"
                self.state_manager.messaging.send_text(f"❌ {error_message}")
                self.update_data({})
                self.set_result("show_dashboard")

                # Mark transaction as failed
                self.state_manager.fail_transaction(transaction_id, error_message)

                return ValidationResult.success({
                    "status": "error",
                    "action": {"type": "ERROR_FAILED"}
                })

            # Success case
            self.state_manager.messaging.send_text("✅ Secured credex offered")

            # Clear offer data after creation
            self.update_data({})

            # Tell headquarters to show dashboard
            self.set_result("show_dashboard")

            # Mark transaction as completed
            self.state_manager.complete_transaction(transaction_id, {
                "status": "success",
                "action": response_data.get("data", {}).get("action", {})
            })

            return ValidationResult.success({
                "status": "success" if action.get("type") == "CREDEX_CREATED" else "error",
                "action": action
            })

        except Exception as e:
            # Mark transaction as failed
            self.state_manager.fail_transaction(transaction_id, str(e))
            # Re-raise the exception
            raise

    def to_verified_data(self, value: Any) -> Dict:
        """Convert API response to verified data

        Note: Dashboard/action data is handled by handle_api_response.
        We just track creation status here.
        """
        return {
            "credex_created": value.get("status") == "success",
            "action_type": value.get("action", {}).get("type"),
            "action_id": value.get("action", {}).get("id")
        }
