"""WhatsApp state management delegating to core StateManager"""
import logging
from typing import Any, Dict, Optional

from core.error.exceptions import SystemException
from core.messaging.interface import MessagingServiceInterface
from core.state.interface import StateManagerInterface
from core.state.manager import StateManager as CoreStateManager

logger = logging.getLogger(__name__)


class StateManager(StateManagerInterface):  # type: ignore
    """WhatsApp state management delegating to core StateManager"""

    def __init__(self, state_manager: CoreStateManager):
        """Initialize with core state manager"""
        if not state_manager:
            raise SystemException(
                message="Core state manager is required: state_manager is None",
                code="STATE_INIT_ERROR",
                service="whatsapp_state",
                action="initialize"
            )

        if not isinstance(state_manager, CoreStateManager):
            raise SystemException(
                message=f"Invalid core state manager type: expected {CoreStateManager.__name__}, got {type(state_manager).__name__}",
                code="STATE_INIT_ERROR",
                service="whatsapp_state",
                action="initialize"
            )

        self._core = state_manager

    @property
    def messaging(self) -> MessagingServiceInterface:
        """Get messaging service"""
        try:
            return self._core.messaging
        except Exception as e:
            raise SystemException(
                message=f"Failed to get messaging service: {str(e)}",
                code="MESSAGING_ERROR",
                service="whatsapp_state",
                action="get_messaging"
            )

    @messaging.setter
    def messaging(self, service: MessagingServiceInterface) -> None:
        """Set messaging service"""
        try:
            self._core.messaging = service
        except Exception as e:
            raise SystemException(
                message=f"Failed to set messaging service: {str(e)}",
                code="MESSAGING_ERROR",
                service="whatsapp_state",
                action="set_messaging"
            )

    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get state value using core state manager"""
        try:
            return self._core.get_state_value(key, default)
        except Exception as e:
            raise SystemException(
                message=f"Failed to get state value for key {key}: {str(e)}",
                code="STATE_GET_ERROR",
                service="whatsapp_state",
                action="get_state"
            )

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state using core state manager"""
        try:
            self._core.update_state(updates)
        except Exception as e:
            raise SystemException(
                message=f"Failed to update state with keys {list(updates.keys())}: {str(e)}",
                code="STATE_UPDATE_ERROR",
                service="whatsapp_state",
                action="update_state"
            )

    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        try:
            return self._core.get_path()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get flow path: {str(e)}",
                code="FLOW_PATH_ERROR",
                service="whatsapp_state",
                action="get_path"
            )

    def get_component(self) -> Optional[str]:
        """Get current component"""
        try:
            return self._core.get_component()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get component: {str(e)}",
                code="FLOW_COMPONENT_ERROR",
                service="whatsapp_state",
                action="get_component"
            )

    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        try:
            return self._core.get_component_result()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get component result: {str(e)}",
                code="FLOW_RESULT_ERROR",
                service="whatsapp_state",
                action="get_component_result"
            )

    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        try:
            return self._core.is_awaiting_input()
        except Exception as e:
            raise SystemException(
                message=f"Failed to check awaiting input: {str(e)}",
                code="FLOW_INPUT_ERROR",
                service="whatsapp_state",
                action="is_awaiting_input"
            )

    def set_component_result(self, result: Optional[str]) -> None:
        """Set component result for flow branching"""
        try:
            self._core.set_component_result(result)
        except Exception as e:
            raise SystemException(
                message=f"Failed to set component result: {str(e)}",
                code="FLOW_RESULT_ERROR",
                service="whatsapp_state",
                action="set_component_result"
            )

    def set_component_awaiting(self, awaiting: bool) -> None:
        """Set component's awaiting input state"""
        try:
            self._core.set_component_awaiting(awaiting)
        except Exception as e:
            raise SystemException(
                message=f"Failed to set awaiting input: {str(e)}",
                code="FLOW_INPUT_ERROR",
                service="whatsapp_state",
                action="set_component_awaiting"
            )

    def update_component_data(self, data: Dict) -> None:
        """Update component's data"""
        try:
            self._core.update_component_data(data)
        except Exception as e:
            raise SystemException(
                message=f"Failed to update component data: {str(e)}",
                code="FLOW_DATA_ERROR",
                service="whatsapp_state",
                action="update_component_data"
            )

    def transition_flow(self, path: str, component: str) -> None:
        """Transition flow to new path/component.
        ONLY used by flow processor for managing transitions."""
        try:
            self._core.transition_flow(path, component)
        except Exception as e:
            raise SystemException(
                message=f"Failed to transition flow to {path}.{component}: {str(e)}",
                code="FLOW_TRANSITION_ERROR",
                service="whatsapp_state",
                action="transition_flow"
            )

    def update_flow_state(
        self,
        path: str,
        component: str,
        data: Optional[Dict] = None,
        component_result: Optional[str] = None,
        awaiting_input: bool = False
    ) -> None:
        """Update flow state including path and component"""
        try:
            self._core.update_flow_state(
                path=path,
                component=component,
                data=data,
                component_result=component_result,
                awaiting_input=awaiting_input
            )
        except Exception as e:
            raise SystemException(
                message=f"Failed to update flow state for {path}.{component}: {str(e)}",
                code="FLOW_STATE_UPDATE_ERROR",
                service="whatsapp_state",
                action="update_flow_state"
            )

    def clear_component_data(self) -> None:
        """Clear flow/component state"""
        try:
            self._core.clear_component_data()
        except Exception as e:
            raise SystemException(
                message=f"Failed to clear component data: {str(e)}",
                code="STATE_CLEAR_ERROR",
                service="whatsapp_state",
                action="clear_component_data"
            )

    def clear_all_state(self) -> None:
        """Clear all state data except channel info"""
        try:
            self._core.clear_all_state()
        except Exception as e:
            raise SystemException(
                message=f"Failed to clear all state: {str(e)}",
                code="STATE_CLEAR_ERROR",
                service="whatsapp_state",
                action="clear_all_state"
            )

    def get_channel_id(self) -> str:
        """Get channel identifier"""
        try:
            return self._core.get_channel_id()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get channel ID: {str(e)}",
                code="CHANNEL_ERROR",
                service="whatsapp_state",
                action="get_channel_id"
            )

    def get_channel_type(self) -> str:
        """Get channel type as string (e.g. "whatsapp", "sms")"""
        try:
            return self._core.get_channel_type()  # Returns ChannelType enum
        except Exception as e:
            raise SystemException(
                message=f"Failed to get channel type: {str(e)}",
                code="CHANNEL_ERROR",
                service="whatsapp_state",
                action="get_channel_type"
            )

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        try:
            return self._core.is_authenticated()
        except Exception as e:
            raise SystemException(
                message=f"Failed to check authentication: {str(e)}",
                code="AUTH_ERROR",
                service="whatsapp_state",
                action="is_authenticated"
            )

    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated"""
        try:
            return self._core.get_member_id()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get member ID: {str(e)}",
                code="AUTH_ERROR",
                service="whatsapp_state",
                action="get_member_id"
            )

    def is_mock_testing(self) -> bool:
        """Check if mock testing mode is enabled"""
        try:
            return self._core.is_mock_testing()
        except Exception as e:
            raise SystemException(
                message=f"Failed to check mock testing mode: {str(e)}",
                code="STATE_ERROR",
                service="whatsapp_state",
                action="is_mock_testing"
            )

    # Transaction tracking methods

    def start_transaction(self, transaction_type: str, data: Dict[str, Any]) -> str:
        """Start a new transaction with unique ID"""
        try:
            return self._core.start_transaction(transaction_type, data)
        except Exception as e:
            raise SystemException(
                message=f"Failed to start transaction: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="start_transaction"
            )

    def update_transaction(self, transaction_id: str, status: str, result: Dict[str, Any] = None) -> None:
        """Update transaction status"""
        try:
            self._core.update_transaction(transaction_id, status, result)
        except Exception as e:
            raise SystemException(
                message=f"Failed to update transaction: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="update_transaction"
            )

    def complete_transaction(self, transaction_id: str, result: Dict[str, Any] = None) -> None:
        """Mark transaction as completed"""
        try:
            self._core.complete_transaction(transaction_id, result)
        except Exception as e:
            raise SystemException(
                message=f"Failed to complete transaction: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="complete_transaction"
            )

    def fail_transaction(self, transaction_id: str, error: str) -> None:
        """Mark transaction as failed"""
        try:
            self._core.fail_transaction(transaction_id, error)
        except Exception as e:
            raise SystemException(
                message=f"Failed to fail transaction: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="fail_transaction"
            )

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID"""
        try:
            return self._core.get_transaction(transaction_id)
        except Exception as e:
            raise SystemException(
                message=f"Failed to get transaction: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="get_transaction"
            )

    def find_similar_transaction(self, transaction_type: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a similar transaction by type and data"""
        try:
            return self._core.find_similar_transaction(transaction_type, data)
        except Exception as e:
            raise SystemException(
                message=f"Failed to find similar transaction: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="find_similar_transaction"
            )

    def is_transaction_completed(self, transaction_type: str, data: Dict[str, Any]) -> bool:
        """Check if a similar transaction has been completed"""
        try:
            return self._core.is_transaction_completed(transaction_type, data)
        except Exception as e:
            raise SystemException(
                message=f"Failed to check if transaction is completed: {str(e)}",
                code="TRANSACTION_ERROR",
                service="whatsapp_state",
                action="is_transaction_completed"
            )

    # Message tracking methods

    def is_message_processed(self, message_id: str) -> bool:
        """Check if a message has already been processed"""
        try:
            return self._core.is_message_processed(message_id)
        except Exception as e:
            raise SystemException(
                message=f"Failed to check if message is processed: {str(e)}",
                code="MESSAGE_TRACKING_ERROR",
                service="whatsapp_state",
                action="is_message_processed"
            )

    def mark_message_processed(self, message_id: str) -> None:
        """Mark a message as processed"""
        try:
            self._core.mark_message_processed(message_id)
        except Exception as e:
            raise SystemException(
                message=f"Failed to mark message as processed: {str(e)}",
                code="MESSAGE_TRACKING_ERROR",
                service="whatsapp_state",
                action="mark_message_processed"
            )

    def get_incoming_message(self) -> Optional[Dict[str, Any]]:
        """Get current incoming message if it exists"""
        try:
            return self._core.get_incoming_message()
        except Exception as e:
            raise SystemException(
                message=f"Failed to get incoming message: {str(e)}",
                code="MESSAGE_ERROR",
                service="whatsapp_state",
                action="get_incoming_message"
            )

    def set_incoming_message(self, message: Dict[str, Any]) -> None:
        """Set the incoming message with validation"""
        try:
            self._core.set_incoming_message(message)
        except Exception as e:
            raise SystemException(
                message=f"Failed to set incoming message: {str(e)}",
                code="MESSAGE_ERROR",
                service="whatsapp_state",
                action="set_incoming_message"
            )

    def initialize_channel(self, channel_type: str, channel_id: str, mock_testing: bool = False) -> None:
        """Initialize or update channel info"""
        try:
            self._core.initialize_channel(channel_type, channel_id, mock_testing)
        except Exception as e:
            raise SystemException(
                message=f"Failed to initialize channel: {str(e)}",
                code="CHANNEL_ERROR",
                service="whatsapp_state",
                action="initialize_channel"
            )
