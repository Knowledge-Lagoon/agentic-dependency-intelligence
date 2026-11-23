# Architecture Diagram Ingestion

## Purpose

Architecture diagram ingestion converts a visual architecture artifact into dependency data that can be loaded into Neo4j.

The capability is AI-assisted. It is not fully autonomous.

## Ingestion Flow

    Architecture PNG
        ->
    SmolVLM2 vision model
        ->
    candidate graph JSON
        ->
    structural validation
        ->
    human review and correction
        ->
    approved_graph.json
        ->
    architecture/load_graph.py
        ->
    Neo4j
        ->
    blast-radius analysis

## Input

The architecture diagram is stored at:

    architecture/input/architecture.png

The diagram may contain:

- applications
- services
- databases
- external systems
- directed connections
- ownership information
- environment information
- legends
- section headings
- decorative icons

## Vision Model

The MVP uses SmolVLM2 through llama.cpp.

The vision server runs locally on port 8081.

The model requires:

- the SmolVLM2 language-model GGUF
- the multimodal projector file
- llama.cpp multimodal support

Example startup command:

    cd ~/llama.cpp

    ./build/bin/llama-server \
      -m ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf \
      --mmproj ~/models/smolvlm2-2.2b/SmolVLM2-2.2B-Instruct-mmproj-f16.gguf \
      --no-jinja \
      --host 127.0.0.1 \
      --port 8081 \
      -c 4096

Verify the server:

    curl -s http://127.0.0.1:8081/health

Expected result:

    {"status":"ok"}

## Candidate Extraction

Run:

    python architecture/extract_graph.py

The extractor:

1. reads the architecture PNG
2. converts the image to base64
3. sends the image to SmolVLM2
4. requests components and relationships
5. preserves the raw vision-model response
6. parses the returned JSON
7. normalizes supported component types
8. performs structural validation
9. writes an extracted graph only when validation succeeds

The raw response is stored at:

    architecture/output/vision_raw_response.txt

The extracted output is stored at:

    architecture/output/extracted_graph.json

These files are candidate outputs only.

They must not be loaded directly into Neo4j.

## Why Human Approval Is Required

Vision models may:

- confuse legend entries with components
- confuse section headings with components
- miss component labels
- create duplicate components
- invent components
- miss relationships
- reverse arrow directions
- infer relationships that are not visible
- create relationships whose source or target is missing
- confuse ownership with dependency
- confuse environment information with dependency
- return valid JSON containing incorrect graph data

Valid JSON does not guarantee an accurate architecture graph.

The vision-model output must therefore be reviewed before graph import.

## Validation Rules

The extraction pipeline validates:

- the top-level JSON structure
- presence of a components list
- presence of a relationships list
- supported component types
- supported relationship types
- duplicate components
- duplicate relationships
- missing component names
- missing relationship sources
- missing relationship targets
- relationships referencing unknown components
- self-referencing relationships

Supported component types:

- Application
- Service
- Database
- ExternalSystem

Supported relationship types:

- USES
- DEPENDS_ON
- CONNECTS_TO

## Component-Type Normalization

The extraction pipeline may normalize equivalent model terminology into the project ontology.

Examples:

    Web Application
        ->
    Application

    Mobile Application
        ->
    Application

    External Service
        ->
    ExternalSystem

    External System
        ->
    ExternalSystem

Normalization must be limited to clear synonyms.

Ambiguous types must be rejected rather than guessed.

## Approved Graph

After validation and human review, the approved architecture graph is stored at:

    architecture/output/approved_graph.json

Only this approved file is eligible for import into Neo4j.

Example structure:

    {
      "components": [
        {
          "name": "Customer Portal",
          "type": "Application"
        },
        {
          "name": "Order Service",
          "type": "Service"
        },
        {
          "name": "Payment Service",
          "type": "Service"
        },
        {
          "name": "PostgreSQL",
          "type": "Database"
        }
      ],
      "relationships": [
        {
          "source": "Customer Portal",
          "target": "Order Service",
          "type": "USES"
        },
        {
          "source": "Order Service",
          "target": "Payment Service",
          "type": "DEPENDS_ON"
        },
        {
          "source": "Payment Service",
          "target": "PostgreSQL",
          "type": "USES"
        }
      ]
    }

## Import to Neo4j

Run:

    python architecture/load_graph.py

The loader:

1. reads only approved_graph.json
2. validates components and relationships
3. connects to Neo4j
4. removes the previous architecture-derived graph
5. imports approved nodes
6. imports approved relationships
7. applies graph-source metadata
8. verifies imported node and relationship counts

Example successful result:

    IMPORT COMPLETE

    Imported nodes: 13
    Imported relationships: 10

    Graph source: architecture_diagram

## Source Tracking

Every architecture-derived node is tagged with:

    source = architecture_diagram

Every architecture-derived relationship is also tagged with:

    source = architecture_diagram

This allows architecture-derived and CSV-derived graphs to coexist in the same Neo4j database.

