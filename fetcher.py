import logging
import requests
from typing import List, Dict, Any, Optional
from models import Instance, Graph, GraphNode, GraphEdge

logger = logging.getLogger(__name__)


class OdooFetcher:
    """Fetches module dependency data from Odoo instances."""
    
    def __init__(self, instance: Instance):
        self.instance = instance
        self.session = requests.Session()
    
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make a JSON-RPC request to the Odoo API."""
        url = f"{self.instance.url}{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                error = result["error"]
                logger.error(f"Odoo API error: {error['message']}")
                raise Exception(f"Odoo API error: {error['message']}")
            
            return result.get("result", {})
        except Exception as e:
            logger.error(f"Failed to fetch data from {url}: {str(e)}")
            raise
    
    def fetch_module_graph(self, module_ids: List[int], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch module dependency graph from Odoo."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "module_ids": module_ids,
                "options": options
            },
            "id": None
        }
        
        return self._make_request("/api/graph/module", payload)
    
    def fetch_reverse_graph(self, module_ids: List[int], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch reverse module dependency graph from Odoo."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "module_ids": module_ids,
                "options": options
            },
            "id": None
        }
        
        return self._make_request("/api/graph/reverse", payload)


def fetch_all(instances: List[Instance], options: Dict[str, Any]) -> Graph:
    """Fetch module dependency graphs from all instances and merge them."""
    merged_graph = Graph()
    node_map = {}  # Track nodes to avoid duplicates
    
    for instance in instances:
        logger.info(f"Fetching data from instance: {instance.name}")
        fetcher = OdooFetcher(instance)
        
        try:
            # Fetch forward dependencies
            module_ids = options.get("module_ids", [333])  # Default to module ID 333 if not specified
            forward_graph = fetcher.fetch_module_graph(module_ids, options)
            
            # Process nodes
            for node_data in forward_graph.get("nodes", []):
                node_id = f"{instance.name}_{node_data['id']}"
                if node_id not in node_map:
                    node = GraphNode(
                        id=node_id,
                        name=node_data.get("name", ""),
                        instance=instance.name,
                        properties=node_data
                    )
                    merged_graph.nodes.append(node)
                    node_map[node_id] = True
            
            # Process edges
            for edge_data in forward_graph.get("edges", []):
                edge = GraphEdge(
                    source=f"{instance.name}_{edge_data['source']}",
                    target=f"{instance.name}_{edge_data['target']}",
                    type="DEPENDS_ON",
                    properties=edge_data
                )
                merged_graph.edges.append(edge)
            
            # Fetch reverse dependencies if requested
            if options.get("include_reverse", True):
                reverse_graph = fetcher.fetch_reverse_graph(module_ids, options)
                
                # Process nodes from reverse graph
                for node_data in reverse_graph.get("nodes", []):
                    node_id = f"{instance.name}_{node_data['id']}"
                    if node_id not in node_map:
                        node = GraphNode(
                            id=node_id,
                            name=node_data.get("name", ""),
                            instance=instance.name,
                            properties=node_data
                        )
                        merged_graph.nodes.append(node)
                        node_map[node_id] = True
                
                # Process edges from reverse graph
                for edge_data in reverse_graph.get("edges", []):
                    edge = GraphEdge(
                        source=f"{instance.name}_{edge_data['source']}",
                        target=f"{instance.name}_{edge_data['target']}",
                        type="REQUIRED_BY",  # Different type for reverse dependencies
                        properties=edge_data
                    )
                    merged_graph.edges.append(edge)
        
        except Exception as e:
            logger.error(f"Failed to fetch data from instance {instance.name}: {str(e)}")
            # Continue with other instances
    
    return merged_graph