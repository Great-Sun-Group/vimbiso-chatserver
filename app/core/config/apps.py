import os
import logging
from pathlib import Path
from django.apps import AppConfig
from django.conf import settings
from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        """Perform startup checks and initialization"""
        logger.info("Initializing Core application...")

        try:
            # Ensure data directories exist
            logger.debug(f"Checking data directories in {settings.BASE_PATH}")
            for subdir in ['static', 'media', 'logs']:
                path = Path(settings.BASE_PATH) / subdir
                if not path.exists():
                    logger.info(f"Creating directory: {path}")
                    path.mkdir(parents=True, exist_ok=True)
                    os.chmod(path, 0o755)

            # Ensure database directory exists
            db_dir = Path(settings.DATABASES['default']['NAME']).parent
            if not db_dir.exists():
                logger.info(f"Creating database directory: {db_dir}")
                db_dir.mkdir(parents=True, exist_ok=True)
                os.chmod(db_dir, 0o755)

            # Test Redis connection
            logger.debug("Testing Redis connection...")
            try:
                # Test low-level Redis connection
                redis_conn = get_redis_connection("default")
                info = redis_conn.info()
                logger.debug(f"Redis version: {info.get('redis_version')}")
                logger.debug(f"Connected clients: {info.get('connected_clients')}")
                logger.debug(f"Used memory: {info.get('used_memory_human')}")

                # Test Django cache interface
                from django.core.cache import cache
                cache.set('startup_test', 'ok', 5)
                result = cache.get('startup_test')
                if result != 'ok':
                    logger.error("Redis cache test failed")
                else:
                    logger.info("Redis connection tests successful")

            except Exception as e:
                logger.error(f"Redis connection error: {str(e)}")

            logger.info("Core application initialization complete")

        except Exception as e:
            logger.error(f"Error during application initialization: {str(e)}")
            # Don't raise the error - let the app try to start anyway
            # The health check will catch any critical issues
