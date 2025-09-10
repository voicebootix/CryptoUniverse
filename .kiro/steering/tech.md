# Technology Stack

## Backend Stack

- **Framework**: FastAPI 0.104.1 with async/await
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15+ with SQLAlchemy 2.0.23 (async)
- **Cache**: Redis 7+ for caching and background tasks
- **ORM**: SQLAlchemy with Alembic for migrations
- **Authentication**: JWT with python-jose, bcrypt for password hashing
- **Background Tasks**: Celery with Redis broker
- **WebSockets**: Native FastAPI WebSocket support
- **HTTP Client**: httpx and aiohttp for external API calls

## Frontend Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5.1.0
- **UI Components**: Radix UI primitives with Tailwind CSS
- **State Management**: Zustand, React Query for server state
- **Forms**: React Hook Form with Zod validation
- **Charts**: Recharts for data visualization
- **Real-time**: Socket.IO client for WebSocket connections

## Infrastructure

- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Docker Compose for local development
- **Deployment**: Render.com (production), supports Railway and Fly.io
- **Process Manager**: Gunicorn with Uvicorn workers
- **Monitoring**: Prometheus + Grafana (optional)
- **Logging**: Structlog with JSON formatting

## External Services

- **AI Services**: OpenAI, Anthropic (Claude), Google AI
- **Crypto Exchanges**: CCXT library for unified exchange APIs
- **Payments**: Stripe for subscription billing
- **Email**: SMTP configuration for notifications
- **Telegram**: Bot integration for alerts and commands

## Development Tools

- **Code Quality**: Black (formatting), isort (imports), mypy (type checking)
- **Testing**: pytest with pytest-asyncio
- **Database**: Alembic for schema migrations
- **Environment**: python-dotenv for configuration management

## Common Commands

### Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
python main.py
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Docker Operations
```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale services
docker-compose up --scale api=3 --scale worker=5

# View logs
docker-compose logs -f backend
```

### Production Deployment
```bash
# Build production image
docker build -f Dockerfile.backend -t cryptouniverse-backend .

# Run with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Frontend Development
```bash
# Install dependencies
cd frontend && npm install

# Start development server
npm run dev

# Build for production
npm run build:production

# Type checking
npm run type-check
```

## Configuration

- Environment variables managed through `.env` files
- Pydantic Settings for type-safe configuration
- Separate configs for development/production environments
- CORS origins configurable via environment variables