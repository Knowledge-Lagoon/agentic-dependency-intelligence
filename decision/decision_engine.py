class DecisionEngine:

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

        component = impact["component"]

        # Production impact
        if impact["production_impact"]:
            score += 3
            reasons.append("PRODUCTION_IMPACT")

        # Failed component itself is critical
        if component.get("critical") is True:
            score += 2
            reasons.append("CRITICAL_COMPONENT")

        # Critical services appear in the blast radius
        if impact["critical_service_impact"]:
            score += 2
            reasons.append("CRITICAL_SERVICE_IMPACT")

        # Customer-facing services appear in blast radius
        if impact["customer_facing_service_impact"]:
            score += 2
            reasons.append("CUSTOMER_FACING_IMPACT")

        # Only databases currently carry redundancy information
        if component.get("redundancy") is False:
            score += 2
            reasons.append("NO_REDUNDANCY")

        # Blast-radius size
        impacted_count = (
            impact["affected_service_count"]
            + impact["affected_application_count"]
        )

        if impacted_count >= 4:
            score += 2
            reasons.append("WIDE_BLAST_RADIUS")

        elif impacted_count >= 1:
            score += 1
            reasons.append("DEPENDENCY_IMPACT")

        # Deep dependency chains add hidden downstream risk
        if impact["max_dependency_depth"] >= 3:
            score += 1
            reasons.append("DEEP_DEPENDENCY_CHAIN")

        if score >= 10:
            severity = "CRITICAL"
            decision = "ESCALATE"

        elif score >= 7:
            severity = "HIGH"
            decision = "ESCALATE"

        elif score >= 4:
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