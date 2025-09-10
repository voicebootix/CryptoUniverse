# Project Structure

## Root Directory Organization

```
cryptouniverse-enterprise/
├── app/                    # Main application package
├── frontend/              # React TypeScript frontend
├── alembic/              # Database migrations
├── tests/                # Test suite
├── docs/                 # Documentation
├── testsprite_tests/     # TestSprite integration tests
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Local development setup
├── Dockerfile*          # Container definitions
└── .env.example        # Environment template
```

## Backend Application Structure (`app/`)

```
app/
├── api/                 # API layer
│   ├── dependencies/    # Dependency injection
│   └── v1/             # API version 1 routes
├── core/               # Core functionality
│   ├── config.py       # Settings and configuration
│   ├── database.py     # Database connection and setup
│   ├── security.py     # Authentication and security
│   ├── redis.py        # Redis connection management
│   └── logging.py      # Structured logging setup
├── middleware/         # Custom middleware
│   ├── auth.py         # Authentication middleware
│   ├── tenant.py       # Multi-tenant isolation
│   ├── rate_limit.py   # Rate limiting
│   └── logging.py      # Request logging
├── models/            # SQLAlchemy models
│   ├── user.py        # User and authentication models
│   ├── trading.py     # Trading-related models
│   ├── ai.py          # AI service models
│   ├── chat.py        # Chat system models
│   └── ...            # Other domain models
├── services/          # Business logic services
│   ├── ai_consensus.py     # AI consensus engine
│   ├── trade_execution.py  # Trade execution service
│   ├── market_analysis.py  # Market analysis service
│   ├── background.py       # Background service manager
│   ├── websocket.py        # WebSocket management
│   └── ...                # Other services
├── tasks/             # Background tasks (Celery)
└── utils/             # Utility functions
```

## Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── components/    # Reusable UI components
│   ├── pages/        # Page components
│   ├── hooks/        # Custom React hooks
│   ├── stores/       # Zustand state stores
│   ├── services/     # API service layer
│   ├── types/        # TypeScript type definitions
│   ├── utils/        # Utility functions
│   └── styles/       # Global styles
├── public/           # Static assets
├── dist/            # Build output
├── package.json     # Node.js dependencies
├── vite.config.ts   # Vite configuration
└── tailwind.config.js # Tailwind CSS config
```

## Key Architectural Patterns

### API Layer (`app/api/`)
- RESTful API design with FastAPI
- Versioned routes under `/api/v1/`
- Dependency injection for database sessions, authentication
- Pydantic models for request/response validation

### Service Layer (`app/services/`)
- Business logic separated from API controllers
- Async/await pattern throughout
- Service classes with dependency injection
- Background services managed by `BackgroundServiceManager`

### Model Layer (`app/models/`)
- SQLAlchemy 2.0 with async support
- Declarative base with proper relationships
- Enum classes for status fields
- UUID primary keys for security

### Middleware Stack
- Applied in reverse order (last added = first executed)
- Authentication → Tenant isolation → Rate limiting → Logging
- CORS configured for multi-origin support

## Configuration Management

### Environment Files
- `.env.example` - Template with all required variables
- `.env` - Local development (gitignored)
- Environment-specific configs in `app/core/config.py`

### Settings Pattern
- Pydantic Settings for type-safe configuration
- Environment variable validation
- Computed fields for derived values (CORS origins, allowed hosts)

## Database Management

### Migrations (`alembic/`)
- Alembic for schema versioning
- Auto-generated migrations with manual review
- Environment-aware configuration
- Rollback support for safe deployments

### Connection Management
- Async SQLAlchemy engine
- Connection pooling configured
- Database manager for lifecycle management
- Health checks for monitoring

## Testing Structure (`tests/`)

```
tests/
├── api/              # API endpoint tests
├── e2e/             # End-to-end tests
├── test_config.py   # Test configuration
└── ...              # Unit tests by module
```

## Deployment Artifacts

### Docker
- Multi-stage builds for optimization
- Separate Dockerfiles for backend/frontend
- Health checks configured
- Non-root user for security

### Process Management
- Gunicorn with Uvicorn workers for production
- Graceful shutdown handling
- Background service lifecycle management
- System monitoring and metrics

## File Naming Conventions

- **Python**: snake_case for files and functions
- **TypeScript**: camelCase for variables, PascalCase for components
- **Configuration**: kebab-case for Docker/YAML files
- **Database**: snake_case for tables and columns
- **API Routes**: kebab-case in URLs, snake_case in code

## Import Organization

- Standard library imports first
- Third-party imports second
- Local application imports last
- Absolute imports preferred over relative
- Type imports separated when using `from __future__ import annotations`