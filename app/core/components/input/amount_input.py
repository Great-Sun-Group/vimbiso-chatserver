"""Amount input component

This component handles amount input with proper validation and balance checking.
"""

import logging
from typing import Any, Dict, Set

from core.error.types import ValidationResult

from ..base import InputComponent

logger = logging.getLogger(__name__)

# Valid denominations
VALID_DENOMS: Set[str] = {"CXX", "XAU", "USD", "CAD"}

# Amount prompt template
AMOUNT_PROMPT = """💸 *Offer how much USD*❓
"""


def safe_float_parse(value_str):
    """Parse float values safely handling different regional formats"""
    if not value_str or not isinstance(value_str, str):
        logger.warning(f"Cannot parse non-string value: {value_str}")
        return None

    # Log original value for debugging
    logger.info(f"Parsing number value: '{value_str}'")

    # Remove any non-breaking spaces or other whitespace
    clean_str = ''.join(value_str.split())
    # Replace commas with periods (for European formatting)
    clean_str = clean_str.replace(',', '.')
    # Strip any currency symbols or other non-numeric chars except period
    clean_str = ''.join(c for c in clean_str if c.isdigit() or c == '.')

    logger.info(f"Cleaned number string: '{clean_str}'")

    try:
        return float(clean_str)
    except ValueError as e:
        logger.warning(f"Failed to parse number: {e}")
        return None


