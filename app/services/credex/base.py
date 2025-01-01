"""Base CredEx functionality using pure functions"""
from typing import Any, Dict

import requests
from core.utils.error_handler import error_decorator
from core.utils.exceptions import APIException, ConfigurationException

from .config import CredExConfig, CredExEndpoints


@error_decorator
def make_credex_request(
    group: str,
    action: str,
    payload: Dict[str, Any] = None,
    state_manager: Any = None,
    method: str = "POST"
) -> Dict[str, Any]:
    """Make an HTTP request to the CredEx API using endpoint groups"""
    # Get endpoint info
    path = CredExEndpoints.get_path(group, action)

    # Let StateManager validate through flow state update
    state_manager.update_state({
        "flow_data": {
            "flow_type": group,  # StateManager validates auth requirements
            "step": 1,
            "current_step": action,
            "data": {
                "request": {
                    "method": method,
                    "payload": payload
                }
            }
        }
    })

    # Build request
    config = CredExConfig.from_env()
    url = config.get_url(path)
    headers = config.get_headers()

    # Add token from validated state if available
    jwt_token = state_manager.get("jwt_token")
    if jwt_token:
        headers["Authorization"] = f"Bearer {jwt_token}"

    # For auth endpoints, ensure phone number is taken from state
    if group == 'auth' and action == 'login':
        channel = state_manager.get("channel")
        if not channel or not channel.get("identifier"):
            raise ConfigurationException("Missing channel identifier in state")
        # Override payload with phone from state
        payload = {"phone": channel["identifier"]}

    try:
        # Make request
        response = requests.request(method, url, headers=headers, json=payload)

        # Handle API errors
        if not response.ok:
            try:
                error_data = {
                    "status_code": response.status_code,
                    "response": response.json()
                }
            except ValueError:
                error_data = {
                    "status_code": response.status_code,
                    "response": response.text
                }
            raise APIException(
                f"API request failed: {response.status_code}",
                error_data
            )

        # Return response data
        return response.json()

    except requests.exceptions.RequestException as e:
        # Handle network errors
        error_data = {"url": url, "error": str(e)}
        raise APIException(
            f"Connection error: {str(e)}",
            error_data
        )
