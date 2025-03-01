"""WhatsApp-specific flow processor implementation"""

import logging
from typing import Any, Dict

from core.error.exceptions import ComponentException
from core.flow.processor import FlowProcessor
from core.messaging.types import InteractiveType, MessageType

logger = logging.getLogger(__name__)


class WhatsAppFlowProcessor(FlowProcessor):
    """WhatsApp implementation of flow processor"""

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
                return {
                    "channel": channel_info,
                    "message": {
                        "type": MessageType.TEXT.value,
                        "text": {
                            "body": text_content.get("body", "")
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
