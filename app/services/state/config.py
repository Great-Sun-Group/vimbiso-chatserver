"""Redis configuration for state management"""
import logging
import time
from typing import Dict, Any
import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from django.conf import settings
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis configuration with optimized settings for state management"""
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        # Use dedicated Redis instance for state management
        self.url = settings.REDIS_STATE_URL
        parsed = urlparse(self.url)

        # Basic settings
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6380
        self.password = parsed.password
        self.db = int(parsed.path[1:]) if parsed.path else 0

        # Connection settings
        self.connection_settings = {
            "socket_timeout": 30,
            "socket_connect_timeout": 30,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "max_connections": 20,
            "decode_responses": True,
            "charset": "utf-8",
            "encoding": "utf-8",
            "retry_on_error": [ConnectionError, TimeoutError],
            "retry_on_timeout": True
        }

        # Retry settings
        self.max_retries = 3
        self.backoff_factor = 1.5
        self._initialized = True

    def _get_connection_pool(self) -> redis.ConnectionPool:
        """Get or create Redis connection pool"""
        if self._pool is None:
            self._pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                **self.connection_settings
            )
            logger.info(f"Created new Redis connection pool for {self.host}:{self.port}")
        return self._pool

    def get_client(self) -> redis.Redis:
        """Get Redis client instance optimized for state management"""
        return redis.Redis(connection_pool=self._get_connection_pool())

    def check_health(self) -> Dict[str, Any]:
        """Check Redis connection health and return status information"""
        health_info = {
            'status': 'healthy',
            'details': {},
            'errors': []
        }

        client = None
        try:
            client = self.get_client()

            # Test basic connectivity
            client.ping()

            # Get server info
            info = client.info()
            health_info['details'] = {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'aof_enabled': info.get('aof_enabled', False),
                'aof_last_write_status': info.get('aof_last_write_status', 'N/A'),
                'role': info.get('role', 'N/A')
            }

            # Check AOF status if enabled
            if info.get('aof_enabled'):
                aof_status = info.get('aof_last_write_status')
                if aof_status != 'ok':
                    health_info['status'] = 'degraded'
                    health_info['errors'].append(
                        f"AOF write status: {aof_status}"
                    )

        except RedisError as e:
            health_info['status'] = 'unhealthy'
            health_info['errors'].append(str(e))
            logger.error(f"Redis health check failed: {str(e)}")

        return health_info

    def execute_with_retry(self, operation, *args, **kwargs):
        """Execute Redis operation with retry logic"""
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                client = self.get_client()
                return operation(client, *args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                attempt += 1
                last_error = e
                if attempt < self.max_retries:
                    backoff = self.backoff_factor ** attempt
                    logger.warning(
                        f"Redis operation attempt {attempt} failed, "
                        f"retrying in {backoff:.1f}s: {str(e)}"
                    )
                    time.sleep(backoff)
                else:
                    logger.error(f"Redis operation failed after {attempt} attempts")
                    raise last_error

    def close_connections(self):
        """Close all connections in the pool"""
        if self._pool:
            try:
                self._pool.disconnect()
                logger.info("Closed all Redis connections in the pool")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {str(e)}")
            finally:
                self._pool = None
