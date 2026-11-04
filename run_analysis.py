import sys

from analysis.impact_analyzer import ImpactAnalyzer
from decision.decision_engine import DecisionEngine
from decision.model_client import (
    DecisionModelClient,
    print_model_decision,
)


def print_impact(impact):
    component = impact["component"]

    # ---------------------------------------------------------
    # Failed component
    # ---------------------------------------------------------

    print()
    print("FAILED COMPONENT")
    print("-" * 60)

    print(f"Component:        {component['name']}")
    print(f"Type:             {component['type']}")
    print(f"Critical:         {component.get('critical')}")
    print(
        f"Customer-facing:  "
        f"{component.get('customer_facing')}"
    )
    print(f"Redundancy:       {component.get('redundancy')}")

    # ---------------------------------------------------------
    # Blast radius
    # ---------------------------------------------------------

    print()
    print("BLAST RADIUS")
    print("-" * 60)

    print()
    print("Direct impact:")

    if not impact["direct_impact"]:
        print("  None")
    else:
        for item in impact["direct_impact"]:
            print(
                f"  - {item['name']} "
                f"[{item['type']}]"
            )

    print()
    print("Indirect impact:")

    if not impact["indirect_impact"]:
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
                f"  - Level {item['distance']}: "
                f"{item['name']} "
                f"[{item['type']}]"
            )

    # ---------------------------------------------------------
    # Impact summary
    # ---------------------------------------------------------

    print()
    print("IMPACT SUMMARY")
    print("-" * 60)

    print(
        f"Production impact:              "
        f"{impact['production_impact']}"
    )

    print(
        f"Critical service impact:        "
        f"{impact['critical_service_impact']}"
    )

    print(
        f"Customer-facing service impact: "
        f"{impact['customer_facing_service_impact']}"
    )

    print(
        f"Affected services:              "
        f"{impact['affected_service_count']}"
    )

    print(
        f"Affected applications:          "
        f"{impact['affected_application_count']}"
    )

    print(
        f"Direct impact count:            "
        f"{impact['direct_impact_count']}"
    )

    print(
        f"Indirect impact count:          "
        f"{impact['indirect_impact_count']}"
    )

    print(
        f"Maximum dependency depth:       "
        f"{impact['max_dependency_depth']}"
    )

    print()
    print("Affected applications:")

    if not impact["affected_applications"]:
        print("  None")
    else:
        for item in impact["affected_applications"]:
            print(f"  - {item['name']}")

    print()
    print("Affected services:")

    if not impact["affected_services"]:
        print("  None")
    else:
        for item in impact["affected_services"]:
            print(f"  - {item['name']}")

    print()
    print("Owners:")

    if not impact["owners"]:
        print("  None")
    else:
        for owner in impact["owners"]:
            print(f"  - {owner}")

    print()
    print("Environments:")

    if not impact["environments"]:
        print("  None")
    else:
        for environment in impact["environments"]:
            print(f"  - {environment}")


def print_policy_decision(decision):
    print()
    print("DETERMINISTIC POLICY BASELINE")
    print("-" * 60)

    print(f"Severity:          {decision['severity']}")
    print(f"Action:            {decision['decision']}")
    print(f"Policy Risk Score: {decision['score']}")

    if "impacted_components" in decision:
        print(
            f"Impacted components: "
            f"{decision['impacted_components']}"
        )

    print()
    print("Reason codes:")

    if not decision["reason_codes"]:
        print("  None")
    else:
        for reason in decision["reason_codes"]:
            print(f"  - {reason}")


def print_comparison(policy, model_result):
    answers = model_result["answers"]

    ai_action = answers["action"]["choice"]
    ai_severity = answers["severity"]["choice"]

    policy_action = policy["decision"]
    policy_severity = policy["severity"]

    severity_match = (
        policy_severity == ai_severity
    )

    action_match = (
        policy_action == ai_action
    )

    print()
    print("DECISION COMPARISON")
    print("-" * 60)

    print(f"Policy severity: {policy_severity}")
    print(f"AI severity:     {ai_severity}")

    print()
    print(f"Policy action:   {policy_action}")
    print(f"AI action:       {ai_action}")

    print()
    print(
        "Severity agreement: "
        f"{'YES' if severity_match else 'NO'}"
    )

    print(
        "Action agreement:   "
        f"{'YES' if action_match else 'NO'}"
    )

    if severity_match and action_match:
        print()
        print(
            "RESULT: Policy and AI decision model agree."
        )
    else:
        print()
        print(
            "RESULT: Policy and AI decision model disagree."
        )

        print(
            "The AI recommendation does not automatically "
            "override deterministic policy."
        )


def main():
    component_name = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "PostgreSQL"
    )

    print()
    print("=" * 60)
    print("AGENTIC DEPENDENCY INTELLIGENCE")
    print("=" * 60)

    print()
    print(
        f"Scenario: {component_name} unavailable"
    )

    analyzer = ImpactAnalyzer()
    policy_engine = DecisionEngine()
    ai_model = DecisionModelClient()

    try:
        # -----------------------------------------------------
        # Step 1
        # Retrieve real dependency evidence from Neo4j
        # -----------------------------------------------------

        impact = analyzer.analyze(
            component_name
        )

        if not impact:
            print()
            print(
                f"Component '{component_name}' "
                "was not found in the dependency graph."
            )

            return

        print_impact(
            impact
        )

        # -----------------------------------------------------
        # Step 2
        # Deterministic policy evaluation
        # -----------------------------------------------------

        policy_decision = (
            policy_engine.evaluate(
                impact
            )
        )

        print_policy_decision(
            policy_decision
        )

        # -----------------------------------------------------
        # Step 3
        # Julia-1 probabilistic decision
        # -----------------------------------------------------

        try:
            model_result = ai_model.evaluate(
                impact
            )

            print_model_decision(
                model_result
            )

            # -------------------------------------------------
            # Step 4
            # Compare policy and AI results
            # -------------------------------------------------

            print_comparison(
                policy_decision,
                model_result,
            )

        except Exception as exc:
            print()
            print("AI DECISION MODEL")
            print("-" * 60)

            print(
                "Julia-1 decision service is unavailable "
                "or returned an error."
            )

            print()
            print(
                f"Error: {exc}"
            )

            print()
            print(
                "The deterministic policy result remains "
                "available."
            )

    finally:
        analyzer.close()

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()