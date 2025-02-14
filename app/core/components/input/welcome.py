"""Welcome component for registration flow

This component handles the registration welcome screen.
"""

from typing import Any

from core.error.types import ValidationResult
from core.messaging.types import Button

from core.components.base import InputComponent

# Registration template
REGISTER = """Welcome to VimbisoPay 💰

We're your portal 🚪to the credex ecosystem 🌱

Become a member 🌐 and open a free account 💳 to get started 📈"""


class Welcome(InputComponent):
    """Handles registration welcome screen"""

    def __init__(self):
        super().__init__("welcome")

    def validate_display(self, value: Any) -> ValidationResult:
        """Validate become_member button press

        Args:
            value: None for initial activation, or incoming message for button validation
        """
        try:
            # Get current state
            current_data = self.state_manager.get_state_value("component_data", {})
            incoming_message = current_data.get("incoming_message")

            # Initial activation - send welcome message
            if not current_data.get("awaiting_input"):
                self.state_manager.messaging.send_interactive(
                    body=REGISTER,
                    buttons=[Button(
                        id="become_member",
                        title="Become a Member"
                    )]
                )
                self.set_awaiting_input(True)
                return ValidationResult.success(None)

            # Process button press
            if not incoming_message:
                return ValidationResult.success(None)

            # Validate it's an interactive button message
            if incoming_message.get("type") != "interactive":
                return ValidationResult.failure(
                    message="Expected interactive message",
                    field="type",
                    details={"message": incoming_message}
                )

            # Get button info
            text = incoming_message.get("text", {})
            if text.get("interactive_type") != "button":
                return ValidationResult.failure(
                    message="Expected button response",
                    field="interactive_type",
                    details={"text": text}
                )

            # Check button ID
            button = text.get("button", {})
            if button.get("id") != "become_member":
                return ValidationResult.failure(
                    message="Invalid response - please click the Become a Member button",
                    field="button",
                    details={"button": button}
                )

            # Valid button press - allow flow to progress
            self.set_awaiting_input(False)
            return ValidationResult.success(None)

        except Exception as e:
            return ValidationResult.failure(
                message=str(e),
                field="welcome",
                details={
                    "component": self.type,
                    "error": str(e),
                    "state": self.state_manager.get_state_value("component_data", {})
                }
            )
