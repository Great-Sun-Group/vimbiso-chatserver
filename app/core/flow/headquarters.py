"""Flow Headquarters

This module defines the core logic that manages member flows through the vimbiso-chatserver application.
It activates a component at each step, and determines the next step through branching logic.
Data management is delegated to the state manager, and action management is delegated to the components.

Components are self-contained with responsibility for their own:
- Business logic and validation
- Activation of shared utilities/helpers/services
- State access through get_state_value() for schema-validated fields
- Freedom to store any data in component_data.data dict
- State updates that must pass schema validation except for component_data.data
- Error handling

The state manager provides:
- Schema validation for all state updates except component_data.data
- Single source of truth for all state
- Clear boundaries through schema validation
- Component freedom through unvalidated data dict
- Atomic updates through Redis persistence
"""

import logging
from typing import Optional, Tuple

from core import components
from core.error.exceptions import ComponentException
from core.error.types import ValidationResult
from core.state.interface import StateManagerInterface

logger = logging.getLogger(__name__)


# Cache for active component instances
_active_components = {}


def activate_component(component_type: str, state_manager: StateManagerInterface) -> ValidationResult:
    """Create or retrieve and activate a component for the current path step.

    Handles component processing:
    1. Creates new component instance or retrieves existing one if awaiting input
    2. Configures state management
    3. Returns component result

    Args:
        component_type: Component for this step (e.g. "Greeting", "LoginApiCall")
        state_manager: State manager for component configuration and validation

    Returns:
        ValidationResult: Component activation result

    Raises:
        ComponentException: If component creation or activation fails
    """
    # Get channel identifier for component cache key
    channel_id = state_manager.get_channel_id()
    cache_key = f"{channel_id}:{component_type}"

    try:
        # Check if we have an active instance awaiting input
        if state_manager.is_awaiting_input() and cache_key in _active_components:
            component = _active_components[cache_key]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Retrieved active component instance: {component.type}")
        else:
            # Create new component instance
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Creating component for step: {component_type}")

            component_class = getattr(components, component_type)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Found component class: {component_class.__name__}")

            component = component_class()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Created component instance: {component.type}")

            # Cache the new instance
            _active_components[cache_key] = component

        # Ensure state manager is set
        component.set_state_manager(state_manager)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Set state manager on component")

        # Activate component
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Activating component")
        result = component.validate(None)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Activation result: {result}")

        # Clear from cache if no longer awaiting input
        if not state_manager.is_awaiting_input():
            _active_components.pop(cache_key, None)

        return result

    except AttributeError as e:
        logger.error(f"Component not found: {component_type}")
        logger.error(f"Available components: {dir(components)}")
        raise ComponentException(
            message=f"Component not found: {component_type}",
            component=component_type,
            field="type",
            value=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to activate component: {str(e)}")
        raise ComponentException(
            message=f"Component activation failed: {str(e)}",
            component=component_type,
            field="activation",
            value=str(e)
        )


def get_next_component(
    path: str,
    component: str,
    state_manager: StateManagerInterface
) -> Tuple[str, str]:
    """Determine next path/Component based on current path/Component completion and optional component_result.
    Handle progression through and between flows.

    Args:
        path: (e.g. "login", "offer_secured", "account")
        component: Current step's component (e.g. "AmountInput", "HandleInput", "ConfirmOffer", "CreateCredexApiCall")
        state_manager: State manager for checking awaiting_input and component_result

    Returns:
        Tuple[str, str]: Next path/Component
    """
    # Get component result for branching
    component_result = state_manager.get_component_result()

    # Branch based on current path
    match (path, component):

        # Login path
        case ("login", "Greeting"):
            return "login", "LoginApiCall"  # Check if user exists
        case ("login", "LoginApiCall"):
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Send account dashboard
            if component_result == "start_onboarding":
                return "onboard", "Welcome"  # Send first message in onboarding path

        # Onboard path
        case ("onboard", "Welcome"):
            return "onboard", "FirstNameInput"  # Start collecting user details
        case ("onboard", "FirstNameInput"):
            return "onboard", "LastNameInput"  # Continue with user details
        case ("onboard", "LastNameInput"):
            return "onboard", "Greeting"  # Send random greeting while API call processes
        case ("onboard", "Greeting"):
            return "onboard", "OnBoardMemberApiCall"  # Create member and account with collected details
        case ("onboard", "OnBoardMemberApiCall"):
            return "account", "AccountDashboard"  # Send account dashboard

        # Account dashboard path
        case ("account", "AccountDashboard"):
            if component_result == "offer_secured":
                return "offer_secured", "AmountInput"  # Start collecting offer details with amount/denom
            if component_result == "accept_offer":
                return "accept_offer", "OfferListDisplay"  # List pending offers to accept
            if component_result == "decline_offer":
                return "decline_offer", "OfferListDisplay"  # List pending offers to decline
            if component_result == "cancel_offer":
                return "cancel_offer", "OfferListDisplay"  # List pending offers to cancel
            if component_result == "view_ledger":
                return "view_ledger", "Greeting"  # Send random greeting while API call processes
            if component_result == "upgrade_membertier":
                return "upgrade_membertier", "ConfirmUpgrade"  # Send upgrade confirmation message

        # Offer secured credex path
        case ("offer_secured", "AmountInput"):
            return "offer_secured", "HandleInput"  # Get recipient handle from member and account details from credex-core
        case ("offer_secured", "HandleInput"):
            return "offer_secured", "ValidateAccountApiCall"  # Validate account exists and get details
        case ("offer_secured", "ValidateAccountApiCall"):
            return "offer_secured", "ConfirmOfferSecured"  # Confirm amount, denom, issuer and recipient accounts
        case ("offer_secured", "ConfirmOfferSecured"):
            return "offer_secured", "Greeting"  # Send random greeting while api call processes
        case ("offer_secured", "Greeting"):
            return "offer_secured", "CreateCredexApiCall"  # Create offer
        case ("offer_secured", "CreateCredexApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)

        # Accept offer path
        case ("accept_offer", "OfferListDisplay"):
            if component_result == "return_to_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard when no offers
            return "accept_offer", "Greeting"  # Send random greeting while api call processes
        case ("accept_offer", "Greeting"):
            return "accept_offer", "ProcessOfferApiCall"  # Process selected offer action
        case ("accept_offer", "ProcessOfferApiCall"):
            if component_result == "return_to_list":
                return "accept_offer", "OfferListDisplay"  # Return to list for more offers
            return "account", "AccountDashboard"  # Return to dashboard when done

        # Decline offer path
        case ("decline_offer", "OfferListDisplay"):
            if component_result == "return_to_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard when no offers
            return "decline_offer", "Greeting"  # Send random greeting while api call processes
        case ("decline_offer", "Greeting"):
            return "decline_offer", "ProcessOfferApiCall"  # Process selected offer action
        case ("decline_offer", "ProcessOfferApiCall"):
            if component_result == "return_to_list":
                return "decline_offer", "OfferListDisplay"  # Return to list for more offers
            return "account", "AccountDashboard"  # Return to dashboard when done

        # Cancel offer path
        case ("cancel_offer", "OfferListDisplay"):
            if component_result == "return_to_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard when no offers
            return "cancel_offer", "Greeting"  # Send random greeting while api call processes
        case ("cancel_offer", "Greeting"):
            return "cancel_offer", "ProcessOfferApiCall"  # Process selected offer action
        case ("cancel_offer", "ProcessOfferApiCall"):
            if component_result == "return_to_list":
                return "cancel_offer", "OfferListDisplay"  # Return to list for more offers
            return "account", "AccountDashboard"  # Return to dashboard when done

        # View ledger path
        case ("view_ledger", "Greeting"):
            return "view_ledger", "ViewLedger"  # Show ledger with pagination
        case ("view_ledger", "ViewLedger"):
            if component_result == "fetch_ledger":
                return "view_ledger", "GetLedgerApiCall"  # Fetch ledger entries
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Return to account dashboard
        case ("view_ledger", "GetLedgerApiCall"):
            return "view_ledger", "ViewLedger"  # Display fetched entries

        # Upgrade member tier path
        case ("upgrade_membertier", "ConfirmUpgrade"):
            return "upgrade_membertier", "Greeting"  # Send random greeting while api call processes
        case ("upgrade_membertier", "Greeting"):
            return "upgrade_membertier", "UpgradeMembertierApiCall"  # Process tier upgrade
        case ("upgrade_membertier", "UpgradeMembertierApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)


def process_component(path: str, component: str, state_manager: StateManagerInterface, depth: int = 0) -> Optional[Tuple[str, str]]:
    """Process current step and determine next step in application paths.

    Handles the complete step processing:
    1. Activates component for current step
    2. Lets component process its logic
    3. Determines next step in path

    Args:
        path: Path category (e.g. "login", "offer_secured", "account")
        component: Current step's component in the path
        state_manager: State manager for component activation and path control

    Returns:
        Optional[Tuple[str, str]]: Next step (path, component) in the current path, or None if activation failed
    """
    logger.info(f"Processing component: {path}.{component} (depth: {depth})")
    if depth > 10:  # Arbitrary limit to catch potential issues
        logger.error(f"Maximum component processing depth exceeded: {path}.{component}")
        return None
    logger.info(f"Current awaiting_input: {state_manager.is_awaiting_input()}")

    # Activate component for current step
    logger.info("Activating component...")
    result = activate_component(component, state_manager)
    logger.info(f"Activation result: {result}")
    logger.info(f"Awaiting input after activation: {state_manager.is_awaiting_input()}")

    # Handle validation failures
    if not result.valid:
        logger.error(f"Component activation failed: {result.error}")

        # Check if we should retry handle input
        if (path == "offer_secured" and
                component == "ValidateAccountApiCall" and
                isinstance(result.error, dict) and
                result.error.get("details", {}).get("retry")):
            return "offer_secured", "HandleInput"

        return None

    # Check if still awaiting input after activation
    if state_manager.is_awaiting_input():
        logger.info("Still awaiting input after activation")
        return path, component

    # Determine next step in path
    logger.info("Getting next component...")
    next_step = get_next_component(path, component, state_manager)
    logger.info(f"Next step: {next_step}")
    logger.info(f"Final awaiting_input: {state_manager.is_awaiting_input()}")

    return next_step
