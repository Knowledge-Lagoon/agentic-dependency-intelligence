import os

from neo4j import GraphDatabase


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

if not NEO4J_PASSWORD:
    raise RuntimeError(
        "NEO4J_PASSWORD environment variable is not set"
    )


class ImpactAnalyzer:

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(
                NEO4J_USERNAME,
                NEO4J_PASSWORD,
            ),
        )

    def close(self):
        self.driver.close()

    def analyze(
        self,
        component_name,
        source=None,
    ):
        query = """
        MATCH (component {name: $component_name})

        WHERE
            $source IS NULL
            OR component.source = $source

        OPTIONAL MATCH path =
            (affected)-[:USES|DEPENDS_ON*1..10]->(component)

        WHERE
            $source IS NULL
            OR affected.source = $source

        WITH
            component,
            collect(
                DISTINCT {
                    id: affected.id,
                    name: affected.name,
                    type: labels(affected)[0],
                    distance: length(path),
                    customer_facing:
                        affected.customer_facing,
                    critical:
                        affected.critical,
                    source:
                        affected.source
                }
            ) AS impacted

        OPTIONAL MATCH
            (service:Service)
            -[:USES|DEPENDS_ON*0..10]->
            (component)

        WHERE
            $source IS NULL
            OR service.source = $source

        OPTIONAL MATCH
            (service)-[:OWNED_BY]->(team:Team)

        WHERE
            $source IS NULL
            OR team.source = $source
            OR team.source IS NULL

        OPTIONAL MATCH
            (service)-[:RUNS_IN]->
            (environment:Environment)

        WHERE
            $source IS NULL
            OR environment.source = $source
            OR environment.source IS NULL

        RETURN
            component.id AS component_id,
            component.name AS component_name,
            labels(component)[0] AS component_type,

            component.customer_facing
                AS component_customer_facing,

            component.critical
                AS component_critical,

            component.redundancy
                AS component_redundancy,

            component.source
                AS component_source,

            impacted,

            collect(
                DISTINCT team.name
            ) AS owners,

            collect(
                DISTINCT environment.name
            ) AS environments
        """

        with self.driver.session() as session:
            records = list(
                session.run(
                    query,
                    component_name=component_name,
                    source=source,
                )
            )

        if not records:
            return None

        result = records[0].data()

        if result["component_name"] is None:
            return None

        impacted = [
            item
            for item in result["impacted"]
            if item.get("id") is not None
            or item.get("name") is not None
        ]

        direct = [
            item
            for item in impacted
            if item.get("distance") == 1
        ]

        indirect = [
            item
            for item in impacted
            if (
                item.get("distance") is not None
                and item["distance"] > 1
            )
        ]

        affected_services = [
            item
            for item in impacted
            if item.get("type") == "Service"
        ]

        affected_applications = [
            item
            for item in impacted
            if item.get("type") == "Application"
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
                if item.get("distance") is not None
            ),
            default=0,
        )

        environments = [
            name
            for name in result["environments"]
            if name is not None
        ]

        owners = [
            name
            for name in result["owners"]
            if name is not None
        ]

        return {
            "graph_source": (
                source
                or result["component_source"]
            ),

            "component": {
                "id":
                    result["component_id"],

                "name":
                    result["component_name"],

                "type":
                    result["component_type"],

                "critical":
                    result[
                        "component_critical"
                    ],

                "customer_facing":
                    result[
                        "component_customer_facing"
                    ],

                "redundancy":
                    result[
                        "component_redundancy"
                    ],

                "source":
                    result[
                        "component_source"
                    ],
            },

            "direct_impact":
                direct,

            "indirect_impact":
                indirect,

            "affected_services":
                affected_services,

            "affected_applications":
                affected_applications,

            "owners":
                owners,

            "environments":
                environments,

            "production_impact":
                "PROD" in environments,

            "critical_service_impact":
                len(critical_services) > 0,

            "customer_facing_service_impact":
                len(
                    customer_facing_services
                ) > 0,

            "affected_service_count":
                len(affected_services),

            "affected_application_count":
                len(
                    affected_applications
                ),

            "direct_impact_count":
                len(direct),

            "indirect_impact_count":
                len(indirect),

            "max_dependency_depth":
                max_dependency_depth,
        }


def print_report(report):

    if not report:
        print(
            "Component not found."
        )
        return

    component = report["component"]

    print()
    print("FAILED COMPONENT")
    print("=" * 60)

    print(
        f"Component:        "
        f"{component['name']}"
    )

    print(
        f"Type:             "
        f"{component['type']}"
    )

    print(
        f"Graph source:     "
        f"{report['graph_source']}"
    )

    print(
        f"Critical:         "
        f"{component['critical']}"
    )

    print(
        f"Customer-facing:  "
        f"{component['customer_facing']}"
    )

    print(
        f"Redundancy:       "
        f"{component['redundancy']}"
    )

    print()
    print("BLAST RADIUS")
    print("=" * 60)

    print()
    print("Direct impact:")

    if not report["direct_impact"]:
        print("  None")

    for item in report[
        "direct_impact"
    ]:
        print(
            f"  - {item['name']} "
            f"[{item['type']}]"
        )

    print()
    print("Indirect impact:")

    if not report[
        "indirect_impact"
    ]:
        print("  None")

    for item in sorted(
        report["indirect_impact"],
        key=lambda x: (
            x["distance"],
            x["name"],
        ),
    ):
        print(
            f"  - Level "
            f"{item['distance']}: "
            f"{item['name']} "
            f"[{item['type']}]"
        )

    print()
    print("IMPACT SUMMARY")
    print("=" * 60)

    print(
        "Production impact:              "
        f"{report['production_impact']}"
    )

    print(
        "Critical service impact:        "
        f"{report['critical_service_impact']}"
    )

    print(
        "Customer-facing service impact: "
        f"{report['customer_facing_service_impact']}"
    )

    print(
        "Affected services:              "
        f"{report['affected_service_count']}"
    )

    print(
        "Affected applications:          "
        f"{report['affected_application_count']}"
    )

    print(
        "Maximum dependency depth:       "
        f"{report['max_dependency_depth']}"
    )


if __name__ == "__main__":
    analyzer = ImpactAnalyzer()

    try:
        report = analyzer.analyze(
            "PostgreSQL"
        )

        print_report(
            report
        )

    finally:
        analyzer.close()