from rag.retriever import GraphRetriever


def display_value(value):
    if value is None:
        return "UNKNOWN"

    return str(value)


class ContextBuilder:

    def __init__(self):
        self.retriever = GraphRetriever()

    def build(self, impact):
        """
        Build graph-grounded RAG context from the
        ImpactAnalyzer result.
        """

        component = impact["component"]

        component_names = [
            component["name"]
        ]

        component_names.extend(
            item["name"]
            for item in impact["affected_services"]
        )

        component_names.extend(
            item["name"]
            for item in impact["affected_applications"]
        )

        # Remove duplicates while preserving order.
        component_names = list(
            dict.fromkeys(component_names)
        )

        documents = self.retriever.retrieve(
            component_names
        )

        context = {
            "failed_component": component,

            "graph_source":
                impact.get("graph_source"),

            "graph_components":
                component_names,

            "direct_impact":
                impact["direct_impact"],

            "indirect_impact":
                impact["indirect_impact"],

            "affected_services":
                impact["affected_services"],

            "affected_applications":
                impact["affected_applications"],

            "impact": {
                "production":
                    impact["production_impact"],

                "critical_service_impact":
                    impact["critical_service_impact"],

                "customer_facing_service_impact":
                    impact[
                        "customer_facing_service_impact"
                    ],

                "affected_service_count":
                    impact["affected_service_count"],

                "affected_application_count":
                    impact[
                        "affected_application_count"
                    ],

                "direct_impact_count":
                    impact["direct_impact_count"],

                "indirect_impact_count":
                    impact["indirect_impact_count"],

                "max_dependency_depth":
                    impact["max_dependency_depth"],

                "owners":
                    impact["owners"],

                "environments":
                    impact["environments"],
            },

            "graph_risk":
                impact.get("graph_risk"),

            "documents":
                documents,
        }

        return context


