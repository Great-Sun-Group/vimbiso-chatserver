"""WhatsApp OTP verification handler

This module provides a handler for OTP verification messages sent via WhatsApp.
It extracts OTP codes from messages starting with "VERIFY" and forwards them
to Credex Core for validation.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

import aiohttp
from core.error.exceptions import ComponentException, SystemException
from core.state.interface import StateManagerInterface

from ..base_handler import format_error_response
from ..types import WhatsAppMessage

logger = logging.getLogger(__name__)

# Get API URL from environment or use default
CREDEX_API_URL = os.getenv('MYCREDEX_APP_URL', 'https://dev.mycredex.dev')
API_KEY = os.getenv('CLIENT_API_KEY', '')


class VerifyOTPHandler:
    """Handle OTP verification messages"""

    @staticmethod
    async def handle_message(message_text: str, channel_id: str, state_manager: Optional[StateManagerInterface] = None) -> WhatsAppMessage:
        """Process verification message

        Args:
            message_text: The message text to process
            channel_id: The WhatsApp channel ID (phone number)
            state_manager: Optional state manager for stateful operation

        Returns:
            WhatsAppMessage: Response message
        """
        try:
            # Extract phone number from channel_id (remove WhatsApp prefix if present)
            phone = channel_id.replace('whatsapp:', '')

            # Check if message starts with VERIFY command (case insensitive)
            if not re.match(r'^verify\s+', message_text, re.IGNORECASE):
                return WhatsAppMessage.create_text(
                    channel_id,
                    "❌ Invalid verification format. Please send a message starting with 'VERIFY' followed by your 6-digit code."
                )

            # Extract OTP from message
            otp_match = re.search(r'verify\s+(\d+)', message_text, re.IGNORECASE)
            if not otp_match:
                return WhatsAppMessage.create_text(
                    channel_id,
                    "❌ Could not find a verification code in your message. Please send 'VERIFY' followed by your 6-digit code."
                )

            otp = otp_match.group(1).strip()

            # Validate OTP format (6 digits)
            if not otp.isdigit() or len(otp) != 6:
                return WhatsAppMessage.create_text(
                    channel_id,
                    "❌ Invalid verification code format. Please send a 6-digit code."
                )

            # Forward to Credex Core for verification
            verification_result = await VerifyOTPHandler.verify_otp_with_credex(otp, phone)

            if verification_result.get("success"):
                # Create a web URL that will redirect to the app
                # WhatsApp will make this URL clickable (unlike custom URL schemes)
                deep_link = f"https://vimbisopay.africa/redirect?dest=vimbisopay://verification-complete&phone={phone}&status=success"
                return WhatsAppMessage.create_text(
                    channel_id,
                    f"✅ Verification successful! You can now return to the app.\n\nTap here to return automatically: {deep_link}"
                )
            else:
                error_message = verification_result.get("message", "Unknown error")
                return WhatsAppMessage.create_text(
                    channel_id,
                    f"❌ Verification failed: {error_message}"
                )

        except ComponentException as e:
            # Component errors become error messages
            logger.error(
                "OTP verification validation error",
                extra={"error": str(e), "channel_id": channel_id}
            )
            return format_error_response(str(e), channel_id)

        except Exception as e:
            # Wrap unexpected errors
            error = SystemException(
                message=str(e),
                code="OTP_VERIFICATION_ERROR",
                service="verify_otp_handler",
                action="handle_message"
            )
            logger.error(
                "OTP verification error",
                extra={"error": str(error), "channel_id": channel_id}
            )
            return format_error_response(str(error), channel_id)

    @staticmethod
    async def verify_otp_with_credex(otp: str, phone: str) -> Dict[str, Any]:
        """Verify OTP with Credex Core

        Args:
            otp: The OTP code to verify
            phone: The phone number that sent the OTP

        Returns:
            Dict[str, Any]: Verification result
        """
        try:
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

            logger.info(f"Sending OTP verification request to Credex Core: {endpoint}")

            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, headers=headers) as response:
                    response_data = await response.json()

                    if response.status == 200:
                        logger.info("OTP verification successful")
                        return {
                            "success": True,
                            "message": "Verification successful",
                            "data": response_data
                        }
                    else:
                        logger.error(f"OTP verification failed: {response_data.get('message', 'Unknown error')}")
                        return {
                            "success": False,
                            "message": response_data.get("message", "Verification failed"),
                            "data": response_data
                        }

        except Exception as e:
            logger.error(f"Error verifying OTP with Credex Core: {str(e)}")
            return {
                "success": False,
                "message": f"Error communicating with verification service: {str(e)}",
                "error": str(e)
            }
