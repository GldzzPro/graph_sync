import logging
from typing import Dict, Any
from neo4j import GraphDatabase
from models import Graph

logger = logging.getLogger(__name__)


class Neo4jLoader:
    """Loads graph data into Neo4j database."""
    
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()
    
    def _create_constraints(self, session):
        """Create necessary constraints in Neo4j."""
        try:
            # Create constraint on ModuleNode(id)
            session.execute_write(lambda tx: tx.run("""
                CREATE CONSTRAINT module_id_constraint IF NOT EXISTS
                FOR (m:ModuleNode) REQUIRE m.id IS UNIQUE
            """))
            logger.info("Neo4j constraints created or already exist")
        except Exception as e:
            logger.error(f"Failed to create Neo4j constraints: {str(e)}")
            raise
    
    def ingest(self, graph: Graph):
        """Ingest graph data into Neo4j."""
        with self.driver.session() as session:
            # Create constraints if they don't exist
            self._create_constraints(session)
            
            # Ingest nodes
            self._ingest_nodes(session, graph)
            
            # Ingest edges
            self._ingest_edges(session, graph)
    
    def _ingest_nodes(self, session, graph: Graph):
        """Ingest nodes into Neo4j using UNWIND."""
        nodes_data = [{
            "id": node.id,
            "name": node.name,
            "instance": node.instance,
            "properties": node.properties
        } for node in graph.nodes]
        
        if not nodes_data:
            logger.warning("No nodes to ingest")
            return
        
        try:
            result = session.execute_write(lambda tx: tx.run("""
                UNWIND $nodes AS node
                MERGE (m:ModuleNode {id: node.id})
                SET m.name = node.name,
                    m.instance = node.instance,
                    m.properties = node.properties,
                    m.last_updated = timestamp()
                RETURN count(m) as count
            """, {"nodes": nodes_data}))
            
            count = result.single()["count"]
            logger.info(f"Ingested {count} nodes into Neo4j")
        except Exception as e:
            logger.error(f"Failed to ingest nodes: {str(e)}")
            raise
    
    def _ingest_edges(self, session, graph: Graph):
        """Ingest edges into Neo4j using UNWIND."""
        edges_data = [{
            "source": edge.source,
            "target": edge.target,
            "type": edge.type,
            "properties": edge.properties
        } for edge in graph.edges]
        
        if not edges_data:
            logger.warning("No edges to ingest")
            return
        
        try:
            result = session.execute_write(lambda tx: tx.run("""
                UNWIND $edges AS edge
                MATCH (source:ModuleNode {id: edge.source})
                MATCH (target:ModuleNode {id: edge.target})
                CALL apoc.merge.relationship(source, edge.type, 
                    {instance: source.instance}, 
                    {properties: edge.properties, last_updated: timestamp()}, 
                    target
                )
                YIELD rel
                RETURN count(rel) as count
            """, {"edges": edges_data}))
            
            count = result.single()["count"]
            logger.info(f"Ingested {count} edges into Neo4j")
        except Exception as e:
            logger.error(f"Failed to ingest edges: {str(e)}")
            raise


def ingest(graph: Graph, neo4j_config: Dict[str, Any]):
    """Ingest graph data into Neo4j."""
    loader = Neo4jLoader(
        uri=neo4j_config["uri"],
        username=neo4j_config["username"],
        password=neo4j_config["password"]
    )
    
    try:
        loader.ingest(graph)
    finally:
        loader.close()