def print_context(context):
    print()
    print("GRAPH-RAG CONTEXT")
    print("=" * 60)

    component = context[
        "failed_component"
    ]

    print()
    print(
        f"Failed component: "
        f"{component['name']}"
    )

    print(
        "Graph source: "
        f"{display_value(context['graph_source'])}"
    )

    print()
    print("Graph components:")

    for component_name in context[
        "graph_components"
    ]:
        print(
            f"  - {component_name}"
        )

    print()
    print("Direct impact:")

    if not context["direct_impact"]:
        print("  None")
    else:
        for item in context[
            "direct_impact"
        ]:
            print(
                f"  - {item['name']} "
                f"[{item['type']}] "
                f"Level {item['distance']}"
            )

    print()
    print("Indirect impact:")

    if not context["indirect_impact"]:
        print("  None")
    else:
        for item in sorted(
            context["indirect_impact"],
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

    graph_risk = context.get(
        "graph_risk"
    )

    if graph_risk:
        print()
        print("Graph risk:")

        print(
            f"  Level: "
            f"{graph_risk['level']}"
        )

        print(
            f"  Score: "
            f"{graph_risk['score']}"
        )

    print()
    print("Retrieved documents:")

    if not context["documents"]:
        print("  None")

    for document in context[
        "documents"
    ]:
        print()
        print(
            f"  {document['title']}"
        )

        print(
            "    Matched: "
            + ", ".join(
                document[
                    "matched_components"
                ]
            )
        )

        print(
            f"    Score: "
            f"{document['score']}"
        )


def build_agent_context(context):
    """
    Convert authoritative Neo4j evidence and retrieved
    operational documents into the grounded text that is
    passed to the generative LLM.

    Neo4j remains the source of truth for dependency facts.
    """

    component = context[
        "failed_component"
    ]

    impact = context[
        "impact"
    ]

    graph_risk = context.get(
        "graph_risk"
    )

    sections = []

    # -----------------------------------------------------
    # Failed component
    # -----------------------------------------------------

    sections.append(
        "FAILED COMPONENT\n"
        f"Name: {component['name']}\n"
        f"Type: {component['type']}\n"
        f"Graph source: "
        f"{display_value(context['graph_source'])}\n"
        f"Declared criticality: "
        f"{display_value(component.get('critical'))}\n"
        f"Customer-facing metadata: "
        f"{display_value(component.get('customer_facing'))}\n"
        f"Redundancy metadata: "
        f"{display_value(component.get('redundancy'))}"
    )

    # -----------------------------------------------------
    # Authoritative direct impact
    # -----------------------------------------------------

    direct_lines = []

    for item in context[
        "direct_impact"
    ]:
        direct_lines.append(
            f"- {item['name']} "
            f"| type={item['type']} "
            f"| distance={item['distance']}"
        )

    if not direct_lines:
        direct_lines.append(
            "- None"
        )

    sections.append(
        "AUTHORITATIVE DIRECT IMPACT\n"
        + "\n".join(
            direct_lines
        )
    )

    # -----------------------------------------------------
    # Authoritative indirect impact
    # -----------------------------------------------------

    indirect_lines = []

    for item in sorted(
        context["indirect_impact"],
        key=lambda item: (
            item["distance"],
            item["name"],
        ),
    ):
        indirect_lines.append(
            f"- {item['name']} "
            f"| type={item['type']} "
            f"| distance={item['distance']}"
        )

    if not indirect_lines:
        indirect_lines.append(
            "- None"
        )

    sections.append(
        "AUTHORITATIVE INDIRECT IMPACT\n"
        + "\n".join(
            indirect_lines
        )
    )

    # -----------------------------------------------------
    # Impact summary
    # -----------------------------------------------------

    owner_text = (
        ", ".join(
            impact["owners"]
        )
        if impact["owners"]
        else "UNKNOWN"
    )

    environment_text = (
        ", ".join(
            impact["environments"]
        )
        if impact["environments"]
        else "UNKNOWN"
    )

    sections.append(
        "IMPACT SUMMARY\n"
        f"Production impact: "
        f"{impact['production']}\n"
        f"Critical service impact: "
        f"{impact['critical_service_impact']}\n"
        f"Customer-facing service impact: "
        f"{impact['customer_facing_service_impact']}\n"
        f"Affected services: "
        f"{impact['affected_service_count']}\n"
        f"Affected applications: "
        f"{impact['affected_application_count']}\n"
        f"Direct impact count: "
        f"{impact['direct_impact_count']}\n"
        f"Indirect impact count: "
        f"{impact['indirect_impact_count']}\n"
        f"Maximum dependency depth: "
        f"{impact['max_dependency_depth']}\n"
        f"Owners: {owner_text}\n"
        f"Environments: {environment_text}"
    )

    # -----------------------------------------------------
    # Graph-derived risk
    # -----------------------------------------------------

    if graph_risk:
        risk_lines = [
            "GRAPH-DERIVED RISK",
            (
                "Declared criticality: "
                f"{display_value(component.get('critical'))}"
            ),
            (
                "Graph risk level: "
                f"{graph_risk['level']}"
            ),
            (
                "Graph risk score: "
                f"{graph_risk['score']}"
            ),
            "Graph risk evidence:",
        ]

        if graph_risk["reasons"]:
            for reason in graph_risk[
                "reasons"
            ]:
                risk_lines.append(
                    f"- "
                    f"{reason['description']} "
                    f"(+{reason['points']})"
                )
        else:
            risk_lines.append(
                "- No downstream graph-risk "
                "evidence detected."
            )

        sections.append(
            "\n".join(
                risk_lines
            )
        )

    # -----------------------------------------------------
    # Graph components
    # -----------------------------------------------------

    sections.append(
        "GRAPH COMPONENTS\n"
        + "\n".join(
            f"- {name}"
            for name in context[
                "graph_components"
            ]
        )
    )

    # -----------------------------------------------------
    # Operational documentation
    # -----------------------------------------------------

    document_sections = []

    for document in context[
        "documents"
    ]:
        document_sections.append(
            f"DOCUMENT: "
            f"{document['title']}\n"
            f"Relevant components: "
            f"{', '.join(document['matched_components'])}\n\n"
            f"{document['content']}"
        )

    if document_sections:
        sections.append(
            "OPERATIONAL DOCUMENTATION\n\n"
            + "\n\n".join(
                document_sections
            )
        )

    else:
        sections.append(
            "OPERATIONAL DOCUMENTATION\n"
            "No relevant operational documents found."
        )

    # -----------------------------------------------------
    # Grounding rules for the LLM
    # -----------------------------------------------------

    sections.append(
        "GROUNDING RULES\n"
        "- Direct and indirect impact above are authoritative "
        "Neo4j results.\n"
        "- Do not change a component's type.\n"
        "- Do not move an indirect dependency into direct impact.\n"
        "- Do not move a direct dependency into indirect impact.\n"
        "- UNKNOWN metadata means the value was not supplied; "
        "it does not mean False.\n"
        "- Graph-derived risk is separate from declared "
        "criticality.\n"
        "- Operational recommendations must be supported by "
        "the supplied documentation."
    )

    return "\n\n".join(
        sections
    )