---
title: Platform Architecture
components:
  - Customer Portal
  - Order Service
  - Payment Service
  - Authentication Service
  - Notification Service
  - PostgreSQL
  - User Database
---

# Platform Architecture

Customer Portal uses Order Service.

Order Service depends on Payment Service and Notification Service.

Payment Service depends on Authentication Service and uses PostgreSQL.

Authentication Service uses User Database.

Service ownership and runtime environment information are maintained in the dependency graph.
