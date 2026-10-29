import csv
import os
from pathlib import Path

from neo4j import GraphDatabase


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD environment variable is not set")


NODE_FILES = {
    "applications.csv": "Application",
    "services.csv": "Service",
    "databases.csv": "Database",
    "teams.csv": "Team",
    "environments.csv": "Environment",
}


def convert_value(value):
    """Convert CSV strings into useful Neo4j property types."""
    if value.lower() == "true":
        return True

    if value.lower() == "false":
        return False

    return value


def read_csv(filename):
    path = DATA_DIR / filename

    with path.open("r", encoding="utf-8") as file:
        return [
            {
                key: convert_value(value)
                for key, value in row.items()
            }
            for row in csv.DictReader(file)
        ]


def create_nodes(tx, label, rows):
    query = f"""
    UNWIND $rows AS row
    MERGE (n:{label} {{id: row.id}})
    SET n += row
    """

    tx.run(query, rows=rows)


def create_relationship(tx, source_id, target_id, relationship_type):
    allowed_relationships = {
        "USES",
        "DEPENDS_ON",
        "OWNED_BY",
        "RUNS_IN",
    }

    if relationship_type not in allowed_relationships:
        raise ValueError(
            f"Unsupported relationship type: {relationship_type}"
        )

    query = f"""
    MATCH (source {{id: $source_id}})
    MATCH (target {{id: $target_id}})
    MERGE (source)-[:{relationship_type}]->(target)
    """

    tx.run(
        query,
        source_id=source_id,
        target_id=target_id,
    )


def load_nodes(driver):
    print("Loading nodes...")

    for filename, label in NODE_FILES.items():
        rows = read_csv(filename)

        with driver.session() as session:
            session.execute_write(
                create_nodes,
                label,
                rows,
            )

        print(f"  {label}: {len(rows)}")


def load_relationships(driver):
    print("Loading relationships...")

    rows = read_csv("relationships.csv")

    with driver.session() as session:
        for row in rows:
            session.execute_write(
                create_relationship,
                row["source"],
                row["target"],
                row["type"],
            )

    print(f"  Relationships: {len(rows)}")


def verify_graph(driver):
    with driver.session() as session:

        node_count = session.run(
            "MATCH (n) RETURN count(n) AS count"
        ).single()["count"]

        relationship_count = session.run(
            "MATCH ()-[r]->() RETURN count(r) AS count"
        ).single()["count"]

    print()
    print("Graph summary")
    print("-------------")
    print(f"Nodes:         {node_count}")
    print(f"Relationships: {relationship_count}")


def main():
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(
            NEO4J_USERNAME,
            NEO4J_PASSWORD,
        ),
    )

    try:
        driver.verify_connectivity()

        print("Connected to Neo4j")
        print()

        load_nodes(driver)
        load_relationships(driver)
        verify_graph(driver)

        print()
        print("SUCCESS: Dependency graph loaded")

    finally:
        driver.close()


if __name__ == "__main__":
    main()