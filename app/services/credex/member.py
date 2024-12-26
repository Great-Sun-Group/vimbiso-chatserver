import logging
from typing import Any, Dict, Optional, Tuple

from .base import BaseCredExService
from .config import CredExEndpoints
from .exceptions import MemberNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class CredExMemberService(BaseCredExService):
    """Service for CredEx member operations"""

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict[str, Any]]:
        """Get dashboard information from login response"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            # Get dashboard data from login response
            success, response = self._auth.login(phone)
            if not success:
                error_msg = response.get("message", "Failed to fetch dashboard")
                logger.error(f"Dashboard fetch failed: {error_msg}")
                if "Member not found" in error_msg:
                    raise MemberNotFoundError(error_msg)
                return False, {"message": error_msg}

            logger.info("Dashboard fetched successfully")
            return True, response

        except MemberNotFoundError as e:
            logger.warning(f"Member not found: {str(e)}")
            return False, {"message": str(e)}
        except Exception as e:
            logger.exception(f"Dashboard fetch failed: {str(e)}")
            return False, {"message": f"Failed to fetch dashboard: {str(e)}"}

    def validate_handle(self, handle: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate a CredEx handle and get account details"""
        if not handle:
            raise ValidationError("Handle is required")

        try:
            # Log the request details
            logger.info(f"Validating handle: {handle}")

            response = self._make_request(
                CredExEndpoints.VALIDATE_HANDLE,
                payload={"accountHandle": handle.lower()}
            )

            # Log the raw response
            logger.debug(f"Raw API response: {response.text}")

            # Handle non-200 responses
            if response.status_code != 200:
                logger.error(f"Handle validation failed with status {response.status_code}")
                return False, {"message": "Invalid handle or account not found"}

            # Parse response
            data = response.json()
            logger.debug(f"Parsed response data: {data}")

            # Check for error in response
            if data.get("error"):
                logger.error(f"API returned error: {data['error']}")
                return False, {"message": data["error"]}

            # Extract account details from action.details
            account_details = data.get("data", {}).get("action", {}).get("details", {})
            if not account_details:
                logger.error("No account details in response")
                return False, {"message": "Account not found"}

            account_id = account_details.get("accountID")
            if not account_id:
                logger.error(f"No account ID found in details: {account_details}")
                return False, {"message": "Could not find account ID"}

            # Return success with account details
            return True, {
                "data": {
                    "accountID": account_id,
                    "accountName": account_details.get("accountName", ""),
                    "accountHandle": handle
                }
            }

        except Exception as e:
            logger.exception(f"Handle validation failed: {str(e)}")
            return False, {"message": f"Failed to validate handle: {str(e)}"}

    def refresh_member_info(
        self, phone: str, reset: bool = True, silent: bool = True, init: bool = False
    ) -> Optional[str]:
        """Refresh member information by re-authenticating"""
        if not phone:
            raise ValidationError("Phone number is required")

        try:
            # Re-authenticate to get fresh data
            success, response = self._auth.login(phone)
            if not success:
                error_msg = response.get("message", "Failed to refresh member info")
                logger.error(f"Member info refresh failed: {error_msg}")
                return error_msg

            logger.info("Member info refreshed successfully")
            return None

        except Exception as e:
            logger.exception("Unexpected error refreshing member info")
            return f"Failed to refresh member info: {str(e)}"

    def get_member_accounts(self, member_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Get available accounts for a member

        Args:
            member_id: ID of the member to get accounts for

        Returns:
            Tuple[bool, Dict[str, Any]]: (success, accounts_data)
        """
        if not member_id:
            raise ValidationError("Member ID is required")

        try:
            # Return account data from login response
            # Get accounts from last login response
            accounts = (self._auth._last_response.get("data", {})
                        .get("dashboard", {})
                        .get("accounts", []))
            return True, {"data": {"accounts": accounts}}

        except Exception as e:
            logger.exception(f"Failed to get member accounts: {str(e)}")
            return False, {"message": f"Failed to get member accounts: {str(e)}"}
