<p align="center">
  <img src="https://img.shields.io/badge/Cases-85.7M-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJ3aGl0ZSI+PHBhdGggZD0iTTEyIDJMMyA3djEwbDkgNSA5LTVWN2wtOS01eiIvPjwvc3ZnPg==" alt="Cases">
  <img src="https://img.shields.io/badge/Jurisdictions-90-green?style=for-the-badge" alt="Jurisdictions">
  <img src="https://img.shields.io/badge/Citations-245M-orange?style=for-the-badge" alt="Citations">
  <img src="https://img.shields.io/badge/MCP_Tools-39-purple?style=for-the-badge" alt="Tools">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>

# ⚖️ Caselaw MCP

**World's largest open caselaw database with 85.7M judicial decisions from 90 jurisdictions.**

Search, analyze, and cross-reference the world's case law through the Model Context Protocol. Built for AI-assisted legal research.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastMCP-2.14%2B-black?logo=data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" alt="FastMCP">
  <img src="https://img.shields.io/badge/SQLite-FTS5-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

---

## 📊 Key Stats

| Metric | Value |
|--------|-------|
| 📚 **Total cases** | 85,700,000+ |
| 🌍 **Jurisdictions** | 90 |
| 🔗 **Citation links** | 245,000,000+ |
| 🗣️ **Languages** | 20+ |
| 💾 **Database size** | 705 GB |
| 🔧 **MCP tools** | 39 |

---

## ✨ Features

- 🔍 **FTS5 full-text search** — BM25-ranked search across 85.7M cases
- 🌐 **Multi-jurisdiction research** — 90 jurisdictions from every continent
- 🔗 **Citation network analysis** — 245M+ citation links with graph traversal
- ⚖️ **Legal risk assessment** — Factor-based risk scoring with case law backing
- 📊 **Comparative law analysis** — Side-by-side jurisdiction comparison
- 🏛️ **IP/patent dispute research** — UDRP, Section 337, EPO, PTAB data
- 📝 **Document generation** — Takedown notices, legal opinions, cease & desist drafts
- 👨‍⚖️ **Judge analytics** — Win rates, sentencing patterns, topic specialization
- 🏢 **Entity resolution** — Canonical company/org matching across sources
- 📈 **Trend analysis** — Legal area trends over time with case volume tracking

---

## 🚀 Quick Start

### Option 1: Claude AI (Remote MCP)

Add the remote MCP endpoint in Claude AI settings:

```
https://caselaw.patent-space.dev/mcp
```

That's it. All 39 tools are immediately available in your Claude conversation.

### Option 2: Claude Code

