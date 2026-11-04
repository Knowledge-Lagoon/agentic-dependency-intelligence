---
title: Payment Service Runbook
components:
  - Payment Service
  - PostgreSQL
  - Order Service
---

# Payment Service Runbook

Payment Service processes payment operations for Order Service.

If Payment Service is unavailable:

1. Check Payment Service health.
2. Verify PostgreSQL connectivity.
3. Review application logs.
4. Check Authentication Service availability.
5. Validate Order Service connectivity.
6. Notify Payments Team.

Customer transaction failures should be treated as production-impacting events.
