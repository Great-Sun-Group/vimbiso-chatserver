"""WhatsApp-specific flow processor implementation"""

import logging
import re
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.flow.processor import FlowProcessor
from core.messaging.types import InteractiveType, MessageType
from .handlers.verify_otp_handler import VerifyOTPHandler

logger = logging.getLogger(__name__)


class WhatsAppFlowProcessor(FlowProcessor):
    """WhatsApp implementation of flow processor"""

    def __init__(self, messaging_service, state_manager):
        """Initialize with messaging service and state manager"""
        super().__init__(messaging_service, state_manager)
        # Initialize the VerifyOTPHandler
        self.verify_handler = VerifyOTPHandler()

    def process_message(self, payload: Dict[str, Any]) -> Any:
        """Process message through flow framework or direct handlers

        Args:
            payload: Raw message payload

        Returns:
            Any: Response message
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
            if not message:
                logger.debug("No valid message content")
                return None

            self.state_manager.set_incoming_message(message)

            # Check if this is a verification message
            if (message.get("type") == MessageType.TEXT.value and message.get("text", {}).get("is_verification", False)):

                logger.info("Handling verification message")
                message_text = message.get("text", {}).get("body", "")
                channel_id = self.state_manager.get_channel_id()

                # Process with VerifyOTPHandler - run async method in sync context
                import asyncio
                return asyncio.run(self.verify_handler.handle_message(message_text, channel_id, self.state_manager))

            # For non-verification messages, use the parent class implementation
            return super().process_message(payload)
        except Exception as e:
            logger.error(f"Error processing WhatsApp message: {str(e)}")
            raise

    def _extract_message_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from WhatsApp payload

        Args:
            payload: WhatsApp message payload

        Returns:
            Dict[str, Any]: Extracted message data

        Raises:
            ComponentException: If payload is invalid
        """
        if not payload:
            raise ComponentException(
                message="Message payload is required",
                component="whatsapp_flow_processor",
                field="payload",
                value=str(payload)
            )

        try:
            # Extract and validate each level
            entry = payload.get("entry", [])
            if not entry:
                raise ValueError("Missing entry array")

            changes = entry[0].get("changes", [])
            if not changes:
                raise ValueError("Missing changes array")

            value = changes[0].get("value", {})
            if not value:
                raise ValueError("Missing value object")

            # Skip non-message updates
            if "statuses" in value:
                return {}

            messages = value.get("messages", [])
            if not messages:
                return {}

            message = messages[0]
            if not message:
                return {}

            # Only process user-initiated messages
            if not message.get("from"):
                return {}

            # Get channel info from payload
            if not value.get("messaging_product") == "whatsapp":
                raise ValueError("Missing or invalid messaging product")

            # Get contact info
            contacts = value.get("contacts", [])
            if not contacts:
                raise ValueError("Missing contacts array")

            contact = contacts[0]
            if not contact or not isinstance(contact, dict):
                raise ValueError("Invalid contact object")

            channel_id = contact.get("wa_id")
            if not channel_id:
                raise ValueError("Missing WhatsApp ID")

            # Return channel info and message content separately
            channel_info = {
                "type": "whatsapp",
                "identifier": channel_id,
                "mock_testing": bool(value.get("metadata", {}).get("mock_testing", False))
            }

            # Check if message has already been processed
            message_id = message.get("id")
            if message_id and self.state_manager.is_message_processed(message_id):
                logger.info(f"Skipping already processed message: {message_id}")
                return {}

            # Mark message as processed to prevent duplicate processing
            if message_id:
                self.state_manager.mark_message_processed(message_id)

            # Extract message content
            message_type = message.get("type")
            if message_type == "text":
                # Handle text messages
                text_content = message.get("text", {})
                message_body = text_content.get("body", "")

                # Check if this is a verification message (starts with VERIFY)
                if re.match(r'^verify\s+', message_body, re.IGNORECASE):
                    logger.info("Detected OTP verification message")
                    # Mark it as a verification message
                    return {
                        "channel": channel_info,
                        "message": {
                            "type": MessageType.TEXT.value,
                            "text": {
                                "body": message_body,
                                "is_verification": True
                            },
                            "id": message_id
                        }
                    }

                # Regular text message
                return {
                    "channel": channel_info,
                    "message": {
                        "type": MessageType.TEXT.value,
                        "text": {
                            "body": message_body
                        },
                        "id": message_id
                    }
                }

            elif message_type == "interactive":
                # Handle interactive messages
                interactive = message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    button = interactive.get("button_reply", {})
                    return {
                        "channel": channel_info,
                        "message": {
                            "type": MessageType.INTERACTIVE.value,
                            "text": {
                                "interactive_type": InteractiveType.BUTTON.value,
                                "button": {
                                    "id": button.get("id"),
                                    "title": button.get("title"),
                                    "type": "reply"
                                }
                            },
                            "id": message_id
                        }
                    }

                elif interactive.get("type") == "list_reply":
                    list_reply = interactive.get("list_reply", {})
                    return {
                        "channel": channel_info,
                        "message": {
                            "type": MessageType.INTERACTIVE.value,
                            "text": {
                                "interactive_type": InteractiveType.LIST.value,
                                "list_reply": {
                                    "id": list_reply.get("id"),
                                    "title": list_reply.get("title"),
                                    "description": list_reply.get("description")
                                }
                            },
                            "id": message_id
                        }
                    }

            # Return empty dict for unsupported message types
            return {}

        except (IndexError, KeyError, ValueError) as e:
            # Get as much info as possible for error context
            value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
            messages = value.get("messages", [])
            message = messages[0] if messages else {}

            raise ComponentException(
                message=f"Invalid message payload format: {str(e)}",
                component="whatsapp_flow_processor",
                field="payload",
                value=str({
                    "error": str(e),
                    "payload": payload,
                    "value": value,
                    "message": message
                })
            )