Add to your Claude Code MCP configuration (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "caselaw": {
      "url": "https://caselaw.patent-space.dev/mcp"
    }
  }
}
```

### Option 3: Self-Hosted

```bash
git clone https://github.com/Agentic-governance/caselaw-mcp.git
cd caselaw-mcp
docker-compose up -d
```

The server starts on port `8006` with MCP endpoint at `/mcp`.

> **Note:** Self-hosting requires providing your own SQLite database at `/mnt/nvme/caselaw-data/caselaw.db` (mounted via volume). The full database is not included in the repository.

---

## 🔧 Tool Catalog (39 Tools)

### 🔍 Search

| Tool | Description |
|------|-------------|
| `search_cases` | Full-text search across cases in any jurisdiction |
| `search_cases_global` | Cross-jurisdiction search (default: US, GB, EU, JP, AU) |
| `search_cases_advanced` | Advanced search with filters for case type, subject area, court level, and outcome |
| `find_similar_cases` | Find similar cases from a text description of facts or legal issues |
| `get_case_detail` | Retrieve full text and metadata for a specific case |
| `tool_search_case_law` | Search case law by jurisdiction, topic, keywords, and year range |
| `search_statutes_v2` | Search statute texts with full-text matching |
| `tool_search_statute` | Search statutes by jurisdiction, law name, article, or keywords |

### 📊 Analysis

| Tool | Description |
|------|-------------|
| `analyze_legal_trend` | Analyze case law trends in a legal area over time |
| `compare_jurisdictions` | Compare how different jurisdictions handle the same legal topic |
| `tool_estimate_legal_risk` | Estimate legal risk for a described situation with factor-based scoring |
| `tool_analyze_party_performance` | Analyze litigation win/loss rates and patterns for an entity |
| `tool_generate_strategic_recommendations` | Generate priority-ranked strategic recommendations from analytics |
| `get_judge_stats` | Judge analytics: case volume, topics, outcomes, sentencing patterns |
| `get_case_importance` | Calculate importance score based on citation network |
| `get_classification_stats` | Statistics on case types, subject areas, and outcomes |
| `get_caselaw_db_stats` | Database-wide statistics (total cases, jurisdictions, date ranges) |

### 🔗 Citations

| Tool | Description |
|------|-------------|
| `check_citation` | Check if a case is still good law (traffic-light: green/yellow/red) |
| `tool_get_citing_cases` | Get cases that cite a given case, with treatment analysis |
| `tool_get_cited_cases` | Get all cases cited by a given case |
| `tool_extract_citations` | Extract legal citations from text (supports 12 jurisdictions) |
| `get_citation_network` | Build citation graph with depth traversal (NetworkX-powered) |

### 🏛️ IP & Disputes

| Tool | Description |
|------|-------------|
| `tool_search_ip_stats` | Search IP statistics (patent applications, grants, filings) |
| `tool_ip_dispute_search` | Search IP disputes globally (UDRP, Section 337, EPO, PTAB) |
| `tool_ip_enforcement_profile` | IP enforcement profile (Special 301 + seizures + Notorious Markets) |
| `tool_ip_dispute_forum_comparison` | Compare forum volumes: UDRP vs Section 337 vs EPO vs PTAB |
| `tool_ip_list_dispute_indicators` | List all available IP dispute and enforcement indicators |
| `search_ip_disputes` | Search IP disputes by type, jurisdiction, and keywords |
| `assess_forum_and_risk` | Assess optimal forum and risk for cross-border IP enforcement |
| `get_ip_dispute_profile` | Build multi-source IP dispute profile for target entities |

### 🏢 Entities & Events

| Tool | Description |
|------|-------------|
| `ip_entity_resolve` | Resolve company/org name to canonical form with aliases |
| `ip_entity_profile` | Cross-source IP activity profile for an organization |
| `ip_entity_search` | Search entity registry by name, country, type, or industry |
| `ip_events_detect` | Detect significant changes in IP statistics (threshold-based) |
| `ip_events_snapshot` | Take a snapshot of current IP stats for change detection |
| `ip_events_history` | View historical IP events and detected changes |

### 📝 Documents & Metadata

| Tool | Description |
|------|-------------|
| `tool_generate_legal_draft` | Generate legal drafts (takedown notices, cease & desist, opinions) |
| `extract_case_metadata` | Extract structured metadata from unstructured case text |
| `case_metadata_schema` | Return the empty case metadata JSON schema template |

---

## 🌍 Data Coverage

### Top 20 Jurisdictions by Case Count

| # | Jurisdiction | Cases | # | Jurisdiction | Cases |
|--:|:-------------|------:|--:|:-------------|------:|
| 1 | 🇨🇳 China | 45,500,000 | 11 | 🇦🇺 Australia | 491,000 |
| 2 | 🇺🇸 United States | 30,600,000 | 12 | 🇵🇱 Poland | 438,000 |
| 3 | 🇧🇷 Brazil | 1,800,000 | 13 | 🇨🇦 Canada | 405,000 |
| 4 | 🇫🇷 France | 1,200,000 | 14 | 🇳🇱 Netherlands | 340,000 |
| 5 | 🇨🇭 Switzerland | 1,100,000 | 15 | 🇩🇪 Germany | 251,000 |
| 6 | 🇹🇷 Turkey | 714,000 | 16 | 🇨🇿 Czech Republic | 238,000 |
| 7 | 🇰🇷 South Korea | 513,000 | 17 | 🇪🇺 EU Courts | 188,000 |
| 8 | 🇦🇷 Argentina | 496,000 | 18 | 🇬🇧 United Kingdom | 175,000 |
| 9 | 🇮🇳 India | 122,000 | 19 | 🇹🇼 Taiwan | 77,000 |
| 10 | 🇯🇵 Japan | 92,000 | 20 | 🇨🇴 Colombia | 24,000 |

*...plus 70 more jurisdictions across every continent.*

### Data Source Coverage

Data is aggregated from open legal databases worldwide, including:

- **Free Law Project / CourtListener** — US federal and state courts
- **CommonLII / AustLII / NZLII** — Australia, New Zealand, Pacific
- **CanLII** — Canada
- **EUR-Lex / HUDOC** — EU institutions and ECHR
- **e-Gov / Courts.go.jp** — Japan
- **Indian Kanoon** — India
- **Government Gazettes** — Various jurisdictions
- **AfricanLII** — Pan-African legal information

---

## 🏗️ Architecture

```
Claude / AI Agent
       │
       │  MCP (StreamableHTTP)
       ▼
