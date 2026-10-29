import os
from neo4j import GraphDatabase


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise RuntimeError("NEO4J_PASSWORD environment variable is not set")


class ImpactAnalyzer:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )

    def close(self):
        self.driver.close()

    def analyze(self, component_name):
        query = """
        MATCH (component {name: $component_name})

        OPTIONAL MATCH path =
            (affected)-[:USES|DEPENDS_ON*1..10]->(component)

        WITH component,
             collect(DISTINCT {
                 id: affected.id,
                 name: affected.name,
                 type: labels(affected)[0],
                 distance: length(path),
                 customer_facing: affected.customer_facing,
                 critical: affected.critical
             }) AS impacted

        OPTIONAL MATCH (service:Service)-[:USES|DEPENDS_ON*0..10]->(component)
        OPTIONAL MATCH (service)-[:OWNED_BY]->(team:Team)
        OPTIONAL MATCH (service)-[:RUNS_IN]->(environment:Environment)

        RETURN
            component.id AS component_id,
            component.name AS component_name,
            labels(component)[0] AS component_type,
            component.redundancy AS redundancy,
            impacted,
            collect(DISTINCT team.name) AS owners,
            collect(DISTINCT environment.name) AS environments
        """

        with self.driver.session() as session:
            record = session.run(
                query,
                component_name=component_name,
            ).single()

            if not record:
                return None

            result = record.data()

        impacted = [
            item for item in result["impacted"]
            if item["id"] is not None
        ]

        direct = [
            item for item in impacted
            if item["distance"] == 1
        ]

        indirect = [
            item for item in impacted
            if item["distance"] > 1
        ]

        customer_facing = any(
            item.get("customer_facing") is True
            for item in impacted
        )

        critical = any(
            item.get("critical") is True
            for item in impacted
        )

        return {
            "component": {
                "id": result["component_id"],
                "name": result["component_name"],
                "type": result["component_type"],
            },
            "direct_impact": direct,
            "indirect_impact": indirect,
            "owners": result["owners"],
            "environments": result["environments"],
            "production": "PROD" in result["environments"],
            "customer_facing": customer_facing,
            "critical": critical,
            "redundancy": result["redundancy"],
        }


def print_report(report):
    if not report:
        print("Component not found.")
        return

    print()
    print("IMPACT ANALYSIS")
    print("=" * 60)

    component = report["component"]

    print(f"Component:       {component['name']}")
    print(f"Type:            {component['type']}")
    print(f"Production:      {report['production']}")
    print(f"Customer-facing: {report['customer_facing']}")
    print(f"Critical:        {report['critical']}")
    print(f"Redundancy:      {report['redundancy']}")

    print("\nDirect impact:")

    for item in report["direct_impact"]:
        print(
            f"  - {item['name']} "
            f"[{item['type']}]"
        )

    print("\nIndirect impact:")

    for item in sorted(
        report["indirect_impact"],
        key=lambda x: (x["distance"], x["name"]),
    ):
        print(
            f"  - Level {item['distance']}: "
            f"{item['name']} [{item['type']}]"
        )

    print("\nOwners:")

    for owner in report["owners"]:
        print(f"  - {owner}")

    print("\nEnvironments:")

    for environment in report["environments"]:
        print(f"  - {environment}")


def main():
    analyzer = ImpactAnalyzer()

    try:
        report = analyzer.analyze("PostgreSQL")
        print_report(report)

    finally:
        analyzer.close()


if __name__ == "__main__":
    main()