class AmountInput(InputComponent):
    """Amount input with pure UI validation"""

    def __init__(self):
        super().__init__("amount_input")

    def _validate(self, value: Any) -> ValidationResult:
        """Validate amount format and balance

        Checks:
        - Basic format requirements (numeric, positive, float)
        - Sufficient balance in active account
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
        logger.info(f"AmountInput processing message: type={type(incoming_message)}")
        if not isinstance(incoming_message, dict):
            logger.warning(f"Incoming message is not a dictionary: {incoming_message}")
            self.state_manager.messaging.send_text(
                text="Sorry, that doesn't look like an amount to me"
            )
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
            )
            return ValidationResult.success(None)

        # Log message structure for debugging
        logger.info(f"Message structure: keys={list(incoming_message.keys())}")
        if "text" in incoming_message:
            logger.info(f"Text structure: type={type(incoming_message['text'])}")
            if isinstance(incoming_message['text'], dict):
                logger.info(f"Text dict keys: {list(incoming_message['text'].keys())}")

        text = incoming_message.get("text", {}).get("body", "")
        logger.info(f"Extracted text for processing: '{text}'")

        if not text:
            logger.warning("No text extracted from message")
            self.state_manager.messaging.send_text(
                text="Sorry, that doesn't look like an amount to me"
            )
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
            )
            return ValidationResult.success(None)

        try:
            # Split input into parts
            parts = text.strip().split()
            logger.info(f"Split text into parts: {parts}")

            # Handle different input formats
            if len(parts) == 1:
                # Just amount - default to USD
                amount = safe_float_parse(parts[0])
                if amount is None:
                    logger.warning(f"Failed to parse single part as amount: {parts[0]}")
                    self.state_manager.messaging.send_text(
                        text="Sorry, that doesn't look like an amount to me"
                    )
                    self.state_manager.messaging.send_text(
                        text=AMOUNT_PROMPT
                    )
                    return ValidationResult.success(None)
                denom = "USD"
                logger.info(f"Parsed single part as amount={amount}, denom={denom}")
            elif len(parts) == 2:
                # Amount and denom in either order
                if parts[0].replace('.', '', 1).replace(',', '', 1).isdigit():
                    # Format: "99 XAU"
                    amount = safe_float_parse(parts[0])
                    denom = parts[1].upper()
                    logger.info(f"Parsed as 'amount denom' format: {amount} {denom}")
                else:
                    # Format: "XAU 99"
                    amount = safe_float_parse(parts[1])
                    denom = parts[0].upper()
                    logger.info(f"Parsed as 'denom amount' format: {denom} {amount}")

                # Check if parsing failed
                if amount is None:
                    logger.warning(f"Failed to parse amount from parts: {parts}")
                    self.state_manager.messaging.send_text(
                        text="Sorry, that doesn't look like an amount to me"
                    )
                    self.state_manager.messaging.send_text(
                        text=AMOUNT_PROMPT
                    )
                    return ValidationResult.success(None)

                # Validate denomination
                if denom not in VALID_DENOMS:
                    self.state_manager.messaging.send_text(
                        text=f"Invalid denomination. Valid options are: {', '.join(sorted(VALID_DENOMS))}"
                    )
                    self.state_manager.messaging.send_text(
                        text=AMOUNT_PROMPT
                    )
                    return ValidationResult.success(None)
            else:
                self.state_manager.messaging.send_text(
                    text="Invalid format. Use: amount or 'amount DENOM' or 'DENOM amount'"
                )
                self.state_manager.messaging.send_text(
                    text=AMOUNT_PROMPT
                )
                return ValidationResult.success(None)

            # Basic format validation
            if amount <= 0:
                self.state_manager.messaging.send_text(
                    text="Amount must be positive"
                )
                self.state_manager.messaging.send_text(
                    text=AMOUNT_PROMPT
                )
                return ValidationResult.success(None)

            # Get member tier and account info
            dashboard = self.state_manager.get_state_value("dashboard", {})
            member = dashboard.get("member", {})
            member_tier = member.get("memberTier")

            # Skip balance check for tier 5 members
            if member_tier == 5:
                # Store validated amount and denom
                self.update_data({
                    "amount": str(amount),
                    "denom": denom
                })
                # Release input wait
                self.set_awaiting_input(False)
                return ValidationResult.success({"amount": amount, "denom": denom})

            # Check daily USD limit for tier 1 members
            if member_tier == 1 and denom == "USD":
                remaining_usd = member.get("remainingAvailableUSD", 0)
                if amount > remaining_usd:
                    self.state_manager.messaging.send_text(
                        text=f"Daily USD limit insufficient. You have {remaining_usd} USD remaining today."
                    )
                    self.state_manager.messaging.send_text(
                        text=AMOUNT_PROMPT
                    )
                    return ValidationResult.success(None)

            # Check balance for non-tier 5 members
            active_account_id = self.state_manager.get_state_value("active_account_id")
            accounts = dashboard.get("accounts", [])

            # Find active account
            active_account = next(
                (acc for acc in accounts if acc["accountID"] == active_account_id),
                None
            )

            if active_account:
                # Extract balances from account
                balance_data = active_account.get("balanceData", {})
                balances = balance_data.get("securedNetBalancesByDenom", [])
                # Find matching denom balance
                matching_balance = next(
                    (bal.strip() for bal in balances if denom in bal),
                    None
                )

                if matching_balance:
                    # Extract amount from balance string (e.g. "99.99 USD")
                    available = float(matching_balance.split()[0])
                    if amount > available:
                        self.state_manager.messaging.send_text(
                            text=f"Insufficient balance. You have {matching_balance} available."
                        )
                        self.state_manager.messaging.send_text(
                            text=AMOUNT_PROMPT
                        )
                        return ValidationResult.success(None)

                    # Store validated amount and denom
                    self.update_data({
                        "amount": str(amount),
                        "denom": denom
                    })

                    # Release input wait
                    self.set_awaiting_input(False)
                    return ValidationResult.success({"amount": amount, "denom": denom})
                else:
                    self.state_manager.messaging.send_text(
                        text=f"No balance found for {denom}"
                    )
                    self.state_manager.messaging.send_text(
                        text=AMOUNT_PROMPT
                    )
                    return ValidationResult.success(None)
            else:
                self.state_manager.messaging.send_text(
                    text="Could not find active account"
                )
                self.state_manager.messaging.send_text(
                    text=AMOUNT_PROMPT
                )
                return ValidationResult.success(None)

        except ValueError as e:
            logger.error(f"ValueError during amount parsing: {e}")
            self.state_manager.messaging.send_text(
                text="Sorry, that doesn't look like an amount to me"
            )
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
            )
            return ValidationResult.success(None)
        except Exception as e:
            logger.error(f"Unexpected error during amount parsing: {e}")
            self.state_manager.messaging.send_text(
                text="Sorry, that doesn't look like an amount to me"
            )
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
            )
            return ValidationResult.success(None)

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
