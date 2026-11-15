import base64
import json
import re
import urllib.error
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

IMAGE_PATH = (
    BASE_DIR
    / "architecture"
    / "input"
    / "architecture.png"
)

OUTPUT_DIR = (
    BASE_DIR
    / "architecture"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "extracted_graph.json"
)

RAW_OUTPUT_PATH = (
    OUTPUT_DIR
    / "vision_raw_response.txt"
)

VISION_URL = (
    "http://127.0.0.1:8081/v1/chat/completions"
)


ALLOWED_COMPONENT_TYPES = [
    "Application",
    "Service",
    "Database",
    "ExternalSystem",
]

ALLOWED_RELATIONSHIP_TYPES = [
    "USES",
    "DEPENDS_ON",
    "CONNECTS_TO",
]


PROMPT = """
Analyze the supplied software architecture diagram.

Extract the architecture as structured graph data.

IMPORTANT:

- Extract only components visibly present in the diagram.
- Do not invent components.
- Do not describe what components might do.
- Do not produce architecture explanations.
- Do not treat legend labels as components.
- Do not duplicate components.
- Ignore decorative icons.
- Ignore section headings unless they represent real components.
- Follow visible arrow directions carefully.
- Do not infer a connection merely because two components
  are visually close.
- If a connection is unclear, omit it.

Allowed component types:

Application
Service
Database
ExternalSystem

Allowed relationship types:

USES
DEPENDS_ON
CONNECTS_TO

Return ONLY structured JSON.

Required structure:

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

Do not return Markdown.

Do not return explanations.

Do not number components.

Do not include text before or after the JSON.
"""


def encode_image(path):
    """
    Read architecture image and convert it to base64
    for the llama.cpp multimodal API.
    """

    with path.open("rb") as file:
        image_bytes = file.read()

    return base64.b64encode(
        image_bytes
    ).decode("utf-8")


def build_payload(image_base64):
    """
    Build the multimodal request sent to SmolVLM2.
    """

    return {
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

        # Keep extraction deterministic where the model/runtime
        # supports this behaviour.
        "temperature": 0,

        # Architecture graph JSON should be significantly smaller
        # than a general prose response.
        "max_tokens": 1200,
    }


def call_vision_model(image_base64):
    """
    Send architecture diagram to the local SmolVLM2
    llama.cpp server.
    """

    payload = build_payload(
        image_base64
    )

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

    try:
        with urllib.request.urlopen(
            request,

            # CPU-only vision inference on our 2-vCPU server
            # can take several minutes.
            timeout=600,

        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            return json.loads(
                body
            )

    except urllib.error.HTTPError as exc:

        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"Vision server returned HTTP "
            f"{exc.code}: {error_body}"
        ) from exc

    except urllib.error.URLError as exc:

        raise RuntimeError(
            "Unable to connect to vision server "
            f"at {VISION_URL}: {exc}"
        ) from exc


