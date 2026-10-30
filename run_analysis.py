import sys

from analysis.impact_analyzer import ImpactAnalyzer
from decision.decision_engine import DecisionEngine
from decision.model_client import (
    DecisionModelClient,
    print_model_decision,
)


def print_impact(impact):
    print()
    print("IMPACT ANALYSIS")
    print("-" * 60)

    component = impact["component"]

    print(f"Component:       {component['name']}")
    print(f"Type:            {component['type']}")
    print(f"Production:      {impact['production']}")
    print(f"Customer-facing: {impact['customer_facing']}")
    print(f"Critical:        {impact['critical']}")
    print(f"Redundancy:      {impact['redundancy']}")

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


def print_baseline_decision(decision):
    print()
    print("DETERMINISTIC POLICY BASELINE")
    print("-" * 60)

    print(f"Severity: {decision['severity']}")
    print(f"Action:   {decision['decision']}")
    print(f"Score:    {decision['score']}")

    if "impacted_components" in decision:
        print(
            "Impacted components: "
            f"{decision['impacted_components']}"
        )

    print()
    print("Reason codes:")

    if not decision["reason_codes"]:
        print("  None")
    else:
        for reason in decision["reason_codes"]:
            print(f"  - {reason}")


def print_comparison(baseline, model_result):
    answers = model_result["answers"]

    ai_action = answers["action"]["choice"]
    ai_severity = answers["severity"]["choice"]

    baseline_action = baseline["decision"]
    baseline_severity = baseline["severity"]

    print()
    print("DECISION COMPARISON")
    print("-" * 60)

    print(
        f"Policy severity: {baseline_severity}"
    )
    print(
        f"AI severity:     {ai_severity}"
    )

    print(
        f"Policy action:   {baseline_action}"
    )
    print(
        f"AI action:       {ai_action}"
    )

    severity_match = (
        baseline_severity == ai_severity
    )

    action_match = (
        baseline_action == ai_action
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

    if not severity_match or not action_match:
        print()
        print(
            "NOTE: The deterministic policy and "
            "AI decision model disagree."
        )
        print(
            "The MVP reports the disagreement; "
            "it does not automatically override "
            "the deterministic policy."
        )


def main():
    component = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "PostgreSQL"
    )

    print()
    print("=" * 60)
    print("AGENTIC DEPENDENCY INTELLIGENCE")
    print("=" * 60)
    print()
    print(f"Scenario: {component} unavailable")

    analyzer = ImpactAnalyzer()
    baseline_engine = DecisionEngine()
    ai_model = DecisionModelClient()

    try:
        # -------------------------------------------------
        # Step 1: Obtain real dependency evidence from Neo4j
        # -------------------------------------------------

        impact = analyzer.analyze(component)

        if not impact:
            print()
            print(
                f"Component '{component}' "
                "was not found in the dependency graph."
            )
            return

        print_impact(impact)

        # -------------------------------------------------
        # Step 2: Deterministic policy baseline
        # -------------------------------------------------

        baseline = baseline_engine.evaluate(
            impact
        )

        print_baseline_decision(
            baseline
        )

        # -------------------------------------------------
        # Step 3: Julia-1 probabilistic decision model
        # -------------------------------------------------

        try:
            model_result = ai_model.evaluate(
                impact
            )

            print_model_decision(
                model_result
            )

            # ---------------------------------------------
            # Step 4: Compare deterministic vs AI decisions
            # ---------------------------------------------

            print_comparison(
                baseline,
                model_result,
            )

        except Exception as exc:
            print()
            print("AI DECISION MODEL")
            print("-" * 60)

            print(
                "Julia-1 decision service unavailable "
                "or returned an error."
            )

            print(
                f"Error: {exc}"
            )

            print()
            print(
                "The deterministic policy decision "
                "remains available."
            )

    finally:
        analyzer.close()

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()