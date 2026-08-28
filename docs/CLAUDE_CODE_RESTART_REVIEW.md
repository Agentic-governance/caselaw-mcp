# Claude Code Restart Review — Caselaw MCP

## Purpose

This branch restarts serious development of `caselaw-mcp`.

The server is believed to be running as an MCP service on the deployment host, and the real SQLite dataset exists on that server. The GitHub repository currently contains the MCP server code and README, but it does **not** fully capture the operational reality: database schema, data inventory, deployment status, observability, and current endpoint health are underdocumented.

Claude Code should treat this as a production-recovery and hardening task, not as a cosmetic README update.

---

## Known repository facts from GPT review

Repository: `Agentic-governance/caselaw-mcp`

Observed files / behavior:

- README advertises a remote MCP endpoint: `https://caselaw.patent-space.dev/mcp`.
- README claims large coverage: 85.7M cases, 90 jurisdictions, 245M citations, 39 MCP tools, 705GB database.
- README self-host section says the full database is not in the repository and expects a local SQLite DB at `/mnt/nvme/caselaw-data/caselaw.db`.
- `docker-compose.yml` mounts `/mnt/nvme/caselaw-data:/app/data` and exposes port `8006`.
- `Dockerfile` runs `python server.py --transport http --host 0.0.0.0 --port 8006`.
- `tools/storage.py` defaults to `data/caselaw.db`, overridable by `CASELAW_DB_PATH`.
- `tools/storage.py:init_db()` expects `data/schema.sql`, but `data/schema.sql` is not currently present in the repository.
- `server.py` is a large mixed entrypoint registering search, statute, IP, entity, event, metadata, and analytics tools.
- Some code paths directly assume DB objects such as `cases`, `case_citations`, and `citation_index`.

---

## Primary development objective

Bring the repository back into alignment with the running server.

The desired outcome is a repo that a future agent or developer can clone, inspect, test, deploy, and operate without relying on hidden context.

Do **not** commit the large database itself.
Do **not** commit raw legal bulk data.
Do **not** commit secrets, tunnel tokens, API keys, private logs, or credentials.

Commit only code, schema, docs, small fixtures, tests, and operational metadata that are safe to publish.

---

## Phase 0 — Server and data reality audit

Run these checks on the deployment host where the MCP server and database live.

```bash
pwd
hostname
whoami

docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker compose ps || true

ls -lah /mnt/nvme/caselaw-data || true
ls -lah /mnt/nvme/caselaw-data/caselaw.db* || true

sqlite3 /mnt/nvme/caselaw-data/caselaw.db '.tables'
sqlite3 /mnt/nvme/caselaw-data/caselaw.db '.schema cases'
sqlite3 /mnt/nvme/caselaw-data/caselaw.db '.schema case_citations'
sqlite3 /mnt/nvme/caselaw-data/caselaw.db '.schema citation_index'

sqlite3 /mnt/nvme/caselaw-data/caselaw.db "select max(rowid) as estimated_cases from cases;"
sqlite3 /mnt/nvme/caselaw-data/caselaw.db "select max(rowid) as estimated_citations from case_citations;"
sqlite3 /mnt/nvme/caselaw-data/caselaw.db "select jurisdiction, count(*) as n from cases group by jurisdiction order by n desc limit 30;"
sqlite3 /mnt/nvme/caselaw-data/caselaw.db "select min(decision_date), max(decision_date) from cases;"

curl -i --max-time 20 http://localhost:8006/mcp || true
curl -i --max-time 20 https://caselaw.patent-space.dev/mcp || true
```

Create a small audit report at:

```text
docs/audit/SERVER_REALITY_AUDIT.md
```

The audit report must include:

- current container/process status
- actual DB path and file size
- actual tables present
- extracted schema, or a redacted/safe schema summary
- real row-count estimates
- jurisdiction distribution
- endpoint health result
- README claims that are confirmed
- README claims that are stale, unverified, or false

---

## Phase 1 — Restore missing schema and safe local fixture

If `data/schema.sql` exists on the server or can be reconstructed from `.schema`, add a safe version to the repository.

Add:

```text
data/schema.sql
```

Requirements:

- Include table definitions needed by all current code paths.
- Include FTS5 definitions if the code depends on them.
- Include indexes needed for common search/detail/citation operations.
- Do not include real data.

Also add a tiny fixture DB or fixture loader for tests:

Option A:

```text
tests/fixtures/minimal_caselaw.sql
```

Option B:

```text
scripts/build_fixture_db.py
```

The fixture must contain a few synthetic/public-domain-safe rows only:

- at least 2 jurisdictions, preferably `JP` and `US`
- at least 3 cases
- at least 2 citation edges
- at least one case with full text
- at least one no-result search path

---

## Phase 2 — Make startup and DB failure modes explicit

Current behavior risks silent creation of an empty DB because `tools/storage.py:get_connection()` creates the DB directory and opens SQLite automatically.

