# Graph Sync Microservice

A stateless microservice for fetching module dependency data from multiple Odoo Docker container instances.

## Overview

This microservice provides a simple way to fetch module dependency information from multiple Odoo instances. It exposes two main endpoints:

- `/healthcheck` - Verify the service is running and view configured instances
- `/trigger` - Fetch module dependency data from all configured instances

The service is designed to be completely stateless, with configuration provided via a `config.yml` file or environment variables. It supports asynchronous JSON-RPC requests to multiple Odoo instances and combines the results.

## Configuration

### config.yml

Create a `config.yml` file with your Odoo instances:

```yaml
# Docker Container Instances Configuration
instances:
  - name: "odoo1"
    url: "http://odoo1:8069"
  
  - name: "odoo2"
    url: "http://odoo2:8069"

# Logging Configuration
log_level: "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Environment Variables

You can also configure instances via environment variables:

- `CONFIG_PATH` - Path to the config.yml file
- `DOCKER_INSTANCES` - Comma-separated list of instances in format `name1:url1,name2:url2`
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Running the Service

### Using Docker Compose

```bash
docker-compose up -d
```

### Using the Control Script

A control script is provided for easy management:

```bash
# Start the service
./graph_sync.sh start

# Check health
./graph_sync.sh healthcheck

# Trigger a sync
./graph_sync.sh trigger --module-ids=333,334 --include-reverse=true

# View logs
./graph_sync.sh logs

# Stop the service
./graph_sync.sh stop
```

### Using GitHub Workflow

You can also control the service using the provided GitHub workflow:

1. Go to the Actions tab in your GitHub repository
2. Select the "Graph Sync Microservice" workflow
3. Click "Run workflow"
4. Choose the action (deploy, trigger, healthcheck)
5. Provide any required parameters
6. Click "Run workflow"

## API Endpoints

### Health Check

```
GET /healthcheck
```

Response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "service": "graph_sync",
  "details": {
    "instances": 3,
    "instance_names": ["odoo1", "odoo2", "odoo3"]
  }
}
```

### Trigger Sync

```
POST /trigger
```

Request Body:
```json
{
  "module_ids": [333, 334],  // Optional: List of module IDs to fetch
  "category_prefixes": ["Custom"],  // Optional: List of category prefixes to filter modules
  "max_depth": 3,  // Optional: Maximum depth for dependency traversal (null for unlimited)
  "include_reverse": true  // Optional: Whether to include reverse dependencies
}
```

Response:
```json
[
  {
    "instance": "odoo1",
    "status": "success",
    "data": {
      "nodes": [...],
      "edges": [...]
    }
  },
  {
    "instance": "odoo2",
    "status": "error",
    "error": "Instance odoo2 is not healthy or not reachable"
  },
  {
    "instance": "odoo3",
    "status": "success",
    "data": {
      "nodes": [...],
      "edges": [...]
    }
  }
]
```

Request body:
```json
{
  "module_ids": [333, 334],
  "category_prefixes": ["Custom"],
  "max_depth": null,
  "include_reverse": true
}
```

Response:
```json
[
  {
    "instance": "odoo1",
    "data": {
      "nodes": [...],
      "edges": [...]
    },
    "status": "success"
  },
  {
    "instance": "odoo2",
    "data": {
      "nodes": [...],
      "edges": [...]
    },
    "status": "success"
  }
]
```

## Development

### Prerequisites

- Python 3.11+
- Docker and Docker Compose

### Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `config.yml` file
6. Run the service: `uvicorn app:app --reload`

### Testing

Run tests with pytest:

```bash
pytest
```