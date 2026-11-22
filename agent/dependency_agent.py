import argparse
import re
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from analysis.impact_analyzer import ImpactAnalyzer
from decision.decision_engine import DecisionEngine
from decision.model_client import DecisionModelClient
from rag.context_builder import ContextBuilder, build_agent_context
from rag.generator import GroundedGenerator


def parse_args():
    parser = argparse.ArgumentParser(
        description="Agentic Dependency Intelligence"
    )

    parser.add_argument(
        "question",
        help="Natural-language dependency question",
    )

    parser.add_argument(
        "--source",
        default=None,
        help="Graph source such as architecture_diagram",
    )

    return parser.parse_args()


class DependencyAgent:

    def __init__(self):
        self.analyzer = ImpactAnalyzer()
        self.policy_engine = DecisionEngine()
        self.decision_model = DecisionModelClient()
        self.context_builder = ContextBuilder()
        self.generator = GroundedGenerator()

    def close(self):
        self.analyzer.close()

    def get_component_names(self, source=None):
        query = """
        MATCH (n)
        WHERE n.name IS NOT NULL
          AND ($source IS NULL OR n.source = $source)
        RETURN DISTINCT n.name AS name
        ORDER BY size(n.name) DESC
        """

        with self.analyzer.driver.session() as session:
            result = session.run(
                query,
                source=source,
            )

            return [
                record["name"]
                for record in result
                if record["name"]
            ]

    def identify_component(self, question, source=None):
        names = self.get_component_names(
            source=source
        )

        question_lower = question.lower()

        for name in names:
            pattern = (
                r"\b"
                + re.escape(name.lower())
                + r"\b"
            )

            if re.search(pattern, question_lower):
                return name

        return None

    def build_decision_summary(
        self,
        policy_decision,
        ai_result,
    ):
        if ai_result:
            answers = ai_result.get(
                "answers",
                {},
            )

            action = answers.get(
                "action",
                {},
            )

            severity = answers.get(
                "severity",
                {},
            )

            return {
                "severity": severity.get("choice"),
                "action": action.get("choice"),
                "confidence": action.get("confidence"),
            }

        return {
            "severity": policy_decision["severity"],
            "action": policy_decision["decision"],
            "confidence": None,
        }

    def analyze(self, question, source=None):
        component_name = self.identify_component(
            question,
            source=source,
        )

        if not component_name:
            return {
                "success": False,
                "message": (
                    "Could not identify a known component "
                    "from the question."
                ),
            }

        impact = self.analyzer.analyze(
            component_name,
            source=source,
        )

        if not impact:
            return {
                "success": False,
                "message": (
                    f"No dependency information found for "
                    f"'{component_name}'."
                ),
            }

        rag_context = self.context_builder.build(
            impact
        )

        context_text = build_agent_context(
            rag_context
        )

        # print()
        # print("=" * 60)
        # print("EXACT CONTEXT SENT TO QWEN")
        # print("=" * 60)
        # print(context_text)
        # print("=" * 60)
        # print()

        policy_decision = self.policy_engine.evaluate(
            impact
        )

        ai_result = None
        decision_warning = None

        try:
            ai_result = self.decision_model.evaluate(
                impact
            )

        except Exception as exc:
            decision_warning = str(exc)

        decision_summary = self.build_decision_summary(
            policy_decision,
            ai_result,
        )

        generation_warning = None

        try:
            answer = self.generator.generate(
                question=question,
                context_text=context_text,
                decision=decision_summary,
            )

        except Exception as exc:
            generation_warning = str(exc)

            answer = self.fallback_answer(
                impact,
                rag_context,
                decision_summary,
            )

        return {
            "success": True,
            "component": component_name,
            "source": source,
            "impact": impact,
            "rag_context": rag_context,
            "policy_decision": policy_decision,
            "decision_summary": decision_summary,
            "answer": answer,
            "decision_warning": decision_warning,
            "generation_warning": generation_warning,
        }

    def fallback_answer(
        self,
        impact,
        rag_context,
        decision,
    ):
        lines = []

        lines.append(
            f"Component: "
            f"{impact['component']['name']}"
        )

        lines.append("")
        lines.append("Direct impact:")

        if impact["direct_impact"]:
            for item in impact["direct_impact"]:
                lines.append(
                    f"- {item['name']} "
                    f"[{item['type']}]"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append("Indirect impact:")

        if impact["indirect_impact"]:
            for item in sorted(
                impact["indirect_impact"],
                key=lambda item: (
                    item["distance"],
                    item["name"],
                ),
            ):
                lines.append(
                    f"- Level {item['distance']}: "
                    f"{item['name']} "
                    f"[{item['type']}]"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append("Relevant documents:")

        documents = rag_context["documents"]

        if documents:
            for document in documents:
                lines.append(
                    f"- {document['title']}"
                )
        else:
            lines.append("- None")

        lines.append("")
        lines.append(
            f"Severity: {decision.get('severity')}"
        )

        lines.append(
            f"Recommended action: "
            f"{decision.get('action')}"
        )

        return "\n".join(lines)


def print_result(result):
    print()
    print("=" * 60)
    print("AGENTIC DEPENDENCY INTELLIGENCE")
    print("=" * 60)

    if not result["success"]:
        print()
        print(result["message"])
        return

    print()
    print(
        f"Component: {result['component']}"
    )

    print(
        "Graph source: "
        f"{result['source'] or 'default'}"
    )

    if result["decision_warning"]:
        print()
        print(
            "Decision model warning: "
            f"{result['decision_warning']}"
        )

    if result["generation_warning"]:
        print()
        print(
            "Generation model warning: "
            f"{result['generation_warning']}"
        )

    print()
    print("GROUNDED ANSWER")
    print("-" * 60)
    print()

    print(result["answer"])

    decision = result["decision_summary"]

    print()
    print("-" * 60)

    print(
        f"Decision: "
        f"{decision.get('action')}"
    )

    print(
        f"Severity: "
        f"{decision.get('severity')}"
    )

    confidence = decision.get(
        "confidence"
    )

    if confidence is not None:
        print(
            f"Decision confidence: "
            f"{confidence:.1%}"
        )

    print()
    print("Grounding documents:")

    documents = result[
        "rag_context"
    ]["documents"]

    if documents:
        for document in documents:
            print(
                f"  - {document['title']}"
            )
    else:
        print("  None")

    print()
    print("=" * 60)


def main():
    args = parse_args()

    agent = DependencyAgent()

    try:
        result = agent.analyze(
            question=args.question,
            source=args.source,
        )

        print_result(result)

    finally:
        agent.close()


if __name__ == "__main__":
    main()