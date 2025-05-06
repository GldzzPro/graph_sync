# GraphSync: Odoo-to-Neo4j Module Dependency Synchronization

A Python FastAPI microservice that synchronizes Odoo module dependency data to Neo4j graph database.

## Overview

GraphSync connects to Odoo's JSON-RPC API endpoints to fetch module dependency information and loads it into a Neo4j graph database. It supports:

- Fetching modules by category (e.g., "Custom" modules)
- Building forward dependency graphs (what each module depends on)
- Building reverse dependency graphs (what depends on each module)
- Combining both graphs for complete dependency visualization

## Architecture

The service follows a clean architecture with separation of concerns:

- `app.py` - FastAPI application with thin API handlers
- `syncer.py` - Core service layer handling the orchestration of RPC calls and Neo4j ingestion
- `models.py` - Pydantic models for data validation
- `config.py` - Configuration management with environment variable support
- `loader.py` - Neo4j database operations

## Project Structure

```
./
├── app.py                 # Main FastAPI application
├── config.py              # Configuration management
├── syncer.py              # Odoo-Neo4j synchronization service
├── loader.py              # Neo4j database loading
├── models.py              # Data models
├── requirements.txt       # Python dependencies
├── test_graphsync.sh      # Test script
├── Dockerfile             # Container definition
├── docker-compose.yml     # Service orchestration
├── config.yaml.example    # Example configuration
└── .env.example           # Example environment variables
```

## Setup

### Prerequisites

- Python 3.8+
- Neo4j database (local or cloud)
- Odoo instance with the `graph_module_dependency` module installed

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure the service (see Configuration section)
5. Run the service:
   ```bash
   uvicorn app:app --reload
   ```

## Configuration

Configuration can be provided via a YAML file or environment variables:

### Environment Variables

Copy `.env.example` to `.env` and adjust the values:

```
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Odoo Configuration
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
# ODOO_API_KEY=your-api-key

# Logging
LOG_LEVEL=INFO
```

### YAML Configuration

Copy `config.yaml.example` to `config.yaml` and adjust the values.

## Usage

### API Endpoints

#### Trigger Sync

```bash
curl -X POST "http://localhost:8000/trigger" \
  -H "Content-Type: application/json" \
  -d '{"module_ids": [], "category_prefixes": ["Custom"], "max_depth": null, "include_reverse": true}'
```

Parameters:
- `module_ids`: List of module IDs to include (empty to use category_prefixes)
- `category_prefixes`: List of category prefixes to match (default: ["Custom"])
- `max_depth`: Maximum depth to traverse in the dependency graph (null for unlimited)
- `stop_conditions`: Optional list of domain conditions to stop traversal
- `include_reverse`: Whether to include reverse dependencies (default: true)

#### Health Check

```bash
curl "http://localhost:8000/health"
```

## Testing

Run the automated test script:

```bash
./test_graphsync.sh
```

This script:
1. Sets up the environment
2. Starts the FastAPI service
3. Triggers a sync operation
4. Monitors logs for successful completion

## Neo4j Visualization

After synchronization, you can visualize the module dependency graph in Neo4j Browser:

```cypher
MATCH (n:ModuleNode)-[r]->(m:ModuleNode)
RETURN n, r, m
LIMIT 100
```

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT