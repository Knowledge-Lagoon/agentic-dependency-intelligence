import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

IMAGE_PATH = BASE_DIR / "architecture" / "input" / "architecture.png"
OUTPUT_DIR = BASE_DIR / "architecture" / "output"
OUTPUT_PATH = OUTPUT_DIR / "extracted_graph.json"
RAW_OUTPUT_PATH = OUTPUT_DIR / "vision_raw_response.txt"

VISION_URL = "http://127.0.0.1:8081/v1/chat/completions"

ALLOWED_COMPONENT_TYPES = {
    "Application",
    "Service",
    "Database",
    "ExternalSystem",
}

ALLOWED_RELATIONSHIP_TYPES = {
    "USES",
    "DEPENDS_ON",
    "CONNECTS_TO",
}

PROMPT = """
Analyze the supplied software architecture diagram.

Extract only architecture components and connections that are clearly visible in the diagram.

Allowed component types:
- Application
- Service
- Database
- ExternalSystem

Allowed relationship types:
- USES
- DEPENDS_ON
- CONNECTS_TO

Return JSON only in this shape:
{
  "components": [
    {"name": "component name", "type": "Application"}
  ],
  "relationships": [
    {"source": "component name", "target": "component name", "type": "USES"}
  ]
}

Rules:
1. Only include components that are clearly visible in the architecture diagram.
2. Do not treat legend entries or labels as components.
3. Do not invent components not present in the diagram.
4. Use exact component names as they appear in the diagram when possible.
5. Names are case-sensitive and must match exactly across sources and targets.
6. Return valid JSON, no markdown fences, no commentary.
"""


def encode_image(image_path):
    with image_path.open("rb") as file:
        image_bytes = file.read()

    return base64.b64encode(image_bytes).decode("utf-8")


def build_payload(image_base64):
    return {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 1200,
    }


def call_vision_model(image_base64):
    payload = build_payload(image_base64)
    request = urllib.request.Request(
        VISION_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=1600) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Vision server returned HTTP {exc.code}: {error_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not connect to vision server at {VISION_URL}: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError("Vision model request timed out.") from exc


def extract_content(response):
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(
            "Unexpected response format from the vision model."
        ) from exc


def save_raw_response(content):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT_PATH.write_text(content, encoding="utf-8")


def clean_json_text(text):
    text = str(text).strip()

    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return match.group(0).strip()

    return text.strip()


def validate_structure(graph):
    if not isinstance(graph, dict):
        raise ValueError("Extracted graph must be a JSON object.")

    components = graph.get("components")
    relationships = graph.get("relationships")

    if not isinstance(components, list):
        raise ValueError("'components' must be a list.")

    if not isinstance(relationships, list):
        raise ValueError("'relationships' must be a list.")


def validate_components(graph):
    seen_components = set()

    for component in graph["components"]:
        if not isinstance(component, dict):
            raise ValueError("Each component must be a JSON object.")

        name = component.get("name")
        component_type = component.get("type")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("A component is missing its name.")

        if component_type not in ALLOWED_COMPONENT_TYPES:
            raise ValueError(
                f"Unsupported component type '{component_type}' for '{name}'"
            )

        normalized_name = name.strip().lower()
        if normalized_name in seen_components:
            raise ValueError(f"Duplicate component: {name}")

        seen_components.add(normalized_name)


def validate_relationships(graph):
    component_names = {component["name"].strip() for component in graph["components"]}
    seen_relationships = set()

    for relationship in graph["relationships"]:
        if not isinstance(relationship, dict):
            raise ValueError("Each relationship must be a JSON object.")

        source = relationship.get("source")
        target = relationship.get("target")
        relationship_type = relationship.get("type")

        if not source:
            raise ValueError("A relationship is missing its source.")

        if not target:
            raise ValueError("A relationship is missing its target.")

        if relationship_type not in ALLOWED_RELATIONSHIP_TYPES:
            raise ValueError(
                f"Unsupported relationship type: {relationship_type}"
            )

        if source not in component_names:
            raise ValueError(f"Unknown relationship source: {source}")

        if target not in component_names:
            raise ValueError(f"Unknown relationship target: {target}")

        if source == target:
            raise ValueError(f"Self relationship detected: {source}")

        relationship_key = (source, target, relationship_type)
        if relationship_key in seen_relationships:
            raise ValueError(
                f"Duplicate relationship: {source} -> {target} ({relationship_type})"
            )

        seen_relationships.add(relationship_key)


def save_graph(graph):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(graph, file, indent=2)


def main():
    print()
    print("ARCHITECTURE DIAGRAM EXTRACTION")
    print("=" * 60)

    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Architecture image not found: {IMAGE_PATH}")

    print(f"Input: {IMAGE_PATH}")

    print()
    print("Encoding architecture diagram...")

    image_base64 = encode_image(IMAGE_PATH)

    print("Sending diagram to vision model...")

    response = call_vision_model(image_base64)
    content = extract_content(response)

    save_raw_response(content)

    print()
    print("Raw response saved to:")
    print(RAW_OUTPUT_PATH)

    cleaned_content = clean_json_text(content)

    try:
        graph = json.loads(cleaned_content)
    except json.JSONDecodeError as exc:
        print()
        print("ERROR: Vision model did not return valid JSON.")

        print()
        print("Raw model output is available at:")
        print(RAW_OUTPUT_PATH)

        raise RuntimeError(
            "Architecture graph extraction failed because the model response was not valid JSON."
        ) from exc

    validate_structure(graph)
    validate_components(graph)
    validate_relationships(graph)

    save_graph(graph)

    print()
    print("Extraction completed successfully.")

    print()
    print(f"Components: {len(graph['components'])}")
    print(f"Relationships: {len(graph['relationships'])}")

    print()
    print("Extracted graph saved to:")
    print(OUTPUT_PATH)

    print()
    print("Review the extracted graph before loading it into Neo4j.")


if __name__ == "__main__":
    main()
