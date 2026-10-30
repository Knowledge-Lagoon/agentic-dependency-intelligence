import json
import urllib.request


JULIA_URL = "http://127.0.0.1:8080/v1/systemone"


class DecisionModelClient:

    def __init__(self, url=JULIA_URL):
        self.url = url

    def evaluate(self, impact):
        state = {
            "component": impact["component"]["name"],
            "component_type": impact["component"]["type"],
            "production": impact["production"],
            "critical": impact["critical"],
            "customer_facing": impact["customer_facing"],
            "redundancy": impact["redundancy"],
            "affected_components": (
                len(impact["direct_impact"])
                + len(impact["indirect_impact"])
            ),
            "direct_impact": [
                item["name"]
                for item in impact["direct_impact"]
            ],
            "indirect_impact": [
                item["name"]
                for item in impact["indirect_impact"]
            ],
            "owners": impact["owners"],
            "environments": impact["environments"],
        }

        payload = {
            "state": state,
            "questions": {
                "action": {
                    "type": "choice",
                    "instructions":
                        "Choose the appropriate operational response.",
                    "criteria": {
                        "MONITOR":
                            "Observe without immediate intervention",
                        "INVESTIGATE":
                            "Investigate and assess the incident",
                        "ESCALATE":
                            "Start an urgent operational response",
                    },
                },
                "severity": {
                    "type": "choice",
                    "instructions":
                        "Classify the operational severity.",
                    "criteria": {
                        "LOW":
                            "Little or no operational impact",
                        "MEDIUM":
                            "Limited operational impact",
                        "HIGH":
                            "Significant production or customer impact",
                        "CRITICAL":
                            "Severe production and customer impact "
                            "requiring urgent response",
                    },
                },
            },
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            return json.loads(response.read().decode("utf-8"))


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
        print(f"  {name:<12} {probability:.1%}")

    print()
    print("Severity probabilities:")

    for name, probability in severity["probabilities"].items():
        print(f"  {name:<12} {probability:.1%}")