#!/bin/bash

# OrgMeet Production Startup Script

set -e

echo "Starting OrgMeet in production mode..."

cd "$(dirname "$0")/.."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start services
docker compose up -d

echo ""
echo "OrgMeet is running!"
echo ""
echo "Services:"
echo "  - Frontend:        http://localhost:3000"
echo "  - PocketBase API:  proxied via frontend at /api/"
echo "  - PocketBase Admin: not publicly accessible (use SSH tunnel)"
echo ""
echo "To view logs: docker compose logs -f"
echo "To stop:      docker compose down"
