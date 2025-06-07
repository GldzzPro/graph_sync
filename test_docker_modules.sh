#!/bin/bash
# test_docker_modules.sh — Test script for Docker environment

set -euo pipefail

# Docker service URLs (accessible from host)
GRAPHSYNC_URL="http://localhost:8000"
NEO4J_SYNC_URL="http://localhost:8001"
LOG_FILE="docker_sync.log"

echo "🐳 Testing GraphSync in Docker environment..."

# Check if services are running
echo "🔍 Checking if services are running..."
if ! curl -s "$GRAPHSYNC_URL/healthcheck" >/dev/null 2>&1; then
  echo "❌ GraphSync service not running on $GRAPHSYNC_URL"
  echo "💡 Run: docker-compose up -d graphsync"
  exit 1
fi

if ! curl -s "$NEO4J_SYNC_URL/healthcheck" >/dev/null 2>&1; then
  echo "❌ Neo4j Sync service not running on $NEO4J_SYNC_URL"
  echo "💡 Run: docker-compose up -d neo4j_sync"
  exit 1
fi

echo "✅ Both services are running"

# Trigger sync operation
echo "🔄 Triggering sync operation..."
SYNC_RESPONSE=$(curl -s -X POST "$GRAPHSYNC_URL/trigger" \
  -H "Content-Type: application/json" \
  -d '{"category_prefixes": ["Custom"], "include_reverse": true, "options": {"exact_match": false, "include_subcategories": true, "max_depth": null, "stop_domains": [], "exclude_domains": []}}')

echo "📊 Sync response: $SYNC_RESPONSE"

# Send to Neo4j
echo "🔄 Sending to Neo4j..."
INGEST_PAYLOAD=$(echo "$SYNC_RESPONSE" | jq '{responses: .}')
INGEST_RESPONSE=$(curl -s -X POST "$NEO4J_SYNC_URL/api/graph/ingest" \
  -H "Content-Type: application/json" \
  -d "$INGEST_PAYLOAD")

echo "📊 Neo4j response: $INGEST_RESPONSE"
echo "✅ Docker test completed successfully!"