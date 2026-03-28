# Changelog

All notable changes to this project will be documented in this file.

## [v1.0.0] - 2026-03-28

### Initial Production Release

**Database:**
- 85.7M judicial decisions across 90 jurisdictions
- 245M citation links with graph traversal
- FTS5 full-text search with BM25 ranking in 20+ languages
- WAL mode with concurrent read access

**MCP Server:**
- 39 MCP tools for search, analysis, citation, IP disputes, entities, and document generation
- 98 jurisdiction adapters for external legal databases
- FastMCP 2.14+ with StreamableHTTP transport
- Graceful degradation with local cache fallback

**Infrastructure:**
- Docker container deployment with health checks
- Cloudflare Tunnel for secure public access
- Public endpoint: `caselaw.patent-space.dev/mcp`

**Top Jurisdictions:**
CN 45.5M | US 30.6M | BR 1.8M | FR 1.2M | CH 1.1M | TR 714K | KR 513K | AR 496K | AU 491K | PL 438K | CA 405K | NL 340K | DE 251K | CZ 238K | EU 188K | GB 175K | IN 122K | JP 92K | TW 77K | CO 24K

[v1.0.0]: https://github.com/Agentic-governance/caselaw-mcp/releases/tag/v1.0.0
