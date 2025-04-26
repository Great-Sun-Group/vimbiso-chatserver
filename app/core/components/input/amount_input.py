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

    logger.debug(f"Attempting to parse float from: '{value_str}'")

    # Remove any non-breaking spaces or other whitespace
    clean_str = ''.join(value_str.split())
    logger.debug(f"After whitespace removal: '{clean_str}'")

    # Handle number formats with different thousand/decimal separators
    if ',' in clean_str and '.' in clean_str:
        # If both comma and period exist, the last one is likely the decimal separator
        last_comma_pos = clean_str.rfind(',')
        last_period_pos = clean_str.rfind('.')

        if last_comma_pos > last_period_pos:
            # Format like "1.000,00" (European)
            clean_str = clean_str.replace('.', '')  # Remove thousand separators
            clean_str = clean_str.replace(',', '.')  # Convert decimal separator to period
        else:
            # Format like "1,000.00" (American/English)
            clean_str = clean_str.replace(',', '')  # Remove thousand separators
    elif ',' in clean_str:
        # Only commas - check position to determine if thousand or decimal separator
        if clean_str.rfind(',') > len(clean_str) - 4:
            # Comma is likely a decimal separator (e.g., "1000,00")
            clean_str = clean_str.replace(',', '.')
        else:
            # Comma is likely a thousand separator (e.g., "1,000")
            clean_str = clean_str.replace(',', '')

    # Strip any currency symbols or other non-numeric chars except period
    clean_str = ''.join(c for c in clean_str if c.isdigit() or c == '.')
    logger.debug(f"After format handling: '{clean_str}'")

    try:
        result = float(clean_str)
        logger.debug(f"Successfully parsed to float: {result}")
        return result
    except ValueError as e:
        logger.warning(f"Failed to parse number: '{value_str}' -> '{clean_str}', error: {e}")
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
        if not isinstance(incoming_message, dict):
            logger.warning(f"Incoming message is not a dictionary: {incoming_message}")
            self.state_manager.messaging.send_text(
                text="Sorry, that doesn't look like an amount to me"
            )
            self.state_manager.messaging.send_text(
                text=AMOUNT_PROMPT
            )
            return ValidationResult.success(None)

        text = incoming_message.get("text", {}).get("body", "")

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
            elif len(parts) == 2:
                # Amount and denom in either order
                if parts[0].replace('.', '', 1).replace(',', '', 1).isdigit():
                    # Format: "99 XAU"
                    amount = safe_float_parse(parts[0])
                    denom = parts[1].upper()
                else:
                    # Format: "XAU 99"
                    amount = safe_float_parse(parts[1])
                    denom = parts[0].upper()

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

            # Skip balance check for tier >= 5 members
            if member_tier >= 5:
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
                    # Log the exact format of the matching balance
                    logger.debug(f"Found matching balance for {denom}: '{matching_balance}' (type: {type(matching_balance).__name__})")

                    # Extract amount from balance string (e.g. "99.99 USD" or "2,000.00 USD")
                    try:
                        balance_amount_str = matching_balance.split()[0]
                        logger.debug(f"Extracted balance amount string: '{balance_amount_str}'")
                    except Exception as e:
                        logger.error(f"Error splitting balance string '{matching_balance}': {e}")
                        balance_amount_str = matching_balance

                    available = safe_float_parse(balance_amount_str)

                    if available is None:
                        logger.error(f"Failed to parse balance amount: '{balance_amount_str}' from full balance string: '{matching_balance}'")
                        logger.error(f"Account balance data: {balance_data}")
                        self.state_manager.messaging.send_text(
                            text="Error processing your balance. Please contact support."
                        )
                        self.state_manager.messaging.send_text(
                            text=AMOUNT_PROMPT
                        )
                        return ValidationResult.success(None)

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
