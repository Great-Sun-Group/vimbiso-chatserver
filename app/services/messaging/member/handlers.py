"""Member operation handlers using clean architecture patterns

Handlers coordinate between flows and services, managing state progression.
"""

import logging
from datetime import datetime
from typing import Any

from core.messaging.interface import MessagingServiceInterface
from core.messaging.types import Message, MessageRecipient
from core.utils.exceptions import FlowException, SystemException
from core.messaging.flow import initialize_flow
from core.utils.error_handler import ErrorHandler

from .flows import RegistrationFlow, UpgradeFlow

logger = logging.getLogger(__name__)


class MemberHandler:
    """Handler for member-related operations"""

    def __init__(self, messaging_service: MessagingServiceInterface):
        self.messaging = messaging_service
        self.registration = RegistrationFlow(messaging_service)
        self.upgrade = UpgradeFlow(messaging_service)

    def _get_recipient(self, state_manager: Any) -> MessageRecipient:
        """Get message recipient from state"""
        return MessageRecipient(
            channel_id=state_manager.get_channel_id(),
            member_id=state_manager.get("member_id")
        )

    def start_registration(self, state_manager: Any) -> Message:
        """Start registration flow with proper state initialization"""
        try:
            # Initialize flow with proper structure
            initialize_flow(
                state_manager=state_manager,
                flow_type="registration",
                initial_data={
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            # Get recipient and flow state
            recipient = self._get_recipient(state_manager)
            flow_state = state_manager.get_flow_state()

            # Get step content with progress
            step_content = self.registration.get_step_content("welcome")
            progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"

            # Send welcome message with progress
            return self.messaging.send_text(
                recipient=recipient,
                text=f"{step_content}\n\n{progress}"
            )

        except Exception as e:
            # Use enhanced error handling
            logger.error("Failed to start registration", extra={
                "error": str(e),
                "handler": "member",
                "action": "start_registration"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="member",
                action="start_registration",
                message="Failed to start registration",
                error=e
            )

            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def start_upgrade(self, state_manager: Any) -> Message:
        """Start upgrade flow with proper state initialization"""
        try:
            # Initialize flow with proper structure
            initialize_flow(
                state_manager=state_manager,
                flow_type="upgrade",
                initial_data={
                    "started_at": datetime.utcnow().isoformat()
                }
            )

            # Get recipient and flow state
            recipient = self._get_recipient(state_manager)
            flow_state = state_manager.get_flow_state()

            # Get step content with progress
            step_content = self.upgrade.get_step_content("confirm")
            progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"

            # Send confirmation message with progress
            return self.messaging.send_text(
                recipient=recipient,
                text=f"{step_content}\n\n{progress}"
            )

        except Exception as e:
            # Use enhanced error handling
            logger.error("Failed to start upgrade", extra={
                "error": str(e),
                "handler": "member",
                "action": "start_upgrade"
            })

            error_response = ErrorHandler.handle_system_error(
                code="FLOW_START_ERROR",
                service="member",
                action="start_upgrade",
                message="Failed to start upgrade",
                error=e
            )

            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

    def handle_flow_step(self, state_manager: Any, flow_type: str, step: str, input_value: Any) -> Message:
        """Handle flow step with proper error boundaries"""
        try:
            # Get flow state for context
            flow_state = state_manager.get_flow_state()
            if not flow_state:
                raise FlowException(
                    message="No active flow",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

            # Process step with proper flow
            if flow_type == "registration":
                result = self.registration.process_step(state_manager, step, input_value)
            elif flow_type == "upgrade":
                result = self.upgrade.process_step(state_manager, step, input_value)
            else:
                raise FlowException(
                    message=f"Invalid flow type: {flow_type}",
                    step=step,
                    action="handle_flow",
                    data={"flow_type": flow_type}
                )

            # Handle success with progress
            if not isinstance(result, FlowException):
                # Get updated flow state
                flow_state = state_manager.get_flow_state()
                if flow_state and "message" in result:
                    # Add progress to message
                    progress = f"Step {flow_state['step_index'] + 1} of {flow_state['total_steps']}"
                    result["message"] = f"{result['message']}\n\n{progress}"

            return result

        except FlowException as e:
            # Enhanced flow error handling
            error_response = ErrorHandler.handle_flow_error(
                step=e.step,
                action=e.action,
                data=e.data,
                message=str(e),
                flow_state=flow_state
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except SystemException as e:
            # Enhanced system error handling
            error_response = ErrorHandler.handle_system_error(
                code=e.code,
                service=e.service,
                action=e.action,
                message=str(e),
                error=e
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )

        except Exception as e:
            # Enhanced unexpected error handling
            error_response = ErrorHandler.handle_system_error(
                code="UNEXPECTED_ERROR",
                service="member",
                action="handle_flow",
                message=f"Unexpected error in {flow_type} flow",
                error=e
            )
            return self.messaging.send_text(
                recipient=self._get_recipient(state_manager),
                text=f"❌ {error_response['error']['message']}"
            )
