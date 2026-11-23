# Agentic Dependency Intelligence

Agentic Dependency Intelligence is a proof-of-concept platform for identifying the direct and indirect impact of a technology-component failure.

The project combines:

- Neo4j dependency modelling
- blast-radius analysis
- architecture-diagram-assisted graph ingestion
- topology-based Graph Risk
- graph-guided document retrieval
- local decision scoring
- local grounded text generation
- natural-language agent orchestration

The MVP is focused on explainable dependency analysis rather than automated remediation or a graphical user interface.

## Problem Statement

Technology dependencies are often distributed across architecture diagrams, service documentation, runbooks, spreadsheets, and individual knowledge.

When a component fails, engineers need to answer:

- What depends directly on the failed component?
- What is affected indirectly?
- Which applications and services are involved?
- How deep is the dependency chain?
- Which operational documents are relevant?
- What response should be considered?
- What evidence supports the result?

The project builds a dependency graph in Neo4j and uses that graph as the authoritative source for blast-radius analysis.

## Example

The sample graph includes this dependency chain:

    Customer Portal
        -> Order Service
        -> Payment Service
        -> PostgreSQL

If PostgreSQL becomes unavailable, Neo4j derives:

    Direct impact:
    - Payment Service

    Indirect impact:
    - Order Service, dependency distance 2
    - Customer Portal, dependency distance 3

    Maximum dependency depth:
    - 3

The system then retrieves relevant runbooks and policies, calculates Graph Risk, obtains a decision recommendation, and generates operational guidance.

## Current MVP Architecture

    Natural-language question
                |
                v
        Dependency Agent
                |
                +-----------------------------+
                |                             |
                v                             v
             Neo4j                     ImpactAnalyzer
                |                             |
                |                             +-- direct impact
                |                             +-- indirect impact
                |                             +-- dependency depth
                |                             +-- affected services
                |                             +-- affected applications
                |                             +-- Graph Risk
                |
                v
          ContextBuilder
                |
                +-- GraphRetriever
                |      |
                |      +-- architecture documents
                |      +-- operational runbooks
                |      +-- incident policy
                |
                +-- authoritative graph evidence
                |
                +-----------------------------+
                |                             |
                v                             v
             Julia-1                    Qwen 0.8B
        decision scoring          grounded explanation
                |                             |
                +-------------+---------------+
                              |
                              v
                       Agent response

## Component Responsibilities

### Neo4j

Neo4j is the source of truth for dependency relationships.

Neo4j stores:

- applications
- services
- databases
- external systems
- teams
- environments
- dependency relationships
- graph-source metadata

Neo4j determines which components are directly and indirectly affected.

### ImpactAnalyzer

`analysis/impact_analyzer.py` queries Neo4j and calculates:

- failed-component details
- direct impact
- indirect impact
- dependency distance
- affected services
- affected applications
- maximum dependency depth
- available ownership information
- available environment information
- Graph Risk

### GraphRetriever

`rag/retriever.py` retrieves relevant operational documents.

The retriever uses component names discovered through Neo4j rather than relying only on words in the original question.

For example, a PostgreSQL incident may cause Neo4j to discover:

    PostgreSQL
    Payment Service
    Order Service
    Customer Portal

The retriever uses those names to select relevant documents from `docs/`.

### ContextBuilder

`rag/context_builder.py` combines:

- failed-component details
- graph source
- authoritative direct impact
- authoritative indirect impact
- affected services and applications
- dependency depth
- Graph Risk
- owners and environments when available
- retrieved document contents
- grounding rules for the generative model

The resulting `context_text` is sent to Qwen.

### Julia-1

Julia-1 is a local decision model served through `llama.cpp`.

Julia-1 evaluates structured evidence and scores predefined outcomes such as:

    MONITOR
    INVESTIGATE
    ESCALATE

Julia-1 also evaluates severity options such as:

    LOW
    MEDIUM
    HIGH
    CRITICAL

Julia-1 returns probabilities rather than generating a free-form explanation.

### Qwen

Qwen 0.8B is the local generative model.

Qwen receives:

- the user's question
- authoritative Neo4j evidence
- Graph Risk
- retrieved document content
- the decision-model result
- grounding instructions

Qwen produces human-readable operational guidance.

Qwen is not the source of truth for dependency facts. Qwen must not redefine direct impact, indirect impact, component type, dependency distance, or Graph Risk.

### Dependency Agent

`agent/dependency_agent.py` orchestrates the complete workflow.

The Agent:

1. accepts a natural-language question
2. identifies a known component
3. queries Neo4j through ImpactAnalyzer
4. calculates blast radius and Graph Risk
5. retrieves relevant documents
6. builds grounded context
7. calls Julia-1
8. calls Qwen
9. returns a grounded operational response

## Ingestion Paths

The MVP supports two graph-ingestion paths.

