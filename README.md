# Vimbiso ChatServer

Secure credex ecosystem account and transaction management via WhatsApp and SMS. Operations secured by auditable digital signatures through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API.

## Core Features

#### Member Operations
- Login
- Onboard and open an account
- Upgrade member tier

#### Account Operations
- Account dashboard with multi-denominational balance display
- View account ledgers with pagination

#### Credex Operations
- Offer secured credex in CXX, XAU, USD, CAD
- Accept/decline/cancel credex offers
- View credex details

## Core Architecture

The system follows a specific message flow pattern through five core pillars:

### 1. Flow Headquarters
- Manages member flows through the application
- Receives incoming messages and initializes state
- Controls flow through awaiting_input mechanism
- Determines next steps through pattern matching

### 2. State Manager
- Single source of truth for all data
- Schema validation for core state
- Component freedom in data storage
- Clear state boundaries

### 3. Component System
- Self-contained operational units
- Display components for UI/messaging
- Input components for validation
- API components for external calls
- Confirm components for authorizations

### 4. API Services
- Integration with credex-core API
- State-based API handling
- Clear validation patterns
- Standard error handling

### 5. Messaging System
- Channel-agnostic messaging (WhatsApp, SMS)
- Stateless message sending
- Flow control through awaiting_input
- Clear component boundaries

See [Architecture Documentation](docs/architecture.md) for detailed implementation patterns and guidelines.

## Infrastructure

See [Infrastructure Documentation](docs/infrastructure.md) for detailed deployment, security, and operations guidelines.

## Quick Start

### Development Environment
```bash
# Build and start services (combined command)
make dev

# Or use individual commands if needed:
make dev-build
make dev-up
make dev-down

# Access services (from host machine)
Application: http://localhost:8000
Mock WhatsApp: http://localhost:8001

# Note: Within Docker network, services communicate using:
- App service: http://app:8000
- Redis: redis://redis:6379
- Mock WhatsApp: http://mock:8001
```

### Production Environment
```bash
# Build and start services (combined command)
make prod

# Or use individual commands if needed:
make prod-build
make prod-up
make prod-down
```

### Fetching Logs
The `scripts/fetchlogs.sh` script allows you to fetch CloudWatch logs from the development environment. It supports both real-time log streaming and historical log retrieval.

Requirements:
- AWS CLI installed
- AWS credentials configured with the following environment variables:
  ```bash
  export AWS_ACCESS_KEY_ID='your_access_key'
  export AWS_SECRET_ACCESS_KEY='your_secret_key'
  ```

Usage:
```bash
# Stream logs in real-time
fetchlogs

# Fetch historical logs in seconds
fetchlogs 60
```

## Development Tools

### Mock WhatsApp Interface
Test the WhatsApp chatserver without hitting WhatsApp:

```bash
# Start all services including mock server
make dev
```

### API Testing
Test API endpoints and webhooks using the mock server.

### AI-Assisted Merge Summaries
Generate diffs for AI-assisted summarization in merge requests:

```bash
make diff <source_branch> <target_branch>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Public domain.
