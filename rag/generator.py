import json
import urllib.error
import urllib.request


GENERATOR_URL = "http://127.0.0.1:8082/v1/chat/completions"


SYSTEM_PROMPT = """
You are the response-generation layer for an operational
dependency intelligence system.

Use only the supplied graph evidence and operational
documentation.

Rules:

1. Do not invent dependencies.
2. Do not invent affected systems.
3. Do not invent owners or environments.
4. Recommendations must come from the supplied documentation.
5. Clearly distinguish direct and indirect impact.
6. If information is unavailable, say that it is unavailable.
7. Keep the response concise and operational.
8. The failed component has status FAILED and distance 0.
9. Components listed under direct or indirect impact are AFFECTED.
10. Never describe an impacted component as Unaffected.
11. UNKNOWN metadata means unavailable, not False.
12. Do not repeat guidance, bullets, sentences, or recommendations.
13. Include each distinct operational recommendation only once.
14. Graph-derived risk and declared criticality are separate concepts.
"""


class GroundedGenerator:

    def __init__(self, url=GENERATOR_URL):
        self.url = url

    def generate(
        self,
        question,
        context_text,
        decision=None,
    ):
        decision_text = ""

        if decision:
            decision_text = (
                "\n\nDECISION MODEL RESULT\n"
                f"Severity: {decision.get('severity')}\n"
                f"Action: {decision.get('action')}\n"
                f"Confidence: {decision.get('confidence')}"
            )

        user_prompt = f"""
USER QUESTION

{question}

GROUNDED CONTEXT

{context_text}

{decision_text}

Using only this information, provide:

1. Relevant operational guidance
2. Recommended action

Do not reproduce the impact summary, failed component,
direct impact, or indirect impact. Those sections are rendered
deterministically from Neo4j by the application.

Status rules:
- The failed component is FAILED at distance 0.
- Direct and indirect dependencies are AFFECTED.
- Never label an impacted component Unaffected.
- Use UNKNOWN when metadata is unavailable.
- Include each operational recommendation only once.
- Do not repeat equivalent guidance in different wording.

Do not introduce facts not present in the supplied context.
"""

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "temperature": 0,
            "max_tokens": 700,
        }

        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=180,
            ) as response:

                body = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.HTTPError as exc:
            error = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"Generator returned HTTP "
                f"{exc.code}: {error}"
            ) from exc

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Could not connect to generation model "
                f"at {self.url}: {exc}"
            ) from exc

        try:
            return (
                body["choices"][0]
                ["message"]["content"]
                .strip()
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:
            raise RuntimeError(
                "Unexpected response from generation model."
            ) from exc