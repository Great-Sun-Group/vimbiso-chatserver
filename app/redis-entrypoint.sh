#!/bin/sh
set -e

# Create Redis data directory with proper permissions
mkdir -p /app/data/redis
chown -R redis:redis /app/data/redis

# Start Redis with proper user
exec gosu redis redis-server \
  --protected-mode no \
  --bind 0.0.0.0 \
  --maxmemory 384mb \
  --maxmemory-policy allkeys-lru \
  --dir /app/data/redis \
  --appendonly no \
  --save "" \
  --tcp-keepalive 60
