import logging
import os
from neo4j import GraphDatabase
from models import Graph, GraphNode, GraphEdge
from loader import Neo4jLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Neo4j connection details
uri = 'neo4j+s://894056ca.databases.neo4j.io'
username = 'neo4j'
password = 'sXUgYO26XZBN1lSz86KbnzmDIjfCiWBehXgXhMRXsxU'

# Create test data with complex property values
def create_test_graph():
    # Create nodes with various property types
    nodes = [
        GraphNode(
            id="module_1",
            name="Test Module 1",
            instance="test",
            properties={
                "category_id": 80,
                "category": "Custom",
                "state": "installed",
                "depth": 0,
                "label": "module_custom_a",
                "complex_value": {"nested": "value"}  # This should be filtered out
            }
        ),
        GraphNode(
            id="module_2",
            name="Test Module 2",
            instance="test",
            properties={
                "category_id": 80,
                "category": "Custom",
                "state": "installed",
                "depth": 1,
                "label": "module_custom_b"
            }
        )
    ]
    
    # Create edges with various property types
    edges = [
        GraphEdge(
            source="module_1",
            target="module_2",
            type="DEPENDS_ON",
            properties={
                "depth": 1,
                "complex_value": {"nested": "value"}  # This should be filtered out
            }
        )
    ]
    
    return Graph(nodes=nodes, edges=edges)

# Main function
def main():
    logger.info("Starting Neo4j loader test")
    
    # Create test graph
    graph = create_test_graph()
    logger.info(f"Created test graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
    
    # Initialize loader
    loader = Neo4jLoader(uri, username, password)
    
    try:
        # Clear existing data
        with loader.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Cleared existing Neo4j data")
        
        # Ingest test data
        loader.ingest(graph)
        
        # Verify data was loaded correctly
        with loader.driver.session() as session:
            # Check nodes
            result = session.run("MATCH (n:ModuleNode) RETURN count(n) as count")
            node_count = result.single()["count"]
            logger.info(f"Verified {node_count} nodes in Neo4j")
            
            # Check relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            logger.info(f"Verified {rel_count} relationships in Neo4j")
            
            # Check node properties
            result = session.run("MATCH (n:ModuleNode) WHERE n.id = 'module_1' RETURN n")
            node = result.single()["n"]
            logger.info(f"Node properties: {dict(node)}")
            
            # Check relationship properties
            result = session.run("MATCH ()-[r]->() RETURN r")
            rel = result.single()["r"]
            logger.info(f"Relationship properties: {dict(rel)}")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
    finally:
        loader.close()
        logger.info("Test completed")

if __name__ == "__main__":
    main()