import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from models import Instance, InstanceResponse, SyncOptions

logger = logging.getLogger(__name__)


class OdooFetcher:
    """Fetches module dependency data from Odoo instances."""
    
    def __init__(self, instance: Instance):
        self.instance = instance
    
    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make an asynchronous JSON-RPC request to the Odoo API."""
        url = f"{self.instance.url}{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if "error" in result:
                        error = result["error"]
                        logger.error(f"Odoo API error for {self.instance.name}: {error['message']}")
                        raise Exception(f"Odoo API error: {error['message']}")
                    
                    return result.get("result", {})
        except asyncio.TimeoutError:
            logger.error(f"Request to {self.instance.name} timed out")
            raise Exception(f"Request to {self.instance.name} timed out after 30 seconds")
        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP error from {self.instance.name}: {e.status} {e.message}")
            raise Exception(f"HTTP error: {e.status} {e.message}")
        except Exception as e:
            logger.error(f"Failed to fetch data from {self.instance.name} at {url}: {str(e)}")
            raise
    
    async def fetch_module_graph(self, module_ids: List[int], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch module dependency graph from Odoo."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "module_ids": module_ids,
                "category_prefixes": options.get("category_prefixes", ["Custom"]),
                "max_depth": options.get("max_depth"),
                "include_reverse": False  # We'll handle reverse dependencies separately
            },
            "id": None
        }
        
        return await self._make_request("/api/graph/module", payload)
    
    async def fetch_reverse_graph(self, module_ids: List[int], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch reverse module dependency graph from Odoo."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "module_ids": module_ids,
                "category_prefixes": options.get("category_prefixes", ["Custom"]),
                "max_depth": options.get("max_depth")
            },
            "id": None
        }
        
        return await self._make_request("/api/graph/reverse", payload)

    async def healthcheck(self) -> bool:
        """Check if the instance is healthy."""
        try:
            url = f"{self.instance.url}/web/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed for {self.instance.name}: {str(e)}")
            return False


async def fetch_instance_data(instance: Instance, options: Dict[str, Any]) -> InstanceResponse:
    """Fetch data from a single instance."""
    fetcher = OdooFetcher(instance)
    response = InstanceResponse(instance=instance.name)
    
    try:
        # Check if instance is healthy
        is_healthy = await fetcher.healthcheck()
        if not is_healthy:
            response.status = "error"
            response.error = f"Instance {instance.name} is not healthy or not reachable"
            return response

        # Fetch forward dependencies
        module_ids = options.get("module_ids", [333])  # Default to module ID 333 if not specified
        if not module_ids:
            module_ids = [333]  # Ensure we have at least one module ID
            
        logger.info(f"Fetching dependencies for {instance.name} with module_ids={module_ids}")
        forward_graph = await fetcher.fetch_module_graph(module_ids, options)
        
        # Fetch reverse dependencies if requested
        if options.get("include_reverse", True):
            logger.info(f"Fetching reverse dependencies for {instance.name}")
            reverse_graph = await fetcher.fetch_reverse_graph(module_ids, options)
            
            # Combine the graphs - ensure unique nodes and edges
            all_nodes = {}
            all_edges = {}
            
            # Process forward graph nodes and edges
            for node in forward_graph.get("nodes", []):
                node_id = node.get("id")
                if node_id:
                    all_nodes[node_id] = node
            
            for edge in forward_graph.get("edges", []):
                edge_id = f"{edge.get('from')}-{edge.get('to')}"
                if edge_id:
                    all_edges[edge_id] = edge
            
            # Process reverse graph nodes and edges
            for node in reverse_graph.get("nodes", []):
                node_id = node.get("id")
                if node_id:
                    all_nodes[node_id] = node
            
            for edge in reverse_graph.get("edges", []):
                edge_id = f"{edge.get('from')}-{edge.get('to')}"
                if edge_id:
                    all_edges[edge_id] = edge
            
            # Create combined data with unique nodes and edges
            combined_data = {
                "nodes": list(all_nodes.values()),
                "edges": list(all_edges.values())
            }
            response.data = combined_data
        else:
            response.data = forward_graph
        
        logger.info(f"Successfully fetched data from {instance.name}: {len(response.data.get('nodes', []))} nodes, {len(response.data.get('edges', []))} edges")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch data from instance {instance.name}: {str(e)}")
        response.status = "error"
        response.error = str(e)
        return response


async def fetch_all(instances: List[Instance], options: Dict[str, Any]) -> List[InstanceResponse]:
    """Fetch module dependency graphs from all instances asynchronously."""
    if not instances:
        logger.warning("No instances configured. Please check your configuration.")
        return []
    
    logger.info(f"Fetching data from {len(instances)} instances with options: {options}")
    tasks = [fetch_instance_data(instance, options) for instance in instances]
    
    try:
        # Use gather with return_exceptions=False to fail fast if any instance fails
        results = await asyncio.gather(*tasks)
        return results
    except Exception as e:
        logger.error(f"Error fetching data from instances: {str(e)}")
        # Return partial results if possible
        return [InstanceResponse(instance="error", status="error", error=str(e))]