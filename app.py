import logging
import asyncio
import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from config import Config
from models import SyncOptions, InstanceResponse, HealthCheckResponse
from fetcher import fetch_all

# Configure logging based on environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GraphSync",
    description="Stateless microservice for fetching Odoo module dependencies",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Dependency for configuration
def get_config():
    return Config()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)}
    )

# Health check endpoint
@app.get("/healthcheck", response_model=HealthCheckResponse)
async def healthcheck(config: Config = Depends(get_config)):
    """Health check endpoint to verify the service is running."""
    response = HealthCheckResponse()
    
    # Add instance count to response
    response.details = {
        "instances": len(config.instances),
        "instance_names": [instance.name for instance in config.instances]
    }
    
    return response

# Request model for trigger endpoint
class TriggerRequest(BaseModel):
    module_ids: Optional[List[int]] = []
    category_prefixes: Optional[List[str]] = ["Custom"]
    max_depth: Optional[int] = None
    include_reverse: bool = True

# Trigger endpoint
@app.post("/trigger", response_model=List[InstanceResponse])
async def trigger(request: TriggerRequest, config: Config = Depends(get_config)):
    """Trigger fetching module dependencies from all configured instances."""
    try:
        # Validate request
        if not config.instances:
            raise HTTPException(status_code=400, detail="No instances configured. Please check your configuration.")
        
        # Prepare options for fetching
        options = {
            "module_ids": request.module_ids,
            "category_prefixes": request.category_prefixes,
            "max_depth": request.max_depth,
            "include_reverse": request.include_reverse
        }
        
        # Log request details
        logger.info(f"Triggering fetch for {len(config.instances)} instances with options: {options}")
        
        # Fetch data from all instances asynchronously
        results = await fetch_all(config.instances, options)
        
        # Log response summary
        success_count = sum(1 for r in results if r.status == "success")
        error_count = sum(1 for r in results if r.status == "error")
        logger.info(f"Fetch completed: {success_count} successful, {error_count} failed")
        
        return results
    except Exception as e:
        logger.error(f"Error in trigger endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)