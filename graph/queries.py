import os
from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD environment variable is not set")


class DependencyGraph:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )

    def close(self):
        self.driver.close()

    def find_component(self, name):
        query = """
        MATCH (n {name: $name})
        RETURN
            labels(n)[0] AS type,
            n.id AS id,
            n.name AS name,
            properties(n) AS properties
        """

        with self.driver.session() as session:
            result = session.run(query, name=name)
            return [record.data() for record in result]

    def direct_dependents(self, name):
        query = """
        MATCH (dependent)-[r]->(component {name: $name})
        WHERE type(r) IN ['USES', 'DEPENDS_ON']
        RETURN
            dependent.name AS dependent,
            labels(dependent)[0] AS type,
            type(r) AS relationship
        ORDER BY dependent
        """

        with self.driver.session() as session:
            result = session.run(query, name=name)
            return [record.data() for record in result]

    def blast_radius(self, name):
        query = """
        MATCH path =
            (affected)-[:USES|DEPENDS_ON*1..10]->
            (component {name: $name})
        RETURN DISTINCT
            affected.id AS id,
            affected.name AS name,
            labels(affected)[0] AS type,
            length(path) AS distance
        ORDER BY distance, name
        """

        with self.driver.session() as session:
            result = session.run(query, name=name)
            return [record.data() for record in result]


def main():
    graph = DependencyGraph()

    try:
        component = "PostgreSQL"

        print()
        print(f"Component: {component}")
        print("=" * 50)

        found = graph.find_component(component)

        if not found:
            print("Component not found.")
            return

        print("\nComponent details:")
        for item in found:
            print(
                f"  {item['type']}: "
                f"{item['name']} ({item['id']})"
            )

        print("\nDirect impact:")

        direct = graph.direct_dependents(component)

        if not direct:
            print("  None")

        for item in direct:
            print(
                f"  {item['dependent']} "
                f"[{item['type']}] "
                f"via {item['relationship']}"
            )

        print("\nBlast radius:")

        impacted = graph.blast_radius(component)

        if not impacted:
            print("  None")

        for item in impacted:
            print(
                f"  Level {item['distance']}: "
                f"{item['name']} "
                f"[{item['type']}]"
            )

    finally:
        graph.close()


if __name__ == "__main__":
    main()