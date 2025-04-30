"""OTP Verification API call component

Handles the verification of OTP codes sent via messaging channels:
- Extracts OTP from message
- Validates OTP format
- Sends verification request to Credex Core
- Returns success or failure message
"""

import logging
import os
import re
from typing import Any

import requests
from core.error.types import ValidationResult

from ..base import ApiComponent

logger = logging.getLogger(__name__)

# Get API URL and key from environment
CREDEX_API_URL = os.getenv('MYCREDEX_APP_URL', 'https://dev.mycredex.dev')
API_KEY = os.getenv('CLIENT_API_KEY', '')


class VerifyOTPApiCall(ApiComponent):
    """Processes OTP verification API calls"""

    def __init__(self):
        super().__init__("VerifyOTPApiCall")

    def _send(self) -> None:
        """Initial component activation - no message needed"""
        # This component doesn't need to send an initial message
        # It will process the incoming verification message directly
        pass

    def validate_api_call(self, value: Any) -> ValidationResult:
        """Process OTP verification API call"""
        try:
            # Get incoming message from state
            incoming_message = self.state_manager.get_incoming_message()
            if not incoming_message:
                logger.error("No incoming message found in state")
                return ValidationResult.failure(
                    message="No incoming message found",
                    field="incoming_message",
                    details={"error": "missing_message"}
                )

            # Get message text
            message_type = incoming_message.get("type", "")
            if message_type != "text":
                logger.error(f"Unsupported message type for OTP verification: {message_type}")
                return ValidationResult.failure(
                    message="Unsupported message type for OTP verification",
                    field="message_type",
                    details={"error": "invalid_message_type", "type": message_type}
                )

            message_text = incoming_message.get("text", {}).get("body", "")
            if not message_text:
                logger.error("Empty message text")
                return ValidationResult.failure(
                    message="Empty message text",
                    field="message_text",
                    details={"error": "empty_message"}
                )

            # Check if message starts with VERIFY command (case insensitive)
            if not re.match(r'^verify\s+', message_text, re.IGNORECASE):
                error_msg = "Invalid verification format. Please send a message starting with 'VERIFY' followed by your 6-digit code."
                self._send_response(f"❌ {error_msg}")
                return ValidationResult.failure(
                    message=error_msg,
                    field="message_format",
                    details={"error": "invalid_format"}
                )

            # Extract OTP from message
            otp_match = re.search(r'verify\s+(\d+)', message_text, re.IGNORECASE)
            if not otp_match:
                error_msg = "Could not find a verification code in your message. Please send 'VERIFY' followed by your 6-digit code."
                self._send_response(f"❌ {error_msg}")
                return ValidationResult.failure(
                    message=error_msg,
                    field="otp",
                    details={"error": "missing_otp"}
                )

            otp = otp_match.group(1).strip()

            # Validate OTP format (6 digits)
            if not otp.isdigit() or len(otp) != 6:
                error_msg = "Invalid verification code format. Please send a 6-digit code."
                self._send_response(f"❌ {error_msg}")
                return ValidationResult.failure(
                    message=error_msg,
                    field="otp",
                    details={"error": "invalid_otp_format"}
                )

            # Get channel ID from state
            channel_id = self.state_manager.get_channel_id()
            if not channel_id:
                logger.error("No channel ID found in state")
                return ValidationResult.failure(
                    message="No channel ID found",
                    field="channel_id",
                    details={"error": "missing_channel_id"}
                )

            # Extract phone number from channel_id (remove WhatsApp prefix if present)
            phone = channel_id.replace('whatsapp:', '')

            # Log environment variables for debugging
            logger.info(f"Using MYCREDEX_APP_URL: {CREDEX_API_URL}")
            logger.info(f"CLIENT_API_KEY set: {bool(API_KEY)}")

            # Send verification request
            endpoint = f"{CREDEX_API_URL}/verify/validateChatbotOtp"
            headers = {
                "Content-Type": "application/json",
                "x-client-api-key": API_KEY
            }
            payload = {
                "otp": otp,
                "phone": phone,
                "source": "chatbot"
            }

            logger.info(f"Sending OTP verification request to: {endpoint}")
            logger.info(f"Request payload: {payload}")

            try:
                response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
                logger.info(f"Response status code: {response.status_code}")
                logger.info(f"Response content: {response.text}")
                response_data = response.json()
                logger.info(f"Response data: {response_data}")
            except Exception as e:
                logger.error(f"Error making request to credex-core: {str(e)}")
                error_msg = "An error occurred during verification. Please try again later."
                self._send_response(f"❌ {error_msg}")
                return ValidationResult.failure(
                    message=f"API request failed: {str(e)}",
                    field="api_request",
                    details={"error": str(e)}
                )

            if response.status_code == 200:
                logger.info("OTP verification successful")
                self._send_response(
                    "✅ Verification successful! Head back to the VimbisoPay app to continue."
                )
                self.set_result("verification_success")
                return ValidationResult.success(response_data)
            else:
                error_message = response_data.get("message", "Unknown error")
                logger.error(f"OTP verification failed: {error_message}")
                self._send_response(f"❌ Verification failed: {error_message}")
                self.set_result("verification_failed")
                return ValidationResult.failure(
                    message=f"Verification failed: {error_message}",
                    field="verification",
                    details={"error": error_message, "response": response_data}
                )

        except Exception as e:
            logger.exception(f"Error in OTP verification: {str(e)}")
            error_msg = "An error occurred during verification. Please try again later."
            self._send_response(f"❌ {error_msg}")
            return ValidationResult.failure(
                message=f"Verification error: {str(e)}",
                field="verification",
                details={"error": str(e)}
            )

    def _send_response(self, message_text: str) -> None:
        """Send response message through messaging service"""
        if not self.state_manager or not self.state_manager.messaging:
            logger.error("Cannot send response: messaging service not available")
            return

        try:
            # Send text message
            self.state_manager.messaging.send_text(message_text)
        except Exception as e:
            logger.error(f"Error sending response message: {str(e)}")
