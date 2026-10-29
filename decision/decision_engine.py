class DecisionEngine:
    """
    Deterministic operational decision model.

    Input:
        Structured evidence produced by ImpactAnalyzer.

    Output:
        Severity, decision, score and reason codes.
    """

    def evaluate(self, impact):
        if not impact:
            return {
                "severity": "UNKNOWN",
                "decision": "INVESTIGATE",
                "score": 0,
                "reason_codes": ["COMPONENT_NOT_FOUND"],
            }

        score = 0
        reasons = []

        # Production impact
        if impact.get("production"):
            score += 3
            reasons.append("PRODUCTION")

        # Critical service impact
        if impact.get("critical"):
            score += 3
            reasons.append("CRITICAL_SERVICE")

        # Customer-facing impact
        if impact.get("customer_facing"):
            score += 2
            reasons.append("CUSTOMER_FACING")

        # Lack of redundancy
        if impact.get("redundancy") is False:
            score += 2
            reasons.append("NO_REDUNDANCY")

        # Blast radius
        impacted_count = (
            len(impact.get("direct_impact", []))
            + len(impact.get("indirect_impact", []))
        )

        if impacted_count >= 3:
            score += 2
            reasons.append("WIDE_BLAST_RADIUS")
        elif impacted_count >= 1:
            score += 1
            reasons.append("DEPENDENCY_IMPACT")

        # Translate score into operational decision.
        if score >= 9:
            severity = "CRITICAL"
            decision = "ESCALATE"
        elif score >= 6:
            severity = "HIGH"
            decision = "ESCALATE"
        elif score >= 3:
            severity = "MEDIUM"
            decision = "INVESTIGATE"
        else:
            severity = "LOW"
            decision = "MONITOR"

        return {
            "severity": severity,
            "decision": decision,
            "score": score,
            "reason_codes": reasons,
            "impacted_components": impacted_count,
        }


def print_decision(decision):
    print()
    print("DECISION MODEL")
    print("=" * 60)

    print(f"Severity:            {decision['severity']}")
    print(f"Decision:            {decision['decision']}")
    print(f"Decision score:       {decision['score']}")

    if "impacted_components" in decision:
        print(
            f"Impacted components: {decision['impacted_components']}"
        )

    print()
    print("Reason codes:")

    for reason in decision["reason_codes"]:
        print(f"  - {reason}")


def main():

    # Temporary test evidence.
    # This mirrors the PostgreSQL scenario produced by ImpactAnalyzer.

    test_impact = {
        "production": True,
        "critical": True,
        "customer_facing": True,
        "redundancy": False,
        "direct_impact": [
            {"name": "Payment Service"}
        ],
        "indirect_impact": [
            {"name": "Order Service"},
            {"name": "Customer Portal"},
        ],
    }

    engine = DecisionEngine()

    decision = engine.evaluate(test_impact)

    print_decision(decision)


if __name__ == "__main__":
    main()