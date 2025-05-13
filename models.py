from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class Instance(BaseModel):
    """Configuration for an Odoo instance."""
    name: str = Field(..., description="Unique name identifier for the instance")
    url: str = Field(..., description="Base URL for the Odoo instance")


class GraphData(BaseModel):
    """Graph data structure for nodes and edges."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)


class InstanceResponse(BaseModel):
    """Response data for a single instance."""
    instance: str
    status: str = "success"
    data: Optional[GraphData] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "graph_sync"
    details: Optional[Dict[str, Any]] = None