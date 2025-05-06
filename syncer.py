import logging
import requests
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator

from models import Graph, GraphNode, GraphEdge, Instance
from loader import Neo4jLoader

logger = logging.getLogger(__name__)


class OdooRpcError(Exception):
    """Exception raised for errors in Odoo RPC operations."""
    pass


class Neo4jError(Exception):
    """Exception raised for errors in Neo4j operations."""
    pass


class OdooConfig(BaseModel):
    """Configuration for Odoo instance."""
    url: str
    db_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None

    @validator('url')
    def validate_url(cls, v):
        if not v.startswith('http'):
            raise ValueError('URL must start with http:// or https://')
        return v.rstrip('/')


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j database."""
    uri: str
    username: str
    password: str


class SyncConfig(BaseModel):
    """Configuration for the synchronization service."""
    odoo: OdooConfig
    neo4j: Neo4jConfig


class OdooNeo4jSyncService:
    """Service for synchronizing Odoo module dependency data to Neo4j."""
    
    def __init__(self, config: SyncConfig):
        self.config = config
        self.session = requests.Session()
        self.odoo_client = None
        self._neo4j_loader = None
    
    def get_neo4j_loader(self):
        """
        Lazy-initialize and return a Neo4j loader.
        This ensures a fresh connection for each usage.
        """
        if not self._neo4j_loader:
            logger.info("Initializing new Neo4j loader connection")
            self._neo4j_loader = Neo4jLoader(
                uri=self.config.neo4j.uri,
                username=self.config.neo4j.username,
                password=self.config.neo4j.password
            )
        return self._neo4j_loader

    def cleanup(self):
        """Clean up resources used by the service."""
        if self._neo4j_loader:
            try:
                logger.info("Closing Neo4j loader connection")
                self._neo4j_loader.close()
                self._neo4j_loader = None
            except Exception as e:
                logger.warning(f"Error closing Neo4j loader: {str(e)}")
        
        if self.odoo_client:
            try:
                # Close any Odoo client resources if applicable
                pass
            except Exception as e:
                logger.warning(f"Error closing Odoo client: {str(e)}")
        
        # Close the requests session
        try:
            if self.session:
                self.session.close()
        except Exception as e:
            logger.warning(f"Error closing requests session: {str(e)}")
    
    def _make_rpc_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request to the Odoo API."""
        url = f"{self.config.odoo.url}{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": None
        }
        
        try:
            logger.debug(f"Making RPC request to {url} with params: {params}")
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                error = result["error"]
                error_msg = error.get("message", "Unknown error")
                logger.error(f"Odoo API error: {error_msg}")
                raise OdooRpcError(f"Odoo API error: {error_msg}")
            
            return result.get("result", {})
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Odoo API at {url}: {str(e)}")
            raise OdooRpcError(f"Failed to connect to Odoo API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in RPC request: {str(e)}")
            raise OdooRpcError(f"Unexpected error in RPC request: {str(e)}")
    
    def fetch_modules_by_category(self, category_prefixes: List[str], options: Dict[str, Any] = None) -> List[int]:
        """Fetch module IDs by category prefixes."""
        options = options or {}
        options.setdefault("max_depth", 0)  # Set max_depth to 0 to only get the module IDs
        
        try:
            logger.info(f"Fetching modules by category prefixes: {category_prefixes}")
            result = self._make_rpc_request(
                "/api/graph/category", 
                {"category_prefixes": category_prefixes, "options": options}
            )
            
            # Extract module IDs from the nodes
            module_ids = [node["id"] for node in result.get("nodes", [])]
            logger.info(f"Found {len(module_ids)} modules matching category prefixes")
            return module_ids
        except Exception as e:
            logger.error(f"Failed to fetch modules by category: {str(e)}")
            raise OdooRpcError(f"Failed to fetch modules by category: {str(e)}")
    
    def fetch_module_graph(self, module_ids: List[int], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fetch module dependency graph from Odoo."""
        options = options or {}
        
        try:
            logger.info(f"Fetching module graph for {len(module_ids)} modules")
            result = self._make_rpc_request(
                "/api/graph/module", 
                {"module_ids": module_ids, "options": options}
            )
            
            logger.info(f"Fetched module graph with {len(result.get('nodes', []))} nodes and {len(result.get('edges', []))} edges")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch module graph: {str(e)}")
            raise OdooRpcError(f"Failed to fetch module graph: {str(e)}")
    
    def fetch_reverse_graph(self, module_ids: List[int], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fetch reverse module dependency graph from Odoo."""
        options = options or {}
        
        try:
            logger.info(f"Fetching reverse module graph for {len(module_ids)} modules")
            result = self._make_rpc_request(
                "/api/graph/reverse", 
                {"module_ids": module_ids, "options": options}
            )
            
            logger.info(f"Fetched reverse module graph with {len(result.get('nodes', []))} nodes and {len(result.get('edges', []))} edges")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch reverse module graph: {str(e)}")
            raise OdooRpcError(f"Failed to fetch reverse module graph: {str(e)}")
    
    def _convert_to_graph_model(self, instance_name: str, graph_data: Dict[str, Any], reverse_graph_data: Optional[Dict[str, Any]] = None) -> Graph:
        """Convert raw graph data to Graph model."""
        graph = Graph()
        node_map = {}  # Track nodes to avoid duplicates
        
        # Process nodes from forward graph
        for node_data in graph_data.get("nodes", []):
            node_id = f"{instance_name}_{node_data['id']}"
            if node_id not in node_map:
                node = GraphNode(
                    id=node_id,
                    name=node_data.get("label", ""),
                    instance=instance_name,
                    properties=node_data
                )
                graph.nodes.append(node)
                node_map[node_id] = True
        
        # Process edges from forward graph
        for edge_data in graph_data.get("edges", []):
            edge = GraphEdge(
                source=f"{instance_name}_{edge_data['from']}",
                target=f"{instance_name}_{edge_data['to']}",
                type="DEPENDS_ON",
                properties=edge_data
            )
            graph.edges.append(edge)
        
        # Process nodes from reverse graph if provided
        if reverse_graph_data:
            for node_data in reverse_graph_data.get("nodes", []):
                node_id = f"{instance_name}_{node_data['id']}"
                if node_id not in node_map:
                    node = GraphNode(
                        id=node_id,
                        name=node_data.get("label", ""),
                        instance=instance_name,
                        properties=node_data
                    )
                    graph.nodes.append(node)
                    node_map[node_id] = True
            
            # Process edges from reverse graph
            for edge_data in reverse_graph_data.get("edges", []):
                edge = GraphEdge(
                    source=f"{instance_name}_{edge_data['from']}",
                    target=f"{instance_name}_{edge_data['to']}",
                    type="REQUIRED_BY",
                    properties=edge_data
                )
                graph.edges.append(edge)
        
        return graph
    
    def sync_modules(self, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronize Odoo module graphs into Neo4j (including schema setup)."""
        opts = options.copy() if options else {}
        instance_name = opts.get("instance_name", "odoo")

        # 1) Determine module_ids (either provided or via category fetch)
        module_ids = opts.get("module_ids") or []
        cat_prefixes = opts.get("category_prefixes", ["Custom"])
        if not module_ids and cat_prefixes:
            logger.info(f"No module_ids provided, fetching by category prefixes: {cat_prefixes}")
            module_ids = self.fetch_modules_by_category(cat_prefixes, {"max_depth": 0})
        if not module_ids:
            msg = "No modules found to synchronize"
            logger.warning(msg)
            return {"status": "warning", "message": msg}

        # 2) Fetch forward & reverse graphs
        graph_opts = {
            "max_depth": opts.get("max_depth"),
            "stop_domains": opts.get("stop_conditions"),
        }
        logger.info(f"Fetching forward graph for module_ids={module_ids}")
        fg = self.fetch_module_graph(module_ids, graph_opts)
        rg = None
        if opts.get("include_reverse", True):
            logger.info(f"Fetching reverse graph for module_ids={module_ids}")
            rg = self.fetch_reverse_graph(module_ids, graph_opts)

        # 3) Convert to our Pydantic Graph model
        graph = self._convert_to_graph_model(instance_name, fg, rg)
        n_nodes, n_edges = len(graph.nodes), len(graph.edges)
        logger.info(f"Prepared graph with {n_nodes} nodes and {n_edges} edges")

        # 4) Ingest into Neo4j with schema bootstrapping
        loader = self.get_neo4j_loader()  # returns an instance of your new Neo4jLoader
        try:
            logger.info("Ensuring Neo4j schema (constraints/indexes)")
            loader.create_schema()

            logger.info(f"Starting ingestion into Neo4j: {n_nodes} nodes, {n_edges} edges")
            loader.ingest(graph)

            logger.info(f"Successfully ingested {n_nodes} nodes and {n_edges} edges into Neo4j")
            return {
                "status": "success",
                "message": f"Synchronized {n_nodes} nodes and {n_edges} edges",
                "stats": {"nodes": n_nodes, "edges": n_edges},
            }

        except Neo4jError as e:
            logger.error(f"Neo4j ingestion error: {e}")
            raise  # let the caller (or FastAPI layer) translate to HTTP 500

        except Exception as e:
            logger.exception("Unexpected error during sync")
            raise

        finally:
            # Always close the driver/session pool
            try:
                loader.close()
            except Exception as close_err:
                logger.warning(f"Error closing Neo4j loader: {close_err}")