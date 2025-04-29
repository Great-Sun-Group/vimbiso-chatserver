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

            # Check if message has already been processed
            message_id = message.get("id")
            if message_id and self.state_manager.is_message_processed(message_id):
                logger.info(f"Skipping already processed message: {message_id}")
                return None

            # Mark message as processed to prevent duplicate processing
            if message_id:
                self.state_manager.mark_message_processed(message_id)

            self.state_manager.set_incoming_message(message)

            # Check if this is a verification message
            if (message.get("type") == MessageType.TEXT.value and message.get("text", {}).get("is_verification", False)):
                try:
                    logger.info("Handling verification message")
                    message_text = message.get("text", {}).get("body", "")
                    channel_id = self.state_manager.get_channel_id()

                    # Get OTP from message
                    import re
                    otp_match = re.search(r'verify\s+(\d+)', message_text, re.IGNORECASE)
                    if not otp_match:
                        # Send error response
                        error_msg = "Could not find a verification code in your message. Please send 'VERIFY' followed by your 6-digit code."
                        from services.whatsapp.types import WhatsAppMessage
                        return WhatsAppMessage.create_text(channel_id, f"❌ {error_msg}")

                    otp = otp_match.group(1).strip()

                    # Validate OTP format (6 digits)
                    if not otp.isdigit() or len(otp) != 6:
                        error_msg = "Invalid verification code format. Please send a 6-digit code."
                        from services.whatsapp.types import WhatsAppMessage
                        return WhatsAppMessage.create_text(channel_id, f"❌ {error_msg}")

                    # Use synchronous method instead of async
                    # This is a temporary fix - a better solution would be to make the entire flow async
                    import os

                    import requests

                    # Get API URL and key from environment
                    credex_api_url = os.getenv('MYCREDEX_APP_URL', 'https://dev.mycredex.dev')
                    api_key = os.getenv('CLIENT_API_KEY', '')

                    # Log environment variables for debugging
                    logger.info(f"Using MYCREDEX_APP_URL: {credex_api_url}")
                    logger.info(f"CLIENT_API_KEY set: {bool(api_key)}")

                    # Extract phone number from channel_id
                    phone = channel_id.replace('whatsapp:', '')

                    # Send verification request
                    endpoint = f"{credex_api_url}/verify/validateChatbotOtp"
                    headers = {
                        "Content-Type": "application/json",
                        "x-client-api-key": api_key
                    }
                    payload = {
                        "otp": otp,
                        "phone": phone,
                        "source": "chatbot"
                    }

                    logger.info(f"Sending OTP verification request to: {endpoint}")
                    logger.info(f"Request payload: {payload}")

                    try:
                        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
                        logger.info(f"Response status code: {response.status_code}")
                        logger.info(f"Response content: {response.text}")
                        response_data = response.json()
                        logger.info(f"Response data: {response_data}")
                    except Exception as e:
                        logger.error(f"Error making request to credex-core: {str(e)}")
                        raise

                    if response.status_code == 200:
                        logger.info("OTP verification successful")
                        from services.whatsapp.types import WhatsAppMessage
                        return WhatsAppMessage.create_text(
                            channel_id,
                            "✅ Verification successful! You can now return to the app."
                        )
                    else:
                        error_message = response_data.get("message", "Unknown error")
                        logger.error(f"OTP verification failed: {error_message}")
                        from services.whatsapp.types import WhatsAppMessage
                        return WhatsAppMessage.create_text(
                            channel_id,
                            f"❌ Verification failed: {error_message}"
                        )
                except Exception as e:
                    # Log the full exception for debugging
                    logger.exception(f"Error in verification flow: {str(e)}")
                    from services.whatsapp.types import WhatsAppMessage
                    return WhatsAppMessage.create_text(
                        channel_id,
                        "❌ An error occurred during verification. Please try again later."
                    )

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

            # Get message ID
            message_id = message.get("id")

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
