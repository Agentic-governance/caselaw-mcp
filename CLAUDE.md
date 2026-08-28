# Claude Code Instructions — caselaw-mcp

Read this file first when working on this repository.

## Primary task

This branch is for restarting serious development of `caselaw-mcp`.

Start by reading the full restart review:

@docs/CLAUDE_CODE_RESTART_REVIEW.md

## Working mode

- Treat this as a production-recovery and hardening task.
- Do not start with broad refactoring.
- First verify the real server/database state and document it.
- Do not commit production database files, bulk legal data, secrets, tokens, logs, or private server-only artifacts.
- Prefer small, reviewable commits.
- Preserve existing MCP tool names unless a change is explicitly justified.

## First concrete deliverable

Create or update:

```text
docs/audit/SERVER_REALITY_AUDIT.md
```

This audit should compare the running server and database against the repository README and code.

## Priority order

1. Audit the deployment host and production DB reality.
2. Add/verify `.gitignore` and data/secret guardrails.
3. Restore or reconstruct safe `data/schema.sql`.
4. Add a minimal synthetic fixture DB or SQL fixture.
5. Harden DB startup/failure behavior.
6. Add fixture-based tests.
7. Update README so verified facts, historical claims, and target claims are clearly separated.
8. Only then consider modularizing `server.py`.
