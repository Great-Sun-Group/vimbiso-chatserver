"""WhatsApp messaging service implementation"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from core.messaging.base import BaseMessagingService
from core.messaging.exceptions import MessageValidationError
from core.messaging.types import (Button, InteractiveContent, InteractiveType,
                                  Message, MessageType, Section, TemplateContent,
                                  TextContent)
from core.state.interface import StateManagerInterface
from decouple import config

from .types import WhatsAppMessage

logger = logging.getLogger(__name__)


class WhatsAppMessagingService(BaseMessagingService):
    """WhatsApp implementation of messaging service"""

    def __init__(self):
        """Initialize WhatsApp messaging service"""
        super().__init__()
        self.state_manager: Optional[StateManagerInterface] = None  # Will be set by MessagingService
        self._mock_testing: bool = False  # Internal mock testing state

    def set_mock_testing(self, mock_testing: bool) -> None:
        """Set mock testing mode"""
        self._mock_testing = mock_testing

    @classmethod
    def wrap_text(
        cls,
        message: str,
        channel_identifier: str,  # Channel identifier from state as SINGLE SOURCE OF TRUTH
        proceed_option: bool = False,
        x_is_menu: bool = False,
        navigate_is: str = "Respond",
        extra_rows: List = [],
        use_buttons: bool = False,
        yes_or_no: bool = False,
        custom: Dict = dict(),
        plain: bool = False,
        include_menu: bool = True,
    ) -> Dict:
        """Wrap text message with WhatsApp formatting"""
        if use_buttons:
            rows = [
                {"type": "reply", "reply": {"id": "N", "title": "❌ No"}},
                {"type": "reply", "reply": {"id": "Y", "title": "✅ Yes"}},
            ]
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel_identifier,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": message},
                    "action": {
                        "buttons": (
                            [
                                {
                                    "type": "reply",
                                    "reply": (
                                        custom
                                        if custom
                                        else {
                                            "id": "X",
                                            "title": (
                                                "🏡 Menu" if x_is_menu else "❌ Cancel"
                                            ),
                                        }
                                    ),
                                }
                            ]
                            if not yes_or_no
                            else rows
                        )
                    },
                },
            }

        if len(message) > 1024 or plain:
            return {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": channel_identifier,
                "type": "text",
                "text": {"body": message},
            }

        rows = extra_rows

        sections = []
        control_rows = []

        # Add any extra rows as a section if provided
        if extra_rows:
            # Ensure each row has required fields
            validated_rows = []
            for row in extra_rows:
                if "id" in row and "title" in row:
                    validated_row = {
                        "id": row["id"],
                        "title": row["title"]
                    }
                    if "description" in row:
                        validated_row["description"] = row["description"]
                    validated_rows.append(validated_row)

            if validated_rows:
                sections.append({
                    "title": "Actions",
                    "rows": validated_rows
                })

        # Add proceed option if requested
        if proceed_option:
            control_rows.append({
                "id": "Y",
                "title": "✅ Continue",
                "description": "Proceed with the current action"
            })

        # Add menu option if requested
        if include_menu:
            control_rows.append({
                "id": "X",
                "title": "🏡 Menu",
                "description": "Return to main menu"
            })

        # Add control section if we have control rows
        if control_rows:
            sections.append({
                "title": "Control",
                "rows": control_rows
            })

        # Build the message
        message_data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": channel_identifier,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": message},
                "action": {
                    "button": f"🕹️ {navigate_is}",
                    "sections": sections
                }
            }
        }

        # Add footer if we have sections
        if sections:
            message_data["interactive"]["footer"] = {
                "text": "Choose an option from the list"
            }

        return message_data

    def _is_mock_mode(self, message: Message = None) -> bool:
        """Check if service is in mock testing mode"""
        # First check internal mock testing state
        if self._mock_testing:
            return True

        # Then check message metadata for direct sends
        if message and message.metadata and message.metadata.get("mock_testing"):
            return True

        # Default to production mode
        return False

    def send_message(self, message: Message) -> Message:
        """Send a message through WhatsApp Cloud API or mock"""
        try:
            # Convert to WhatsApp format using state if available
            whatsapp_message = WhatsAppMessage.from_core_message(
                message,
                state_manager=self.state_manager
            )

            # Log basic info - full payload not needed since we're async
            logger.info("Sending %s message to %s",
                        message.content.type,
                        message.recipient.identifier)

            # Determine mock mode from state or message metadata
            handler = (
                self._handle_mock_send if self._is_mock_mode(message)
                else self._handle_production_send
            )
            return handler(message, whatsapp_message)

        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise MessageValidationError(
                message=f"Failed to send message: {str(e)}",
                service="whatsapp",
                action="send_message",
                validation_details={
                    "error": str(e),
                    "message_type": message.content.type if message and message.content else None
                }
            )

    def _handle_mock_send(self, message: Message, whatsapp_message: Dict) -> Message:
        """Handle mock message sending path"""
        logger.info("Mock mode: sending to mock server")

        try:
            # Send and wait for response
            response = requests.post(
                "http://mock:8001/bot/webhook",
                json=whatsapp_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            # Track when sent and response
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "mock": True,
                "status_code": response.status_code
            }

            # Try to parse response
            try:
                response_data = response.json()
                message.metadata["response"] = response_data

                # Check if response indicates success
                if response.status_code != 200 or not response_data.get("messaging_product"):
                    logger.error(f"Mock server error response: {response_data}")
                    raise MessageValidationError(
                        message="Mock server returned error response",
                        service="whatsapp",
                        action="send_message",
                        validation_details={
                            "status_code": response.status_code,
                            "response": response_data
                        }
                    )
            except Exception as e:
                message.metadata["response"] = response.text
                logger.error(f"Error parsing mock response: {str(e)}")
                raise MessageValidationError(
                    message=f"Failed to parse mock response: {str(e)}",
                    service="whatsapp",
                    action="send_message",
                    validation_details={
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )

            return message

        except Exception as e:
            # Log error and include in metadata
            logger.warning("Mock server request failed: %s", e)
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "mock": True,
                "error": str(e)
            }
            return message

    def _handle_production_send(self, message: Message, whatsapp_message: Dict) -> Message:
        """Handle production message sending path"""
        logger.info("Production mode: sending to WhatsApp")

        # Get API configuration
        phone_number_id = config("WHATSAPP_PHONE_NUMBER_ID")
        business_id = config("WHATSAPP_BUSINESS_ID")
        api_url = config("WHATSAPP_API_URL", default="https://graph.facebook.com/v22.0/")
        url = f"{api_url}{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {config('WHATSAPP_ACCESS_TOKEN')}",
            "Content-Type": "application/json",
            "X-Business-Id": business_id  # Add business ID for v22.0 authentication
        }

        try:
            # Send and wait for response
            response = requests.post(
                url,
                json=whatsapp_message,
                headers=headers,
                timeout=10
            )

            # Track when sent and response
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "status_code": response.status_code
            }

            # Try to parse response and validate
            try:
                response_data = response.json()
                message.metadata["response"] = response_data

                # Validate WhatsApp API response format
                if response.status_code != 200:
                    logger.error(f"WhatsApp API error response: {response_data}")
                    raise MessageValidationError(
                        message="WhatsApp API returned error response",
                        service="whatsapp",
                        action="send_message",
                        validation_details={
                            "status_code": response.status_code,
                            "response": response_data
                        }
                    )

                # Check for required success indicators
                if not response_data.get("messaging_product") == "whatsapp":
                    logger.error(f"Invalid messaging product in response: {response_data}")
                    raise MessageValidationError(
                        message="Invalid messaging product in WhatsApp response",
                        service="whatsapp",
                        action="send_message",
                        validation_details={
                            "response": response_data
                        }
                    )

                # Check for message ID indicating successful queuing
                messages = response_data.get("messages", [])
                if not messages or not messages[0].get("id"):
                    logger.error(f"No message ID in response: {response_data}")
                    raise MessageValidationError(
                        message="No message ID in WhatsApp response",
                        service="whatsapp",
                        action="send_message",
                        validation_details={
                            "response": response_data
                        }
                    )

                return message

            except MessageValidationError:
                raise
            except Exception as e:
                message.metadata["response"] = response.text
                logger.error(f"Error parsing WhatsApp response: {str(e)}")
                raise MessageValidationError(
                    message=f"Failed to parse WhatsApp response: {str(e)}",
                    service="whatsapp",
                    action="send_message",
                    validation_details={
                        "status_code": response.status_code,
                        "response": response.text
                    }
                )

        except Exception as e:
            # Log error and include in metadata
            logger.warning("WhatsApp API request failed: %s", e)
            message.metadata = {
                "sent_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            return message

    def send_text(
        self,
        text: str,
        preview_url: bool = False
    ) -> Message:
        """Send a text message"""
        # Validate text content
        if not isinstance(text, str):
            raise MessageValidationError(
                message="Invalid text content type",
                service="whatsapp",
                action="send_text",
                validation_details={
                    "error": "invalid_type",
                    "expected": "str",
                    "received": type(text).__name__
                }
            )

        # Create message with just content
        message = Message(
            content=TextContent(body=text, preview_url=preview_url)
        )
        return self.send_message(message)

    def send_interactive(
        self,
        body: str,
        buttons: Optional[List[Button]] = None,
        sections: Optional[List[Dict[str, Any]]] = None,
        header: Optional[str] = None,
        footer: Optional[str] = None,
        button_text: Optional[str] = None
    ) -> Message:
        """Send an interactive message following WhatsApp Cloud API format"""
        # Import WhatsApp limits
        from .types import WhatsAppMessage
        LIMITS = WhatsAppMessage.LIMITS

        # Validate and truncate body text
        if len(body) > LIMITS["text_body"]:
            body = body[:LIMITS["text_body"]]

        # Validate and truncate header/footer
        if header and len(header) > LIMITS["header"]:
            header = header[:LIMITS["header"]]
        if footer and len(footer) > LIMITS["footer"]:
            footer = footer[:LIMITS["footer"]]

        # Validate button text for list messages
        if button_text and len(button_text) > LIMITS["button_text"]:
            button_text = button_text[:LIMITS["button_text"]]

        # Validate buttons and sections are mutually exclusive
        if buttons and sections:
            raise MessageValidationError(
                message="Cannot specify both buttons and sections",
                service="whatsapp",
                action="send_interactive",
                validation_details={
                    "error": "invalid_params",
                    "detail": "buttons and sections are mutually exclusive"
                }
            )

        interactive_type = InteractiveType.BUTTON if buttons else InteractiveType.LIST

        if buttons:
            # Validate and process buttons
            validated_buttons = []
            for button in buttons[:LIMITS["buttons_count"]]:  # Limit number of buttons
                title = button.title[:LIMITS["button_text"]] if len(button.title) > LIMITS["button_text"] else button.title
                validated_buttons.append(Button(id=button.id, title=title))

            message = Message(
                content=InteractiveContent(
                    interactive_type=interactive_type,
                    body=body,
                    buttons=validated_buttons,
                    sections=[],  # Empty sections for button messages
                    header=header,
                    footer=footer
                )
            )

        elif sections:
            # Validate and process sections
            validated_sections = []
            for section in sections[:LIMITS["sections_count"]]:  # Limit number of sections
                # Validate section title
                title = section["title"][:LIMITS["list_title"]] if len(section["title"]) > LIMITS["list_title"] else section["title"]

                # Validate and process rows
                validated_rows = []
                for row in section["rows"][:LIMITS["rows_per_section"]]:  # Limit rows per section
                    # Validate row title and description
                    row_title = row["title"][:LIMITS["list_title"]]
                    row_desc = row.get("description", "")
                    if row_desc:
                        row_desc = row_desc[:LIMITS["list_description"]]

                    validated_row = {
                        "id": row["id"],
                        "title": row_title
                    }
                    if row_desc:
                        validated_row["description"] = row_desc

                    validated_rows.append(validated_row)

                validated_sections.append(Section(
                    title=title,
                    rows=validated_rows
                ))

            message = Message(
                content=InteractiveContent(
                    interactive_type=interactive_type,
                    body=body,
                    buttons=[],  # Empty buttons for list messages
                    sections=validated_sections,
                    button_text=button_text or "Select",
                    header=header,
                    footer=footer
                )
            )

        else:
            raise MessageValidationError(
                message="Either buttons or sections must be provided",
                service="whatsapp",
                action="send_interactive",
                validation_details={
                    "error": "missing_content",
                    "detail": "interactive message requires buttons or sections"
                }
            )

        return self.send_message(message)

    def send_template(
        self,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Send template message through WhatsApp"""
        try:
            # Create template message with just content
            message = Message(
                content=TemplateContent(
                    name=template_name,
                    language=language,
                    components=components or []
                )
            )
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error sending template {template_name}: {str(e)}")
            raise MessageValidationError(
                message=f"Failed to send template: {str(e)}",
                service="whatsapp",
                action="send_template",
                validation_details={
                    "error": str(e),
                    "template_name": template_name,
                    "language": language
                }
            )

    def extract_message_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message data from WhatsApp payload"""
        if not payload:
            raise MessageValidationError(
                message="Message payload is required",
                service="whatsapp",
                action="extract_message",
                validation_details={"error": "missing_payload"}
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

            # Check if this is a status update
            if "statuses" in value:
                return {}

            # Check for messages
            messages = value.get("messages", [])
            if not messages:
                return {}

            message = messages[0]
            if not message:
                return {}

            # Only process user-initiated messages
            if not message.get("from"):
                return {}

            # Validate this is a WhatsApp message
            if not value.get("messaging_product") == "whatsapp":
                raise ValueError("Expected messaging_product 'whatsapp'")

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

            # Extract message content
            message_type = message.get("type")
            if message_type == "text":
                # Handle text messages
                text_content = message.get("text", {})
                return {
                    "channel": {
                        "type": "whatsapp",
                        "identifier": channel_id,
                        "mock_testing": bool(value.get("metadata", {}).get("mock_testing", False))
                    },
                    "message": {
                        "type": MessageType.TEXT.value,
                        "text": {
                            "body": text_content.get("body", "")
                        }
                    }
                }
            elif message_type == "interactive":
                # Handle interactive messages
                interactive = message.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    button = interactive.get("button_reply", {})
                    return {
                        "channel": {
                            "type": "whatsapp",
                            "identifier": channel_id,
                            "mock_testing": bool(value.get("metadata", {}).get("mock_testing", False))
                        },
                        "message": {
                            "type": MessageType.INTERACTIVE.value,
                            "text": {
                                "interactive_type": InteractiveType.BUTTON.value,
                                "button": {
                                    "id": button.get("id"),
                                    "title": button.get("title"),
                                    "type": "reply"
                                }
                            }
                        }
                    }
                elif interactive.get("type") == "list_reply":
                    list_reply = interactive.get("list_reply", {})
                    return {
                        "channel": {
                            "type": "whatsapp",
                            "identifier": channel_id,
                            "mock_testing": bool(value.get("metadata", {}).get("mock_testing", False))
                        },
                        "message": {
                            "type": MessageType.INTERACTIVE.value,
                            "text": {
                                "interactive_type": InteractiveType.LIST.value,
                                "list_reply": {
                                    "id": list_reply.get("id"),
                                    "title": list_reply.get("title"),
                                    "description": list_reply.get("description")
                                }
                            }
                        }
                    }

            # Unsupported message type
            return {}

        except (IndexError, KeyError, ValueError) as e:
            # Get as much info as possible for error context
            value = payload.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
            messages = value.get("messages", [])
            message = messages[0] if messages else {}

            raise MessageValidationError(
                message=f"Invalid message payload format: {str(e)}",
                service="whatsapp",
                action="extract_message",
                validation_details={
                    "error": str(e),
                    "payload": payload,
                    "value": value,
                    "message": message
                }
            )
