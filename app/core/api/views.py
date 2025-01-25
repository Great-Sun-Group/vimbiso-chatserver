"""Cloud API webhook views"""
import logging
import sys

from core.messaging.service import MessagingService
from core.messaging.types import Message as DomainMessage
from core.messaging.types import MessageRecipient, TemplateContent
from core.state.manager import StateManager
from core.state.persistence.client import get_redis_client
from core.state.persistence.redis_operations import RedisAtomic
from decouple import config
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView
from services.whatsapp.flow_processor import WhatsAppFlowProcessor
from services.whatsapp.service import WhatsAppMessagingService
from services.whatsapp.state_manager import \
    StateManager as WhatsAppStateManager

# Configure logging with a standardized format
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s", "taskName": null}',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


class HealthCheck(APIView):
    """Health check endpoint for container health monitoring"""
    permission_classes = []
    throttle_classes = []

    @staticmethod
    def get(request):
        # Initialize Redis status
        redis_status = "unhealthy"

        try:
            # Get Redis client the same way the application does
            redis_client = get_redis_client()
            redis_atomic = RedisAtomic(redis_client)

            # Test Redis connectivity using the same atomic operations the app uses
            success, _, error = redis_atomic.execute_atomic(
                key="health_check",
                operation="set",
                value={"status": "ok"},
                ttl=30,  # 30 second TTL for health check
                max_retries=3  # Will retry 3 times with built-in handling
            )

            if success:
                # Verify we can read the value back
                success, result, error = redis_atomic.execute_atomic(
                    key="health_check",
                    operation="get"
                )

                if success and result and result.get("status") == "ok":
                    redis_status = "healthy"
                    logger.info("Redis connection test successful using atomic operations")
                else:
                    logger.warning(f"Redis read verification failed: {error or 'value mismatch'}")
            else:
                logger.warning(f"Redis write operation failed: {error}")

        except Exception as e:
            logger.error(f"Redis client initialization failed: {str(e)}")

        try:
            # Ensure proper JSON structure
            health_status = {
                "status": "healthy",  # Keep app healthy even if Redis is down
                "components": {
                    "app": "healthy",
                    "redis": redis_status
                }
            }

            # Enhanced logging for health status
            logger.info(f"Health check status: {health_status}")

            # Use DRF's Response for consistent JSON handling
            from rest_framework.response import Response
            return Response(
                health_status,
                status=status.HTTP_200_OK,
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Error generating health check response: {str(e)}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_messaging_service(state_manager, channel_type: str):
    """Get properly initialized messaging service with state and channel

    Args:
        state_manager: State manager instance
        channel_type: Type of messaging channel ("whatsapp", "sms")

    Returns:
        MessagingService: Initialized messaging service
    """
    # Create channel-specific service based on type
    if channel_type == "whatsapp":
        channel_service = WhatsAppMessagingService()
    elif channel_type == "sms":
        # TODO: Implement SMS service
        raise NotImplementedError("SMS channel not yet implemented")
    else:
        raise ValueError(f"Unsupported channel type: {channel_type}")

    # Create core messaging service with channel service and state
    messaging_service = MessagingService(
        channel_service=channel_service,
        state_manager=state_manager
    )

    return messaging_service


class CredexCloudApiWebhook(APIView):
    """Cloud Api Webhook"""

    permission_classes = []
    parser_classes = (JSONParser,)
    throttle_classes = []  # Disable throttling for webhook endpoint

    @staticmethod
    def _extract_whatsapp_info(value: dict, is_mock_testing: bool) -> tuple[str, str] | None:
        """Extract WhatsApp channel info from payload"""
        # Validate WhatsApp value
        if not is_mock_testing:
            metadata = value.get("metadata", {})
            if not metadata or metadata.get("phone_number_id") != config("WHATSAPP_PHONE_NUMBER_ID"):
                return None

        # Skip status updates
        if value.get("statuses"):
            return None

        # Get contact info
        contacts = value.get("contacts", [])
        if not contacts:
            return None

        contact = contacts[0]
        if not isinstance(contact, dict):
            return None

        channel_id = contact.get("wa_id")
        if not channel_id:
            return None

        return "whatsapp", channel_id

    @staticmethod
    def _extract_channel_info(value: dict, is_mock_testing: bool) -> tuple[str, str] | None:
        """Extract channel info from payload"""
        if "messaging_product" in value and value["messaging_product"] == "whatsapp":
            return CredexCloudApiWebhook._extract_whatsapp_info(value, is_mock_testing)
        return None

    @staticmethod
    def post(request):
        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Processing webhook request")

            # Validate basic webhook structure
            if not isinstance(request.data, dict):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            entries = request.data.get("entry", [])
            if not entries or not isinstance(entries, list):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            changes = entries[0].get("changes", [])
            if not changes or not isinstance(changes, list):
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Get mock testing flag from header
            is_mock_testing = request.headers.get('X-Mock-Testing') == 'true'
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Mock testing: {is_mock_testing}")

            # Get and validate the raw payload value
            value = changes[0].get("value", {})
            if not value or not isinstance(value, dict):
                logger.debug("Invalid or empty value object")
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            # Add mock testing flag to value metadata if header present
            if is_mock_testing:
                value.setdefault("metadata", {})["mock_testing"] = True
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Updated value metadata: {value.get('metadata')}")

            # Extract channel info from payload
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Extracting channel info from value: {value}")
            channel_info = CredexCloudApiWebhook._extract_channel_info(value, is_mock_testing)
            if not channel_info:
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            channel_type, channel_id = channel_info
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Extracted channel info - type: {channel_type}, id: {channel_id}")

            # Initialize state managers
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Initializing state managers")
            core_state_manager = StateManager(f"channel:{channel_id}")
            state_manager = (
                WhatsAppStateManager(core_state_manager)
                if channel_type == "whatsapp"
                else core_state_manager
            )

            # Initialize channel state with proper enum type
            state_manager.initialize_channel(
                channel_type=channel_type,
                channel_id=channel_id,
                mock_testing=is_mock_testing
            )

            try:
                # Get messaging service for channel
                service = get_messaging_service(state_manager, channel_type)

                # Create flow processor for channel type
                if channel_type == "whatsapp":
                    flow_processor = WhatsAppFlowProcessor(service, state_manager)
                else:
                    raise ValueError(f"Unsupported channel type: {channel_type}")

                # Process message - component handles its own messaging
                flow_processor.process_message(request.data)
                return JsonResponse({"message": "received"}, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Message processing error: {str(e)}")
                return JsonResponse(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return JsonResponse(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request, *args, **kwargs):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Webhook verification request")
        return HttpResponse(request.query_params.get("hub.challenge"), 200)


class WipeCache(APIView):
    """Message"""

    parser_classes = (JSONParser,)

    @staticmethod
    def post(request):
        number = request.data.get("number")
        if number:
            cache.delete(number)
        return JsonResponse({"message": "Success"}, status=status.HTTP_200_OK)


class CredexSendMessageWebhook(APIView):
    """Channel-agnostic message sending webhook"""

    parser_classes = (JSONParser,)
    throttle_classes = []  # Disable throttling for webhook endpoint

    @staticmethod
    def post(request):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Processing send message request")

        # Validate API key
        if request.headers.get("apiKey", "").lower() != config("CLIENT_API_KEY").lower():
            return JsonResponse(
                {"status": "error", "message": "Invalid API key"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Validate required fields
        required_fields = ["phoneNumber", "memberName", "message", "channel"]
        if not all(field in request.data for field in required_fields):
            return JsonResponse(
                {"status": "error", "message": "Missing required fields"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get channel type from request
            channel_type = request.data["channel"].lower()
            if channel_type not in ["whatsapp", "sms"]:
                return JsonResponse(
                    {"status": "error", "message": f"Unsupported channel: {request.data['channel']}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create channel-agnostic message
            recipient = MessageRecipient(
                type=channel_type,
                identifier=request.data["phoneNumber"]
            )

            # Create template message
            message = DomainMessage(
                recipient=recipient,
                content=TemplateContent(
                    name="incoming_notification",
                    language={"code": "en_US"},
                    components=[{
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": request.data["memberName"]
                            },
                            {
                                "type": "text",
                                "text": request.data["message"]
                            }
                        ]
                    }]
                )
            )

            # Get mock testing flag from header
            is_mock_testing = request.headers.get('X-Mock-Testing') == 'true'
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Mock testing: {is_mock_testing}")

            # Create channel-specific service based on type
            if channel_type == "whatsapp":
                service = WhatsAppMessagingService()
            elif channel_type == "sms":
                # TODO: Implement SMS service
                raise NotImplementedError("SMS channel not yet implemented")
            else:
                raise ValueError(f"Unsupported channel type: {channel_type}")

            # Set mock mode in message metadata
            if is_mock_testing:
                message.metadata = message.metadata or {}
                message.metadata["mock_testing"] = True

            # Send through service
            response = service.send_message(message)
            return JsonResponse(response.to_dict(), status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Message sending error: {str(e)}")
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
