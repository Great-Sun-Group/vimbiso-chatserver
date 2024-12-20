import time
import logging
from core.api.tests import test_integrations
from core.api.views import (CredexCloudApiWebhook, CredexSendMessageWebhook,
                            WelcomeMessage, WipeCache)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework import routers
from core.utils.throttling import HealthCheckRateThrottle
from services.state.config import RedisConfig

from api import views


# Create a router and register our viewsets with it
router = routers.DefaultRouter()
router.register(r'companies', views.CompanyViewSet, basename='company')
router.register(r'members', views.MemberViewSet, basename='member')
router.register(r'offers', views.OfferViewSet, basename='offer')


# Health check endpoint with improved error handling and logging
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([HealthCheckRateThrottle])
def health_check(request):
    """
    Enhanced health check endpoint that provides detailed system health status
    """
    status_info = {
        "status": "healthy",
        "message": "Service health status",
        "timestamp": int(time.time()),
        "components": {
            "cache_redis": {
                "status": "unknown",
                "details": {}
            },
            "state_redis": {
                "status": "unknown",
                "details": {}
            }
        }
    }

    # Check cache Redis
    try:
        # Test basic connectivity
        cache.set("health_check", "ok", 10)
        result = cache.get("health_check")

        if result == "ok":
            status_info["components"]["cache_redis"]["status"] = "healthy"
            # Get cache backend info if possible
            if hasattr(cache, '_cache'):
                client = cache._cache.get_client()
                if hasattr(client, 'info'):
                    info = client.info()
                    status_info["components"]["cache_redis"]["details"] = {
                        "connected_clients": info.get('connected_clients', 'N/A'),
                        "used_memory": info.get('used_memory_human', 'N/A'),
                        "role": info.get('role', 'N/A')
                    }
        else:
            status_info["components"]["cache_redis"]["status"] = "degraded"

    except Exception as e:
        logger = logging.getLogger("django")
        logger.warning(f"Cache Redis check failed: {str(e)}")
        status_info["components"]["cache_redis"]["status"] = "unhealthy"
        status_info["components"]["cache_redis"]["error"] = str(e)

    # Check state Redis using enhanced health check
    try:
        redis_config = RedisConfig()
        health_info = redis_config.check_health()

        status_info["components"]["state_redis"].update({
            "status": health_info["status"],
            "details": health_info["details"]
        })

        if health_info["errors"]:
            status_info["components"]["state_redis"]["errors"] = health_info["errors"]

    except Exception as e:
        logger = logging.getLogger("django")
        logger.warning(f"State Redis check failed: {str(e)}")
        status_info["components"]["state_redis"]["status"] = "unhealthy"
        status_info["components"]["state_redis"]["error"] = str(e)

    # Determine overall status
    component_statuses = [
        comp["status"] for comp in status_info["components"].values()
    ]

    if any(status == "unhealthy" for status in component_statuses):
        status_info["status"] = "unhealthy"
        status_info["message"] = "One or more components are unhealthy"
        return JsonResponse(status_info, status=503)
    elif any(status == "degraded" for status in component_statuses):
        status_info["status"] = "degraded"
        status_info["message"] = "One or more components are degraded"
        return JsonResponse(status_info, status=200)
    else:
        status_info["status"] = "healthy"
        status_info["message"] = "All components are healthy"
        return JsonResponse(status_info, status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("api/test-integrations/", test_integrations, name="test_integrations"),
    # Bot endpoints
    path("bot/webhook", CredexCloudApiWebhook.as_view(), name="webhook"),
    path("bot/notify", CredexSendMessageWebhook.as_view(), name="notify"),
    path("bot/welcome/message", WelcomeMessage.as_view(), name="welcome_message"),
    path("bot/wipe", WipeCache.as_view(), name="wipe"),
    # New API endpoints
    path("api/", include(router.urls)),
    path("api/webhooks/", views.webhook_handler, name="webhook-handler"),
]

if settings.DEBUG:
    import debug_toolbar  # type: ignore

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
