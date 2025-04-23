# GraphSync: Odoo-to-Neo4j Module Dependency Synchronization

A Python FastAPI microservice that synchronizes Odoo module dependency data to Neo4j graph database.

## Overview

GraphSync fetches module dependency information from Odoo instances via JSON-RPC calls to the `/api/graph/module` and `/api/graph/reverse` endpoints, then loads this data into a Neo4j graph database for visualization and analysis.

## Features

- Configuration via environment variables and YAML file
- FastAPI HTTP endpoint for triggering sync jobs
- Support for multiple Odoo instances
- Tagging of nodes with instance information
- Docker and docker-compose support

## Project Structure

```
./
├── app.py                 # Main FastAPI application
├── config.py              # Configuration management
├── fetcher.py             # Odoo API data fetching
├── loader.py              # Neo4j database loading
├── models.py              # Data models
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Service orchestration
├── config.yaml.example    # Example configuration
└── .env.example           # Example environment variables
```

## Setup

1. Copy `.env.example` to `.env` and configure environment variables
2. Copy `config.yaml.example` to `config.yaml` and configure Odoo instances
3. Install dependencies: `pip install -r requirements.txt`
4. Run the service: `uvicorn app:app --reload`

## Docker Deployment

```bash
docker-compose up -d
```

## API Usage

Trigger a sync job:

```bash
curl -X POST http://localhost:8000/trigger
```

## License

MIT