## Count Graph Sources

Run in Neo4j Browser:

    MATCH (n)
    RETURN
      coalesce(n.source, 'csv_original') AS graph_source,
      count(n) AS nodes
    ORDER BY graph_source

## Show the Architecture-Derived Graph

    MATCH
      (a {source: 'architecture_diagram'})
      -[r]->
      (b {source: 'architecture_diagram'})
    RETURN a, r, b

## Show the Original CSV Graph

    MATCH (a)-[r]->(b)
    WHERE a.source IS NULL
      AND b.source IS NULL
    RETURN a, r, b

## Show Both Graphs

    MATCH (a)-[r]->(b)
    RETURN a, r, b

## Architecture-Derived PostgreSQL Path

Run:

    MATCH path =
      (affected {source: 'architecture_diagram'})
      -[:USES|DEPENDS_ON*1..10]->
      (db:Database {
        name: 'PostgreSQL',
        source: 'architecture_diagram'
      })
    RETURN path

Expected sample path:

    Customer Portal
        -> Order Service
        -> Payment Service
        -> PostgreSQL

Expected failure impact:

    Direct impact:
    - Payment Service

    Indirect impact:
    - Order Service at distance 2
    - Customer Portal at distance 3

## Source-Specific Analysis

Run:

    python run_analysis.py PostgreSQL \
      --source architecture_diagram

The source option ensures that the analysis uses only nodes and relationships imported from the architecture diagram.

Without source filtering, similarly named components from the CSV graph could also match.

## Agent Analysis

Run:

    python agent/dependency_agent.py \
      "What happens if PostgreSQL goes down?" \
      --source architecture_diagram

The Agent then orchestrates:

    natural-language question
        ->
    component identification
        ->
    architecture-derived Neo4j graph
        ->
    blast-radius analysis
        ->
    Graph Risk
        ->
    graph-guided document retrieval
        ->
    Julia-1 decision scoring
        ->
    Qwen operational guidance

## Architecture Topology vs Operational Metadata

Architecture diagrams primarily provide topology.

Topology includes:

- component existence
- component type
- directed dependencies
- direct impact
- indirect impact
- dependency depth
- graph-derived blast radius

Architecture diagrams may not provide authoritative information about:

- declared criticality
- customer-facing classification
- production environment
- ownership
- redundancy
- service tier
- SLA or SLO
- recovery objectives

Missing metadata must be reported as:

    UNKNOWN

Missing metadata must not automatically be interpreted as false.

## Declared Criticality

Declared criticality should come from an authoritative source such as:

- CMDB
- service catalogue
- business-impact assessment
- approved service metadata
- SLA or service tier
- reviewed operational documentation

The vision model must not invent declared criticality from topology.

## Graph Risk

When declared criticality is unavailable, the system can still calculate Graph Risk from Neo4j topology.

Graph Risk uses:

- direct impact
- indirect impact
- affected applications
- maximum dependency depth

Example:

    Declared criticality: UNKNOWN
    Graph Risk: HIGH
    Graph Risk Score: 8

Graph Risk is not a replacement for declared criticality.

## Current Status

Implemented:

- architecture PNG input
- local SmolVLM2 integration
- candidate graph extraction
- preservation of raw model output
- component-type normalization
- structural validation
- reviewed approved graph
- safe approved-graph import
- source tagging
- source-specific Neo4j queries
- architecture-derived blast-radius analysis
- architecture-derived Graph Risk
- Agent analysis over the architecture-derived graph

## Current Limitations

- Vision extraction requires human review.
- The local vision model may miss or invent relationships.
- A valid JSON response may still contain incorrect topology.
- Architecture ingestion does not automatically establish criticality.
- Architecture ingestion does not automatically establish ownership.
- Architecture ingestion does not automatically establish production status.
- Architecture ingestion does not automatically establish redundancy.
- Vision processing may be slow on the CPU-only lab server.
- The architecture-derived graph currently uses synthetic MVP data.
- No automatic graph mutation is allowed from raw vision output.

## MVP Positioning

This feature should be described as:

    AI-assisted architecture-to-graph discovery with structural
    validation and human approval before Neo4j import.

This feature should not be described as:

- fully autonomous architecture understanding
- guaranteed relationship extraction
- automatic production CMDB creation
- automatic criticality classification
- automatic incident remediation

## Acceptance Test

Architecture ingestion is considered successful when:

1. an architecture diagram is supplied
2. a candidate graph is extracted
3. the candidate graph is reviewed
4. approved_graph.json is created
5. the approved graph is loaded into Neo4j
6. architecture-derived nodes are source-tagged
7. Neo4j recovers the expected dependency path
8. source-specific blast-radius analysis returns the expected impact

For the sample PostgreSQL scenario, the acceptance result is:

    PostgreSQL
        <-
    Payment Service
        <-
    Order Service
        <-
    Customer Portal

This proves that the approved architecture mapping can drive dependency analysis in Neo4j.
