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

        # Topology-derived risk remains useful when architecture
        # metadata such as criticality or environment is UNKNOWN.
        graph_risk = impact.get("graph_risk") or {}
        graph_risk_level = graph_risk.get("level")

        if graph_risk_level == "CRITICAL":
            score += 4
            reasons.append("CRITICAL_GRAPH_RISK")
        elif graph_risk_level == "HIGH":
            score += 3
            reasons.append("HIGH_GRAPH_RISK")
        elif graph_risk_level == "MEDIUM":
            score += 2
            reasons.append("MEDIUM_GRAPH_RISK")

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