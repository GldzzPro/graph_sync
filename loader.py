# neo4j_loader.py

import logging
from typing import Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
from models import Graph

logger = logging.getLogger(__name__)

class Neo4jLoader:
    """Loads graph data into Neo4j and bootstraps schema if needed."""

    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        logger.info(f"Connecting to remote Neo4j at {uri}")

    def close(self):
        """Close the Neo4j driver (pools)."""
        self.driver.close()

    def create_schema(self):
        with self.driver.session() as session:
            logger.info("creating chema for the remote")
            try:
                # Unique constraint on ModuleNode.id
                session.write_transaction(lambda tx: tx.run(
                    "CREATE CONSTRAINT module_node_id IF NOT EXISTS "
                    "FOR (n:ModuleNode) REQUIRE n.id IS UNIQUE"
                ))
                logger.info("Ensured unique constraint on ModuleNode.id")

                # Index on last_updated for queries
                session.write_transaction(lambda tx: tx.run(
                    "CREATE INDEX module_last_updated IF NOT EXISTS "
                    "FOR (n:ModuleNode) ON (n.last_updated)"
                ))
                logger.info("Ensured index on ModuleNode.last_updated")

            except Neo4jError as e:
                logger.error(f"Failed to create schema: {e}")
                raise

    def ingest(self, graph: Graph):
            """Bootstrap schema, then load nodes and edges into Neo4j, with full debug logging."""
            rel_label_map = {
                "dependency": "DEPENDS_ON",
                "reverse_dependency": "REQUIRED_BY",
            }

            with self.driver.session() as session:
                # --- NODE INGESTION ---
                # 1. Normalize and log node IDs
                # Ensure all IDs are properly formatted with consistent prefix
                raw_node_ids = [n.id for n in graph.nodes]
                # Ensure all IDs are strings and have consistent format
                str_node_ids = []
                for node_id in raw_node_ids:
                    # Remove any existing prefix to avoid double prefixing
                    if isinstance(node_id, str) and node_id.startswith('odoo_'):
                        str_node_ids.append(node_id)
                    else:
                        str_node_ids.append(f"odoo_{node_id}")
                logger.info("Raw node IDs (%d): %s", len(raw_node_ids), raw_node_ids[:5])
                logger.info("Normalized node IDs: %s", str_node_ids[:5])

                # 2. Pre‑ingest match debug
                debug_nodes_cypher = """
                    UNWIND $ids AS id
                    MATCH (m:ModuleNode {id: id})
                    RETURN count(m) AS matched
                """
                try:
                    matched = session.run(debug_nodes_cypher, {"ids": str_node_ids})\
                                    .single().get("matched", 0)
                    logger.info("Pre‑ingest node match: %d/%d", matched, len(str_node_ids))
                except Exception as e:
                    logger.warning("Node match‑debug failed: %s", e)

                # 3. Ensure schema
                logger.info("Ensuring Neo4j schema (constraints/indexes)")
                self.create_schema()

                # 4. Bulk ingest nodes
                from typing import List, Dict
                nodes_data: List[Dict[str,Any]] = []
                for n in graph.nodes:
                    # Ensure consistent ID format with prefix
                    if isinstance(n.id, str) and n.id.startswith('odoo_'):
                        node_id = n.id
                    else:
                        node_id = f"odoo_{n.id}"
                    
                    # Filter properties to only include primitive types
                    primitive_props = {
                        k: v for k, v in n.properties.items()
                        if isinstance(v, (str, int, float, bool)) or
                        (isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v))
                    }
                    nodes_data.append({
                        "id": node_id,
                        "name": n.name,
                        "instance": n.instance,
                        **primitive_props
                    })

                logger.info("Ingesting %d nodes", len(nodes_data))
                logger.debug("Sample nodes_data IDs/types: %s",
                            [(nd["id"], type(nd["id"]).__name__) for nd in nodes_data[:5]])

                def ingest_nodes_tx(tx):
                    cypher = """
                        UNWIND $nodes AS node
                        MERGE (m:ModuleNode {id: node.id})
                        SET m += node, m.last_updated = timestamp()
                        RETURN count(m) AS created
                    """
                    logger.debug("Node ingestion Cypher:\n%s", cypher)
                    result = tx.run(cypher, {"nodes": nodes_data})
                    return result.consume()

                try:
                    summary = session.write_transaction(ingest_nodes_tx)
                    logger.info(
                        "Nodes ingestion summary: created=%d, properties_set=%d",
                        summary.counters.nodes_created,
                        summary.counters.properties_set,
                    )
                except Neo4jError:
                    logger.exception("Node ingestion failed")
                    raise

                # --- EDGE INGESTION ---
                # 1. Normalize and log edge endpoints
                from typing import List, Dict
                edges_data: List[Dict[str,Any]] = []
                for e in graph.edges:
                    # Ensure consistent ID format with prefix for source and target
                    source_id = e.source
                    if not (isinstance(source_id, str) and source_id.startswith('odoo_')):
                        source_id = f"odoo_{source_id}"
                        
                    target_id = e.target
                    if not (isinstance(target_id, str) and target_id.startswith('odoo_')):
                        target_id = f"odoo_{target_id}"
                    
                    # Filter properties to only include primitive types
                    primitive_props = {
                        k: v for k, v in e.properties.items()
                        if isinstance(v, (str, int, float, bool)) or
                        (isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v))
                    }
                    
                    edges_data.append({
                        "source": source_id,
                        "target": target_id,
                        "type": e.type,
                        **primitive_props
                    })
                logger.info("Preparing to ingest %d edges", len(edges_data))
                logger.debug("Sample edges_data endpoints: %s",
                            [(ed["source"], ed["target"]) for ed in edges_data[:5]])

                # 2. Pre‑ingest edge match debug
                debug_edges_cypher = """
                    UNWIND $edges AS edge
                    MATCH (a:ModuleNode {id: edge.source})
                    MATCH (b:ModuleNode {id: edge.target})
                    RETURN count(*) AS matched
                """
                try:
                    matched_pairs = session.run(debug_edges_cypher, {"edges": edges_data})\
                                        .single().get("matched", 0)
                    logger.info("Pre‑ingest edge match: %d/%d", matched_pairs, len(edges_data))
                except Exception as e:
                    logger.warning("Edge match‑debug failed: %s", e)

                # 3. Group & ingest edges by mapped label
                from collections import defaultdict
                edges_by_type = defaultdict(list)
                for ed in edges_data:
                    edges_by_type[ed["type"]].append(ed)

                for raw_type, group in edges_by_type.items():
                    label = rel_label_map.get(raw_type)
                    if not label:
                        logger.warning("Skipping %d edges of unknown type '%s'", len(group), raw_type)
                        continue
                    logger.info("Ingesting %d edges of raw type '%s' as '%s'",
                                len(group), raw_type, label)

                    def ingest_edges_tx(tx, label=label, group=group):
                        cypher = f"""
                            UNWIND $edges AS edge
                            MATCH (a:ModuleNode {{id: edge.source}})
                            MATCH (b:ModuleNode {{id: edge.target}})
                            MERGE (a)-[r:`{label}`]->(b)
                            SET r += edge, r.last_updated = timestamp()
                            RETURN count(r) AS created
                        """
                        logger.debug("Edge ingestion Cypher for %s:\n%s", label, cypher)
                        result = tx.run(cypher, {"edges": group})
                        return result.consume()

                    try:
                        summary = session.write_transaction(ingest_edges_tx)
                        logger.info(
                            "Edges ingestion summary for %s: created=%d",
                            label, summary.counters.relationships_created
                        )
                    except Neo4jError:
                        logger.exception("Edge ingestion failed for %s", label)
                        raise

                logger.info("Data loading complete")
                
                # --- POST‑INGEST VERIFICATION ---

            try:
                # 1) How many ModuleNode nodes are really in the DB?
                node_count = session.run(
                    "MATCH (n:ModuleNode) RETURN count(n) AS cnt"
                ).single().get("cnt")
                logger.info("Post‑ingest: total ModuleNode count = %d", node_count)
                
                # 2) Sample 5 node IDs
                sample_nodes = [ record["id"] for record in session.run(
                    "MATCH (n:ModuleNode) RETURN n.id AS id LIMIT 5"
                ) ]
                logger.info("Post‑ingest: sample node IDs = %s", sample_nodes)
                
                # 3) How many relationships of each type exist?
                # Use a simpler query that doesn't require APOC
                rel_counts = {}
                try:
                    for row in session.run(
                        "MATCH ()-[r]->() RETURN type(r) AS relationshipType, count(r) AS count"
                    ):
                        rel_counts[row["relationshipType"]] = row["count"]
                    logger.info("Post‑ingest: relationship counts = %s", rel_counts)
                except Exception as e:
                    logger.warning("Relationship count query failed: %s", e)
            except Exception as e:
                logger.warning("Post‑ingest verification failed: %s", e)