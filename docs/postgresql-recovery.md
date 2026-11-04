---
title: PostgreSQL Recovery Runbook
components:
  - PostgreSQL
  - Payment Service
---

# PostgreSQL Recovery Runbook

If PostgreSQL becomes unavailable:

1. Confirm database health and connectivity.
2. Check whether database redundancy or replicas are available.
3. Validate connectivity from Payment Service.
4. Check recent database changes and resource exhaustion.
5. Notify the Payments Team if Payment Service is affected.
6. Escalate when customer transactions are affected.

Recovery should be validated by confirming successful Payment Service database connections.