### CSV Ingestion

    CSV files
        ->
    ingestion/load_graph.py
        ->
    Neo4j

The CSV path loads structured component and relationship data.

### Architecture-Diagram Ingestion

    Architecture PNG
        ->
    SmolVLM2
        ->
    candidate graph
        ->
    validation and human review
        ->
    approved_graph.json
        ->
    architecture/load_graph.py
        ->
    Neo4j

Architecture-diagram ingestion is AI-assisted, not fully autonomous.

The raw vision-model response must not be loaded directly into Neo4j.

Only this reviewed file is eligible for import:

    architecture/output/approved_graph.json

## Architecture Graph Source

Architecture-derived nodes and relationships are tagged with:

    source = architecture_diagram

This allows the architecture-derived graph and the original CSV graph to coexist in the same Neo4j database.

A source-specific analysis can be run with:

    python run_analysis.py PostgreSQL --source architecture_diagram

The source filter prevents similarly named nodes from the CSV graph from being used accidentally.

## Viewing Both Graphs in Neo4j

Count nodes by source:

    MATCH (n)
    RETURN
      coalesce(n.source, 'csv_original') AS graph_source,
      count(n) AS nodes
    ORDER BY graph_source

Show only the architecture-derived graph:

    MATCH
      (a {source: 'architecture_diagram'})
      -[r]->
      (b {source: 'architecture_diagram'})
    RETURN a, r, b

Show only the original CSV graph:

    MATCH (a)-[r]->(b)
    WHERE a.source IS NULL
      AND b.source IS NULL
    RETURN a, r, b

Show both graphs:

    MATCH (a)-[r]->(b)
    RETURN a, r, b

## Architecture-Derived Blast Radius

To test the PostgreSQL path using only architecture-derived relationships:

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

## Declared Criticality

Declared criticality is authoritative operational metadata.

It may come from:

- a CMDB
- a service catalogue
- a business-impact assessment
- an SLA or service tier
- application metadata
- approved operational documentation
- manually reviewed metadata

Example:

    critical = true

If no authoritative source supplies the value, criticality is:

    UNKNOWN

UNKNOWN does not mean false.

The AI must not invent declared criticality from graph topology alone.

## Graph Risk

Graph Risk measures topology-based downstream impact.

Graph Risk is separate from declared criticality.

The MVP score uses:

- each directly affected component: 2 points
- each indirectly affected component: 1 point
- each affected application: 2 points
- maximum dependency depth of 3 or more: 2 points
- maximum dependency depth of 5 or more: 1 additional point

Risk levels:

- 0 to 2: LOW
- 3 to 5: MEDIUM
- 6 to 8: HIGH
- 9 or more: CRITICAL

These weights and thresholds are MVP policy choices, not an industry standard.

Example for PostgreSQL:

    1 direct impact             +2
    2 indirect impacts          +2
    1 affected application      +2
    Maximum depth >= 3          +2
                                  --
    Graph Risk Score             8
    Graph Risk Level             HIGH

The result should be read as:

    Declared criticality: UNKNOWN
    Graph Risk: HIGH

Graph Risk must not overwrite declared criticality.

## Missing Operational Metadata

Architecture-derived nodes may not contain:

- criticality
- customer-facing classification
- redundancy
- production environment
- ownership
- service tier
- SLA information

Missing metadata is reported as:

    UNKNOWN

Examples:

    Criticality: UNKNOWN
    Redundancy: UNKNOWN
    Environment: UNKNOWN
    Owner: UNKNOWN

UNKNOWN means no authoritative evidence supplied the value.

## Graph-Guided RAG

The current implementation uses graph-guided document retrieval.

The retrieval flow is:

    User question
        ->
    Neo4j blast radius
        ->
    affected component names
        ->
    GraphRetriever
        ->
    relevant documents
        ->
    ContextBuilder
        ->
    Qwen

The local Markdown documents under `docs/` are synthetic MVP artifacts.

The current MVP does not automatically retrieve production documents from SharePoint, Confluence, ServiceNow, Jira, or a CMDB.

## Decision Layer

The project contains two decision mechanisms.

### Deterministic Policy

`decision/decision_engine.py` applies explicit Python rules.

The deterministic policy is intended as an explainable baseline.

### Julia-1 Decision Model

`decision/model_client.py` sends structured evidence to Julia-1.

Julia-1 returns probabilistic severity and action results.

### Decision Comparison

The comparison reports whether the deterministic policy and Julia-1 agree.

The comparison is not a third decision model.

The Julia-1 recommendation must not silently override deterministic policy.

