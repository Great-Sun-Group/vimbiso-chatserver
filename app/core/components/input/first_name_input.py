"""First name input component

This component handles first name input with proper validation.
"""

from typing import Any, Dict

from core.components.base import InputComponent
from core.error.types import ValidationResult


class FirstNameInput(InputComponent):
    """First name input with validation"""

    def __init__(self):
        super().__init__("firstname_input")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate first name with proper tracking"""
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        incoming_message = current_data.get("incoming_message")

        # Initial activation - send prompt
        if not current_data.get("awaiting_input"):
            self.state_manager.messaging.send_text(
                text="""🔥 Excellent, let's get you signed up.

🌞 What's your first name?"""
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

        # Validate length
        firstname = text.strip()
        if len(firstname) < 3 or len(firstname) > 50:
            return ValidationResult.failure(
                message="First name must be between 3 and 50 characters",
                field="firstname",
                details={
                    "min_length": 3,
                    "max_length": 50,
                    "actual_length": len(firstname)
                }
            )

        # Store validated firstname for subsequent components
        self.update_data({"firstname": firstname})

        # Release input wait
        self.set_awaiting_input(False)
        return ValidationResult.success(firstname)

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified first name"""
        return {
            "firstname": value.strip()
        }
