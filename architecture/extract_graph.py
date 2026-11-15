import base64
import json
import re
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

IMAGE_PATH = (
    BASE_DIR
    / "architecture"
    / "input"
    / "architecture.png"
)

OUTPUT_PATH = (
    BASE_DIR
    / "architecture"
    / "output"
    / "extracted_graph.json"
)

VISION_URL = (
    "http://127.0.0.1:8081/v1/chat/completions"
)


PROMPT = """
Analyze this software architecture diagram carefully.

Your task is to extract ONLY information visibly present
in the diagram.

Identify components using these types only:

Application
Service
Database
ExternalSystem
Environment
Team

Identify directed relationships shown by arrows or explicit
connections.

Use these relationship types only:

USES
DEPENDS_ON
CONNECTS_TO
OWNED_BY
RUNS_IN

Important rules:

1. Do not invent components.
2. Do not invent relationships.
3. Follow arrow direction carefully.
4. Use the component labels exactly as shown.
5. Ignore decorative icons.
6. Do not infer a dependency merely because two boxes
   are visually close.
7. If an arrow direction is unclear, omit the relationship.
8. Return JSON only.
9. Do not include markdown fences.
10. Do not include explanations outside the JSON.

Return exactly this structure:

{
  "components": [
    {
      "name": "component name",
      "type": "Application"
    }
  ],
  "relationships": [
    {
      "source": "source component",
      "target": "target component",
      "type": "USES"
    }
  ]
}
"""


def encode_image(path):
    with path.open("rb") as file:
        encoded = base64.b64encode(
            file.read()
        ).decode("utf-8")

    return encoded


def call_vision_model(image_base64):
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                "data:image/png;base64,"
                                + image_base64
                            )
                        },
                    },
                ],
            }
        ],
        "temperature": 0,
        "max_tokens": 2000,
    }

    data = json.dumps(
        payload
    ).encode("utf-8")

    request = urllib.request.Request(
        VISION_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=600,
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def extract_content(response):
    return (
        response["choices"][0]["message"]["content"]
    )


def clean_json_text(text):
    """
    Remove markdown fences if the model ignores the prompt
    and returns ```json ... ```.
    """

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    return text.strip()


def validate_basic_structure(graph):
    if not isinstance(graph, dict):
        raise ValueError(
            "Extracted result is not a JSON object"
        )

    if "components" not in graph:
        raise ValueError(
            "Missing 'components'"
        )

    if "relationships" not in graph:
        raise ValueError(
            "Missing 'relationships'"
        )

    if not isinstance(
        graph["components"],
        list,
    ):
        raise ValueError(
            "'components' must be a list"
        )

    if not isinstance(
        graph["relationships"],
        list,
    ):
        raise ValueError(
            "'relationships' must be a list"
        )


def main():
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"Architecture image not found: "
            f"{IMAGE_PATH}"
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("ARCHITECTURE DIAGRAM EXTRACTION")
    print("=" * 60)

    print(
        f"Input: {IMAGE_PATH}"
    )

    print()
    print(
        "Encoding architecture diagram..."
    )

    image_base64 = encode_image(
        IMAGE_PATH
    )

    print(
        "Sending diagram to vision model..."
    )

    response = call_vision_model(
        image_base64
    )

    content = extract_content(
        response
    )

    raw_output_path = (
    `BASE_DIR
    / "architecture"
    / "output"
    / "vision_raw_response.txt"
)

raw_output_path.write_text(
    content,
    encoding="utf-8",
)

print(
    f"Raw vision response saved to: "
    f"{raw_output_path}"
)

    cleaned = clean_json_text(
        content
    )

    try:
        graph = json.loads(
            cleaned
        )

    except json.JSONDecodeError:
        print()
        print(
            "ERROR: Vision model did not return "
            "valid JSON."
        )

        print()
        print("Raw response:")
        print(cleaned)

        raise

    validate_basic_structure(
        graph
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            graph,
            file,
            indent=2,
        )

    print()
    print(
        "Extraction complete."
    )

    print(
        f"Components:    "
        f"{len(graph['components'])}"
    )

    print(
        f"Relationships: "
        f"{len(graph['relationships'])}"
    )

    print()
    print(
        f"Output: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
