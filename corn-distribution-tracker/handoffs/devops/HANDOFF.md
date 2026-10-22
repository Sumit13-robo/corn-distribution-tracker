# DevOps / Release Agent Handoff

## Own
Dockerfiles, Compose, `.env.example`, `Makefile`, production runbook, CI/release workflow if added, observability and backup/restore documentation.

## Required outcomes
- Reproducible clean-checkout local run with PostgreSQL/PostGIS and app health checks.
- No secrets in build args, client bundle, logs or committed files.
- Non-root runtime images where feasible; minimal images; dependency lockfiles.
- Explicit migration command/job, not every app replica racing migrations.
- TLS/reverse-proxy guidance, strict CORS, private storage configuration, secure cookies and provider map config.
- Backup and restore instructions include database plus linked evidence objects/versions and a periodic restore drill.
- Readiness/liveness, request ID logging, redaction and metrics/alert guidance.

## Report
Exact startup/test/build commands, assumptions about hosting/object storage/map provider, production env requirements and unresolved launch risks.
