# Vibe Kanban - Docker Infrastructure

This repository contains the Docker infrastructure setup for the Vibe Kanban application.

## Services

The application consists of 6 services:

1. **Frontend** - React/Vue/Angular application (Port: 3000)
2. **Backend** - Node.js/Express API server (Port: 8000)
3. **PostgreSQL** - Primary database (Port: 5432)
4. **Redis** - Session management and caching (Port: 6379)
5. **Qdrant** - Vector database for AI features (Port: 6333)
6. **Nginx** - Reverse proxy and load balancer (Port: 80/443)

## Quick Start

1. Clone this repository
2. Copy environment file: `cp .env.example .env`
3. Start all services: `docker-compose up -d`
4. Access the application at: http://localhost

## Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Rebuild and restart services
docker-compose up -d --build

# Remove all containers and volumes
docker-compose down -v

# Check service health
docker-compose ps
```

## Data Persistence

All data is persisted using Docker volumes:
- `postgres_data` - PostgreSQL database files
- `redis_data` - Redis data files
- `qdrant_data` - Qdrant vector database files
- `nginx_logs` - Nginx access and error logs

## Health Checks

All services have health checks configured:
- Frontend: HTTP check on port 3000
- Backend: HTTP check on /health endpoint
- PostgreSQL: pg_isready check
- Redis: Redis ping check
- Qdrant: HTTP check on /health endpoint
- Nginx: HTTP check on /health endpoint

## Network Configuration

Services communicate through a custom Docker network `vibe-network` with subnet 172.20.0.0/16.

## Development

For development, you can mount local directories as volumes to enable hot reloading:

```yaml
volumes:
  - ./frontend:/app
  - ./backend:/app
```

## Production Considerations

Before deploying to production:

1. Change default passwords in `.env`
2. Use proper SSL certificates for Nginx
3. Configure proper backup strategies for data volumes
4. Set up monitoring and logging
5. Configure resource limits for containers