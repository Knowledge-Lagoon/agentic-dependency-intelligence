import sys

from analysis.impact_analyzer import ImpactAnalyzer
from decision.decision_engine import DecisionEngine


def main():
    component = sys.argv[1] if len(sys.argv) > 1 else "PostgreSQL"

    analyzer = ImpactAnalyzer()
    decision_engine = DecisionEngine()

    try:
        print()
        print("=" * 60)
        print("AGENTIC DEPENDENCY INTELLIGENCE")
        print("=" * 60)
        print(f"Scenario: {component} unavailable")

        # Step 1: get real evidence from Neo4j
        impact = analyzer.analyze(component)

        if not impact:
            print(f"\nComponent '{component}' was not found.")
            return

        # Step 2: evaluate real evidence
        decision = decision_engine.evaluate(impact)

        print("\nIMPACT")
        print("-" * 60)

        print(f"Component:       {impact['component']['name']}")
        print(f"Type:            {impact['component']['type']}")
        print(f"Production:      {impact['production']}")
        print(f"Customer-facing: {impact['customer_facing']}")
        print(f"Critical:        {impact['critical']}")
        print(f"Redundancy:      {impact['redundancy']}")

        print("\nDirect impact:")
        for item in impact["direct_impact"]:
            print(f"  - {item['name']} [{item['type']}]")

        print("\nIndirect impact:")
        for item in sorted(
            impact["indirect_impact"],
            key=lambda x: (x["distance"], x["name"]),
        ):
            print(
                f"  - Level {item['distance']}: "
                f"{item['name']} [{item['type']}]"
            )

        print("\nOwners:")
        for owner in impact["owners"]:
            print(f"  - {owner}")

        print("\nDECISION")
        print("-" * 60)

        print(f"Severity: {decision['severity']}")
        print(f"Action:   {decision['decision']}")
        print(f"Score:    {decision['score']}")

        print("\nReason codes:")
        for reason in decision["reason_codes"]:
            print(f"  - {reason}")

        print()
        print("=" * 60)

    finally:
        analyzer.close()


if __name__ == "__main__":
    main()