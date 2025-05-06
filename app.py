import logging
import fastapi
import functools
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from starlette.concurrency import run_in_threadpool

from config import Config
from models import SyncOptions
from syncer import OdooNeo4jSyncService, SyncConfig, OdooConfig, Neo4jConfig, OdooRpcError, Neo4jError

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


# Dependency for sync service
def get_sync_service(config: Config = Depends(get_config)):
    # Convert Config to SyncConfig for the service
    odoo_instance = config.instances[0] if config.instances else None
    if not odoo_instance:
        raise ValueError("No Odoo instance configured")
    
    sync_config = SyncConfig(
        odoo=OdooConfig(
            url=odoo_instance.url,
            db_name=odoo_instance.db_name,
            username=odoo_instance.username,
            password=odoo_instance.password,
            api_key=odoo_instance.api_key
        ),
        neo4j=Neo4jConfig(
            uri=config.neo4j.uri,
            username=config.neo4j.username,
            password=config.neo4j.password
        )
    )
    
    return OdooNeo4jSyncService(sync_config)


# Request model for trigger endpoint
class TriggerRequest(BaseModel):
    module_ids: Optional[List[int]] = []
    category_prefixes: Optional[List[str]] = ["Custom"]
    max_depth: Optional[int] = None
    stop_conditions: Optional[List[List[List[Any]]]] = None
    include_reverse: bool = True


# Response model for trigger endpoint
class TriggerResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None
    stats: Optional[Dict[str, int]] = None


# Background sync task
def sync_task_wrapper(sync_service: OdooNeo4jSyncService, options: Dict[str, Any]):
    """
    Wrapper for sync task to ensure it's executed in a synchronous context.
    This function will be called by FastAPI background task system.
    """
    # Get the configuration from the service but don't use the service directly
    # to avoid sharing database connections between requests
    config = sync_service.config
    task_service = None
    
    try:
        logger.info(f"Starting sync task with options: {options}")
        
        # Create a completely new service instance for this background task
        # This ensures we don't share database connections between requests
        task_service = OdooNeo4jSyncService(config)
        
        try:
            # Execute the sync operation (now using proper session handling internally)
            result = task_service.sync_modules(options)
            logger.info("Sync task completed successfully")
            return result
        except Exception as e:
            logger.error(f"Sync task failed: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Sync task wrapper failed: {str(e)}")
        # Don't re-raise to avoid crashing the background task
        # Log the error instead so the API endpoint can still return
        return {"status": "error", "message": f"Sync failed: {str(e)}"}
    finally:
        # Ensure all resources are properly cleaned up
        if task_service:
            try:
                # Clean up Neo4j connections
                if hasattr(task_service, 'cleanup'):
                    task_service.cleanup()
            except Exception as cleanup_error:
                logger.warning(f"Error during task service cleanup: {str(cleanup_error)}")


@app.post("/trigger", response_model=TriggerResponse)
async def trigger_sync(
    request: TriggerRequest,
    background_tasks: BackgroundTasks,
    sync_service: OdooNeo4jSyncService = Depends(get_sync_service)
):
    """Trigger a sync job to fetch module dependency data and load it into Neo4j."""
    try:
        # Prepare options for the sync service
        options = {
            "module_ids": request.module_ids,
            "category_prefixes": request.category_prefixes,
            "max_depth": request.max_depth,
            "stop_conditions": request.stop_conditions,
            "include_reverse": request.include_reverse
        }
        
        # Add task to background tasks with proper sync context handling
        background_tasks.add_task(sync_task_wrapper, sync_service, options)
        
        return TriggerResponse(
            status="success",
            message="Sync job started successfully",
            job_id="job-" + str(hash(str(options)))
        )
    except OdooRpcError as e:
        logger.error(f"Odoo RPC error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Odoo RPC error: {str(e)}")
    except Neo4jError as e:
        logger.error(f"Neo4j error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Neo4j error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to trigger sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}