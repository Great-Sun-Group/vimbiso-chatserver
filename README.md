# VimbisoPay

A WhatsApp bot service that facilitates financial transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in a secure WhatsApp chat.

### Quick Start
After cloning and setting up environment variables, or activation of a codespace:

Development environment:
```bash
# Build development environment
make dev-build

# Start development server
make dev-up

# Stop development server
make dev-down
```

Production environment:
```bash
# Build production environment
make prod-build

# Start production server (detached mode)
make prod-up

# Stop production server
make prod-down
```

The application will be available at http://localhost:8000

### Development Tools

#### Mock WhatsApp Interface
A development tool for testing the WhatsApp bot without needing real WhatsApp credentials:

```bash
# Start the mock WhatsApp interface (with hot reload)
make mockery

# Stop the mock WhatsApp interface
make mockery-down
```

The mock interface will be available at http://localhost:8001 and provides:
- Custom phone numbers and usernames for testing different users
- Support for text, button, and interactive messages
- Real-time conversation history
- WhatsApp-style chat interface
- Detailed message logging in the server console
- Hot reload - server automatically restarts when code changes

##### CLI Interface
You can also interact with the mock WhatsApp interface through the command line:

```bash
# Send a basic text message
./mock/cli.py "Hello, world!"

# Send a message with custom phone and username
./mock/cli.py --phone 1234567890 --username "Test User" "Hello!"

# Send a button response
./mock/cli.py --type button "button_1"

# Send an interactive message
./mock/cli.py --type interactive "menu_option_1"

# Use a different port (if mock server is running on different port)
./mock/cli.py --port 8002 "Hello!"
```

## Core Features

### Financial Operations
- Secured credex transactions with immediate settlement
- Unsecured credex with configurable due dates (up to 5 weeks)
- Multi-tier account system:
  - Personal accounts with basic features
  - Business accounts with advanced capabilities
  - Member authorization management
- Balance tracking with denomination support
- Transaction history with pagination
- Pending offers management:
  - Individual and bulk acceptance
  - Offer cancellation
  - Review of incoming/outgoing offers

### WhatsApp Interface
- Interactive menus and buttons
- Form-based data collection with validation
- Rich message formatting with emojis
- State-based conversation flow with Redis persistence:
  - 5-minute session timeout
  - Automatic state cleanup
  - Cross-device state sync(?)
- Time-aware greetings and messages
- Navigation commands:
  - `menu` - Return to main menu
  - `x` or `c` - Cancel current operation
  - `home` - Return to account dashboard
- Custom message templates for:
  - Account balances and limits
  - Transaction history
  - Offer confirmations
  - Error messages
  - Status updates
- Notification preferences per account

### Security
- JWT authentication with configurable lifetimes
- Rate limiting (100/day anonymous, 1000/day authenticated)
- XSS protection and HSTS
- CORS configuration
- Input validation and sanitization
- Secure state management

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Access to Credex Core API development server
- WhatsApp Business API credentials from Meta

### Development Features
- Live code reloading
- Django Debug Toolbar
- Redis for state management
- Console email backend
- Comprehensive logging
- Mock WhatsApp interface for testing (web and CLI)
- Hot reload for mock server

### Code Quality
```bash
# Format and lint
black .
isort .
flake8

# Type checking
mypy .

# Run tests
pytest --cov=app
```

## Production Deployment
See [Deployment Documentation](docs/deployment.md).

### Docker Configuration
- Multi-stage builds
- Security-hardened production image
- Non-privileged user
- Gunicorn with gevent workers
- Health monitoring

### Server Configuration
```bash
# Build production image
docker build --target production -t vimbiso-pay:latest .

# Run with production settings
docker run -d \
  --name vimbiso-pay \
  -p 8000:8000 \
  -e DJANGO_ENV=production \
  [additional environment variables]
  vimbiso-pay:latest
```

### Health Monitoring
- Built-in health checks (30s interval)
- Redis connection monitoring
- API integration verification
- Comprehensive logging

## Troubleshooting

### Common Issues
1. API Connection
   - Verify API URL and credentials
   - Check network connectivity
   - Validate JWT token

2. WhatsApp Integration
   - Verify API credentials
   - Test webhook configuration
   - Check message templates
   - Use mock interface (web or CLI) for local testing

3. State Management
   - Verify Redis connection
   - Check session timeouts (5 minutes)
   - Monitor state transitions
   - Test state flows using mock interface

### Debug Mode
- Django Debug Toolbar at /__debug__/
- Detailed error pages
- Auto-reload on code changes
- Console email backend
- Comprehensive logging
- Mock WhatsApp interface for testing scenarios

## Future Improvements

1. Monitoring
   - JSON logging configuration
   - Error tracking
   - Performance metrics

2. Performance
   - Redis caching strategy
   - Container optimization
   - State management tuning

3. Infrastructure
   - AWS deployment
   - Terraform configurations
   - Production deployment guide