Improve this carefully.

Requirements:

- Add explicit DB existence validation for runtime search mode.
- Do not silently create an empty production DB when the expected DB file is missing.
- Keep a controlled initialization path for tests/dev only.
- Add a clear error message such as:

```text
CASELAW_DB_PATH does not exist. Set CASELAW_DB_PATH or mount /app/data/caselaw.db.
```

Recommended approach:

- Introduce a config module, e.g. `tools/config.py`.
- Add `CASELAW_DB_PATH` and `CASELAW_ALLOW_INIT_EMPTY_DB=false` behavior.
- Only allow automatic `init_db()` when explicitly requested.

---

## Phase 3 — Split the monolithic server entrypoint

`server.py` currently mixes multiple domains:

- generic case search
- statute search
- legal draft generation
- legal risk scoring
- IP stats/disputes
- entity resolution
- events/snapshots
- metadata extraction
- analytics

Do not attempt a risky rewrite in one pass.

Instead:

1. Add a lightweight tool registration structure.
2. Move groups into modules only if tests can prove behavior remains intact.
3. Preserve current MCP tool names.
4. Add a tool inventory generated from code.

Suggested target:

```text
server.py
mcp_tools/search_tools.py
mcp_tools/citation_tools.py
mcp_tools/metadata_tools.py
mcp_tools/ip_tools.py
mcp_tools/entity_tools.py
mcp_tools/event_tools.py
mcp_tools/analytics_tools.py
```

If this is too much for the first PR, create a technical debt map instead:

```text
docs/architecture/TOOL_BOUNDARY_MAP.md
```

---

## Phase 4 — Tests that must exist before serious feature work

Add tests with the fixture DB.

Minimum tests:

```text
tests/test_storage_schema.py
tests/test_search_cases.py
tests/test_get_case_detail.py
tests/test_metadata_extractor.py
tests/test_mcp_tool_inventory.py
```

Test requirements:

- Use a temp DB path via `CASELAW_DB_PATH`.
- Never require the 705GB production DB.
- Verify no-result behavior returns structured suggestions, not exceptions.
- Verify invalid jurisdiction returns clear error.
- Verify `get_case_detail` returns expected metadata and does not leak huge unbounded text.
- Verify registered MCP tool count matches documented inventory, or explicitly document divergence.

---

## Phase 5 — README truth maintenance

Update README only after Phase 0 audit.

README must clearly separate:

1. **Current public server status**
2. **Repository capabilities**
3. **Production dataset claims**
4. **Self-host requirements**
5. **Development/test mode with fixture DB**

Do not keep unverified claims as if they are live facts.

Recommended wording pattern:

```markdown
The production deployment has historically used a large SQLite corpus mounted outside this repository. Current corpus statistics are tracked in docs/audit/SERVER_REALITY_AUDIT.md. The repository includes schema and test fixtures, but not the production database.
```

---

## Phase 6 — MCP endpoint verification

Add a script:

```text
scripts/check_mcp_endpoint.py
```

It should verify:

- local endpoint responds
- remote endpoint responds, if configured
- MCP handshake/tool listing works if FastMCP client supports it
- failure output is readable

Environment variables:

```text
MCP_LOCAL_URL=http://localhost:8006/mcp
MCP_REMOTE_URL=https://caselaw.patent-space.dev/mcp
```

Do not require remote access for unit tests.

---

## Phase 7 — Security and publication guardrails

Add or verify `.gitignore` covers:

```gitignore
*.db
*.sqlite
*.sqlite3
*.db-wal
*.db-shm
.env
.env.*
*.log
/data/*.db
/data/*.sqlite*
```

Add a short policy doc:

```text
docs/ops/DATA_AND_SECRET_GUARDRAILS.md
```

It should state:

- production DB is not committed
- only schema/fixtures are committed
- no copyrighted bulk corpus dumps
- no API keys/tunnel tokens
- no private legal text dumps unless licensing is explicit

---

## Priority order

Do this in order:

1. Phase 0 audit
2. `.gitignore` and guardrails
3. schema restore / fixture DB
4. DB failure-mode fix
5. tests
6. README truth update
7. modularization
8. endpoint check script

Do not start with refactoring before the audit and tests.

---

## Acceptance criteria for the first serious PR

The first PR should be considered successful if:

- It documents the real server/data state.
- It prevents accidental empty DB startup in production mode.
- It restores or reconstructs `data/schema.sql` safely.
- It adds minimal fixture-based tests.
- It updates README claims to distinguish verified facts from historical/target claims.
- It does not commit real DB files, secrets, or bulk legal data.

---

## Notes for Claude Code

Be aggressive about finding contradictions, but conservative about code rewrites.

This repository is valuable because it may already have a running MCP and a large server-side dataset. The immediate goal is to make the system legible, reproducible, and safe to develop again.

Treat undocumented production reality as the main risk.