## Project Structure

    agentic-dependency-intelligence/
    |
    +-- agent/
    |   +-- dependency_agent.py
    |
    +-- analysis/
    |   +-- impact_analyzer.py
    |
    +-- architecture/
    |   +-- input/
    |   |   +-- architecture.png
    |   +-- output/
    |   |   +-- approved_graph.json
    |   +-- extract_graph.py
    |   +-- load_graph.py
    |
    +-- data/
    |   +-- applications.csv
    |   +-- databases.csv
    |   +-- environments.csv
    |   +-- relationships.csv
    |   +-- services.csv
    |   +-- teams.csv
    |
    +-- decision/
    |   +-- decision_engine.py
    |   +-- model_client.py
    |
    +-- docs/
    |   +-- architecture-ingestion.md
    |   +-- authentication-service-runbook.md
    |   +-- graph-risk.md
    |   +-- incident-response-policy.md
    |   +-- payment-service-runbook.md
    |   +-- platform-architecture.md
    |   +-- postgresql-recovery.md
    |   +-- startup-guide.md
    |
    +-- graph/
    |   +-- queries.py
    |
    +-- ingestion/
    |   +-- load_graph.py
    |
    +-- rag/
    |   +-- context_builder.py
    |   +-- generator.py
    |   +-- retriever.py
    |
    +-- run_analysis.py

## Runtime Services

The MVP uses these local services:

- Neo4j in Podman
- Julia-1 on port 8080
- SmolVLM2 on port 8081 when architecture extraction is needed
- Qwen 0.8B on port 8082

SmolVLM2 does not need to run during normal dependency analysis.

## Start Neo4j

    podman start neo4j-adi
    podman ps --filter name=neo4j-adi

## Activate Python

    cd ~/agentic-dependency-intelligence
    source .venv/bin/activate

## Configure Neo4j

    export NEO4J_URI='bolt://localhost:7687'
    export NEO4J_USERNAME='neo4j'
    export NEO4J_PASSWORD='YOUR-PASSWORD'

Do not commit the password to Git.

## Start Julia-1

Run in a dedicated SSH session:

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -m ~/models/Julia-1-Q8_0.gguf \
      --host 127.0.0.1 \
      --port 8080

Verify:

    curl -s http://127.0.0.1:8080/health

## Start Qwen

Run in another dedicated SSH session:

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -hf gguf/Qwen3.5-0.8B-GGUF:Q4_K_M \
      --host 127.0.0.1 \
      --port 8082 \
      -c 4096 \
      --reasoning off

Verify:

    curl -s http://127.0.0.1:8082/health

## Start SmolVLM2 When Needed

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -m ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf \
      --mmproj ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-mmproj-f16.gguf \
      --no-jinja \
      --host 127.0.0.1 \
      --port 8081 \
      -c 4096

Verify:

    curl -s http://127.0.0.1:8081/health

## Run Dependency Analysis

Original/default graph:

    python run_analysis.py PostgreSQL

Architecture-derived graph:

    python run_analysis.py PostgreSQL \
      --source architecture_diagram

## Run the Agent

    python agent/dependency_agent.py \
      "What happens if PostgreSQL goes down?" \
      --source architecture_diagram

## Access Neo4j Browser

From a Mac terminal:

    ssh -N \
      -L 7474:127.0.0.1:7474 \
      -L 7687:127.0.0.1:7687 \
      cloud_user@54.206.42.48

Open:

    http://localhost:7474

Connection settings:

    URI: bolt://localhost:7687
    Username: neo4j
    Password: configured Neo4j password

## Current MVP Status

Implemented:

- Neo4j dependency graph
- CSV ingestion
- architecture-diagram-assisted ingestion
- reviewed and approved architecture graph
- source tracking
- direct dependency analysis
- indirect dependency analysis
- maximum dependency depth
- affected-service and application identification
- Graph Risk
- graph-guided document retrieval
- grounded context construction
- deterministic policy baseline
- Julia-1 decision scoring
- Qwen grounded generation
- natural-language Agent orchestration

## Limitations

- Architecture-diagram extraction requires human review.
- The architecture diagram does not automatically provide criticality, environment, redundancy, or ownership.
- Missing metadata must be treated as UNKNOWN.
- Graph Risk is an MVP topology score, not a formal industry risk standard.
- Local Markdown runbooks are synthetic test documents.
- Qwen may incorrectly restate graph evidence, so authoritative dependency results should be rendered directly from Neo4j.
- No automated remediation is performed.
- No UI is included.
- No live CMDB, ServiceNow, Jira, SharePoint, Confluence, or Kubernetes integration is included.
- The local lab server has limited CPU and memory, so vision extraction may be slow.

## MVP Positioning

The project should be described as:

    An explainable dependency-intelligence MVP that uses Neo4j
    to calculate blast radius, graph-guided retrieval to locate
    relevant operational knowledge, local decision models to score
    response options, and a local generative model to produce
    grounded operational guidance.

Architecture-diagram ingestion should be described as:

    AI-assisted architecture-to-graph discovery with validation
    and human approval.

It should not be described as fully autonomous architecture understanding or automated incident remediation.
