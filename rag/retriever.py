from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"


class GraphRetriever:
    """
    Retrieve operational documents using component names
    discovered dynamically from the Neo4j dependency graph.

    Component names are supplied by ContextBuilder from
    ImpactAnalyzer results.

    This retriever contains no hard-coded dependency
    relationships or component lists.
    """

    def __init__(self, docs_dir=DOCS_DIR):
        self.docs_dir = Path(docs_dir)

    def _parse_document(self, path):

        text = path.read_text(encoding="utf-8")

        title = path.stem
        components = []
        body = text

        if text.startswith("---"):
            parts = text.split("---", 2)

            if len(parts) == 3:
                metadata = parts[1]
                body = parts[2].strip()

                reading_components = False

                for line in metadata.splitlines():
                    line = line.strip()

                    if line.startswith("title:"):
                        title = line.split(
                            ":",
                            1,
                        )[1].strip()

                        reading_components = False

                    elif line == "components:":
                        reading_components = True

                    elif (
                        reading_components
                        and line.startswith("-")
                    ):
                        component = line[1:].strip()

                        if component:
                            components.append(
                                component
                            )

                    elif line:
                        reading_components = False

        return {
            "title": title,
            "path": str(path),
            "components": components,
            "content": body,
        }

    def load_documents(self):

        if not self.docs_dir.exists():
            raise FileNotFoundError(
                "Documentation directory not found: "
                f"{self.docs_dir}"
            )

        documents = []

        for path in sorted(
            self.docs_dir.glob("*.md")
        ):
            documents.append(
                self._parse_document(path)
            )

        return documents

    def retrieve(self, component_names):

        requested = {
            name.strip()
            for name in component_names
            if name and name.strip()
        }

        if not requested:
            return []

        results = []

        for document in self.load_documents():

            document_components = set(
                document["components"]
            )

            matches = requested.intersection(
                document_components
            )

            if not matches:
                continue

            result = dict(document)

            result[
                "matched_components"
            ] = sorted(matches)

            result["score"] = len(
                matches
            )

            results.append(result)

        results.sort(
            key=lambda item: (
                -item["score"],
                item["title"].lower(),
            )
        )

        return results


def print_results(results):

    print()
    print(
        "GRAPH-RAG DOCUMENT RETRIEVAL"
    )
    print("=" * 60)

    if not results:
        print(
            "No relevant documents found."
        )
        return

    for index, result in enumerate(
        results,
        start=1,
    ):
        print()

        print(
            f"{index}. "
            f"{result['title']}"
        )

        print(
            "   Matched components: "
            + ", ".join(
                result["matched_components"]
            )
        )

        print(
            "   Graph match score: "
            f"{result['score']}"
        )

        print(
            "   Source: "
            f"{result['path']}"
        )
