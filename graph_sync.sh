#!/bin/bash

# Graph Sync Microservice Control Script

set -e

function show_help {
  echo "Usage: $0 [command] [options]"
  echo ""
  echo "Commands:"
  echo "  start         Start the microservice"
  echo "  stop          Stop the microservice"
  echo "  restart       Restart the microservice"
  echo "  status        Check the status of the microservice"
  echo "  healthcheck   Check the health of the microservice"
  echo "  trigger       Trigger a sync operation"
  echo "  logs          View the logs of the microservice"
  echo ""
  echo "Options for 'trigger':"
  echo "  --category-prefixes=<prefixes>  Comma-separated list of category prefixes (default: Custom)"
  echo "  --include-reverse=<bool>        Include reverse dependencies (default: true)"
  echo "  --exact-match=<bool>            Match exact category names, not prefixes (default: false)"
  echo "  --include-subcategories=<bool>  Include modules from subcategories (default: true)"
  echo "  --max-depth=<int>               Maximum depth for dependency traversal (default: null for unlimited)"
  echo ""
  echo "Examples:"
  echo "  $0 start"
  echo "  $0 trigger --category-prefixes=Custom,Technical --include-reverse=true"
}

function start {
  echo "Starting Graph Sync microservice..."
  docker-compose up -d
}

function stop {
  echo "Stopping Graph Sync microservice..."
  docker-compose down
}

function restart {
  echo "Restarting Graph Sync microservice..."
  docker-compose restart
}

function status {
  echo "Graph Sync microservice status:"
  docker-compose ps
}

function healthcheck {
  echo "Checking health of Graph Sync microservice..."
  curl -s http://localhost:8000/healthcheck | jq
}

function trigger {
  # Default values
  CATEGORY_PREFIXES="Custom"
  INCLUDE_REVERSE="true"
  EXACT_MATCH="false"
  INCLUDE_SUBCATEGORIES="true"
  MAX_DEPTH="null"
  
  # Parse arguments
  for arg in "$@"; do
    case $arg in
      --category-prefixes=*)
        CATEGORY_PREFIXES="${arg#*=}"
        ;;
      --include-reverse=*)
        INCLUDE_REVERSE="${arg#*=}"
        ;;
      --exact-match=*)
        EXACT_MATCH="${arg#*=}"
        ;;
      --include-subcategories=*)
        INCLUDE_SUBCATEGORIES="${arg#*=}"
        ;;
      --max-depth=*)
        MAX_DEPTH="${arg#*=}"
        ;;
    esac
  done
  
  # Convert comma-separated categories to JSON array
  CATEGORIES_JSON="[$(echo $CATEGORY_PREFIXES | sed 's/,/","/g' | sed 's/^/"/' | sed 's/$/"/' | sed 's/,/, /g')]"
  
  # Prepare JSON payload
  PAYLOAD='{
    "category_prefixes": '$CATEGORIES_JSON',
    "include_reverse": '$INCLUDE_REVERSE',
    "options": {
      "exact_match": '$EXACT_MATCH',
      "include_subcategories": '$INCLUDE_SUBCATEGORIES',
      "max_depth": '$MAX_DEPTH'
    }
  }'
  
  echo "Triggering sync with payload: $PAYLOAD"
  
  # Send request to trigger endpoint
  curl -X POST \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    http://localhost:8000/trigger | jq
}

function logs {
  echo "Viewing logs of Graph Sync microservice..."
  docker-compose logs -f
}

# Main script logic
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

COMMAND=$1
shift

case $COMMAND in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    restart
    ;;
  status)
    status
    ;;
  healthcheck)
    healthcheck
    ;;
  trigger)
    trigger "$@"
    ;;
  logs)
    logs
    ;;
  help)
    show_help
    ;;
  *)
    echo "Unknown command: $COMMAND"
    show_help
    exit 1
    ;;
esac