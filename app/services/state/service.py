"""State management service implementation"""
import json
import logging
import time
from enum import Enum
from typing import Any, Dict, Optional

from redis.exceptions import WatchError, RedisError

from .config import RedisConfig
from .exceptions import StateValidationError, StateOperationError

logger = logging.getLogger(__name__)


class StateStage(Enum):
    """Valid state stages"""
    INIT = "init"
    AUTH = "auth"
    MENU = "menu"
    CREDEX = "credex"
    ACCOUNT = "account"
    REGISTRATION = "registration"


class StateTransition:
    """Represents valid state transitions"""
    VALID_TRANSITIONS = {
        StateStage.INIT: [StateStage.AUTH, StateStage.MENU, StateStage.REGISTRATION],
        StateStage.AUTH: [StateStage.MENU, StateStage.REGISTRATION],
        StateStage.MENU: [StateStage.CREDEX, StateStage.ACCOUNT, StateStage.AUTH, StateStage.MENU],
        StateStage.CREDEX: [StateStage.MENU],
        StateStage.ACCOUNT: [StateStage.MENU],
        StateStage.REGISTRATION: [StateStage.MENU]
    }

    @classmethod
    def is_valid_transition(cls, from_stage: str, to_stage: str) -> bool:
        """Check if state transition is valid"""
        try:
            # Handle initial state case
            if from_stage is None:
                return True

            # Handle menu to credex transitions
            if from_stage == "handle_action_menu" and (
                to_stage == StateStage.CREDEX.value or
                to_stage == "handle_action_offer_credex"
            ):
                return True

            # Handle credex offer transitions
            if from_stage == "handle_action_offer_credex" and (
                to_stage == StateStage.CREDEX.value or
                to_stage == "credex"
            ):
                return True

            # Handle action commands
            if to_stage.startswith("handle_action_"):
                return True

            # Handle direct stage transitions
            try:
                from_enum = StateStage(from_stage)
                to_enum = StateStage(to_stage)

                # Allow same stage transitions
                if from_enum == to_enum:
                    return True

                return to_enum in cls.VALID_TRANSITIONS.get(from_enum, [])
            except ValueError:
                # If from_stage is not a valid enum, check if it's a handle_action
                if from_stage.startswith("handle_action_"):
                    try:
                        to_enum = StateStage(to_stage)
                        # Allow transitions from any handle_action to valid stages
                        return True
                    except ValueError:
                        # Both stages are custom - allow the transition
                        return True
                return True

        except Exception as e:
            logger.error(f"Error validating state transition: {str(e)}")
            return False


