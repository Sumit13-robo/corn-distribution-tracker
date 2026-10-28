# File Handoff: `.github/dependabot.yml`

**Status:** IMPLEMENTED
**Primary owner:** DevOps/Lead
**File purpose:** Automated dependency-update pull requests.

## Current implementation

Weekly pip updates for `apps/api`, weekly npm updates for `apps/web`, and monthly GitHub Actions updates. Each ecosystem has a pull-request limit.

## Verification

YAML is part of the statically validated `.github` configuration. No Dependabot run has occurred in this workspace.

## Unresolved issues

Dependency updates require human review and the CI gates before merge.
