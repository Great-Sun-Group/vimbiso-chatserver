"""Amount input component

This component handles amount input with proper validation.
"""

from typing import Any, Dict, Set

from core.error.types import ValidationResult

from ..base import InputComponent

# Valid denominations
VALID_DENOMS: Set[str] = {"CXX", "XAU", "USD", "CAD", "ZWG"}

# Amount prompt template
AMOUNT_PROMPT = """💸 *Offer how much❓*
✨ Defaults to USD or use
✨ ZWG 99.99 or 9.99 ZWG"""


class AmountInput(InputComponent):
    """Amount input with pure UI validation"""

    def __init__(self):
        super().__init__("amount_input")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate amount format only

        Only checks basic format requirements:
        - Must be numeric
        - Must be positive
        - Must parse as float

        Business validation (limits etc) happens in service layer
        """
        # Get current state
        current_data = self.state_manager.get_state_value("component_data", {})
        incoming_message = current_data.get("incoming_message")

        # Initial activation - send prompt
        if not current_data.get("awaiting_input"):
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
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

        try:
            # Split input into parts
            parts = text.strip().split()

            # Handle different input formats
            if len(parts) == 1:
                # Just amount - default to USD
                amount = float(parts[0])
                denom = "USD"
            elif len(parts) == 2:
                # Amount and denom in either order
                if parts[0].replace('.', '', 1).isdigit():
                    # Format: "99 ZWG"
                    amount = float(parts[0])
                    denom = parts[1].upper()
                else:
                    # Format: "ZWG 99"
                    amount = float(parts[1])
                    denom = parts[0].upper()

                # Validate denomination
                if denom not in VALID_DENOMS:
                    return ValidationResult.failure(
                        message=f"Invalid denomination. Valid options are: {', '.join(sorted(VALID_DENOMS))}",
                        field="denomination",
                        details={"denom": denom}
                    )
            else:
                return ValidationResult.failure(
                    message="Invalid format. Use: amount or 'amount DENOM' or 'DENOM amount'",
                    field="format",
                    details={"text": text}
                )

            # Basic format validation
            if amount <= 0:
                return ValidationResult.failure(
                    message="Amount must be positive",
                    field="amount",
                    details={"amount": amount}
                )

            # Store validated amount and denom
            self.update_data({
                "amount": str(amount),
                "denom": denom
            })

            # Release input wait
            self.set_awaiting_input(False)
            return ValidationResult.success({"amount": amount, "denom": denom})

        except ValueError:
            return ValidationResult.failure(
                message="Invalid amount format",
                field="amount",
                details={"text": text}
            )

    def to_verified_data(self, value: Any) -> Dict:
        """Convert to verified amount and denomination"""
        if isinstance(value, dict):
            return {
                "amount": str(float(value["amount"])),
                "denom": value["denom"]
            }
        # Handle legacy format where value was just the amount
        return {
            "amount": str(float(value)),
            "denom": "USD"
        }
