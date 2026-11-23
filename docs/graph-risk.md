# Graph Risk

## Purpose

Graph Risk measures the potential downstream impact of a component failure using dependency topology stored in Neo4j.

Graph Risk is separate from declared criticality.

## Declared Criticality

Declared criticality is authoritative operational metadata obtained from sources such as:

- CMDB or service catalogue
- business impact assessment
- SLA or service tier
- application metadata
- approved operational documentation
- manually reviewed component metadata

Example:

    critical = true

If no authoritative source supplies this information, declared criticality is:

    UNKNOWN

UNKNOWN does not mean false.

## Graph-Derived Risk

Graph Risk is calculated from dependency relationships stored in Neo4j.

Example dependency chain:

    Customer Portal
        -> Order Service
        -> Payment Service
        -> PostgreSQL

Even if PostgreSQL has no declared criticality, Neo4j can establish that a PostgreSQL failure affects multiple upstream components.

## Graph Risk Inputs

The MVP Graph Risk calculation uses:

- directly affected components
- indirectly affected components
- affected applications
- maximum dependency depth

## Scoring

- Each directly affected component: +2
- Each indirectly affected component: +1
- Each affected application: +2
- Maximum dependency depth of 3 or more: +2
- Maximum dependency depth of 5 or more: +1 additional

## Risk Levels

- Score 0 to 2: LOW
- Score 3 to 5: MEDIUM
- Score 6 to 8: HIGH
- Score 9 or more: CRITICAL

These weights and thresholds are MVP policy choices. They are not an industry standard.

## Example: PostgreSQL

Neo4j discovers:

    PostgreSQL
        <- Payment Service
        <- Order Service
        <- Customer Portal

Risk calculation:

    1 direct impact             +2
    2 indirect impacts          +2
    1 affected application      +2
    Maximum depth >= 3          +2
                                  --
    Graph Risk Score             8
    Graph Risk Level             HIGH

The result should be presented as:

    Declared criticality: UNKNOWN
    Graph Risk: HIGH
    Graph Risk Score: 8

Graph Risk must not overwrite or masquerade as declared criticality.

## Example: User Database

Neo4j discovers:

    User Database
        <- Authentication Service
        <- Payment Service
        <- Order Service
        <- Customer Portal

Risk calculation:

    1 direct impact             +2
    3 indirect impacts          +3
    1 affected application      +2
    Maximum depth >= 3          +2
                                  --
    Graph Risk Score             9
    Graph Risk Level             CRITICAL

This means User Database has CRITICAL graph-derived risk even if its declared criticality is UNKNOWN.

## Unknown Metadata

The following values may be UNKNOWN in an architecture-derived graph:

- criticality
- customer-facing classification
- redundancy
- production environment
- ownership

UNKNOWN means the information was not supplied by an authoritative source.

UNKNOWN does not mean false.

For example:

    Redundancy: UNKNOWN

means no authoritative evidence has established whether the component has replicas, failover, clustering, or another recovery mechanism.

Likewise:

    Critical: UNKNOWN

means the component has not been explicitly classified as critical or non-critical.

## Graph Risk vs Operational Metadata

The system keeps topology-derived evidence separate from operational metadata.

Example:

    User Database

    Declared criticality: UNKNOWN
    Environment:          UNKNOWN
    Redundancy:           UNKNOWN

    Graph evidence:
    Direct impact:        1
    Indirect impact:      3
    Affected applications: 1
    Maximum depth:        4

    Graph Risk Score:     9
    Graph Risk Level:     CRITICAL

An architecture diagram can reveal dependency relationships without necessarily containing business criticality, production status, ownership, or redundancy information.

## Architecture-Derived Graph Risk

Architecture-derived Neo4j nodes and relationships are tagged with:

    source = architecture_diagram

Graph Risk can therefore be calculated specifically from the architecture-derived graph.

Example:

    python run_analysis.py PostgreSQL --source architecture_diagram

## Responsibilities

Neo4j provides the dependency topology.

ImpactAnalyzer calculates:

- direct impact
- indirect impact
- affected services
- affected applications
- maximum dependency depth
- Graph Risk score
- Graph Risk level

GraphRetriever retrieves operational documents related to affected components.

Julia-1 evaluates structured operational evidence for decision scoring.

Qwen generates human-readable operational guidance.

The generative model may explain Graph Risk, but it must not recalculate or replace the authoritative Graph Risk score.

## Design Principle

The processing model is:

    Declared Criticality
            |
            | authoritative metadata
            v
       Graph Topology
            |
            | Neo4j traversal
            v
        Graph Risk
            |
            | deterministic calculation
            v
      Decision Model
            |
            | operational recommendation
            v
       Agent Response

This prevents missing metadata from being presented as known information and prevents AI from inventing business criticality classifications.

## MVP Limitation

The current Graph Risk formula is intentionally simple.

It demonstrates that useful operational risk can be derived from dependency topology even when declared metadata is unavailable.

Future versions may incorporate authoritative evidence such as:

- production environment
- number of customer-facing applications affected
- service tier
- redundancy
- SLA or SLO
- recovery time objective
- recovery point objective
- historical incidents
- dependency centrality
- number of owning teams
- business-service relationships

These inputs should be added only when they can be obtained from authoritative sources.
