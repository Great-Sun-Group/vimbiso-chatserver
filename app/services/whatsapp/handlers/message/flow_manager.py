"""Flow initialization and management"""
import logging
from typing import Any, Dict, Optional, Tuple

from core.messaging.flow import Flow
from core.utils.flow_audit import FlowAuditLogger
from ...types import WhatsAppMessage
from ...state_manager import StateManager
from ..credex import CredexFlow
from ..member import RegistrationFlow, UpgradeFlow

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class FlowManager:
    """Handles flow initialization and management"""

    def __init__(self, service: Any):
        self.service = service

    def _get_member_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract member and account IDs from state"""
        try:
            state = self.service.user.state.state or {}
            member_id = state.get("member_id")
            account_id = state.get("account_id")
            return member_id, account_id
        except Exception as e:
            logger.error(f"Error extracting member info: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "member_info_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return None, None

    def initialize_flow(self, flow_type: str, flow_class: Any, **kwargs) -> WhatsAppMessage:
        """Initialize a new flow"""
        try:
            # Log flow start attempt
            audit.log_flow_event(
                "bot_service",
                "flow_start_attempt",
                None,
                {
                    "flow_type": flow_type,
                    "flow_class": flow_class.__name__ if hasattr(flow_class, '__name__') else str(flow_class),
                    **kwargs
                },
                "in_progress"
            )

            # Get member and account IDs
            member_id, account_id = self._get_member_info()
            if not member_id or not account_id:
                logger.error(f"Missing required IDs - member_id: {member_id}, account_id: {account_id}")
                return WhatsAppMessage.create_text(
                    self.service.user.mobile_number,
                    "Account not properly initialized. Please try sending 'hi' to restart."
                )

            # Prepare initial state
            initial_state = {
                "id": f"{flow_type}_{member_id}",
                "step": 0,
                "data": {
                    "phone": self.service.user.mobile_number,
                    "member_id": member_id,
                    "account_id": account_id,
                    "mobile_number": self.service.user.mobile_number,
                    "_validation_context": {},  # Initialize validation context
                    "_validation_state": {}     # Initialize validation state
                }
            }

            # Add pending offers for cancel flow
            if flow_type == "cancel":
                initial_state["data"]["pending_offers"] = self._get_pending_offers()

            # Initialize flow with state
            flow = self._create_flow(flow_type, flow_class, initial_state, **kwargs)
            flow.credex_service = self.service.credex_service

            # Get initial message
            result = flow.current_step.get_message(flow.data)

            # If result is a WhatsAppMessage, return it immediately
            if isinstance(result, WhatsAppMessage):
                return result

            # Update state only for non-WhatsAppMessage responses
            self._update_flow_state(flow, flow_type, flow_class, kwargs)

            audit.log_flow_event(
                "bot_service",
                "flow_start_success",
                None,
                {"flow_id": flow.id},
                "success"
            )

            return result

        except Exception as e:
            logger.error(f"Flow start error: {str(e)}")
            audit.log_flow_event(
                "bot_service",
                "flow_start_error",
                None,
                {"error": str(e)},
                "failure"
            )
            return WhatsAppMessage.create_text(
                self.service.user.mobile_number,
                f"❌ Failed to start flow: {str(e)}"
            )

    def _get_pending_offers(self) -> list:
        """Get pending offers from current account state"""
        current_state = self.service.user.state.state or {}
        current_account = current_state.get("current_account", {})
        pending_out = current_account.get("pendingOutData", [])

        return [{
            "id": offer.get("credexID"),
            "amount": offer.get("formattedInitialAmount", "0").lstrip("-"),
            "to": offer.get("counterpartyAccountName")
        } for offer in pending_out if all(
            offer.get(k) for k in ["credexID", "formattedInitialAmount", "counterpartyAccountName"]
        )]

    def _create_flow(self, flow_type: str, flow_class: Any, initial_state: Dict, **kwargs) -> Flow:
        """Create flow instance with proper initialization"""
        if flow_class in {RegistrationFlow, UpgradeFlow}:
            return flow_class(**kwargs)

        # Initialize flow with state
        flow_kwargs = kwargs.copy()  # Create a copy to avoid modifying original kwargs
        if flow_class == CredexFlow:
            flow_kwargs['flow_type'] = flow_type
        return flow_class(
            state=initial_state,
            **flow_kwargs
        )

    def _update_flow_state(self, flow: Flow, flow_type: str, flow_class: Any, kwargs: Dict):
        """Update state with flow data"""
        current_state = self.service.user.state.state or {}

        # Store the modified kwargs in state
        flow_kwargs = kwargs.copy()
        if flow_class == CredexFlow:
            flow_kwargs['flow_type'] = flow_type

        new_state = StateManager.prepare_state_update(
            current_state,
            flow_data={
                **flow.get_state(),
                "flow_type": flow_type,
                "kwargs": flow_kwargs
            },
            mobile_number=self.service.user.mobile_number
        )

        # Validate and update state
        error = StateManager.validate_and_update(
            self.service.user.state,
            new_state,
            current_state,
            "flow_start",
            self.service.user.mobile_number
        )
        if error:
            raise ValueError(f"State update failed: {error}")
