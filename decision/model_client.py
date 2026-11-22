import json
import urllib.request


JULIA_URL = "http://127.0.0.1:8080/v1/systemone"


class DecisionModelClient:

    def __init__(self, url=JULIA_URL):
        self.url = url

    def evaluate(self, impact):

        component = impact["component"]
        graph_risk = impact.get("graph_risk") or {}

        state = {
            "failed_component": component["name"],
            "component_type": component["type"],

            "component_critical":
                component.get("critical"),

            "component_customer_facing":
                component.get("customer_facing"),

            "component_redundancy":
                component.get("redundancy"),

            "production_impact":
                impact["production_impact"],

            "critical_service_impact":
                impact["critical_service_impact"],

            "customer_facing_service_impact":
                impact["customer_facing_service_impact"],

            "affected_service_count":
                impact["affected_service_count"],

            "affected_application_count":
                impact["affected_application_count"],

            "direct_impact_count":
                impact["direct_impact_count"],

            "indirect_impact_count":
                impact["indirect_impact_count"],

            "maximum_dependency_depth":
                impact["max_dependency_depth"],

            "graph_risk_level":
                graph_risk.get("level"),

            "graph_risk_score":
                graph_risk.get("score"),

            "graph_risk_reasons": [
                reason.get("description")
                for reason in graph_risk.get(
                    "reasons",
                    [],
                )
            ],

            "affected_services": [
                item["name"]
                for item in impact["affected_services"]
            ],

            "affected_applications": [
                item["name"]
                for item in impact["affected_applications"]
            ],

            "owners":
                impact["owners"],

            "environments":
                impact["environments"],
        }

        payload = {
            "state": state,

            "questions": {

                "action": {
                    "type": "choice",

                    "instructions":
                        "Choose the appropriate operational response "
                        "to the failed technology component based only "
                        "on the supplied dependency and impact evidence.",

                    "criteria": {

                        "MONITOR":
                            "Low operational risk. No significant "
                            "production, critical-service, or "
                            "customer-facing impact. Observation is "
                            "sufficient.",

                        "INVESTIGATE":
                            "Meaningful operational impact requiring "
                            "technical investigation, but the supplied "
                            "evidence does not justify an immediate "
                            "major operational escalation.",

                        "ESCALATE":
                            "Serious production impact affecting "
                            "critical or customer-facing workloads, "
                            "especially with broad downstream impact "
                            "or lack of redundancy. Immediate "
                            "operational escalation is appropriate.",
                    },
                },

                "severity": {
                    "type": "choice",

                    "instructions":
                        "Classify the operational severity of the "
                        "failure using only the supplied dependency "
                        "and impact evidence.",

                    "criteria": {

                        "LOW":
                            "Little operational impact, generally "
                            "non-production or isolated with no "
                            "important downstream dependencies.",

                        "MEDIUM":
                            "Limited operational impact. Investigation "
                            "is required, but customer-facing or "
                            "critical production impact is limited.",

                        "HIGH":
                            "Significant production impact involving "
                            "important services, applications, or "
                            "customer-facing workloads.",

                        "CRITICAL":
                            "Severe production impact involving "
                            "critical or customer-facing workloads "
                            "with broad blast radius, deep dependency "
                            "chains, or lack of redundancy.",
                    },
                },
            },
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            self.url,
            data=data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )


def print_model_decision(result):

    answers = result["answers"]

    action = answers["action"]
    severity = answers["severity"]

    print()
    print("AI DECISION MODEL")
    print("=" * 60)

    print(
        f"Action:     {action['choice']} "
        f"(confidence {action['confidence']:.1%})"
    )

    print(
        f"Severity:   {severity['choice']} "
        f"(confidence {severity['confidence']:.1%})"
    )

    print()
    print("Action probabilities:")

    for name, probability in action["probabilities"].items():
        print(
            f"  {name:<12} "
            f"{probability:.1%}"
        )

    print()
    print("Severity probabilities:")

    for name, probability in severity["probabilities"].items():
        print(
            f"  {name:<12} "
            f"{probability:.1%}"
        )