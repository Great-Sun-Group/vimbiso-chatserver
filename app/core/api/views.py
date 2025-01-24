"""Cloud API webhook views"""
import logging
import sys
import time
import socket
from core.messaging.service import MessagingService
from core.messaging.types import Message as DomainMessage
from core.messaging.types import MessageRecipient, TemplateContent
from core.state.manager import StateManager
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
from django.conf import settings
import redis

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
    def get_redis_info():
        """Get detailed Redis connection info"""
        redis_url = settings.CACHES['default']['LOCATION']
        host = redis_url.split('//')[1].split(':')[0]
        port = int(redis_url.split(':')[-1].split('/')[0])

        info = {
            "url": redis_url,
            "host": host,
            "port": port,
            "dns": None,
            "socket": None,
            "ping": None,
            "error": None
        }

        try:
            # DNS lookup
            info["dns"] = socket.gethostbyname(host)
        except Exception as e:
            info["error"] = f"DNS lookup failed: {str(e)}"
            return info

        try:
            # Socket connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((info["dns"], port))
            sock.close()
            info["socket"] = "Connected" if result == 0 else f"Failed (error: {result})"
        except Exception as e:
            info["error"] = f"Socket connection failed: {str(e)}"
            return info

        try:
            # Redis ping test
            r = redis.Redis(host=host, port=port, socket_timeout=1)
            info["ping"] = r.ping()
        except Exception as e:
            info["error"] = f"Redis ping failed: {str(e)}"

        return info

    @staticmethod
    def get(request):
        max_retries = 3
        retry_delay = 1  # seconds
        health_check_key = 'health_check'
        health_check_ttl = 5  # seconds

        health_data = {
            "status": "unhealthy",
            "redis": {
                "status": "disconnected",
                "attempts": [],
                "info": None
            }
        }

        for attempt in range(max_retries):
            try:
                # Get Redis diagnostics
                redis_info = HealthCheck.get_redis_info()
                health_data["redis"]["info"] = redis_info

                attempt_data = {
                    "attempt": attempt + 1,
                    "timestamp": time.time(),
                }

                # Try to set a value in Redis
                cache.set(health_check_key, 'ok', health_check_ttl)
                time.sleep(0.1)  # Wait for propagation
                result = cache.get(health_check_key)

                if result == 'ok':
                    health_data["status"] = "healthy"
                    health_data["redis"]["status"] = "connected"
                    attempt_data["success"] = True
                    health_data["redis"]["attempts"].append(attempt_data)
                    return JsonResponse(health_data, status=status.HTTP_200_OK)

                attempt_data["success"] = False
                attempt_data["error"] = "Value mismatch"
                health_data["redis"]["attempts"].append(attempt_data)
                logger.warning(f"Health check value mismatch on attempt {attempt + 1}")

            except Exception as e:
                attempt_data = {
                    "attempt": attempt + 1,
                    "timestamp": time.time(),
                    "success": False,
                    "error": str(e)
                }
                health_data["redis"]["attempts"].append(attempt_data)
                logger.error(f"Health check attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        return JsonResponse(health_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)


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
