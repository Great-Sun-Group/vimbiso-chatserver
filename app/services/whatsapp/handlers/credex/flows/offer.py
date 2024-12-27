"""Offer flow implementation enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict, List

from core.messaging.flow import Step, StepType
from core.utils.flow_audit import FlowAuditLogger
from core.utils.state_validator import StateValidator

from services.whatsapp.types import WhatsAppMessage
from .base import CredexFlow
from .messages import create_offer_confirmation
from .transformers import validate_and_parse_amount

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()


class OfferFlow(CredexFlow):
    """Flow for creating a new credex offer with strict state management"""

    def __init__(self, state_manager: Any) -> None:
        """Initialize with state manager enforcing SINGLE SOURCE OF TRUTH

        Args:
            state_manager: State manager instance

        Raises:
            ValueError: If state validation fails or required data missing
        """
        if not state_manager:
            raise ValueError("State manager required")

        # Validate ALL required state at boundary
        required_fields = {"channel", "member_id", "authenticated", "flow_data"}
        current_state = {
            field: state_manager.get(field)
            for field in required_fields
        }

        # Initial validation
        validation = StateValidator.validate_before_access(
            current_state,
            {"channel", "member_id"}  # Core requirements
        )
        if not validation.is_valid:
            raise ValueError(f"State validation failed: {validation.error_message}")

        # Get channel info (SINGLE SOURCE OF TRUTH)
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ValueError("Channel identifier not found")

        # Initialize base class
        super().__init__(id="offer_flow")

        # Initialize services
        self.state_manager = state_manager
        self.credex_service = state_manager.get_credex_service()
        if not self.credex_service:
            raise ValueError("Failed to initialize credex service")

        self.steps = self._create_steps()

        # Log initialization
        logger.info(f"Initialized OfferFlow for channel {channel['identifier']}")

    def _create_steps(self) -> List[Step]:
        """Create steps for offer flow with strict state validation"""
        return [
            Step(
                id="amount",
                type=StepType.TEXT,
                message=self._get_amount_prompt,
                validator=self._validate_amount,
                transformer=self._store_amount
            ),
            Step(
                id="handle",
                type=StepType.TEXT,
                message=self._get_handle_prompt,
                validator=self._validate_handle,
                transformer=self._store_handle
            ),
            Step(
                id="confirm",
                type=StepType.BUTTON,
                message=self._get_confirmation_message,
                validator=lambda x: x.lower() in ["yes", "no"]
            )
        ]

    def _get_amount_prompt(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Get amount prompt with strict state validation"""
        channel = self.state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Enter amount:\n\n"
            "Examples:\n"
            "100     (USD)\n"
            "USD 100\n"
            "ZWG 100\n"
            "XAU 1"
        )

    def _validate_amount(self, value: str) -> bool:
        """Validate amount input"""
        try:
            validate_and_parse_amount(value)
            return True
        except ValueError:
            return False

    def _store_amount(self, value: str) -> None:
        """Store amount data enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not value or not isinstance(value, str):
                raise ValueError("Invalid amount value")

            # Parse amount
            amount, denomination = validate_and_parse_amount(value)

            # Get flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                flow_data = {}

            # Prepare new flow data
            new_flow_data = flow_data.copy()
            new_flow_data.update({
                "offer_amount": amount,
                "offer_denomination": denomination
            })

            # Validate state update
            new_state = {"flow_data": new_flow_data}
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid flow data: {validation.error_message}")

            # Update state
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Log success
            channel = self.state_manager.get("channel")
            logger.info(f"Stored amount {amount} {denomination} for channel {channel['identifier']}")

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Failed to store amount: {str(e)} for channel {channel_id}")
            raise

    def _get_handle_prompt(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Get handle prompt with strict state validation"""
        channel = self.state_manager.get("channel")
        return WhatsAppMessage.create_text(
            channel["identifier"],
            "Enter recipient handle:"
        )

    def _validate_handle(self, value: str) -> bool:
        """Validate handle input"""
        handle = value.strip()
        return bool(handle and len(handle) >= 3)

    def _store_handle(self, value: str) -> None:
        """Store handle enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate input
            if not value or not isinstance(value, str):
                raise ValueError("Invalid handle value")

            handle = value.strip().lower()
            if not handle:
                raise ValueError("Empty handle after cleaning")

            # Get flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                flow_data = {}

            # Prepare new flow data
            new_flow_data = flow_data.copy()
            new_flow_data["offer_handle"] = handle

            # Validate state update
            new_state = {"flow_data": new_flow_data}
            validation = StateValidator.validate_state(new_state)
            if not validation.is_valid:
                raise ValueError(f"Invalid flow data: {validation.error_message}")

            # Update state
            success, error = self.state_manager.update_state(new_state)
            if not success:
                raise ValueError(f"Failed to update flow data: {error}")

            # Log success
            channel = self.state_manager.get("channel")
            logger.info(f"Stored handle {handle} for channel {channel['identifier']}")

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Failed to store handle: {str(e)} for channel {channel_id}")
            raise

    def _get_confirmation_message(self, state: Dict[str, Any]) -> WhatsAppMessage:
        """Get confirmation message with strict state validation"""
        try:
            # Validate state access at boundary
            validation = StateValidator.validate_before_access(
                {
                    "channel": self.state_manager.get("channel"),
                    "flow_data": self.state_manager.get("flow_data")
                },
                {"channel", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(validation.error_message)

            channel = self.state_manager.get("channel")
            flow_data = self.state_manager.get("flow_data")

            return create_offer_confirmation(
                channel["identifier"],
                flow_data["offer_amount"],
                flow_data["offer_denomination"],
                flow_data["offer_handle"]
            )

        except ValueError as e:
            logger.error(f"Failed to create confirmation message: {str(e)}")
            raise

    def complete(self) -> Dict[str, Any]:
        """Complete offer flow enforcing SINGLE SOURCE OF TRUTH"""
        try:
            # Validate ALL required state at boundary
            required_fields = {"channel", "member_id", "flow_data", "authenticated"}
            current_state = {
                field: self.state_manager.get(field)
                for field in required_fields
            }

            # Validate required fields
            validation = StateValidator.validate_before_access(
                current_state,
                {"channel", "member_id", "flow_data"}
            )
            if not validation.is_valid:
                raise ValueError(f"State validation failed: {validation.error_message}")

            # Get channel info (SINGLE SOURCE OF TRUTH)
            channel = self.state_manager.get("channel")
            if not channel or not channel.get("identifier"):
                raise ValueError("Channel identifier not found")

            # Get and validate flow data (SINGLE SOURCE OF TRUTH)
            flow_data = self.state_manager.get("flow_data")
            if not isinstance(flow_data, dict):
                raise ValueError("Invalid flow data format")

            # Validate required offer data
            required_offer_fields = {"offer_amount", "offer_denomination", "offer_handle"}
            if not all(field in flow_data for field in required_offer_fields):
                raise ValueError("Missing required offer data")

            # Prepare offer data
            offer_data = {
                "amount": flow_data["offer_amount"],
                "denomination": flow_data["offer_denomination"],
                "handle": flow_data["offer_handle"]
            }

            # Make API call
            success, response = self.credex_service.offer_credex(offer_data)
            if not success:
                error_msg = response.get("message", "Offer failed")
                logger.error(f"API call failed: {error_msg} for channel {channel['identifier']}")
                raise ValueError(error_msg)

            # Log success
            audit.log_flow_event(
                self.id,
                "completion_success",
                None,
                {
                    "channel_id": channel["identifier"],
                    "offer_data": offer_data,
                    "response": response
                },
                "success"
            )

            logger.info(f"Successfully completed offer flow for channel {channel['identifier']}")

            return {
                "success": True,
                "message": "CredEx offer created successfully",
                "response": response
            }

        except ValueError as e:
            # Get channel info for error logging
            try:
                channel = self.state_manager.get("channel")
                channel_id = channel["identifier"] if channel else "unknown"
            except (ValueError, KeyError, TypeError) as err:
                logger.error(f"Failed to get channel for error logging: {str(err)}")
                channel_id = "unknown"

            logger.error(f"Failed to complete offer: {str(e)} for channel {channel_id}")
            raise
