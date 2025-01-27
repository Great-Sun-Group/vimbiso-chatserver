"""Handle input component

This component handles Credex handle input with proper validation.
"""

from typing import Any

from core.error.types import ValidationResult

from ..base import InputComponent

# Handle prompt template
HANDLE_PROMPT = "*💳 What's the account handle❓*"


class HandleInput(InputComponent):
    """Handle input with pure UI validation"""

    def __init__(self):
        super().__init__("handle_input")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate handle format only

        Only checks basic format requirements:
        - Must be string
        - Must not be empty
        - Must be <= 30 chars

        Business validation (availability etc) happens in service layer
        """
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        incoming_message = current_data.get("incoming_message")

        # Initial activation - send prompt
        if not current_data.get("awaiting_input"):
            self.state_manager.messaging.send_text(
                text=HANDLE_PROMPT
            )
            self.set_awaiting_input(True)
            return ValidationResult.success(None)

        # Process input
        if not incoming_message:
            return ValidationResult.success(None)

        # Get text from message
        if not isinstance(incoming_message, dict):
            return ValidationResult.failure(
                message="Expected text message",
                field="type",
                details={"message": incoming_message}
            )

        text = incoming_message.get("text", {}).get("body", "")
        if not text:
            return ValidationResult.failure(
                message="No text provided",
                field="text",
                details={"message": incoming_message}
            )

        # Validate basic format
        handle = text.strip()
        if not handle:
            return ValidationResult.failure(
                message="Handle required",
                field="handle"
            )

        if len(handle) > 30:
            return ValidationResult.failure(
                message="Handle too long (max 30 chars)",
                field="handle",
                details={"length": len(handle)}
            )

        # Store validated handle
        self.update_data({"handle": handle})

        # Keep awaiting input if there's a validation error in state
        api_response = self.state_manager.get_state_value("action", {})
        if api_response.get("type") == "ERROR_VALIDATION":
            error_details = api_response.get("details", {})
            if error_details.get("field") == "accountHandle":
                self.state_manager.messaging.send_text(
                    text=f"❌ {error_details.get('reason')}\n\n{HANDLE_PROMPT}"
                )
                self.set_awaiting_input(True)
                return ValidationResult.success(None)

        # Release input wait if no validation error
        self.set_awaiting_input(False)
        return ValidationResult.success(None)  # Signal to move to next component
