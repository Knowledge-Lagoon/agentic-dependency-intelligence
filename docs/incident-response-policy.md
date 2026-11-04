---
title: Incident Response Policy
components:
  - PostgreSQL
  - Payment Service
  - Authentication Service
  - Order Service
  - Notification Service
---

# Incident Response Policy

Production incidents should be evaluated using:

- customer impact
- critical service impact
- dependency blast radius
- redundancy
- number of applications affected
- number of teams involved

Incidents affecting customer-facing production workloads require investigation.

Broad impact involving critical services or unavailable non-redundant dependencies should be considered for escalation.
