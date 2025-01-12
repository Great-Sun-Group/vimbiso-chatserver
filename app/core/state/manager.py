"""State management implementation

This module implements the StateManagerInterface with:
- Single source of truth
- Clear boundaries
- Simple validation
- Minimal nesting
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from core.error.exceptions import ComponentException
from core.error.handler import ErrorHandler
from core.error.types import ErrorContext
from core.messaging.interface import MessagingServiceInterface
from core.state.persistence.client import get_redis_client

from .atomic_manager import AtomicStateManager
from .interface import StateManagerInterface
from .validator import StateValidator

logger = logging.getLogger(__name__)


class StateManager(StateManagerInterface):
    """Manages state with clear boundaries"""

    def __init__(self, key_prefix: str):
        """Initialize state manager"""
        if not key_prefix or not key_prefix.startswith("channel:"):
            raise ComponentException(
                message="Invalid key prefix format",
                component="state_manager",
                field="key_prefix",
                value=str(key_prefix)
            )

        self.key_prefix = key_prefix
        redis_client = get_redis_client()
        self.atomic_state = AtomicStateManager(redis_client)
        self._state = self._initialize_state()
        self._messaging = None  # Will be set by MessagingService

    @property
    def messaging(self) -> MessagingServiceInterface:
        """Get messaging service with validation"""
        if self._messaging is None:
            raise ComponentException(
                message="Messaging service not initialized",
                component="state_manager",
                field="messaging"
            )
        return self._messaging

    @messaging.setter
    def messaging(self, service: MessagingServiceInterface) -> None:
        """Set messaging service"""
        self._messaging = service

    def _initialize_state(self) -> Dict[str, Any]:
        """Initialize state structure"""
        # Start with empty initial state
        initial_state = {}

        # Get existing state
        state_data = None
        try:
            state_data = self.atomic_state.atomic_get(self.key_prefix)
        except Exception as e:
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_INIT_ERROR",
                    "service": "state_manager",
                    "action": "initialize",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )

        return state_data if state_data is not None else initial_state

    def initialize_channel(self, channel_type: str, channel_id: str, mock_testing: bool = False) -> None:
        """Initialize or update channel info"""
        updates = {
            "channel": {
                "type": channel_type,
                "identifier": channel_id
            },
            "mock_testing": mock_testing
        }

        # Validate and apply updates
        prepared_state = StateValidator.prepare_state_update(updates)
        new_state = {**self._state, **prepared_state}
        self.atomic_state.atomic_update(self.key_prefix, new_state)
        self._state = new_state

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with validation"""
        if not isinstance(updates, dict):
            raise ComponentException(
                message="Updates must be a dictionary",
                component="state_manager",
                field="updates",
                value=str(type(updates))
            )

        # Prevent channel modifications through normal updates
        if "channel" in updates:
            raise ComponentException(
                message="Channel can only be modified through initialize_channel",
                component="state_manager",
                field="channel",
                value=str(updates)
            )

        try:
            # Validate and apply updates
            prepared_state = StateValidator.prepare_state_update(updates)
            new_state = {**self._state, **prepared_state}
            self.atomic_state.atomic_update(self.key_prefix, new_state)
            self._state = new_state

        except Exception as e:
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_UPDATE_ERROR",
                    "service": "state_manager",
                    "action": "update",
                    "updates": list(updates.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )

    def _get(self, key: str) -> Any:
        """Internal method to get raw state value"""
        if not key or not isinstance(key, str):
            raise ComponentException(
                message="Key must be a non-empty string",
                component="state_manager",
                field="key",
                value=str(key)
            )

        return self._state.get(key)

    def get_state_value(self, key: str, default: Any = None) -> Any:
        """Get any state value with default handling"""
        try:
            value = self._get(key)
            return value if value is not None else default
        except Exception as e:
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_GET_ERROR",
                    "service": "state_manager",
                    "action": "get_value",
                    "key": key,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )
            return default

    def get_path(self) -> Optional[str]:
        """Get current flow path"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("path")

    def get_component(self) -> Optional[str]:
        """Get current component"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("component")

    def get_component_result(self) -> Optional[str]:
        """Get component result for flow branching"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("component_result")

    def is_awaiting_input(self) -> bool:
        """Check if component is waiting for input"""
        component_data = self.get_state_value("component_data", {})
        return component_data.get("awaiting_input", False)

    def get_incoming_message(self) -> Optional[Dict[str, Any]]:
        """Get current incoming message if it exists"""
        try:
            component_data = self.get_state_value("component_data", {})
            message = component_data.get("incoming_message")

            # Validate message structure if present
            if message:
                test_update = {
                    "component_data": {
                        "incoming_message": message
                    }
                }
                StateValidator.prepare_state_update(test_update)

            return message

        except Exception as e:
            logger.error(f"Error getting incoming message: {str(e)}")
            return None

    def set_incoming_message(self, message: Dict[str, Any]) -> None:
        """Set the incoming message with validation"""
        if not isinstance(message, dict):
            raise ComponentException(
                message="Message must be a dictionary",
                component="state_manager",
                field="incoming_message",
                value=str(type(message))
            )

        try:
            current_data = self.get_state_value("component_data", {})
            updates = {
                "component_data": {
                    **current_data,
                    "incoming_message": message
                }
            }
            self.update_state(updates)

        except Exception as e:
            raise ComponentException(
                message=f"Failed to set incoming message: {str(e)}",
                component="state_manager",
                field="incoming_message",
                value=str(message)
            ) from e

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
            # Preserve existing component data if not provided
            if data is None:
                component_data = self.get_state_value("component_data", {})
                data = component_data.get("data", {})

            # Update state
            self.update_state({
                "component_data": {
                    "path": path,
                    "component": component,
                    "data": data,
                    "component_result": component_result,
                    "awaiting_input": awaiting_input
                }
            })

        except Exception as e:
            error_context = ErrorContext(
                error_type="flow",
                message=str(e),
                details={
                    "path": path,
                    "component": component,
                    "action": "update_current",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_flow_error(
                step=error_context.details["path"],
                action=error_context.details["action"],
                data={"component": error_context.details["component"]},
                message=error_context.message
            )

    def clear_component_data(self) -> None:
        """Clear component state including unvalidated data"""
        self.update_state({"component_data": None})

    def clear_all_state(self) -> None:
        """Clear all state data while preserving mock testing flag"""
        try:
            mock_testing = self.get_state_value("mock_testing", False)
            complete_state = {"mock_testing": mock_testing} if mock_testing else {}
            self._state = complete_state
            self.atomic_state.atomic_update(self.key_prefix, complete_state)

        except Exception as e:
            error_context = ErrorContext(
                error_type="system",
                message=str(e),
                details={
                    "code": "STATE_CLEAR_ERROR",
                    "service": "state_manager",
                    "action": "clear_all",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            ErrorHandler.handle_system_error(
                code=error_context.details["code"],
                service=error_context.details["service"],
                action=error_context.details["action"],
                message=error_context.message,
                error=e
            )

    def get_channel_id(self) -> str:
        """Get channel identifier"""
        channel = self.get_state_value("channel", {})
        if not channel.get("identifier"):
            raise ComponentException(
                message="Channel identifier not found",
                component="state_manager",
                field="channel.identifier",
                value=str(channel)
            )
        return channel["identifier"]

    def get_channel_type(self) -> str:
        """Get channel type"""
        channel_type = self.get_state_value("channel", {}).get("type")
        if not channel_type:
            raise ComponentException(
                message="Channel type not found",
                component="state_manager",
                field="channel.type"
            )
        return channel_type

    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token"""
        try:
            auth = self.get_state_value("auth", {})
            dashboard = self.get_state_value("dashboard", {})
            jwt_token = auth.get("token")

            if not dashboard.get("member_id") or not jwt_token:
                return False

            from decouple import config
            from jwt import InvalidTokenError, decode
            try:
                decode(jwt_token, config("JWT_SECRET"), algorithms=["HS256"])
                return True
            except InvalidTokenError:
                return False

        except Exception:
            return False

    def get_member_id(self) -> Optional[str]:
        """Get member ID if authenticated"""
        if not self.is_authenticated():
            return None

        dashboard = self.get_state_value("dashboard", {})
        return dashboard.get("member_id")

    def is_mock_testing(self) -> bool:
        """Check if mock testing mode is enabled for this request"""
        return bool(self.get_state_value("mock_testing"))