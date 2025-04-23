from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class Instance(BaseModel):
    """Represents an Odoo instance configuration."""
    name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    db_name: Optional[str] = None


class GraphNode(BaseModel):
    """Represents a node in the dependency graph."""
    id: str
    name: str
    instance: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Represents an edge in the dependency graph."""
    source: str
    target: str
    type: str = "DEPENDS_ON"
    properties: Dict[str, Any] = Field(default_factory=dict)


class Graph(BaseModel):
    """Represents a complete dependency graph."""
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class SyncOptions(BaseModel):
    """Options for the sync operation."""
    max_depth: Optional[int] = None
    stop_conditions: Optional[List[List[List[Any]]]] = None
    include_reverse: bool = True