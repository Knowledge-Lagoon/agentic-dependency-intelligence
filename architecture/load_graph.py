import json
import os
from pathlib import Path

from neo4j import GraphDatabase


BASE_DIR = Path(__file__).resolve().parent.parent

GRAPH_PATH = (
    BASE_DIR
    / "architecture"
    / "output"
    / "approved_graph.json"
)

NEO4J_URI = os.getenv(
    "NEO4J_URI",
    "bolt://localhost:7687",
)

NEO4J_USERNAME = os.getenv(
    "NEO4J_USERNAME",
    "neo4j",
)

NEO4J_PASSWORD = os.getenv(
    "NEO4J_PASSWORD"
)

GRAPH_SOURCE = "architecture_diagram"


ALLOWED_COMPONENT_TYPES = {
    "Application",
    "Service",
    "Database",
    "ExternalSystem",
}

ALLOWED_RELATIONSHIP_TYPES = {
    "USES",
    "DEPENDS_ON",
    "CONNECTS_TO",
}


def load_json():
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(
            f"Approved graph not found: {GRAPH_PATH}"
        )

    with GRAPH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_graph(graph):
    components = graph.get("components")
    relationships = graph.get("relationships")

    if not isinstance(components, list):
        raise ValueError(
            "'components' must be a list."
        )

    if not isinstance(relationships, list):
        raise ValueError(
            "'relationships' must be a list."
        )

    component_names = set()

    for component in components:
        name = component.get("name")
        component_type = component.get("type")

        if not name:
            raise ValueError(
                "Component missing name."
            )

        if component_type not in ALLOWED_COMPONENT_TYPES:
            raise ValueError(
                f"Unsupported component type: "
                f"{component_type}"
            )

        component_names.add(name)

    for relationship in relationships:
        source = relationship.get("source")
        target = relationship.get("target")
        relationship_type = relationship.get("type")

        if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unsupported relationship: "
                f"{relationship_type}"
            )

        if source not in component_names:
            raise ValueError(
                f"Unknown source component: {source}"
            )

        if target not in component_names:
            raise ValueError(
                f"Unknown target component: {target}"
            )


def create_node(tx, component):
    label = component["type"]

    query = f"""
    MERGE (n:{label} {{
        name: $name,
        source: $source
    }})
    SET n += $properties
    """

    properties = dict(component)
    properties["source"] = GRAPH_SOURCE

    tx.run(
        query,
        name=component["name"],
        source=GRAPH_SOURCE,
        properties=properties,
    )


def create_relationship(tx, relationship):
    relationship_type = relationship["type"]

    query = f"""
    MATCH (sourceNode {{
        name: $source_name,
        source: $graph_source
    }})

    MATCH (targetNode {{
        name: $target_name,
        source: $graph_source
    }})

    MERGE (sourceNode)-[r:{relationship_type}]->(targetNode)

    SET r.source = $graph_source
    """

    tx.run(
        query,
        source_name=relationship["source"],
        target_name=relationship["target"],
        graph_source=GRAPH_SOURCE,
    )


def clear_existing_graph(driver):
    query = """
    MATCH (n {source: $source})
    DETACH DELETE n
    """

    with driver.session() as session:
        session.run(
            query,
            source=GRAPH_SOURCE,
        )


def load_graph(driver, graph):
    with driver.session() as session:
        for component in graph["components"]:
            session.execute_write(
                create_node,
                component,
            )

        for relationship in graph["relationships"]:
            session.execute_write(
                create_relationship,
                relationship,
            )


def verify_graph(driver):
    query = """
    MATCH (n {source: $source})
    OPTIONAL MATCH
        (n)-[r]->(m {source: $source})

    RETURN
        count(DISTINCT n) AS nodes,
        count(DISTINCT r) AS relationships
    """

    with driver.session() as session:
        record = session.run(
            query,
            source=GRAPH_SOURCE,
        ).single()

    return (
        record["nodes"],
        record["relationships"],
    )


def main():
    if not NEO4J_PASSWORD:
        raise RuntimeError(
            "NEO4J_PASSWORD environment variable is not set."
        )

    print()
    print("ARCHITECTURE GRAPH IMPORT")
    print("=" * 60)

    graph = load_json()

    print()
    print(
        f"Approved graph: {GRAPH_PATH}"
    )

    print(
        f"Components: {len(graph['components'])}"
    )

    print(
        f"Relationships: {len(graph['relationships'])}"
    )

    print()
    print("Validating graph...")

    validate_graph(graph)

    print("Validation passed.")

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USERNAME,
            NEO4J_PASSWORD,
        ),
    )

    try:
        driver.verify_connectivity()

        print()
        print("Connected to Neo4j.")

        print(
            "Removing previous architecture-diagram graph..."
        )

        clear_existing_graph(driver)

        print(
            "Loading approved architecture graph..."
        )

        load_graph(
            driver,
            graph,
        )

        nodes, relationships = verify_graph(
            driver
        )

        print()
        print("IMPORT COMPLETE")
        print("-" * 60)

        print(
            f"Imported nodes: "
            f"{nodes}"
        )

        print(
            f"Imported relationships: "
            f"{relationships}"
        )

        print()
        print(
            "Graph source: "
            f"{GRAPH_SOURCE}"
        )

    finally:
        driver.close()


if __name__ == "__main__":
    main()