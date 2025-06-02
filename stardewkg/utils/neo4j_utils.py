from neo4j import Driver, GraphDatabase
import dotenv
import os

def get_neo4j_driver() -> Driver:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    print(uri, username, password)

    if password is None:
        raise ValueError("NEO4J_PASSWORD must be set")

    return GraphDatabase.driver(uri, auth=(username, password))


def create_node_neo4j(driver: Driver, labels: list[str], name: str, properties=None):
    """
    Create or update a node with optional labels in Neo4j.

    - If labels are provided, they are dynamically assigned after merging.
    - If no labels are provided, the node is created/merged without labels.

    Args:
        driver (neo4j.GraphDatabase.driver): The Neo4j driver instance.
        labels (list or str or None): A single label as a string, multiple labels as a list, or None.
        name (str): The unique name of the node.
        properties (dict, optional): Additional properties to set on the node.
    """
    properties = properties or {}

    if isinstance(labels, str):
        labels = [labels]

    # Prepare label-setting statements dynamically (only if labels exist)
    set_labels = f"SET n{':'.join([':' + lbl for lbl in labels])}" if labels else ""

    query = f"""
    MERGE (n {{name: $name}})
    {set_labels}
    SET n += $properties
    RETURN n
    """

    with driver.session() as session:
        return session.run(query, name=name, properties=properties).single()

def create_relationship_neo4j(
    driver: Driver,
    from_node_name: str,
    from_node_labels: list[str],
    to_node_name: str,
    to_node_labels: list[str],
    rel_type: str,
    properties=None,
):
    """
    Create or update a relationship between two nodes in Neo4j.

    - If labels are provided, they are dynamically assigned after merging.
    - If no labels are provided, nodes are created/merged without labels.

    Args:
        driver (neo4j.GraphDatabase.driver): The Neo4j driver instance.
        from_node_name (str): Unique name of the starting node.
        from_labels (list or None): Labels for the starting node (if any).
        to_node_name (str): Unique name of the ending node.
        to_labels (list or None): Labels for the ending node (if any).
        rel_type (str): Type of the relationship.
        properties (dict, optional): Additional properties for the relationship.
    """
    properties = properties or {}

    # Ensure labels are lists
    if isinstance(from_node_labels, str):
        from_node_labels = [from_node_labels]
    if isinstance(to_node_labels, str):
        to_node_labels = [to_node_labels]

    # Prepare label-setting statements dynamically (only if labels exist)
    set_from_labels = (
        f"SET a{':'.join([':' + lbl for lbl in from_node_labels])}"
        if from_node_labels
        else ""
    )
    set_to_labels = (
        f"SET b{':'.join([':' + lbl for lbl in to_node_labels])}"
        if to_node_labels
        else ""
    )

    query = f"""
    MERGE (a {{name: $from_node_name}})
    {set_from_labels}
    MERGE (b {{name: $to_node_name}})
    {set_to_labels}
    MERGE (a)-[r:{rel_type}]->(b)
    ON CREATE SET r.created = timestamp(), r += $properties
    ON MATCH  SET r.lastUpdated = timestamp(), r += $properties
    RETURN r
    """

    with driver.session() as session:
        return session.run(
            query,
            from_node_name=from_node_name,
            to_node_name=to_node_name,
            properties=properties,
        ).single()


def make_query(driver: Driver, query: str):
    with driver.session() as session:
        return session.run(query).single()
