import logging
import asyncio
import aiohttp
from typing import List, Dict, Any
from models import Instance, InstanceResponse, GraphData

logger = logging.getLogger(__name__)


class OdooJsonRPC:
    """Helper class for Odoo JSON-RPC operations."""
    
    def __init__(self, instance: Instance):
        self.instance = instance
    
    async def call(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make an asynchronous JSON-RPC request to the Odoo API."""
        url = f"{self.instance.url}{endpoint}"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": params,
            "id": 1
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if "error" in result:
                        error = result["error"]
                        logger.error(f"Odoo API error for {self.instance.name}: {error.get('message', error)}")
                        raise Exception(f"Odoo API error: {error.get('message', error)}")
                    
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


class OdooGraphFetcher:
    """Fetches module dependency graph data from Odoo instances."""
    
    def __init__(self, instance: Instance):
        self.instance = instance
        self.rpc = OdooJsonRPC(instance)
    
    async def fetch_category_module_graph(self, category_prefixes: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch category module dependency graph from Odoo."""
        params = {
            "category_prefixes": category_prefixes,
            "options": options
        }
        
        return await self.rpc.call("/api/graph/category", params)
    
    async def fetch_reverse_category_module_graph(self, category_prefixes: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch reverse category module dependency graph from Odoo."""
        params = {
            "category_prefixes": category_prefixes,
            "options": options
        }
        
        return await self.rpc.call("/api/graph/category/reverse", params)

    async def healthcheck(self) -> bool:
        """Check if the instance is healthy by attempting to call a simple JSON-RPC endpoint."""
        try:
            # Try a simple JSON-RPC call to check if Odoo is responsive
            # We'll use the session_info endpoint which is lightweight and available in all Odoo instances
            url = f"{self.instance.url}/web/session/get_session_info"
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {},
                "id": 1
            }
            
            headers = {"Content-Type": "application/json"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=5) as response:
                    if response.status != 200:
                        return False
                    
                    result = await response.json()
                    return "result" in result and "error" not in result
                    
        except Exception as e:
            logger.error(f"Health check failed for {self.instance.name}: {str(e)}")
            return False


async def fetch_instance_data(instance: Instance, fetch_options: Dict[str, Any]) -> InstanceResponse:
    """Fetch graph data from a single instance."""
    fetcher = OdooGraphFetcher(instance)
    response = InstanceResponse(instance=instance.name)
    
    try:
        # Check if instance is healthy
        is_healthy = await fetcher.healthcheck()
        if not is_healthy:
            response.status = "error"
            response.error = f"Instance {instance.name} is not healthy or not reachable"
            return response

        # Extract options
        category_prefixes = fetch_options.get("category_prefixes", ["Custom"])
        options = fetch_options.get("options", {})
        include_reverse = fetch_options.get("include_reverse", True)
        
        # Fetch forward category module graph
        logger.info(f"Fetching category module graph for {instance.name} with prefixes={category_prefixes}")
        forward_graph = await fetcher.fetch_category_module_graph(category_prefixes, options)
        
        # Initialize graph data structure
        graph_data = GraphData(
            nodes=forward_graph.get("nodes", []),
            edges=forward_graph.get("edges", [])
        )
        
        # Fetch reverse dependencies if requested
        if include_reverse:
            logger.info(f"Fetching reverse category module graph for {instance.name}")
            reverse_graph = await fetcher.fetch_reverse_category_module_graph(category_prefixes, options)
            
            # Combine the graphs - ensure unique nodes and edges
            all_nodes = {node.get("id"): node for node in graph_data.nodes if "id" in node}
            all_edges = {}
            
            # Add edges from forward graph
            for edge in graph_data.edges:
                edge_id = f"{edge.get('from')}-{edge.get('to')}"
                if edge_id:
                    all_edges[edge_id] = edge
            
            # Process reverse graph nodes and edges
            for node in reverse_graph.get("nodes", []):
                node_id = node.get("id")
                if node_id and node_id not in all_nodes:
                    all_nodes[node_id] = node
            
            for edge in reverse_graph.get("edges", []):
                edge_id = f"{edge.get('from')}-{edge.get('to')}"
                if edge_id and edge_id not in all_edges:
                    all_edges[edge_id] = edge
            
            # Create combined data with unique nodes and edges
            graph_data = GraphData(
                nodes=list(all_nodes.values()),
                edges=list(all_edges.values())
            )
        
        response.data = graph_data
        logger.info(f"Successfully fetched data from {instance.name}: {len(graph_data.nodes)} nodes, {len(graph_data.edges)} edges")
        return response
    except Exception as e:
        logger.error(f"Failed to fetch data from instance {instance.name}: {str(e)}")
        response.status = "error"
        response.error = str(e)
        return response


async def fetch_all(instances: List[Instance], fetch_options: Dict[str, Any]) -> List[InstanceResponse]:
    """Fetch module dependency graphs from all instances asynchronously."""
    if not instances:
        logger.warning("No instances configured. Please check your configuration.")
        return []
    
    logger.info(f"Fetching data from {len(instances)} instances with options: {fetch_options}")
    tasks = [fetch_instance_data(instance, fetch_options) for instance in instances]
    
    try:
        # Gather all results, even if some fail
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, converting exceptions to error responses
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Convert exception to error response
                instance_name = instances[i].name if i < len(instances) else "unknown"
                processed_results.append(
                    InstanceResponse(
                        instance=instance_name, 
                        status="error", 
                        error=f"Unhandled exception: {str(result)}"
                    )
                )
            else:
                processed_results.append(result)
                
        return processed_results
    except Exception as e:
        logger.error(f"Error fetching data from instances: {str(e)}")
        # Return error response
        return [InstanceResponse(instance="error", status="error", error=str(e))]