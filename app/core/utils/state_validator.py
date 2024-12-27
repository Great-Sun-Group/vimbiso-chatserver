"""Core state validation enforcing SINGLE SOURCE OF TRUTH"""
from typing import Any, Dict, Set

from .validator_interface import ValidationResult


class StateValidator:
    """Validates core state structure focusing on SINGLE SOURCE OF TRUTH"""

    # Critical fields that must be validated
    CRITICAL_FIELDS = {
        "member_id",
        "channel",
        "jwt_token"
    }

    # Fields that must never be duplicated
    UNIQUE_FIELDS = {
        "member_id",
        "channel"
    }

    @classmethod
    def validate_state(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate state structure enforcing SINGLE SOURCE OF TRUTH"""
        # Validate state is dictionary
        if not isinstance(state, dict):
            return ValidationResult(
                is_valid=False,
                error_message="State must be a dictionary"
            )

        # Validate critical fields exist
        missing_fields = cls.CRITICAL_FIELDS - set(state.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing critical fields: {', '.join(missing_fields)}"
            )

        # Validate channel structure (required)
        channel_validation = cls._validate_channel(state.get("channel"))
        if not channel_validation.is_valid:
            return channel_validation

        # Validate member_id (SINGLE SOURCE OF TRUTH)
        if not isinstance(state["member_id"], (str, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="Member ID must be string or None"
            )

        # Validate jwt_token (SINGLE SOURCE OF TRUTH)
        if not isinstance(state["jwt_token"], (str, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="JWT token must be string or None"
            )

        # Validate no state duplication
        duplication_validation = cls._validate_no_duplication(state)
        if not duplication_validation.is_valid:
            return duplication_validation

        # Validate flow_data if present
        if "flow_data" in state:
            flow_validation = cls._validate_flow_data(state["flow_data"])
            if not flow_validation.is_valid:
                return flow_validation

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_channel(cls, channel: Any) -> ValidationResult:
        """Validate channel structure"""
        if not isinstance(channel, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Channel must be a dictionary"
            )

        # Required channel fields
        required_fields = {"type", "identifier"}
        missing_fields = required_fields - set(channel.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Channel missing required fields: {', '.join(missing_fields)}"
            )

        # Validate field types
        if not isinstance(channel["type"], str):
            return ValidationResult(
                is_valid=False,
                error_message="Channel type must be string"
            )

        if not isinstance(channel["identifier"], (str, type(None))):
            return ValidationResult(
                is_valid=False,
                error_message="Channel identifier must be string or None"
            )

        # Validate metadata if present
        if "metadata" in channel:
            if not isinstance(channel["metadata"], dict):
                return ValidationResult(
                    is_valid=False,
                    error_message="Channel metadata must be a dictionary"
                )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_flow_data(cls, flow_data: Any) -> ValidationResult:
        """Validate flow data structure"""
        if flow_data is None:
            return ValidationResult(is_valid=True)

        if not isinstance(flow_data, dict):
            return ValidationResult(
                is_valid=False,
                error_message="Flow data must be a dictionary"
            )

        # Required flow fields
        required_fields = {"step", "flow_type"}
        missing_fields = required_fields - set(flow_data.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Flow data missing required fields: {', '.join(missing_fields)}"
            )

        return ValidationResult(is_valid=True)

    @classmethod
    def _validate_no_duplication(cls, state: Dict[str, Any]) -> ValidationResult:
        """Validate no state duplication"""
        # Check for nested member_id
        if any(isinstance(v, dict) and "member_id" in v for v in state.values()):
            return ValidationResult(
                is_valid=False,
                error_message="member_id found in nested state - must only exist at top level"
            )

        # Check for nested channel info
        if any(isinstance(v, dict) and "channel" in v for v in state.values()):
            return ValidationResult(
                is_valid=False,
                error_message="channel info found in nested state - must only exist at top level"
            )

        # Check for state passing in flow data
        if "flow_data" in state and isinstance(state["flow_data"], dict):
            for field in cls.UNIQUE_FIELDS:
                if field in state["flow_data"]:
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"{field} found in flow data - must not be passed between components"
                    )

        return ValidationResult(is_valid=True)

    @classmethod
    def validate_before_access(cls, state: Dict[str, Any], required_fields: Set[str]) -> ValidationResult:
        """Validate state before accessing fields"""
        # First validate core state structure
        validation = cls.validate_state(state)
        if not validation.is_valid:
            return validation

        # Then validate required fields exist
        missing_fields = required_fields - set(state.keys())
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                error_message=f"Missing required fields for access: {', '.join(missing_fields)}"
            )

        # Validate no state duplication in access
        for field in required_fields:
            if field in cls.UNIQUE_FIELDS:
                duplication_validation = cls._validate_no_duplication(state)
                if not duplication_validation.is_valid:
                    return duplication_validation

        return ValidationResult(is_valid=True)
