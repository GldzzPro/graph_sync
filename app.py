import logging
import fastapi
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from config import Config
from models import SyncOptions
from fetcher import fetch_all
from loader import ingest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GraphSync",
    description="Odoo-to-Neo4j Module Dependency Synchronization",
    version="1.0.0"
)

# Dependency for configuration
def get_config():
    return Config()


# Request model for trigger endpoint
class TriggerRequest(BaseModel):
    module_ids: Optional[List[int]] = [333]  # Default to module ID 333
    max_depth: Optional[int] = None
    stop_conditions: Optional[List[List[List[Any]]]] = None
    include_reverse: bool = True


# Response model for trigger endpoint
class TriggerResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None


# Background sync task
def sync_task(config: Config, options: Dict[str, Any]):
    try:
        logger.info(f"Starting sync task with options: {options}")
        
        # Fetch data from all instances
        graph = fetch_all(config.instances, options)
        logger.info(f"Fetched {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
        # Ingest data into Neo4j
        ingest(graph, {
            "uri": config.neo4j.uri,
            "username": config.neo4j.username,
            "password": config.neo4j.password
        })
        
        logger.info("Sync task completed successfully")
    except Exception as e:
        logger.error(f"Sync task failed: {str(e)}")


@app.post("/trigger", response_model=TriggerResponse)
async def trigger_sync(
    request: TriggerRequest,
    background_tasks: BackgroundTasks,
    config: Config = Depends(get_config)
):
    """Trigger a sync job to fetch module dependency data and load it into Neo4j."""
    try:
        # Prepare options for fetcher
        options = {
            "module_ids": request.module_ids,
            "max_depth": request.max_depth,
            "stop_conditions": request.stop_conditions,
            "include_reverse": request.include_reverse
        }
        
        # Add task to background tasks
        background_tasks.add_task(sync_task, config, options)
        
        return TriggerResponse(
            status="success",
            message="Sync job started successfully",
            job_id="job-" + str(hash(str(options)))
        )
    except Exception as e:
        logger.error(f"Failed to trigger sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)