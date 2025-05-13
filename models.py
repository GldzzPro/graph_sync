from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class Instance(BaseModel):
    """Represents an Odoo instance configuration."""
    name: str
    url: str


class SyncOptions(BaseModel):
    """Options for synchronization."""
    module_ids: List[int] = Field(default_factory=list)
    include_reverse: bool = True
    max_depth: Optional[int] = None
    category_prefixes: List[str] = Field(default_factory=lambda: ["Custom"])


class InstanceResponse(BaseModel):
    """Response from an instance."""
    instance: str
    data: Dict[str, Any] = Field(default_factory=dict)
    status: str = "success"
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "graph_sync"
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)