┌──────────────────────┐
│   FastMCP Server     │  Python 3.13
│   (server.py)        │  39 registered tools
├──────────────────────┤
│   SQLite + FTS5      │  85.7M cases, WAL mode
│   (caselaw.db)       │  BM25 ranking
├──────────────────────┤
│   Citation Graph     │  245M+ edges
│   (NetworkX)         │  Depth-traversal queries
├──────────────────────┤
│   98 API Adapters    │  External legal databases
│   (tools/adapters/)  │  Statute APIs, IP offices
└──────────────────────┘
       │
       │  Cloudflare Tunnel
       ▼
  Public endpoint
  caselaw.patent-space.dev/mcp
```

**Key design decisions:**

- **SQLite + FTS5** for full-text search with BM25 ranking over 85.7M cases
- **WAL mode** with `busy_timeout=30000` for concurrent read access
- **FastMCP** for MCP protocol compliance with StreamableHTTP transport
- **Docker** container with 4 GB memory limit, health-checked
- **Cloudflare Tunnel** for secure public exposure without open ports
- **Graceful degradation** — external API failures fall back to local cache

---

## 🔌 API Reference

| Property | Value |
|----------|-------|
| **Endpoint** | `https://caselaw.patent-space.dev/mcp` |
| **Transport** | StreamableHTTP |
| **Protocol** | Model Context Protocol (MCP) |
| **Port** (self-hosted) | `8006` |
| **Health check** | TCP connection to `/mcp` |

### Example: Connect with any MCP client

```python
from fastmcp import Client

async with Client("https://caselaw.patent-space.dev/mcp") as client:
    result = await client.call_tool("search_cases", {
        "query": "fair use transformative",
        "jurisdiction": "US",
        "max_results": 5
    })
    print(result)
```

---

## 📦 Self-Hosting

### Requirements

- Docker and Docker Compose
- SQLite database with the caselaw schema
- Sufficient disk space for the SQLite database

### Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `0.0.0.0` | Server bind address |
| `MCP_PORT` | `8006` | Server port |

### Database Schema

The server expects a SQLite database with at minimum:

- `cases` table with `case_name`, `full_text`, `date_decided`, `court`, `jurisdiction` columns
- `cases_fts` FTS5 virtual table over `case_name` and `full_text`
- `citations` table for citation network queries

---

## 📄 License

This project's source code is released under the **MIT License**.

**Data sources** are subject to their own licenses and terms of use. Case law text is generally in the public domain in most jurisdictions, but specific database compilations may have their own terms. Please consult individual data providers for licensing details.

---

## 🙏 Credits

Built by **[Rei Kumaki](https://github.com/Rei02061986)** and **[Claude](https://claude.ai)** (Anthropic).

Powered by open legal data from [Free Law Project](https://free.law), [CommonLII](https://www.commonlii.org), [EUR-Lex](https://eur-lex.europa.eu), [e-Gov](https://laws.e-gov.go.jp), and many more.

---

<p align="center">
  <sub>⚖️ This is a legal research tool. It does not provide legal advice. All results should be verified by qualified legal professionals.</sub>
</p>
