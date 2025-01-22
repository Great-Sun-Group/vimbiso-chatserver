"""Flow processor for handling message flows through components.

This module handles the complete flow processing lifecycle:
1. Takes channel input and prepares for flow
2. Manages state through schema validation
3. Processes through components (which can store unvalidated data)
4. Converts results to messages

The flow processor is channel-agnostic and works with any messaging service
that implements the MessagingServiceInterface. All state updates are protected
by schema validation except for component_data.data which gives components
freedom to store their own data.
"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.error.handler import ErrorHandler
from core.error.types import ValidationResult
from core.messaging.service import MessagingService
from core.messaging.types import Message, MessageType, TextContent
from core.messaging.utils import get_recipient
from core.state.interface import StateManagerInterface

from .constants import GREETING_COMMANDS
from .component_manager import process_component

logger = logging.getLogger(__name__)


class FlowProcessor:
    """Processes messages through the flow framework"""

    def __init__(self, messaging_service: MessagingService, state_manager: StateManagerInterface):
        """Initialize with messaging service and state manager

        Args:
            messaging_service: Channel-agnostic messaging service
            state_manager: State manager instance
        """
        self.messaging = messaging_service
        self.state_manager = state_manager
        # Ensure bidirectional relationship is set up
        if not hasattr(state_manager, 'messaging') or state_manager.messaging is None:
            state_manager.messaging = messaging_service

    def process_message(self, payload: Dict[str, Any]) -> Message:
        """Process message through flow framework

        Args:
            payload: Raw message payload

        Returns:
            Message: Response message
        """
        try:
            # Extract message data using channel-specific implementation
            extracted_data = self._extract_message_data(payload)
            if not extracted_data:
                logger.debug("No valid message data extracted")
                return None

            # Initialize channel state
            channel_info = extracted_data.get("channel")
            if channel_info:
                self.state_manager.initialize_channel(
                    channel_type=channel_info["type"],
                    channel_id=channel_info["identifier"],
                    mock_testing=channel_info.get("mock_testing", False)
                )

            # Set message in state
            message = extracted_data.get("message")
            if message:
                self.state_manager.set_incoming_message(message)
            else:
                logger.debug("No valid message content")
                return None

            # Get existing state before processing any message
            current_state = self.state_manager.get_state_value("component_data")

            # Get message type
            message_type = message.get("type", "")

            # Process based on message type
            if message_type == MessageType.TEXT.value:
                message_text = message.get("text", {}).get("body", "").lower().strip()
                if not message_text:
                    logger.debug("No valid message text to process")
                    return None
            elif message_type == MessageType.INTERACTIVE.value:
                # Interactive messages (like button clicks) are always valid
                message_text = "interactive"  # Placeholder for flow control
            else:
                logger.debug(f"Unsupported message type: {message_type}")
                return None

            # For greetings, always start fresh
            if message_type == MessageType.TEXT.value and message_text in GREETING_COMMANDS:
                try:
                    # Preserve channel and message info
                    channel_type = self.state_manager.get_channel_type()
                    channel_id = self.state_manager.get_channel_id()
                    current_message = self.state_manager.get_incoming_message()

                    # Clear all state (mock_testing is preserved)
                    self.state_manager.clear_all_state()

                    # Reinitialize channel with preserved info
                    self.state_manager.initialize_channel(
                        channel_type=channel_type,
                        channel_id=channel_id
                    )

                    # Restore message and start login flow
                    if current_message:
                        self.state_manager.set_incoming_message(current_message)

                    # Start login flow through headquarters
                    self.state_manager.transition_flow(
                        path="login",
                        component="Greeting"
                    )

                    # Get updated state after initialization
                    current_state = self.state_manager.get_state_value("component_data")
                    if not current_state:
                        logger.error("Failed to initialize component state")
                        return None

                except Exception as e:
                    logger.error(f"Failed to initialize state: {str(e)}")
                    return None
            # If no state and not a greeting, trigger login flow
            elif not current_state:
                logger.debug("No state found - triggering login flow")
                try:
                    # Initialize channel with preserved info
                    channel_type = self.state_manager.get_channel_type()
                    channel_id = self.state_manager.get_channel_id()
                    current_message = self.state_manager.get_incoming_message()

                    # Clear all state (mock_testing is preserved)
                    self.state_manager.clear_all_state()

                    # Reinitialize channel
                    self.state_manager.initialize_channel(
                        channel_type=channel_type,
                        channel_id=channel_id
                    )

                    # Restore message
                    if current_message:
                        self.state_manager.set_incoming_message(current_message)

                    # Start login flow through headquarters
                    self.state_manager.transition_flow(
                        path="login",
                        component="Greeting"
                    )

                    # Get updated state after initialization
                    current_state = self.state_manager.get_state_value("component_data")
                    if not current_state:
                        logger.error("Failed to initialize component state")
                        return None

                except Exception as e:
                    logger.error(f"Failed to initialize state: {str(e)}")
                    return None

            context = current_state.get("path")
            component = current_state.get("component")

            # Process components until awaiting input or failure
            while True:
                logger.info(f"Processing component: {context}.{component}")
                logger.info(f"Current state: {current_state}")
                logger.info(f"Awaiting input: {self.state_manager.is_awaiting_input()}")

                # Process current component
                next_step = process_component(context, component, self.state_manager, depth=0)
                result = self.state_manager.get_component_result()

                logger.info(f"Component processing complete. Next step: {next_step}")
                logger.info(f"Component result: {result}")
                logger.info(f"Awaiting input: {self.state_manager.is_awaiting_input()}")

                # Handle component failure
                if next_step is None:
                    logger.error(f"Component failed: {context}.{component}")
                    return None

                # Handle validation error
                if isinstance(result, ValidationResult) and not result.valid:
                    content = TextContent(body=result.error.get("message", "Validation failed"))
                    return Message(content=content)

                # Get next step
                next_context, next_component = next_step
                if next_context != context or next_component != component:
                    # Log state transition
                    logger.info(f"Flow transition: {context}.{component} -> {next_context}.{next_component}")

                    # Get current component data
                    component_data = self.state_manager.get_state_value("component_data", {})
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Current flow state: {component_data}")

                    # Transition to next component
                    self.state_manager.transition_flow(
                        path=next_context,
                        component=next_component
                    )

                    # Update for next iteration - process_component will handle activation
                    context = next_context
                    component = next_component
                    current_state = self.state_manager.get_state_value("component_data")
                else:
                    # No state change - return
                    return None

        except ComponentException as e:
            # Handle component errors with validation state
            error_response = ErrorHandler.handle_component_error(
                component=e.details["component"],
                field=e.details["field"],
                value=e.details["value"],
                message=str(e),
                validation_state=e.details.get("validation")
            )
            recipient = get_recipient(self.state_manager)
            content = TextContent(body=error_response["error"]["message"])
            return Message(content=content, recipient=recipient)

        except Exception as e:
            # Handle system errors
            error_response = ErrorHandler.handle_system_error(
                code="FLOW_ERROR",
                service="flow_processor",
                action="process_message",
                message=str(e),
                error=e
            )
            recipient = get_recipient(self.state_manager)
            content = TextContent(body=error_response["error"]["message"])
            return Message(content=content, recipient=recipient)

    def _extract_message_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from payload

        This method should be overridden by channel-specific processors
        to handle channel-specific payload formats.

        Args:
            payload: Raw message payload

        Returns:
            Dict[str, Any]: Extracted message data including:
                - type: Message type
                - text: Message text data
                - channel_type: Channel type string ("whatsapp" or "sms")
                - channel_id: Channel identifier string (e.g. phone number)

        Raises:
            ComponentException: If payload is invalid
        """
        raise NotImplementedError("Channel-specific processors must implement _extract_message_data")