class StateService:
    """Implementation of the state management service"""

    def __init__(self, redis_client=None):
        """Initialize the state service with a Redis client"""
        # Always create a new Redis client for state management
        self.redis = RedisConfig().get_client()
        self.state_key_prefix = "user_state:"
        self.state_lock_prefix = "user_state_lock:"
        self.state_ttl = 3600  # 1 hour TTL for state
        self.lock_timeout = 30  # 30 seconds lock timeout

        # Verify Redis connection on initialization
        try:
            if not self.redis.ping():
                raise StateOperationError("Redis ping failed")
        except RedisError as e:
            logger.error("Failed to connect to Redis")
            raise StateOperationError("Could not connect to Redis", cause=e)

    def _validate_user_id(self, user_id: str) -> None:
        """Validate user ID"""
        if not user_id or not isinstance(user_id, str):
            raise StateValidationError(f"Invalid user ID: {user_id}")

    def _get_state_key(self, user_id: str) -> str:
        """Generate Redis key for user state"""
        return f"{self.state_key_prefix}{user_id}"

    def _get_lock_key(self, user_id: str) -> str:
        """Generate Redis key for state lock"""
        return f"{self.state_lock_prefix}{user_id}"

    def _acquire_lock(self, user_id: str, timeout: int = 10) -> bool:
        """Acquire lock for state updates with timeout"""
        lock_key = self._get_lock_key(user_id)
        end_time = time.time() + timeout

        try:
            while time.time() < end_time:
                if self.redis.set(lock_key, "1", nx=True, ex=self.lock_timeout):
                    return True
                time.sleep(0.1)
            raise StateOperationError(f"Could not acquire lock for user {user_id}")
        except RedisError as e:
            raise StateOperationError("Lock acquisition failed", cause=e)

    def _release_lock(self, user_id: str) -> None:
        """Release state update lock"""
        try:
            self.redis.delete(self._get_lock_key(user_id))
        except RedisError as e:
            logger.error(f"Failed to release lock: {str(e)}")

    def _validate_state_data(self, state_data: Dict[str, Any]) -> None:
        """Validate state data structure and required fields"""
        if not isinstance(state_data, dict):
            raise StateValidationError("State must be a dictionary")

        required_fields = {"stage", "option"}
        missing_fields = required_fields - set(state_data.keys())
        if missing_fields:
            raise StateValidationError(f"State missing required fields: {missing_fields}")

        # Validate nested structures
        if "flow_data" in state_data:
            flow_data = state_data["flow_data"]
            if not isinstance(flow_data, dict):
                raise StateValidationError("Flow data must be a dictionary")
            required_flow_fields = {"id", "current_step", "data"}
            missing_flow_fields = required_flow_fields - set(flow_data.keys())
            if missing_flow_fields:
                raise StateValidationError(f"Flow data missing required fields: {missing_flow_fields}")

    def _preserve_state_data(self, current_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Preserve essential state data during updates"""
        preserved_fields = {
            "jwt_token",
            "profile",
            "current_account",
            "member",
            "flow_data",
            "authorizer_member_id",
            "issuer_member_id",
            "sender_account",
            "sender_account_id"
        }

        result = new_state.copy()

        # Always preserve JWT token if it exists
        if "jwt_token" in current_state:
            result["jwt_token"] = current_state["jwt_token"]

        # Preserve profile data if it exists and has valid content
        if "profile" in current_state:
            profile_data = current_state["profile"]
            if isinstance(profile_data, dict):
                data = profile_data.get("data", {})
                dashboard = data.get("dashboard", {})

                # Check if we have valid dashboard data
                has_dashboard = (
                    isinstance(dashboard, dict) and
                    (
                        # Either has accounts
                        (isinstance(dashboard.get("accounts"), list) and
                         len(dashboard["accounts"]) > 0 and
                         any(
                             isinstance(account, dict) and
                             account.get("success") and
                             isinstance(account.get("data"), dict)
                             for account in dashboard["accounts"]
                         )) or
                        # Or has member ID
                        dashboard.get("memberID") or
                        # Or has other essential dashboard data
                        (isinstance(dashboard.get("data"), dict) and dashboard["data"])
                    )
                )

                if has_dashboard:
                    # Preserve the entire profile data including dashboard
                    result["profile"] = profile_data

        # Preserve other fields only if they don't exist in new state and have content
        for field in preserved_fields - {"jwt_token", "profile"}:
            if field in current_state and field not in new_state:
                field_data = current_state[field]
                if field_data:  # Only preserve non-empty data
                    result[field] = field_data

        # Handle flow data preservation
        if "flow_data" in current_state and "flow_data" not in new_state:
            flow_data = current_state["flow_data"]
            if isinstance(flow_data, dict) and flow_data.get("data"):
                result["flow_data"] = flow_data
                # Ensure JWT token is also in flow data if it exists
                if "jwt_token" in current_state:
                    result["flow_data"]["data"]["jwt_token"] = current_state["jwt_token"]

        return result

    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Retrieve the current state for a user"""
        self._validate_user_id(user_id)

        try:
            state_key = self._get_state_key(user_id)
            state_json = self.redis.get(state_key)

            if not state_json:
                logger.info(f"Creating new state for user {user_id}")
                new_state = {
                    "stage": StateStage.INIT.value,
                    "option": "",
                    "last_updated": time.time(),
                    "version": 1
                }
                self.redis.set(state_key, json.dumps(new_state), ex=self.state_ttl)
                return new_state

            try:
                # Handle both string and dict responses from Redis
                if isinstance(state_json, str):
                    state = json.loads(state_json)
                else:
                    state = state_json

                # Handle nested state field if it exists
                if isinstance(state.get("state"), str):
                    try:
                        nested_state = json.loads(state["state"])
                        # Preserve JWT token if it exists
                        jwt_token = state.get("jwt_token")
                        state.update(nested_state)
                        state.pop("state", None)
                        if jwt_token:
                            state["jwt_token"] = jwt_token
                    except json.JSONDecodeError:
                        logger.error("Failed to parse nested state JSON")
                        state.pop("state", None)

                self._validate_state_data(state)
                return state
            except json.JSONDecodeError:
                raise StateValidationError("Corrupted state data")

        except RedisError as e:
            raise StateOperationError("Failed to retrieve state", cause=e)

    def update_state(
        self,
        user_id: str,
        new_state: Dict[str, Any],
        stage: str,
        update_from: str,
        option: Optional[str] = None
    ) -> None:
        """Update the state for a user with atomic operations"""
        self._validate_user_id(user_id)
        self._validate_state_data(new_state)

        state_key = self._get_state_key(user_id)

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(state_key)

                    # Get current state
                    current_state_json = pipe.get(state_key)
                    if isinstance(current_state_json, str):
                        current_state = json.loads(current_state_json)
                    else:
                        current_state = current_state_json or {}

                    # Handle nested state if it exists
                    if isinstance(current_state.get("state"), str):
                        try:
                            nested_state = json.loads(current_state["state"])
                            # Preserve JWT token if it exists
                            jwt_token = current_state.get("jwt_token")
                            current_state.update(nested_state)
                            current_state.pop("state", None)
                            if jwt_token:
                                current_state["jwt_token"] = jwt_token
                        except json.JSONDecodeError:
                            logger.error("Failed to parse nested state JSON")
                            current_state.pop("state", None)

                    current_stage = current_state.get("stage") if current_state else None

                    # Validate state transition
                    if not StateTransition.is_valid_transition(current_stage, stage):
                        raise StateValidationError(f"Invalid state transition from {current_stage} to {stage}")

                    pipe.multi()

                    # Preserve essential data and prepare new state
                    if current_state:
                        new_state = self._preserve_state_data(current_state, new_state)

                    # Update state metadata
                    new_state.update({
                        "stage": stage,
                        "update_from": update_from,
                        "option": option if option is not None else "",
                        "last_updated": time.time(),
                        "version": (current_state.get("version", 0) + 1) if current_state else 1
                    })

                    # Ensure JWT token is preserved in flow data if it exists
                    if "jwt_token" in new_state and "flow_data" in new_state:
                        if isinstance(new_state["flow_data"], dict) and "data" in new_state["flow_data"]:
                            new_state["flow_data"]["data"]["jwt_token"] = new_state["jwt_token"]

                    # Store updated state
                    pipe.set(state_key, json.dumps(new_state), ex=self.state_ttl)
                    pipe.execute()
                    logger.info(f"Updated state for user {user_id}: stage={stage}, update_from={update_from}")
                    break

                except WatchError:
                    logger.warning(f"Concurrent state update detected for user {user_id}, retrying")
                    continue
                except RedisError as e:
                    raise StateOperationError("Failed to update state", cause=e)

    def reset_state(self, user_id: str, preserve_auth: bool = True) -> None:
        """Reset the state for a user"""
        self._validate_user_id(user_id)
        state_key = self._get_state_key(user_id)

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(state_key)

                    if preserve_auth:
                        current_state_json = pipe.get(state_key)
                        if current_state_json:
                            if isinstance(current_state_json, str):
                                current_state = json.loads(current_state_json)
                            else:
                                current_state = current_state_json

                            # Handle nested state if it exists
                            if isinstance(current_state.get("state"), str):
                                try:
                                    nested_state = json.loads(current_state["state"])
                                    current_state.update(nested_state)
                                    current_state.pop("state", None)
                                except json.JSONDecodeError:
                                    logger.error("Failed to parse nested state JSON")
                                    current_state.pop("state", None)

                            jwt_token = current_state.get("jwt_token")

                            if jwt_token:
                                pipe.multi()
                                # Initialize with empty profile structure
                                new_state = {
                                    "stage": StateStage.INIT.value,
                                    "option": None,
                                    "jwt_token": jwt_token,
                                    "profile": {
                                        "data": {
                                            "action": {"details": {}},
                                            "details": {}
                                        }
                                    },
                                    "current_account": None,
                                    "flow_data": None,
                                    "last_updated": time.time(),
                                    "version": current_state.get("version", 0) + 1
                                }
                                pipe.set(state_key, json.dumps(new_state), ex=self.state_ttl)
                                pipe.execute()
                                logger.info(f"Reset state for user {user_id} preserving JWT token")
                                return

                    pipe.multi()
                    pipe.delete(state_key)
                    pipe.execute()
                    logger.info(f"Reset state for user {user_id}")
                    break

                except WatchError:
                    continue
                except RedisError as e:
                    raise StateOperationError("Failed to reset state", cause=e)

    def get_stage(self, user_id: str) -> str:
        """Get the current stage for a user"""
        state = self.get_state(user_id)
        return state.get("stage", StateStage.INIT.value)

    def set_stage(self, user_id: str, stage: str) -> None:
        """Set the current stage for a user"""
        if not stage:
            raise StateValidationError("Stage cannot be empty")

        state = self.get_state(user_id)
        current_stage = state.get("stage")

        if not StateTransition.is_valid_transition(current_stage, stage):
            raise StateValidationError(f"Invalid state transition from {current_stage} to {stage}")

        state["stage"] = stage
        self.update_state(
            user_id=user_id,
            new_state=state,
            stage=stage,
            update_from="set_stage"
        )
        logger.info(f"Set stage for user {user_id} to {stage}")

    def get_option(self, user_id: str) -> Optional[str]:
        """Get the current option for a user"""
        state = self.get_state(user_id)
        return state.get("option")

    def set_option(self, user_id: str, option: str) -> None:
        """Set the current option for a user"""
        if not option:
            raise StateValidationError("Option cannot be empty")

        state = self.get_state(user_id)
        state["option"] = option
        self.update_state(
            user_id=user_id,
            new_state=state,
            stage=state["stage"],
            update_from="set_option",
            option=option
        )
        logger.info(f"Set option for user {user_id} to {option}")

    def get_member_info(self, user_id: str) -> Dict[str, Any]:
        """Get member information for a user"""
        state = self.get_state(user_id)
        return state.get("member", {})

    def update_member_info(self, user_id: str, new_info: Dict[str, Any]) -> None:
        """Update member information for a user"""
        if not isinstance(new_info, dict):
            raise StateValidationError("Member info must be a dictionary")

        state = self.get_state(user_id)
        current_member_info = state.get("member", {})
        current_member_info.update(new_info)
        state["member"] = current_member_info

        self.update_state(
            user_id=user_id,
            new_state=state,
            stage=state["stage"],
            update_from="update_member_info"
        )
        logger.info(f"Updated member info for user {user_id}")

    def clear_member_info(self, user_id: str) -> None:
        """Clear member information for a user"""
        state = self.get_state(user_id)
        state["member"] = {}

        self.update_state(
            user_id=user_id,
            new_state=state,
            stage=state["stage"],
            update_from="clear_member_info"
        )
        logger.info(f"Cleared member info for user {user_id}")
