from rag.retriever import GraphRetriever


class ContextBuilder:

    def __init__(self):
        self.retriever = GraphRetriever()

    def build(self, impact):
        """
        Build graph-grounded context from an ImpactAnalyzer result.
        """

        component = impact["component"]

        # Start with the failed component itself.
        component_names = [
            component["name"]
        ]

        # Add every service/result discovered through Neo4j.
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
            "graph_components": component_names,

            "impact": {
                "production":
                    impact["production_impact"],

                "critical_service_impact":
                    impact["critical_service_impact"],

                "customer_facing_service_impact":
                    impact["customer_facing_service_impact"],

                "affected_service_count":
                    impact["affected_service_count"],

                "affected_application_count":
                    impact["affected_application_count"],

                "max_dependency_depth":
                    impact["max_dependency_depth"],

                "owners":
                    impact["owners"],

                "environments":
                    impact["environments"],
            },

            "documents": documents,
        }

        return context


def print_context(context):

    print()
    print("GRAPH-RAG CONTEXT")
    print("=" * 60)

    print()
    print(
        "Failed component: "
        f"{context['failed_component']['name']}"
    )

    print()
    print("Graph components:")

    for component in context["graph_components"]:
        print(f"  - {component}")

    print()
    print("Retrieved documents:")

    if not context["documents"]:
        print("  None")

    for document in context["documents"]:

        print()
        print(
            f"  {document['title']}"
        )

        print(
            "    Matched: "
            + ", ".join(
                document["matched_components"]
            )
        )

        print(
            f"    Score: "
            f"{document['score']}"
        )


def build_agent_context(context):
    """
    Convert graph + operational documentation into a text
    context that can later be supplied to an agent/LLM.
    """

    component = context["failed_component"]
    impact = context["impact"]

    sections = []

    sections.append(
        "FAILED COMPONENT\n"
        f"Name: {component['name']}\n"
        f"Type: {component['type']}\n"
        f"Critical: {component.get('critical')}\n"
        f"Customer-facing: "
        f"{component.get('customer_facing')}\n"
        f"Redundancy: {component.get('redundancy')}"
    )

    sections.append(
        "IMPACT\n"
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
        f"Maximum dependency depth: "
        f"{impact['max_dependency_depth']}\n"
        f"Owners: {', '.join(impact['owners'])}"
    )

    sections.append(
        "GRAPH COMPONENTS\n"
        + "\n".join(
            f"- {name}"
            for name in context["graph_components"]
        )
    )

    document_sections = []

    for document in context["documents"]:
        document_sections.append(
            f"DOCUMENT: {document['title']}\n"
            f"Relevant components: "
            f"{', '.join(document['matched_components'])}\n\n"
            f"{document['content']}"
        )

    if document_sections:
        sections.append(
            "OPERATIONAL DOCUMENTATION\n\n"
            + "\n\n".join(document_sections)
        )

    return "\n\n".join(sections)
