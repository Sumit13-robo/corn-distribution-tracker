# DevOps / Release Agent Handoff

## Own
Dockerfiles, Compose, `.env.example`, `Makefile`, production runbook, CI/release workflow if added, observability and backup/restore documentation.

## Required outcomes
- Reproducible clean-checkout local run with PostgreSQL 17 and Django health checks.
- No secrets in build args, client bundle, logs or committed files.
- Non-root runtime images where feasible; minimal images; pinned dependencies.
- Explicit migration command/job, not every app replica racing migrations.
- TLS/reverse-proxy guidance, strict CORS/CSRF origins, private storage, secure cookies and provider map config.
- Backup and restore instructions include database plus linked evidence objects/versions and a periodic restore drill.
- Readiness/liveness, request ID logging, redaction and metrics/alert guidance.

## Current verification
- Docker image build/Compose startup **not executed** on this host (no Docker/Podman/Buildah; rootless namespaces blocked).
- Non-Docker local path verified: Django migrations, 58 backend tests, 18 web tests, production build and 8 Playwright tests.
- Gunicorn is pinned/installed; verify the Compose command on a Docker-capable host.
- Local Django-schema backup/restore drill passed on synthetic E2E data; production provider drill remains pending.

## Report
Exact startup/test/build commands, assumptions about hosting/object storage/map provider, production env requirements and unresolved launch risks.
