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
  echo "  --module-ids=<ids>       Comma-separated list of module IDs (default: 333)"
  echo "  --include-reverse=<bool> Include reverse dependencies (default: true)"
  echo ""
  echo "Examples:"
  echo "  $0 start"
  echo "  $0 trigger --module-ids=333,334 --include-reverse=true"
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
  MODULE_IDS="333"
  INCLUDE_REVERSE="true"
  
  # Parse arguments
  for arg in "$@"; do
    case $arg in
      --module-ids=*)
        MODULE_IDS="${arg#*=}"
        ;;
      --include-reverse=*)
        INCLUDE_REVERSE="${arg#*=}"
        ;;
    esac
  done
  
  # Convert comma-separated module IDs to JSON array
  MODULE_IDS_JSON="[$(echo $MODULE_IDS | sed 's/,/,/g')]"
  
  # Prepare JSON payload
  PAYLOAD='{"module_ids": '$MODULE_IDS_JSON', "include_reverse": '$INCLUDE_REVERSE'}}'
  
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