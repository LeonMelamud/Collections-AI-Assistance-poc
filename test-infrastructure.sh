#!/bin/bash

# Vibe Kanban - Infrastructure Test Script
# Tests the Docker infrastructure setup

set -e

echo "🐋 Testing Vibe Kanban Docker Infrastructure..."

# Test docker-compose configuration
echo "✅ Testing docker-compose configuration..."
docker-compose config > /dev/null
echo "   Configuration is valid"

# Start infrastructure services
echo "🚀 Starting infrastructure services..."
docker-compose up -d postgres redis qdrant

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

# Test PostgreSQL
echo "🐘 Testing PostgreSQL..."
docker exec vibe-kanban-postgres pg_isready -U postgres
echo "   PostgreSQL is ready"

# Test Redis
echo "🟥 Testing Redis..."
docker exec vibe-kanban-redis redis-cli -a redis_password ping > /dev/null
echo "   Redis is ready"

# Test Qdrant
echo "🎯 Testing Qdrant..."
curl -sf http://localhost:6333/collections > /dev/null
echo "   Qdrant is ready"

# Test data persistence
echo "💾 Testing data persistence..."

# Insert test data
docker exec vibe-kanban-postgres psql -U postgres -d vibe_kanban_dev -c "INSERT INTO users (email, username, password_hash, first_name, last_name) VALUES ('persist@test.com', 'persistuser', 'hash123', 'Persist', 'Test');" > /dev/null

docker exec vibe-kanban-redis redis-cli -a redis_password set persist_test "persistence_works" > /dev/null 2>&1

# Restart services
docker-compose restart postgres redis qdrant > /dev/null
sleep 10

# Verify data persisted
POSTGRES_DATA=$(docker exec vibe-kanban-postgres psql -U postgres -d vibe_kanban_dev -t -c "SELECT COUNT(*) FROM users WHERE email = 'persist@test.com';" | tr -d ' ')
REDIS_DATA=$(docker exec vibe-kanban-redis redis-cli -a redis_password get persist_test 2>/dev/null)

if [ "$POSTGRES_DATA" = "1" ] && [ "$REDIS_DATA" = "persistence_works" ]; then
    echo "   Data persistence verified ✅"
else
    echo "   Data persistence failed ❌"
    exit 1
fi

# Check volumes
echo "📦 Docker volumes created:"
docker volume ls | grep vk-c6c1-docker-inf

# Check network
echo "🌐 Docker network created:"
docker network ls | grep vibe-network

echo ""
echo "🎉 Infrastructure test completed successfully!"
echo ""
echo "Services running:"
docker-compose ps

echo ""
echo "To stop services: docker-compose down"
echo "To remove volumes: docker-compose down -v"