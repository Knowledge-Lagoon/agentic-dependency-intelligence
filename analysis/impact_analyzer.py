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

    def calculate_graph_risk(
        self,
        direct_impact,
        indirect_impact,
        affected_applications,
        max_dependency_depth,
    ):
        """
        Calculate topology-based operational risk.

        This is independent of declared criticality.

        MVP scoring:

        Each direct dependency impact       +2
        Each indirect dependency impact     +1
        Each affected application           +2
        Dependency depth >= 3               +2
        Dependency depth >= 5               +1 additional

        Risk levels:

        0-2   LOW
        3-5   MEDIUM
        6-8   HIGH
        9+    CRITICAL
        """

        score = 0
        reasons = []

        direct_count = len(
            direct_impact
        )

        indirect_count = len(
            indirect_impact
        )

        application_count = len(
            affected_applications
        )

        if direct_count > 0:
            points = (
                direct_count * 2
            )

            score += points

            reasons.append(
                {
                    "reason":
                        "DIRECT_DEPENDENCY_IMPACT",

                    "description":
                        f"{direct_count} directly "
                        "affected component(s)",

                    "points":
                        points,
                }
            )

        if indirect_count > 0:
            points = (
                indirect_count
            )

            score += points

            reasons.append(
                {
                    "reason":
                        "INDIRECT_DEPENDENCY_IMPACT",

                    "description":
                        f"{indirect_count} indirectly "
                        "affected component(s)",

                    "points":
                        points,
                }
            )

        if application_count > 0:
            points = (
                application_count * 2
            )

            score += points

            reasons.append(
                {
                    "reason":
                        "APPLICATION_IMPACT",

                    "description":
                        f"{application_count} affected "
                        "application(s)",

                    "points":
                        points,
                }
            )

        if max_dependency_depth >= 3:
            score += 2

            reasons.append(
                {
                    "reason":
                        "DEEP_DEPENDENCY_CHAIN",

                    "description":
                        "Maximum dependency depth "
                        "is at least 3",

                    "points":
                        2,
                }
            )

        if max_dependency_depth >= 5:
            score += 1

            reasons.append(
                {
                    "reason":
                        "VERY_DEEP_DEPENDENCY_CHAIN",

                    "description":
                        "Maximum dependency depth "
                        "is at least 5",

                    "points":
                        1,
                }
            )

        if score >= 9:
            level = "CRITICAL"

        elif score >= 6:
            level = "HIGH"

        elif score >= 3:
            level = "MEDIUM"

        else:
            level = "LOW"

        return {
            "level":
                level,

            "score":
                score,

            "direct_count":
                direct_count,

            "indirect_count":
                indirect_count,

            "affected_application_count":
                application_count,

            "max_dependency_depth":
                max_dependency_depth,

            "reasons":
                reasons,
        }

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
            (affected)
            -[:USES|DEPENDS_ON*1..10]->
            (component)

        WHERE
            $source IS NULL
            OR affected.source = $source

        WITH
            component,
            collect(
                DISTINCT {
                    id:
                        affected.id,

                    name:
                        affected.name,

                    type:
                        labels(affected)[0],

                    distance:
                        length(path),

                    customer_facing:
                        affected.customer_facing,

                    critical:
                        affected.critical,

                    redundancy:
                        affected.redundancy,

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
            (service)-[:OWNED_BY]->
            (team:Team)

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
            component.id
                AS component_id,

            component.name
                AS component_name,

            labels(component)[0]
                AS component_type,

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
                    component_name=
                        component_name,

                    source=
                        source,
                )
            )

        if not records:
            return None

        result = records[0].data()

        if result.get(
            "component_name"
        ) is None:
            return None

        impacted = [
            item
            for item in result.get(
                "impacted",
                [],
            )
            if item.get("name")
            is not None
        ]

        # All nodes returned by the dependency traversal are
        # downstream affected components. The failed component
        # itself is represented separately with distance 0.
        for item in impacted:
            item["status"] = "AFFECTED"

        direct = [
            item
            for item in impacted
            if item.get(
                "distance"
            ) == 1
        ]

        indirect = [
            item
            for item in impacted
            if (
                item.get(
                    "distance"
                )
                is not None
                and
                item["distance"] > 1
            )
        ]

        affected_services = [
            item
            for item in impacted
            if item.get(
                "type"
            ) == "Service"
        ]

        affected_applications = [
            item
            for item in impacted
            if item.get(
                "type"
            ) == "Application"
        ]

        critical_services = [
            item
            for item in affected_services
            if item.get(
                "critical"
            ) is True
        ]

        customer_facing_services = [
            item
            for item in affected_services
            if item.get(
                "customer_facing"
            ) is True
        ]

        max_dependency_depth = max(
            (
                item["distance"]
                for item in impacted
                if item.get(
                    "distance"
                )
                is not None
            ),
            default=0,
        )

        owners = [
            owner
            for owner in result.get(
                "owners",
                [],
            )
            if owner is not None
        ]

        environments = [
            environment
            for environment in result.get(
                "environments",
                [],
            )
            if environment is not None
        ]

        graph_risk = (
            self.calculate_graph_risk(
                direct_impact=
                    direct,

                indirect_impact=
                    indirect,

                affected_applications=
                    affected_applications,

                max_dependency_depth=
                    max_dependency_depth,
            )
        )

        # Preserve UNKNOWN when graph metadata is absent.
        #
        # False should mean that metadata was available and
        # explicitly showed no such impact. It must not mean
        # that the property was missing from the architecture
        # diagram.
        production_impact = (
            "PROD" in environments
            if environments
            else None
        )

        critical_values = [
            item.get("critical")
            for item in affected_services
        ]

        if any(value is True for value in critical_values):
            critical_service_impact = True
        elif critical_values and all(
            value is False
            for value in critical_values
        ):
            critical_service_impact = False
        else:
            critical_service_impact = None

        customer_facing_values = [
            item.get("customer_facing")
            for item in affected_services
        ]

        if any(
            value is True
            for value in customer_facing_values
        ):
            customer_facing_service_impact = True
        elif customer_facing_values and all(
            value is False
            for value in customer_facing_values
        ):
            customer_facing_service_impact = False
        else:
            customer_facing_service_impact = None

        return {
            "graph_source":
                source
                or result.get(
                    "component_source"
                ),

            "component": {
                "id":
                    result.get(
                        "component_id"
                    ),

                "name":
                    result.get(
                        "component_name"
                    ),

                "type":
                    result.get(
                        "component_type"
                    ),

                "critical":
                    result.get(
                        "component_critical"
                    ),

                "customer_facing":
                    result.get(
                        "component_customer_facing"
                    ),

                "redundancy":
                    result.get(
                        "component_redundancy"
                    ),

                "source":
                    result.get(
                        "component_source"
                    ),

                "status":
                    "FAILED",

                "distance":
                    0,
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
                production_impact,

            "critical_service_impact":
                critical_service_impact,

            "customer_facing_service_impact":
                customer_facing_service_impact,

            "affected_service_count":
                len(
                    affected_services
                ),

            "affected_application_count":
                len(
                    affected_applications
                ),

            "direct_impact_count":
                len(
                    direct
                ),

            "indirect_impact_count":
                len(
                    indirect
                ),

            "max_dependency_depth":
                max_dependency_depth,

            "graph_risk":
                graph_risk,
        }


def display_value(value):
    if value is None:
        return "UNKNOWN"

    return value


def print_report(report):

    if not report:
        print(
            "Component not found."
        )
        return

    component = report[
        "component"
    ]

    print()
    print("FAILED COMPONENT")
    print("=" * 60)

    print(
        f"Name:             "
        f"{component['name']}"
    )

    print(
        f"Type:             "
        f"{component['type']}"
    )

    print(
        f"Graph source:     "
        f"{display_value(report['graph_source'])}"
    )

    print(
        f"Critical:         "
        f"{display_value(component['critical'])}"
    )

    print(
        f"Customer-facing:  "
        f"{display_value(component['customer_facing'])}"
    )

    print(
        f"Redundancy:       "
        f"{display_value(component['redundancy'])}"
    )

    print()
    print("BLAST RADIUS")
    print("=" * 60)

    print()
    print("Direct impact:")

    if not report[
        "direct_impact"
    ]:
        print("  None")

    else:
        for item in report[
            "direct_impact"
        ]:
            print(
                f"  - {item['name']} "
                f"[{item['type']}] "
                f"Level {item['distance']}"
            )

    print()
    print("Indirect impact:")

    if not report[
        "indirect_impact"
    ]:
        print("  None")

    else:
        for item in sorted(
            report[
                "indirect_impact"
            ],
            key=lambda item: (
                item["distance"],
                item["name"],
            ),
        ):
            print(
                f"  - {item['name']} "
                f"[{item['type']}] "
                f"Level {item['distance']}"
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

    graph_risk = report[
        "graph_risk"
    ]

    print()
    print("GRAPH RISK")
    print("=" * 60)

    print(
        f"Level: "
        f"{graph_risk['level']}"
    )

    print(
        f"Score: "
        f"{graph_risk['score']}"
    )

    print()
    print("Risk evidence:")

    if not graph_risk[
        "reasons"
    ]:
        print(
            "  - No downstream dependency "
            "risk detected."
        )

    else:
        for reason in graph_risk[
            "reasons"
        ]:
            print(
                f"  - "
                f"{reason['description']}: "
                f"+{reason['points']}"
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