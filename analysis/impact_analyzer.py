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

        OPTIONAL MATCH
            (service:Service)-[:USES|DEPENDS_ON*0..10]->(component)

        OPTIONAL MATCH
            (service)-[:OWNED_BY]->(team:Team)

        OPTIONAL MATCH
            (service)-[:RUNS_IN]->(environment:Environment)

        RETURN
            component.id AS component_id,
            component.name AS component_name,
            labels(component)[0] AS component_type,

            component.customer_facing AS component_customer_facing,
            component.critical AS component_critical,
            component.redundancy AS component_redundancy,

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
            item
            for item in result["impacted"]
            if item["id"] is not None
        ]

        direct = [
            item
            for item in impacted
            if item["distance"] == 1
        ]

        indirect = [
            item
            for item in impacted
            if item["distance"] > 1
        ]

        affected_services = [
            item
            for item in impacted
            if item["type"] == "Service"
        ]

        affected_applications = [
            item
            for item in impacted
            if item["type"] == "Application"
        ]

        critical_services = [
            item
            for item in affected_services
            if item.get("critical") is True
        ]

        customer_facing_services = [
            item
            for item in affected_services
            if item.get("customer_facing") is True
        ]

        max_dependency_depth = max(
            (
                item["distance"]
                for item in impacted
                if item["distance"] is not None
            ),
            default=0,
        )

        return {
            "component": {
                "id": result["component_id"],
                "name": result["component_name"],
                "type": result["component_type"],

                "critical": result["component_critical"],
                "customer_facing":
                    result["component_customer_facing"],
                "redundancy":
                    result["component_redundancy"],
            },

            "direct_impact": direct,
            "indirect_impact": indirect,

            "affected_services": affected_services,
            "affected_applications": affected_applications,

            "owners": result["owners"],
            "environments": result["environments"],

            "production_impact":
                "PROD" in result["environments"],

            "critical_service_impact":
                len(critical_services) > 0,

            "customer_facing_service_impact":
                len(customer_facing_services) > 0,

            "affected_service_count":
                len(affected_services),

            "affected_application_count":
                len(affected_applications),

            "direct_impact_count":
                len(direct),

            "indirect_impact_count":
                len(indirect),

            "max_dependency_depth":
                max_dependency_depth,
        }


def print_report(report):

    if not report:
        print("Component not found.")
        return

    component = report["component"]

    print()
    print("FAILED COMPONENT")
    print("=" * 60)

    print(f"Component:        {component['name']}")
    print(f"Type:             {component['type']}")
    print(f"Critical:         {component['critical']}")
    print(
        f"Customer-facing:  "
        f"{component['customer_facing']}"
    )
    print(f"Redundancy:       {component['redundancy']}")

    print()
    print("BLAST RADIUS")
    print("=" * 60)

    print("\nDirect impact:")

    if not report["direct_impact"]:
        print("  None")

    for item in report["direct_impact"]:
        print(
            f"  - {item['name']} "
            f"[{item['type']}]"
        )

    print("\nIndirect impact:")

    if not report["indirect_impact"]:
        print("  None")

    for item in sorted(
        report["indirect_impact"],
        key=lambda x: (x["distance"], x["name"]),
    ):
        print(
            f"  - Level {item['distance']}: "
            f"{item['name']} "
            f"[{item['type']}]"
        )

    print()
    print("IMPACT SUMMARY")
    print("=" * 60)

    print(
        f"Production impact:             "
        f"{report['production_impact']}"
    )

    print(
        f"Critical service impact:       "
        f"{report['critical_service_impact']}"
    )

    print(
        f"Customer-facing service impact:"
        f" {report['customer_facing_service_impact']}"
    )

    print(
        f"Affected services:             "
        f"{report['affected_service_count']}"
    )

    print(
        f"Affected applications:         "
        f"{report['affected_application_count']}"
    )

    print(
        f"Maximum dependency depth:      "
        f"{report['max_dependency_depth']}"
    )

    print("\nOwners:")

    if not report["owners"]:
        print("  None")

    for owner in report["owners"]:
        print(f"  - {owner}")

    print("\nEnvironments:")

    if not report["environments"]:
        print("  None")

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