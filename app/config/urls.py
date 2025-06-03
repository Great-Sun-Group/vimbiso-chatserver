from core.api.views import (CredexCloudApiWebhook, CredexSendMessageWebhook,
                            WipeCache, HealthCheck)
from django.urls import path, re_path
from django.views.static import serve
from django.conf import settings
import os

# Path to static site files
STATIC_SITE_ROOT = os.path.join(settings.BASE_DIR, 'static_site')

urlpatterns = [
    path("health/", HealthCheck.as_view(), name="health_check"),
    # Bot endpoints
    path("bot/webhook", CredexCloudApiWebhook.as_view(), name="webhook"),
    path("bot/notify", CredexSendMessageWebhook.as_view(), name="notify"),
    path("bot/wipe", WipeCache.as_view(), name="wipe"),

    # Serve static site files with explicit paths
    re_path(r'^(?P<path>css/.*)$', serve, {'document_root': STATIC_SITE_ROOT}),
    re_path(r'^(?P<path>js/.*)$', serve, {'document_root': STATIC_SITE_ROOT}),
    re_path(r'^(?P<path>images/.*)$', serve, {'document_root': STATIC_SITE_ROOT}),
    re_path(r'^(?P<path>fonts/.*)$', serve, {'document_root': STATIC_SITE_ROOT}),
    re_path(r'^(?P<path>.*\.ico)$', serve, {'document_root': STATIC_SITE_ROOT}),

    # Add specific pattern for HTML files
    re_path(r'^(?P<path>.*\.html)$', serve, {'document_root': STATIC_SITE_ROOT}),

    # Specific pattern for the redirect page
    re_path(r'^redirect/?$', serve, {'path': 'redirect.html', 'document_root': STATIC_SITE_ROOT}),

    # Serve index.html at root and any unmatched paths
    re_path(r'^$', serve, {'path': 'index.html', 'document_root': STATIC_SITE_ROOT}),
    re_path(r'^(?!bot/|health/|redirect/).*$', serve, {'path': 'index.html', 'document_root': STATIC_SITE_ROOT}),
]
