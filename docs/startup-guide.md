# Startup Guide

This guide explains how to restart the Agentic Dependency Intelligence MVP after the RHEL lab server has been stopped or restarted.

## Runtime Components

The MVP uses four local services:

| Service | Port | Purpose |
|---|---:|---|
| Neo4j | 7474 and 7687 | Dependency graph |
| Julia-1 | 8080 | Decision scoring |
| SmolVLM2 | 8081 | Architecture-diagram extraction |
| Qwen 0.8B | 8082 | Grounded text generation |

SmolVLM2 is required only when processing an architecture diagram. It does not need to run during normal dependency analysis.

## 1. Start Neo4j

Check all Podman containers:

    podman ps -a

Start the Neo4j container:

    podman start neo4j-adi

Verify the container:

    podman ps --filter name=neo4j-adi

Check its port mappings:

    podman port neo4j-adi

Expected ports include:

    7474
    7687

Test the Neo4j HTTP endpoint:

    curl -I http://127.0.0.1:7474

## 2. Activate the Python Environment

Move to the repository:

    cd ~/agentic-dependency-intelligence

Activate the virtual environment:

    source .venv/bin/activate

Verify the active Python interpreter:

    which python

Expected path:

    /home/cloud_user/agentic-dependency-intelligence/.venv/bin/python

Verify the Neo4j Python driver:

    python -c "import neo4j; print(neo4j.__version__)"

If the Neo4j driver is missing:

    python -m pip install neo4j

## 3. Configure Neo4j Environment Variables

Set the Neo4j connection values in every new SSH session:

    export NEO4J_URI='bolt://localhost:7687'
    export NEO4J_USERNAME='neo4j'
    export NEO4J_PASSWORD='YOUR-NEO4J-PASSWORD'

Do not commit the password to Git.

Verify that the variables exist without displaying the password:

    echo "$NEO4J_URI"
    echo "$NEO4J_USERNAME"
    test -n "$NEO4J_PASSWORD" && echo "Neo4j password is set"

## 4. Verify the Neo4j Connection

Run:

    python - <<'PY'
    import os
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(
            os.environ["NEO4J_USERNAME"],
            os.environ["NEO4J_PASSWORD"],
        ),
    )

    try:
        driver.verify_connectivity()

        with driver.session() as session:
            record = session.run(
                "MATCH (n) RETURN count(n) AS count"
            ).single()

        print("SUCCESS: Connected to Neo4j")
        print("Total nodes:", record["count"])

    finally:
        driver.close()
    PY

## 5. Start Julia-1

Julia-1 provides probabilistic decision scoring.

Open a dedicated SSH session and run:

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -m ~/models/Julia-1-Q8_0.gguf \
      --host 127.0.0.1 \
      --port 8080

Leave that terminal running.

From another SSH session, verify:

    curl -s http://127.0.0.1:8080/health

Expected result:

    {"status":"ok"}

## 6. Start Qwen

Qwen generates grounded operational guidance using Neo4j evidence and retrieved documentation.

Open another dedicated SSH session and run:

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -hf gguf/Qwen3.5-0.8B-GGUF:Q4_K_M \
      --host 127.0.0.1 \
      --port 8082 \
      -c 4096 \
      --reasoning off

Leave that terminal running.

Verify:

    curl -s http://127.0.0.1:8082/health

Expected result:

    {"status":"ok"}

Reasoning is disabled because Qwen is used to summarize evidence already established by Neo4j, GraphRetriever, ContextBuilder, and Julia-1.

Test Qwen directly:

    curl -s http://127.0.0.1:8082/v1/chat/completions \
      -H 'Content-Type: application/json' \
      -d '{
        "messages": [
          {
            "role": "user",
            "content": "Reply with exactly: GENERATION MODEL OK"
          }
        ],
        "temperature": 0,
        "max_tokens": 50
      }'

The response content should contain:

    GENERATION MODEL OK

## 7. Start SmolVLM2 When Required

SmolVLM2 is needed only for architecture-diagram extraction.

Because the lab server has limited CPU and memory, stop SmolVLM2 after architecture extraction is complete.

Open a dedicated SSH session and run:

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -m ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf \
      --mmproj ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-mmproj-f16.gguf \
      --no-jinja \
      --host 127.0.0.1 \
      --port 8081 \
      -c 4096

Leave that terminal running.

Verify:

    curl -s http://127.0.0.1:8081/health

Expected result:

    {"status":"ok"}

## 8. Verify All Runtime Services

Run:

    podman ps --filter name=neo4j-adi

Then:

    curl -s http://127.0.0.1:8080/health
    curl -s http://127.0.0.1:8082/health

When architecture extraction is required, also run:

    curl -s http://127.0.0.1:8081/health

## 9. Run Standard Dependency Analysis

Activate the project environment:

    cd ~/agentic-dependency-intelligence
    source .venv/bin/activate

