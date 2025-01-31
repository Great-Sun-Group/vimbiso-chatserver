"""Flow Headquarters

This module defines the core branching logic that determines the next step in member flows
through the vimbiso-chatserver application.
"""
import logging
from typing import Tuple

from core.state.interface import StateManagerInterface

logger = logging.getLogger(__name__)


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
            if component_result == "send_multi_dashboard":
                return "multi_account", "MultiAccountDashboard"  # Send multi-account dashboard for tier 5
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Send account dashboard
            if component_result == "start_onboarding":
                return "onboard", "Welcome"  # Send first message in onboarding path

        # Multi-account dashboard path
        case ("multi_account", "MultiAccountDashboard"):
            if component_result == "account_selected":
                return "account", "AccountDashboard"  # Transition to selected account's dashboard

        # Onboard path
        case ("onboard", "Welcome"):
            return "onboard", "FirstNameInput"  # Start collecting user details
        case ("onboard", "FirstNameInput"):
            return "onboard", "LastNameInput"  # Continue with user details
        case ("onboard", "LastNameInput"):
            return "onboard", "ProcessingNow"  # Send message while API call processes
        case ("onboard", "ProcessingNow"):
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
                return "view_ledger", "ProcessingNow"  # Send message while API call processes
            if component_result == "upgrade_membertier":
                return "upgrade_membertier", "ConfirmUpgrade"  # Send upgrade confirmation message
            if component_result == "switch_account":
                return "multi_account", "MultiAccountDashboard"  # Switch to multi-account dashboard

        # Offer secured credex path
        case ("offer_secured", "AmountInput"):
            return "offer_secured", "HandleInput"  # Get recipient handle from member and account details from credex-core
        case ("offer_secured", "HandleInput"):
            return "offer_secured", "ValidateAccountApiCall"  # Validate account exists and get details
        case ("offer_secured", "ValidateAccountApiCall"):
            if component_result == "return_to_handle":
                return "offer_secured", "HandleInput"  # Return to handle input for invalid handle
            return "offer_secured", "ConfirmOfferSecured"  # Confirm amount, denom, issuer and recipient accounts
        case ("offer_secured", "ConfirmOfferSecured"):
            if component_result == "cancelled":
                return "account", "AccountDashboard"  # Return to dashboard if cancelled
            return "offer_secured", "ProcessingNow"  # Send message while API call processes
        case ("offer_secured", "ProcessingNow"):
            return "offer_secured", "CreateCredexApiCall"  # Create offer
        case ("offer_secured", "CreateCredexApiCall"):
            return "account", "AccountDashboard"  # Return to account dashboard (success/fail message passed in state for dashboard display)

        # Upgrade member tier path
        case ("upgrade_membertier", "ConfirmUpgrade"):
            if component_result == "cancelled":
                return "account", "AccountDashboard"  # Return to dashboard if cancelled
            return "upgrade_membertier", "ProcessingNow"  # Process upgrade after confirmation
        case ("upgrade_membertier", "ProcessingNow"):
            return "upgrade_membertier", "UpgradeMembertierApiCall"  # Process upgrade after confirmation
        case ("upgrade_membertier", "UpgradeMembertierApiCall"):
            return "account", "AccountDashboard"  # Return to dashboard after upgrade

        # Accept offer path
        case ("accept_offer", "OfferListDisplay"):
            if component_result == "process_offer":
                return "accept_offer", "ProcessingNow"  # Send message while API call processes
            if component_result == "return_to_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard if no offers or user selected back
        case ("accept_offer", "ProcessingNow"):
            return "accept_offer", "ProcessOfferApiCall"  # Process selected offer
        case ("accept_offer", "ProcessOfferApiCall"):
            if component_result == "return_to_list":
                return "accept_offer", "OfferListDisplay"  # Return to list for more offers
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard when done

        # Decline offer path
        case ("decline_offer", "OfferListDisplay"):
            if component_result == "process_offer":
                return "decline_offer", "ProcessingNow"  # Send message while API call processes
            if component_result == "return_to_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard if no offers or user selected back
        case ("decline_offer", "ProcessingNow"):
            return "decline_offer", "ProcessOfferApiCall"  # Process selected offer
        case ("decline_offer", "ProcessOfferApiCall"):
            if component_result == "return_to_list":
                return "decline_offer", "OfferListDisplay"  # Return to list for more offers
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard when done

        # Cancel offer path
        case ("cancel_offer", "OfferListDisplay"):
            if component_result == "process_offer":
                return "cancel_offer", "ProcessingNow"  # Send message while API call processes
            if component_result == "return_to_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard if no offers or user selected back
        case ("cancel_offer", "ProcessingNow"):
            return "cancel_offer", "ProcessOfferApiCall"  # Process selected offer
        case ("cancel_offer", "ProcessOfferApiCall"):
            if component_result == "return_to_list":
                return "cancel_offer", "OfferListDisplay"  # Return to list for more offers
            if component_result == "send_dashboard":
                return "account", "AccountDashboard"  # Return to dashboard when done
