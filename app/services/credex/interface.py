from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class CredExServiceInterface(ABC):
    """Interface defining CredEx service operations"""

    @abstractmethod
    def login(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Authenticate user with the CredEx API

        Args:
            state_manager: State manager instance containing channel info

        Returns:
            Tuple of (success: bool, response: Dict[str, Any])
        """
        pass

    @abstractmethod
    def register_member(self, member_data: Dict[str, Any], state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Register a new member

        Args:
            member_data: Member registration information
            state_manager: State manager instance containing channel info

        Returns:
            Tuple of (success: bool, response: Dict[str, Any])
        """
        pass

    @abstractmethod
    def get_dashboard(self, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Fetch member's dashboard information

        Args:
            state_manager: State manager instance containing member info

        Returns:
            Tuple of (success: bool, dashboard_data: Dict[str, Any])
        """
        pass

    @abstractmethod
    def validate_account_handle(self, handle: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Validate a CredEx handle

        Args:
            handle: Handle to validate

        Returns:
            Tuple of (success: bool, validation_data: Dict)
        """
        pass

    @abstractmethod
    def offer_credex(self, offer_data: Dict[str, Any], state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Create a new CredEx offer

        Args:
            offer_data: Offer details

        Returns:
            Tuple of (success: bool, offer_result: Dict)
        """
        pass

    @abstractmethod
    def confirm_credex(self, credex_id: str, issuer_account_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Confirm a CredEx offer

        Args:
            credex_id: ID of the offer to confirm
            issuer_account_id: ID of the issuer's account

        Returns:
            Tuple of (success: bool, confirmation_result: Dict)
        """
        pass

    @abstractmethod
    def accept_credex(self, offer_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Accept a CredEx offer

        Args:
            offer_id: ID of the offer to accept

        Returns:
            Tuple of (success: bool, acceptance_result: Dict)
        """
        pass

    @abstractmethod
    def accept_bulk_credex(self, offer_ids: list[str], state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Accept multiple CredEx offers

        Args:
            offer_ids: List of offer IDs to accept

        Returns:
            Tuple of (success: bool, acceptance_result: Dict)
        """
        pass

    @abstractmethod
    def decline_credex(self, offer_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Decline a CredEx offer

        Args:
            offer_id: ID of the offer to decline

        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def cancel_credex(self, offer_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a CredEx offer

        Args:
            offer_id: ID of the offer to cancel

        Returns:
            Tuple of (success: bool, message: str)
        """
        pass

    @abstractmethod
    def get_credex(self, offer_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a specific CredEx offer

        Args:
            offer_id: ID of the offer to retrieve

        Returns:
            Tuple of (success: bool, offer_details: Dict)
        """
        pass

    @abstractmethod
    def get_ledger(self, member_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get member's ledger information

        Args:
            member_id: ID of the member

        Returns:
            Tuple of (success: bool, ledger_data: Dict)
        """
        pass

    @abstractmethod
    def refresh_member_info(self, state_manager: Any) -> Optional[str]:
        """Refresh member information

        Args:
            state_manager: State manager instance containing member info

        Returns:
            Optional error message if refresh fails
        """
        pass

    @abstractmethod
    def get_member_accounts(self, member_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get available accounts for a member

        Args:
            member_id: ID of the member to get accounts for

        Returns:
            Tuple[bool, Dict[str, Any]]: (success, accounts_data) where accounts_data contains
            a list of accounts with their details including ID, name, type, and denomination
        """
        pass


class CredExRecurringInterface(ABC):
    """Interface defining recurring payment operations"""

    @abstractmethod
    def create_recurring(self, payment_data: Dict[str, Any], state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Create a recurring payment

        Args:
            payment_data: Dictionary containing:
                - sourceAccountID: ID of the source account
                - templateType: Type of recurring payment template
                - payFrequency: Payment frequency in days
                - startDate: Start date for recurring payment
                - memberTier: Target member tier (for subscriptions)
                - securedCredex: Whether credex is secured
                - amount: Payment amount
                - denomination: Payment denomination

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass

    @abstractmethod
    def accept_recurring(self, payment_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Accept a recurring payment

        Args:
            payment_id: ID of the recurring payment to accept

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass

    @abstractmethod
    def cancel_recurring(self, payment_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Cancel a recurring payment

        Args:
            payment_id: ID of the recurring payment to cancel

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass

    @abstractmethod
    def get_recurring(self, payment_id: str, state_manager: Any) -> Tuple[bool, Dict[str, Any]]:
        """Get details of a recurring payment

        Args:
            payment_id: ID of the recurring payment to retrieve

        Returns:
            Tuple[bool, Dict[str, Any]]: Success flag and response data
        """
        pass
