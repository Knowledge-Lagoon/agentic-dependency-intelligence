from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"


class GraphRetriever:
    """
    Retrieves operational documents based on component names
    discovered from the Neo4j dependency graph.

    This MVP intentionally uses graph-derived metadata matching
    rather than embeddings or a vector database.
    """

    def __init__(self, docs_dir=DOCS_DIR):
        self.docs_dir = Path(docs_dir)

    def _parse_document(self, path):
        """
        Parse Markdown documents with simple YAML-like front matter.

        Example:

        ---
        title: PostgreSQL Recovery Runbook
        components:
          - PostgreSQL
          - Payment Service
        ---

        # PostgreSQL Recovery Runbook
        ...
        """

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
                        title = line.split(":", 1)[1].strip()
                        reading_components = False

                    elif line == "components:":
                        reading_components = True

                    elif reading_components and line.startswith("-"):
                        component = line[1:].strip()

                        if component:
                            components.append(component)

                    elif line:
                        reading_components = False

        return {
            "title": title,
            "path": str(path),
            "components": components,
            "content": body,
        }

    def load_documents(self):
        """
        Load all Markdown documents from docs/.
        """

        if not self.docs_dir.exists():
            raise FileNotFoundError(
                f"Documentation directory not found: {self.docs_dir}"
            )

        documents = []

        for path in sorted(self.docs_dir.glob("*.md")):
            documents.append(
                self._parse_document(path)
            )

        return documents

    def retrieve(self, component_names):
        """
        Retrieve documents related to components discovered
        through dependency analysis.

        Ranking:
            One point is awarded for every matching component.

        Example input:
            [
                "PostgreSQL",
                "Payment Service",
                "Order Service",
                "Customer Portal",
            ]
        """

        requested = {
            name.strip()
            for name in component_names
            if name and name.strip()
        }

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

            result["matched_components"] = sorted(
                matches
            )

            result["score"] = len(matches)

            results.append(result)

        # Highest graph match first.
        # Title provides deterministic ordering for ties.
        results.sort(
            key=lambda item: (
                -item["score"],
                item["title"].lower(),
            )
        )

        return results


def print_results(results):
    """
    Pretty-print retrieval results for CLI testing.
    """

    print()
    print("GRAPH-RAG DOCUMENT RETRIEVAL")
    print("=" * 60)

    if not results:
        print("No relevant documents found.")
        return

    for index, result in enumerate(results, start=1):

        print()
        print(
            f"{index}. {result['title']}"
        )

        print(
            "   Matched components: "
            + ", ".join(
                result["matched_components"]
            )
        )

        print(
            f"   Graph match score: "
            f"{result['score']}"
        )

        print(
            f"   Source: {result['path']}"
        )


def main():
    """
    Standalone test.

    These component names represent what our Neo4j
    blast-radius analysis discovers for PostgreSQL.

    In the next step, these values will come directly
    from ImpactAnalyzer instead of being hard-coded.
    """

    components = [
        "PostgreSQL",
        "Payment Service",
        "Order Service",
        "Customer Portal",
    ]

    retriever = GraphRetriever()

    results = retriever.retrieve(
        components
    )

    print_results(
        results
    )


if __name__ == "__main__":
    main()
