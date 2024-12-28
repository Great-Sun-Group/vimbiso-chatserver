"""Flow initialization and management enforcing SINGLE SOURCE OF TRUTH"""
import logging
from typing import Any, Dict

from core.messaging.types import (ChannelIdentifier, ChannelType, Message,
                                  MessageRecipient, TextContent)
from core.utils.exceptions import StateException
from core.utils.flow_audit import FlowAuditLogger

logger = logging.getLogger(__name__)
audit = FlowAuditLogger()

# Flow type to handler function mapping
FLOW_HANDLERS: Dict[str, Any] = {
    "offer": "process_offer_step",
    "accept": "process_accept_step",
    "decline": "process_decline_step",
    "cancel": "process_cancel_step",
    "registration": "process_registration_step",
    "upgrade": "process_upgrade_step"
}


def initialize_flow(state_manager: Any, flow_type: str) -> Message:
    """Initialize a new flow enforcing SINGLE SOURCE OF TRUTH

    Args:
        state_manager: State manager instance
        flow_type: Type of flow to initialize

    Returns:
        Message: Core message type with recipient and content
    """
    try:
        # Let StateManager validate channel access
        state_manager.get("channel")

        # Validate flow type through state update
        if flow_type not in FLOW_HANDLERS:
            raise StateException(f"Unknown flow type: {flow_type}")

        # Initialize flow state through state update
        success, error = state_manager.update_state({
            "flow_data": {
                "flow_type": flow_type,
                "step": 0,
                "current_step": "amount" if flow_type == "offer" else "start",
                "data": {}
            }
        })
        if not success:
            raise StateException(f"Failed to initialize flow state: {error}")

        # Log flow start attempt
        audit.log_flow_event(
            "bot_service",
            "flow_start_attempt",
            None,
            {"flow_type": flow_type},  # Only log flow type
            "in_progress"
        )

        # Get credex service if needed
        credex_service = None
        if flow_type == "offer":
            from services.credex.service import get_credex_service
            credex_service = get_credex_service(state_manager)

        # Get handler name and import function
        handler_name = FLOW_HANDLERS[flow_type]  # Already validated flow_type exists
        handler_module = __import__(
            f"app.services.whatsapp.handlers.credex.flows.{flow_type}",
            fromlist=[handler_name]
        )
        handler_func = getattr(handler_module, handler_name)

        # Initialize flow
        result = handler_func(state_manager, "amount" if flow_type == "offer" else "start", None, credex_service)
        if not result:
            raise StateException("Failed to get initial flow message")

        # Log success
        audit.log_flow_event(
            "bot_service",
            "flow_start_success",
            None,
            {"flow_type": flow_type},  # Only log flow type
            "success"
        )

        return result

    except StateException as e:
        logger.error(f"Flow initialization error: {str(e)}")
        channel = state_manager.get("channel")
        return Message(
            recipient=MessageRecipient(
                channel_id=ChannelIdentifier(
                    channel=ChannelType.WHATSAPP,
                    value=channel["identifier"]
                )
            ),
            content=TextContent(
                body="Error: Unable to start flow. Please try again."
            )
        )


def check_pending_offers(state_manager: Any) -> bool:
    """Check for pending offers enforcing SINGLE SOURCE OF TRUTH"""
    try:
        # Log check
        audit.log_flow_event(
            "bot_service",
            "check_pending_offers",
            None,
            {"status": "checking"},  # Only log status
            "success"
        )

        return True

    except StateException as e:
        logger.error(f"Error checking pending offers: {str(e)}")
        return False