def extract_content(response):
    """
    Extract assistant response text from llama.cpp's
    OpenAI-compatible chat-completions response.
    """

    try:
        return (
            response["choices"][0]
            ["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:

        raise ValueError(
            "Unexpected response structure from "
            "vision model."
        ) from exc


def save_raw_response(content):
    """
    Always preserve the raw vision output.

    This is especially important when JSON parsing fails,
    because vision inference is comparatively expensive.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    RAW_OUTPUT_PATH.write_text(
        content,
        encoding="utf-8",
    )


def clean_json_text(text):
    """
    Clean common Markdown wrappers from model output.

    This does NOT attempt to convert arbitrary prose into JSON.
    If the model returns prose, validation should fail.
    """

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
     *  flags=re.IGNORECASE,
    )

    *ext = re.sub(
        r"^```\s*",
*       "",
        text,
    )

  * text = re.sub(
        r"\s*```$"*
        "",
        text,
    )

*   return text.strip()


def valid*te_basic_structure(graph):
    """*    Perform basic structural valid*tion before writing
    extracted *raph data.
    """

    if not isi*stance(
        graph,
        dic*,
    ):
        raise ValueError(*            "Extracted result is n*t a JSON object."
        )

    i* "components" not in graph:
      * raise ValueError(
            "Ex*racted graph is missing "
        *   "'components'."
        )

    *f "relationships" not in graph:
  *     raise ValueError(
           *"Extracted graph is missing "
    *       "'relationships'."
        *

    if not isinstance(
        g*aph["components"],
        list,
 *  ):
        raise ValueError(
   *        "'components' must be a li*t."
        )

    if not isinstan*e(
        graph["relationships"],*        list,
    ):
        raise*ValueError(
            "'relation*hips' must be a list."
        )

*def validate_components(graph):
  * """
    Validate component struct*re and allowed types.
    """

   *seen_names = set()

    for compon*nt in graph["components"]:

      * if not isinstance(
            co*ponent,
            dict,
        *:
            raise ValueError(
  *             "Every component must*be "
                "a JSON objec*."
            )

        name = c*mponent.get(
            "name"
  *     )

        component_type = c*mponent.get(
            "type"
  *     )

        if not name:
     *      raise ValueError(
          *     "Component missing name."
   *        )

        if component_ty*e not in (
            ALLOWED_COM*ONENT_TYPES
        ):
           *raise ValueError(
                *"Unsupported component type "
    *           f"'{component_type}' fo* '{name}'."
            )

       *normalized_name = (
            na*e.strip().lower()
        )

     *  if normalized_name in seen_names*
            raise ValueError(
   *            f"Duplicate component:*{name}"
            )

        see*_names.add(
            normalized*name
        )


def validate_rela*ionships(graph):
    """
    Valid*te relationship structure.

    Bo*h source and target must correspon* to components
    extracted from *he diagram.
    """

    component*names = {
        component["name"]
        for component
        in *raph["components"]
    }

    seen*relationships = set()

    for rel*tionship in graph[
        "relationships"
    ]:

        if not isi*stance(
            relationship,
*           dict,
        ):
      *     raise ValueError(
           *    "Every relationship must be "
*               "a JSON object."
  *         )

        source = relat*onship.get(
            "source"
 *      )

        target = relation*hip.get(
            "target"
    *   )

        relationship_type = *
            relationship.get("typ*")
        )

        if not sourc*:
            raise ValueError(
                "Relationship missing source."
            )

        if not target:
            raise ValueError(
                "Relationship missing target."
            )

        if relationship_type not in (
            ALLOWED_RELATIONSHIP_TYPES
        ):
            raise ValueError(
                f"Unsupported relationship type: "
                f"{relationship_type}"
            )

        if source not in component_names:
            raise ValueError(
                f"Relationship source '{source}' "
                "does not exist in components."
            )

        if target not in component_names:
            raise ValueError(
                f"Relationship target '{target}' "
                "does not exist in components."
            )

        if source == target:
            raise ValueError(
                f"Self-relationship detected: "
                f"{source}"
            )

        relationship_key = (
            source,
            target,
            relationship_type,
        )

        if relationship_key in (
            seen_relationships
        ):
            raise ValueError(
                "Duplicate relationship: "
                f"{source} -> {target} "
                f"({relationship_type})"
            )

        seen_relationships.add(
            relationship_key
        )


def save_graph(graph):
    """
    Save validated extracted graph.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
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


def main():

    print()
    print(
        "ARCHITECTURE DIAGRAM EXTRACTION"
    )
    print("=" * 60)

    if not IMAGE_PATH.exists():

        raise FileNotFoundError(
            "Architecture image not found: "
            f"{IMAGE_PATH}"
        )

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

    save_raw_response(
        content
    )

    print()
    print(
        "Raw vision response saved to:"
    )

    print(
        RAW_OUTPUT_PATH
    )

    cleaned = clean_json_text(
        content
    )

    try:

        graph = json.loads(
            cleaned
        )

    except json.JSONDecodeError as exc:

        print()
        print(
            "ERROR: Vision model did not "
            "return valid JSON."
        )

        print()
        print(
            "The raw response has been "
            "preserved at:"
        )

        print(
            RAW_OUTPUT_PATH
        )

        print()
        print(
            "First 500 characters of "
            "raw response:"
        )

        print()
        print(
            content[:500]
        )

        raise RuntimeError(
            "Architecture extraction failed "
            "because the model response was "
            "not valid JSON."
        ) from exc

    validate_basic_structure(
        graph
    )

    validate_components(
        graph
    )

    validate_relationships(
        graph
    )

    save_graph(
        graph
    )

    print()
    print(
        "Extraction complete."
    )

    print()
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
        "Extracted graph saved to:"
    )

    print(
        OUTPUT_PATH
    )

    print()
    print(
        "IMPORTANT: Review the extracted "
        "graph before loading it into Neo4j."
    )


if __name__ == "__main__":
    main()