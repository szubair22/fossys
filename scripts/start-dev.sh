#!/bin/bash

# OrgMeet Development Startup Script

set -e

echo "Starting OrgMeet in development mode..."

cd "$(dirname "$0")/.."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
docker compose -f docker-compose.dev.yml up -d

echo ""
echo "OrgMeet is starting up!"
echo ""
echo "Services:"
echo "  - Frontend:        http://localhost:3000"
echo "  - PocketBase API:  http://localhost:8090"
echo "  - PocketBase Admin: http://localhost:8090/_/"
echo ""
echo "To view logs: docker compose -f docker-compose.dev.yml logs -f"
echo "To stop:      docker compose -f docker-compose.dev.yml down"
