
import argparse

from analysis.impact_analyzer import (
    ImpactAnalyzer,
)

from decision.decision_engine import (
    DecisionEngine,
)

from decision.model_client import (
    DecisionModelClient,
    print_model_decision,
)

from rag.context_builder import (
    ContextBuilder,
    print_context,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Agentic Dependency Intelligence"
        )
    )

    parser.add_argument(
        "component",
        help=(
            "Component to analyse, "
            "for example PostgreSQL"
        ),
    )

    parser.add_argument(
        "--source",
        default=None,
        help=(
            "Restrict analysis to a graph source. "
            "Example: architecture_diagram"
        ),
    )

    return parser.parse_args()


def print_impact(impact):

    component = impact["component"]

    print()
    print("FAILED COMPONENT")
    print("-" * 60)

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
        f"{impact['graph_source']}"
    )

    print(
        f"Critical:         "
        f"{component.get('critical')}"
    )

    print(
        f"Customer-facing:  "
        f"{component.get('customer_facing')}"
    )

    print(
        f"Redundancy:       "
        f"{component.get('redundancy')}"
    )

    print()
    print("BLAST RADIUS")
    print("-" * 60)

    print()
    print("Direct impact:")

    if not impact[
        "direct_impact"
    ]:
        print("  None")

    else:
        for item in impact[
            "direct_impact"
        ]:

            print(
                f"  - {item['name']} "
                f"[{item['type']}]"
            )

    print()
    print("Indirect impact:")

    if not impact[
        "indirect_impact"
    ]:
        print("  None")

    else:
        for item in sorted(
            impact["indirect_impact"],
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
    print("-" * 60)

    print(
        "Production impact:              "
        f"{impact['production_impact']}"
    )

    print(
        "Critical service impact:        "
        f"{impact['critical_service_impact']}"
    )

    print(
        "Customer-facing service impact: "
        f"{impact['customer_facing_service_impact']}"
    )

    print(
        "Affected services:              "
        f"{impact['affected_service_count']}"
    )

    print(
        "Affected applications:          "
        f"{impact['affected_application_count']}"
    )

    print(
        "Direct impact count:            "
        f"{impact['direct_impact_count']}"
    )

    print(
        "Indirect impact count:          "
        f"{impact['indirect_impact_count']}"
    )

    print(
        "Maximum dependency depth:       "
        f"{impact['max_dependency_depth']}"
    )

    print()
    print("Affected applications:")

    if not impact[
        "affected_applications"
    ]:

        print("  None")

    else:
        for item in impact[
            "affected_applications"
        ]:

            print(
                f"  - {item['name']}"
            )

    print()
    print("Affected services:")

    if not impact[
        "affected_services"
    ]:

        print("  None")

    else:
        for item in impact[
            "affected_services"
        ]:

            print(
                f"  - {item['name']}"
            )

    print()
    print("Owners:")

    if not impact["owners"]:
        print("  None")

    else:
        for owner in impact[
            "owners"
        ]:

            print(
                f"  - {owner}"
            )

    print()
    print("Environments:")

    if not impact[
        "environments"
    ]:

        print("  None")

    else:
        for environment in impact[
            "environments"
        ]:

            print(
                f"  - {environment}"
            )


def print_policy_decision(
    decision,
):
    print()
    print(
        "DETERMINISTIC POLICY BASELINE"
    )
    print("-" * 60)

    print(
        f"Severity:          "
        f"{decision['severity']}"
    )

    print(
        f"Action:            "
        f"{decision['decision']}"
    )

    print(
        f"Policy Risk Score: "
        f"{decision['score']}"
    )

    if (
        "impacted_components"
        in decision
    ):

        print(
            "Impacted components: "
            f"{decision['impacted_components']}"
        )

    print()
    print("Reason codes:")

    if not decision[
        "reason_codes"
    ]:

        print("  None")

    else:
        for reason in decision[
            "reason_codes"
        ]:

            print(
                f"  - {reason}"
            )


def print_comparison(
    policy,
    model_result,
):
    answers = model_result[
        "answers"
    ]

    ai_action = (
        answers[
            "action"
        ]["choice"]
    )

    ai_severity = (
        answers[
            "severity"
        ]["choice"]
    )

    policy_action = (
        policy[
            "decision"
        ]
    )

    policy_severity = (
        policy[
            "severity"
        ]
    )

    severity_match = (
        policy_severity
        == ai_severity
    )

    action_match = (
        policy_action
        == ai_action
    )

    print()
    print("DECISION COMPARISON")
    print("-" * 60)

    print(
        f"Policy severity: "
        f"{policy_severity}"
    )

    print(
        f"AI severity:     "
        f"{ai_severity}"
    )

    print()

    print(
        f"Policy action:   "
        f"{policy_action}"
    )

    print(
        f"AI action:       "
        f"{ai_action}"
    )

    print()

    print(
        "Severity agreement: "
        f"{'YES' if severity_match else 'NO'}"
    )

    print(
        "Action agreement:   "
        f"{'YES' if action_match else 'NO'}"
    )

    print()

    if (
        severity_match
        and action_match
    ):

        print(
            "RESULT: Policy and AI "
            "decision model agree."
        )

    else:

        print(
            "RESULT: Policy and AI "
            "decision model disagree."
        )

        print(
            "The AI recommendation does not "
            "automatically override "
            "deterministic policy."
        )


def main():

    args = parse_args()

    component_name = (
        args.component
    )

    source = (
        args.source
    )

    print()
    print("=" * 60)
    print(
        "AGENTIC DEPENDENCY INTELLIGENCE"
    )
    print("=" * 60)

    print()

    print(
        f"Scenario: "
        f"{component_name} unavailable"
    )

    if source:
        print(
            f"Requested graph source: "
            f"{source}"
        )

    analyzer = (
        ImpactAnalyzer()
    )

    policy_engine = (
        DecisionEngine()
    )

    ai_model = (
        DecisionModelClient()
    )

    context_builder = (
        ContextBuilder()
    )

    try:

        impact = analyzer.analyze(
            component_name,
            source=source,
        )

        if not impact:
            print()
            print(
                f"Component "
                f"'{component_name}' "
                "was not found"
                + (
                    f" in graph source "
                    f"'{source}'."
                    if source
                    else "."
                )
            )

            return

        print_impact(
            impact
        )

        rag_context = (
            context_builder.build(
                impact
            )
        )

        print_context(
            rag_context
        )

        policy_decision = (
            policy_engine.evaluate(
                impact
            )
        )

        print_policy_decision(
            policy_decision
        )

        try:

            model_result = (
                ai_model.evaluate(
                    impact
                )
            )

            print_model_decision(
                model_result
            )

            print_comparison(
                policy_decision,
                model_result,
            )

        except Exception as exc:

            print()
            print(
                "AI DECISION MODEL"
            )
            print("-" * 60)

            print(
                "Julia-1 decision service "
                "is unavailable or returned "
                "an error."
            )

            print()

            print(
                f"Error: {exc}"
            )

            print()

            print(
                "The deterministic policy "
                "result remains available."
            )

    finally:
        analyzer.close()

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()