Run against the default graph:

    python run_analysis.py PostgreSQL

## 10. Run Architecture-Specific Analysis

Run against only the architecture-derived graph:

    python run_analysis.py PostgreSQL \
      --source architecture_diagram

This prevents similarly named components in the original CSV graph from being used.

## 11. Run the Dependency Agent

Run:

    python agent/dependency_agent.py \
      "What happens if PostgreSQL goes down?" \
      --source architecture_diagram

Another example:

    python agent/dependency_agent.py \
      "What happens if User Database goes down?" \
      --source architecture_diagram

The Agent performs:

    natural-language question
        ->
    component identification
        ->
    Neo4j dependency traversal
        ->
    direct and indirect impact
        ->
    Graph Risk
        ->
    graph-guided document retrieval
        ->
    Julia-1 decision scoring
        ->
    Qwen operational guidance

## 12. Run Architecture Extraction

Make sure SmolVLM2 is running on port 8081.

Then:

    cd ~/agentic-dependency-intelligence
    source .venv/bin/activate

    python architecture/extract_graph.py

The raw model response is saved to:

    architecture/output/vision_raw_response.txt

The model output must be reviewed before Neo4j import.

## 13. Load the Approved Architecture Graph

Only the reviewed file below should be loaded:

    architecture/output/approved_graph.json

Load it using:

    python architecture/load_graph.py

Expected result:

    IMPORT COMPLETE

    Imported nodes: 13
    Imported relationships: 10

    Graph source: architecture_diagram

## 14. Access Neo4j Browser from a Mac

Make sure Neo4j is running on the RHEL server.

From a Mac terminal:

    ssh -N \
      -L 7474:127.0.0.1:7474 \
      -L 7687:127.0.0.1:7687 \
      cloud_user@54.206.42.48

Leave the SSH tunnel open.

Open in the Mac browser:

    http://localhost:7474

Use:

    URI: bolt://localhost:7687
    Username: neo4j
    Password: configured Neo4j password

## 15. Display Both Neo4j Graph Sources

Count nodes by source:

    MATCH (n)
    RETURN
      coalesce(n.source, 'csv_original') AS graph_source,
      count(n) AS nodes
    ORDER BY graph_source

Show the architecture-derived graph:

    MATCH
      (a {source: 'architecture_diagram'})
      -[r]->
      (b {source: 'architecture_diagram'})
    RETURN a, r, b

Show the original CSV graph:

    MATCH (a)-[r]->(b)
    WHERE a.source IS NULL
      AND b.source IS NULL
    RETURN a, r, b

Show both graphs:

    MATCH (a)-[r]->(b)
    RETURN a, r, b

## 16. Test the Architecture-Derived PostgreSQL Path

Run in Neo4j Browser:

    MATCH path =
      (affected {source: 'architecture_diagram'})
      -[:USES|DEPENDS_ON*1..10]->
      (db:Database {
        name: 'PostgreSQL',
        source: 'architecture_diagram'
      })
    RETURN path

Expected path:

    Customer Portal
        -> Order Service
        -> Payment Service
        -> PostgreSQL

## 17. Check Running Model Servers

Run:

    ps -ef | grep llama-server

Ports identify the model:

    8080 = Julia-1
    8081 = SmolVLM2
    8082 = Qwen

## 18. Stop a Model Server

Find the process ID:

    ps -ef | grep llama-server

Stop the required process:

    kill PID

Replace `PID` with the process ID.

## 19. Troubleshooting

### Neo4j container is stopped

    podman start neo4j-adi

### Python cannot import Neo4j

    cd ~/agentic-dependency-intelligence
    source .venv/bin/activate
    python -m pip install neo4j

### NEO4J_PASSWORD is missing

    export NEO4J_PASSWORD='YOUR-NEO4J-PASSWORD'

### Julia connection is refused

Confirm the Julia server:

    curl -s http://127.0.0.1:8080/health

Restart Julia if required.

### Qwen generates an empty response

Make sure Qwen was started with:

    --reasoning off

Without this option, the token budget may be consumed by reasoning content while the final response remains empty.

### SmolVLM2 reports that image input is unsupported

Confirm that the server was started with:

    --mmproj ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-mmproj-f16.gguf

### SmolVLM2 fails to tokenize the prompt

Confirm that the server was started with:

    --no-jinja

### SSH tunnel reports address already in use

On the Mac, check the process using the port:

    lsof -nP -iTCP:7474 -sTCP:LISTEN
    lsof -nP -iTCP:7687 -sTCP:LISTEN

Stop the old SSH process or use alternative local ports.

Example:

    ssh -N \
      -L 17474:127.0.0.1:7474 \
      -L 17687:127.0.0.1:7687 \
      cloud_user@54.206.42.48

Then access:

    http://localhost:17474

Use this Bolt URI:

    bolt://localhost:17687
