# Solution Architecture — Multi-Agent System

## Architecture Decision Context

**Key constraints that drive architecture choices:**

1. **No Clearwater API** — Data ingestion is manual Excel upload (user downloads from Clearwater portal, uploads to our system)
2. **SEC compliance** — Full audit trail required. Every generated artifact must be traceable to source data. Every AI invocation must be logged.
3. **Data sensitivity** — Client portfolio data must not leave controlled infrastructure. No third-party AI training exposure.
4. **Low volume, high value** — ~200-400 decks/year. Accuracy and quality matter more than throughput.
5. **Human-in-the-loop** — Generated decks are drafts requiring analyst review/approval.
6. **Client is Azure-native** — Performa runs Microsoft 365 / Azure. Solution is cloud-agnostic — can deploy on Azure, AWS, GCP, or on-premise.

---

## Why Multi-Agent

A traditional pipeline (workflow engine + serverless functions) treats deck generation as a deterministic ETL job. The problem is messier than that:

- Clearwater exports are inconsistent — two analysts use different export methods, formatting varies, sometimes PDF-to-Excel is the only option. Rigid parsers break.
- Compliance rules are combinatorial — IPS constraints vary per client, domicile regulations differ by jurisdiction (Vermont RRG vs Bermuda captive vs SC captive), NAIC rating limits interact with allocation rules. Rule engines get brittle fast.
- Deck assembly involves judgment — which sections to include, how to handle missing data, what to flag for analyst attention, how to paginate holdings.
- The roadmap expands — Phase 2 adds commentary generation, anomaly explanation, reconciliation. Agent architecture absorbs this naturally.

**Agents provide reasoning. Tools provide precision.** Each agent calls deterministic tools (openpyxl, python-pptx, database queries) for the mechanical work, but uses LLM reasoning for edge cases, validation logic, and orchestration decisions.

---

## Three Data Sources

The system has three distinct data sources, each owned by a different agent:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCES                                 │
│                                                                         │
│  ┌─────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐ │
│  │ Clearwater Analytics │ │ IPS Parameters   │ │ Market Context       │ │
│  │                      │ │                  │ │                      │ │
│  │ Portfolio data:      │ │ Per-client       │ │ Source TBD.          │ │
│  │ - Board Reports      │ │ constraints:     │ │ Candidate sources:   │ │
│  │   (AGG performance,  │ │ - Target alloc.  │ │ - Bloomberg API/feed │ │
│  │   MV history,        │ │ - Allowed ranges │ │ - FRED (Fed data)    │ │
│  │   contributions,     │ │ - Benchmark def. │ │ - Market data vendor │ │
│  │   allocation)        │ │ - Domicile rules │ │ - Manually uploaded  │ │
│  │ - SMA Holdings       │ │ - Entity type    │ │   quarterly brief    │ │
│  │   (per-bond detail)  │ │ - NAIC limits    │ │ - Performa's own     │ │
│  │                      │ │                  │ │   published content  │ │
│  │ Ingestion: Manual    │ │ Ingestion:       │ │   (Market Updates,   │ │
│  │ Excel upload (no API)│ │ Database config   │ │   Fed Dashboard)    │ │
│  │                      │ │ (pre-loaded)     │ │                      │ │
│  │ Owner: Portfolio     │ │ Owner: Compliance│ │ Owner: Market Data   │ │
│  │        Agent         │ │        Agent     │ │        Agent         │ │
│  └──────────┬──────────┘ └────────┬─────────┘ └──────────┬───────────┘ │
│             │                     │                       │             │
└─────────────┼─────────────────────┼───────────────────────┼─────────────┘
              │                     │                       │
              ▼                     ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ANALYST PROMPT (4th input — human intent)                              │
│                                                                         │
│  Free-text instructions from the analyst that shape generation:         │
│  - Deck type & visual preferences ("use bar charts not pie charts")    │
│  - Emphasis & narrative tone ("highlight the equity outperformance")   │
│  - Section customization ("skip ETF overviews, add cash flow page")   │
│  - Client-specific context ("board meeting — keep it high-level")     │
│  - Override defaults ("use the Q2 market update, not Q3")             │
│                                                                         │
│  Flows to: Orchestrator → all downstream agents as generation context  │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
              ┌────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI GENERATION LAYER                              │
│                  (Strands Agents — Containerized)                       │
└─────────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     ADVISOR REVIEW & REFINEMENT                         │
│                     (Web App — Human-in-the-loop)                       │
│                                                                         │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────────────┐   │
│  │ Review   │──▶│ Approve  │──▶│ Approved │──▶│ Client-Ready    │   │
│  │ Draft    │   └──────────┘   └──────────┘   │ Deck (.pptx)    │   │
│  │          │                                  └─────────────────┘   │
│  │          │    ┌──────────────────┐                                │
│  │          │──▶│ Request Changes  │──┐                              │
│  │          │   │ (feedback prompt) │  │                              │
│  └─────────┘   └──────────────────┘  │                              │
│       ▲                               │  feedback loop               │
│       │                               │                              │
│       └───────────────────────────────┘                              │
│               Refined deck returned                                   │
│               for re-review                                           │
└─────────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DATA SOURCE INGESTION                                                  │
│                                                                         │
│  ┌────────────────┐  ┌────────────────────┐  ┌──────────────────────┐  │
│  │ Clearwater      │  │ IPS Parameters     │  │ Market Context       │  │
│  │ Excel Upload    │  │ (Document Database)│  │ (Source TBD)         │  │
│  │ ┌────────────┐ │  │ ┌────────────────┐ │  │ ┌──────────────────┐ │  │
│  │ │Board Report│ │  │ │ client-config   │ │  │ │ market-context/  │ │  │
│  │ │(.xlsx)     │ │  │ │ compliance-rules│ │  │ │ {quarter}.json   │ │  │
│  │ └────────────┘ │  │ └────────────────┘ │  │ │                  │ │  │
│  │ ┌────────────┐ │  │                    │  │ │ Uploaded brief,  │ │  │
│  │ │SMA Holdings│ │  │                    │  │ │ API feed, or     │ │  │
│  │ │(.xlsx)     │ │  │                    │  │ │ scraped content  │ │  │
│  │ └────────────┘ │  │                    │  │ └──────────────────┘ │  │
│  └───────┬────────┘  └─────────┬──────────┘  └──────────┬───────────┘  │
│          │                     │                         │              │
└──────────┼─────────────────────┼─────────────────────────┼──────────────┘
           │                     │                         │
           ▼                     ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  Web Application (React / Next.js)                                     │
│  Upload Excel + Market Context → Configure → Generate → Review          │
│                                                                         │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │ HTTPS
                    ┌──────────────▼──────────────┐
                    │  API Gateway                    │
                    │  + CDN                          │
                    │  + Identity Provider (Auth)     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│                    ORCHESTRATOR AGENT                                   │
│                    (Strands Agents — Containerized)                     │
│                                                                        │
│    Receives: client_id, report_period, uploaded files                  │
│              (Clearwater Excel + Market Context)                        │
│    Decides:  which agents to invoke, in what order, with what params  │
│    Returns:  generated .pptx URL + compliance report + audit record   │
│                                                                        │
│    ┌─────────────────────────────────────────────────────────────┐     │
│    │                    Orchestration Logic                       │     │
│    │                                                              │     │
│    │  1. Resolve client config (type, strategies, IPS, domicile) │     │
│    │  2. Dispatch to specialist agents (parallel where possible) │     │
│    │     - Market Data Agent ← market context source             │     │
│    │     - Portfolio Agent   ← Clearwater Excel files            │     │
│    │     (these two run in PARALLEL — no dependency)             │     │
│    │  3. Collect and merge agent outputs                         │     │
│    │  4. Hand off merged data to Deck Builder                    │     │
│    │  5. Run Compliance Agent on final deck                      │     │
│    │     ← IPS params + domicile rules from database              │     │
│    │  6. Store artifacts + audit trail                           │     │
│    │  7. Notify analyst                                          │     │
│    └─────────────────────────────────────────────────────────────┘     │
│                                                                        │
│    ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐       │
│    │  Market   │  │Portfolio │  │Compliance │  │ Deck Builder │       │
│    │  Data     │  │  Agent   │  │  Agent    │  │    Agent     │       │
│    │  Agent    │  │          │  │           │  │              │       │
│    └────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘       │
│         │             │              │                │               │
└─────────┼─────────────┼──────────────┼────────────────┼───────────────┘
          │             │              │                │
          ▼             ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          TOOL LAYER                                     │
│                                                                         │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────┐ ┌──────────────┐   │
│  │ Object Store │ │ Excel Parser  │ │ Document   │ │ PPTX Builder │   │
│  │ Read/Write   │ │ (openpyxl)    │ │ DB R/W     │ │ (python-pptx)│   │
│  └──────────────┘ └───────────────┘ └────────────┘ └──────────────┘   │
│                                                                         │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────┐ ┌──────────────┐   │
│  │ Chart Builder│ │ Data Hasher   │ │ Notify Svc │ │ Audit Logger │   │
│  │ (matplotlib/ │ │ (SHA-256)     │ │            │ │              │   │
│  │  pptx charts)│ │               │ │            │ │              │   │
│  └──────────────┘ └───────────────┘ └────────────┘ └──────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────┐                  │
│  │ Market Context Adapter (pluggable — source TBD)  │                  │
│  │ - fetch_market_context(quarter, source_type)      │                  │
│  │ - parse_market_brief(file_path)                   │                  │
│  │ - get_macro_indicators(date_range)                │                  │
│  └──────────────────────────────────────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
          │             │              │                │
          ▼             ▼              ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       DATA & STORAGE LAYER                              │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │  Object Storage   │  │ Document Database │  │  LLM Provider      │   │
│  │                   │  │                   │  │                    │   │
│  │  /uploads/        │  │  client-config    │  │  Claude (Anthropic)│   │
│  │  /templates/      │  │  generation-log   │  │  via private       │   │
│  │  /market-context/ │  │  compliance-rules │  │  endpoint           │   │
│  │  /generated/      │  │                   │  │  No data leaves    │   │
│  │  /audit/          │  │                   │  │  controlled infra  │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY & SECURITY                          │
│                                                                         │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐                │
│  │ Observability │  │ Audit Logging │  │ Private       │                │
│  │ (OTel)        │  │               │  │ Network       │                │
│  │  Agent traces │  │  API-level    │  │  Private nets │                │
│  │  Tool calls   │  │  audit trail  │  │  Private      │                │
│  │  LLM logs     │  │  SEC-ready    │  │  endpoints    │                │
│  │  Latency/errs │  │               │  │  No egress    │                │
│  └──────────────┘  └───────────────┘  └──────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Specifications

### 1. Orchestrator Agent

**Runtime:** Containerized (Docker/Kubernetes)
**Framework:** Agent Strands (Python SDK)
**Model:** Claude Sonnet via LLM Provider (fast, cost-effective for coordination)

**Responsibility:** Receive generation and refinement requests, plan execution, coordinate specialist agents, handle errors. Operates in two modes: **initial generation** and **refinement**.

**System prompt context:**
- Knows client types (AGG, SMA, AGG+SMA) and which agents each type requires
- Knows the three data sources and which agent owns each
- Knows the execution graph and parallelization rules
- Interprets the analyst prompt to determine section overrides, visual preferences, and emphasis
- In refinement mode: analyzes feedback to determine minimum agent re-invocation scope
- Handles partial failures (e.g., if Market Data Agent fails, can still generate deck using last quarter's cached market context from object storage)

**Execution flow — Initial Generation:**

```
GenerationRequest received (client_id, period, files[], analyst_prompt)
│
├─▶ Tool: read_client_config(client_id)
│   Returns: client_type, strategies, IPS, domicile, sections[]
│
├─▶ Decision: Interpret analyst_prompt + overrides
│   - Merge section preferences (prompt overrides > explicit overrides > client defaults)
│   - Extract visual preferences, emphasis, and context for downstream agents
│   - Determine which agents need the analyst prompt context
│
├─▶ Decision: Plan agent dispatch based on client_type
│   AGG-only:     Portfolio Agent + Market Data Agent (parallel)
│   SMA-only:     Portfolio Agent + Market Data Agent (parallel)
│   AGG+SMA:      Portfolio Agent (both datasets) + Market Data Agent (parallel)
│
├─▶ Dispatch: Market Data Agent ──────────────────────────┐
│             (receives: market context source +            │
│              relevant analyst prompt context)             │
│                                                           │
├─▶ Dispatch: Portfolio Agent ─────────────────────────┐   │
│             (receives: Clearwater Excel files +       │   │
│              relevant analyst prompt context)          │   │
│                                                       ▼   ▼
├─▶ Collect: Merge agent outputs ◀──── market_context + portfolio_data
│
├─▶ Dispatch: Deck Builder Agent
│             (receives: portfolio_data + market_context + client config
│              + analyst prompt for visual/layout/emphasis instructions)
│             Returns: draft .pptx storage key
│
├─▶ Dispatch: Compliance Agent
│             (receives: draft deck + IPS params + domicile rules
│              + any compliance-specific analyst context)
│             Returns: compliance report (pass/warn/fail[])
│
├─▶ Decision: If compliance.status == "fail"
│   ├─▶ Flag for analyst with compliance failures
│   └─▶ Still store the deck (analyst may override)
│
├─▶ Tool: store_audit_record(...)
├─▶ Tool: notify_analyst(...)
│
└─▶ Return: { deck_url, compliance_report, warnings[] }
```

**Execution flow — Refinement:**

```
RefinementRequest received (gen_id, refinement_prompt, structured_feedback)
│
├─▶ Tool: load_previous_generation(gen_id)
│   Returns: previous deck, agent outputs, original prompt, client config
│
├─▶ Decision: Analyze feedback scope
│   For each piece of feedback, determine:
│   - Which slides are affected?
│   - Which agent(s) own those slides?
│   - Is source data affected, or only presentation?
│
│   Scope classification:
│   VISUAL_ONLY      → Deck Builder only (chart type, spacing, colors)
│   CONTENT_REORDER  → Market Data or Portfolio + Deck Builder
│   DATA_CORRECTION  → Portfolio Agent re-parse (requires new Excel upload)
│   SECTION_CHANGE   → Orchestrator re-plans + Deck Builder
│   COMPLIANCE_FLAG  → Compliance Agent re-check
│
├─▶ Dispatch: ONLY agents in scope (skip unchanged agents)
│             Each receives: previous output + targeted feedback
│             Each returns: delta (only modified outputs)
│
├─▶ Dispatch: Deck Builder Agent (always runs in refinement)
│             Rebuilds ONLY flagged slides
│             Preserves untouched slides from previous version
│
├─▶ Dispatch: Compliance Agent (always re-checks modified slides)
│
├─▶ Tool: store_as_new_version(parent_gen_id, ...)
├─▶ Tool: notify_analyst("Refinement ready for re-review")
│
└─▶ Return: { deck_url, version_diff, compliance_report }
```

**Key design choices:**
- The Orchestrator does NOT do any data processing itself. It only plans, dispatches, and merges.
- In refinement mode, it minimizes work — only re-invoking agents whose output needs to change.
- The analyst prompt and refinement feedback are treated as first-class inputs, not afterthoughts.

**Batch mode:** For quarter-end (100+ clients), the Orchestrator fans out parallel sub-orchestrations, one per client. Kubernetes handles the concurrency and queuing. Batch mode uses default prompts (or a shared batch prompt) — per-client refinement happens after batch generation.

---

### 2. Portfolio Agent

**Runtime:** Containerized (Docker/Kubernetes)
**Framework:** Agent Strands
**Model:** Claude Sonnet via LLM Provider

**Why this needs to be an agent (not just a parser):**
- Clearwater exports come in inconsistent formats — some users export Excel directly, others export PDF then convert to Excel, column layouts can shift
- The agent can reason about the data structure it sees rather than assuming a fixed schema
- When data is ambiguous or missing, the agent can flag it with context ("Market value for ANGL ETF is missing — this holding may have been recently sold") rather than silently failing

**Tools available:**

| Tool | Purpose |
|------|---------|
| `parse_excel(file_path, sheet_name)` | Read Excel with openpyxl, return raw cell data |
| `read_file(bucket, key)` | Download uploaded file from object storage |
| `write_json(bucket, key, data)` | Write parsed output to object storage |
| `read_client_config(client_id)` | Get expected strategies, benchmarks from document database |
| `hash_file(file_path)` | SHA-256 hash for audit trail |

**Input:** Raw Clearwater Excel files (Board Report and/or SMA Holdings)
**Output:** Normalized portfolio data as structured JSON:

```json
{
  "client_id": "CAPE-21",
  "report_period": "2024-12-01/2025-11-30",
  "as_of_date": "2025-11-30",
  "source_files_hash": "sha256:...",

  "performance": {
    "net": {
      "qtd": 0.0143, "ytd": 0.0973, "trailing_1yr": 0.0834,
      "trailing_3yr": 0.0752, "trailing_5yr": 0.0385,
      "trailing_10yr": null, "since_inception": 0.0436
    },
    "index": {
      "qtd": 0.0134, "ytd": 0.1023, "trailing_1yr": 0.0900,
      "trailing_3yr": 0.0851, "trailing_5yr": 0.0415,
      "trailing_10yr": null, "since_inception": 0.0504
    }
  },

  "market_value_history": [
    {"date": "2024-12-31", "value": 35257835.27},
    {"date": "2025-01-31", "value": 35643265.47}
  ],

  "allocation": [
    {
      "strategy": "CASH & INVESTMENT GRADE BONDS",
      "market_value": 56366317,
      "actual_pct": 0.646,
      "target_pct": 0.65,
      "target_range": [0.55, 0.80],
      "sub_strategies": []
    }
  ],

  "contribution_by_strategy": [
    {"strategy": "FI SMA", "contribution": 0.0440},
    {"strategy": "ISHARES RUSSELL 2000 VALUE ETF", "contribution": 0.0023}
  ],

  "rollforward": {
    "beginning_mv": 99743733,
    "net_transfers": 62850000,
    "income": 5477205,
    "expenses": -27828,
    "net_realized_gl": -19331,
    "change_unrealized_gl": 7620073,
    "ending_mv": 175643852
  },

  "sma_holdings": [
    {
      "issuer": "MCCT 231 A",
      "sector": "ABS",
      "sector_category": "Structured Products",
      "duration": 0.063,
      "yield": 0.042,
      "sp_rating": "NA",
      "moodys_rating": "Aaa",
      "maturity": "2027-06-21",
      "market_value": 100164.32,
      "pct_of_portfolio": 0.0035
    }
  ],

  "sma_summary": {
    "total_market_value": 28298389.50,
    "avg_credit_quality": "AA",
    "yield_to_maturity": 0.0396,
    "avg_duration": 3.75,
    "num_holdings": 112,
    "sector_allocation": {"U.S. Treasury": 0.598, "Corporate Credit": 0.337},
    "credit_quality_allocation": {"AAA": 0.041, "AA": 0.677, "A": 0.190}
  },

  "warnings": [],
  "parsing_notes": []
}
```

**Agent reasoning examples:**
- "Board Report has 79 columns but only ~30 contain data — the rest are spacer columns from Clearwater's export format. Skipping empty columns."
- "SMA Holdings sheet name is 'SMA Holdings (JJ)' — extracting client identifier 'JJ' from sheet name as cross-reference."
- "'Trailing 10 Years' shows '---' — client inception date is 2019-07-01, so 10-year history is unavailable. Setting to null."
- "Return value 0.097 detected — this is a raw decimal. Converting to 9.7% for display but keeping raw value for calculations."

---

### 3. Market Data Agent

**Runtime:** Containerized (Docker/Kubernetes)
**Framework:** Agent Strands
**Model:** Claude Sonnet via LLM Provider

**This agent owns the "Market Context" data source** — the third pillar alongside Clearwater Analytics and IPS Parameters. Market context feeds into both the static market update slides (Section 1) and, critically, into the AI Generation Layer for drafting client-contextualized content.

#### Market Context — Source Definition

The exact source for market context is **TBD** (to be determined during Discovery). The agent is designed with a pluggable adapter pattern so the source can be swapped without changing agent logic.

**Candidate sources (to be evaluated during Discovery):**

| Source | What it provides | Ingestion method | Feasibility |
|--------|-----------------|------------------|-------------|
| **Manual upload** (quarterly brief) | Performa's own market commentary as a Word/PDF document | File upload via web app, stored in object storage | Simplest. Mirrors current process. |
| **Performa published content** | Their Quarterly Market Updates, Market Perspectives, Fed Translation Dashboard (already authored internally) | Scrape from performa.com or upload | Low effort — content already exists |
| **Bloomberg Terminal / Data License** | Benchmark returns, yield curves, credit spreads, economic indicators | Bloomberg API (B-PIPE or Data License) or manual export | Performa already has Bloomberg — check license terms |
| **FRED (Federal Reserve Economic Data)** | Fed funds rate, Treasury yields, inflation data, employment data | Free REST API (api.stlouisfed.org) | Free, reliable, covers macro slides |
| **Market data vendor** (e.g., Refinitiv, FactSet) | Broad market data, index returns, sector performance | API integration | Higher cost, more data than needed |
| **News/FOMC feeds** | FOMC statements, meeting minutes, press conference transcripts | Fed website scrape or structured feed | Feeds the "Fed Translation Dashboard" content |

**Phase 1 approach (recommended):** Dual-input model —
1. **Structured data** from a free/existing source (FRED API or Bloomberg export) for chart data points (yields, spreads, index levels)
2. **Narrative content** from manual upload — Performa uploads their quarterly market brief (they already write this) as a Word doc or structured text

This mirrors the current process (humans write the market commentary) while adding structured data for charts that today are manually built.

#### Tools available

| Tool | Purpose |
|------|---------|
| `read_file(bucket, key)` | Fetch uploaded market context file from object storage |
| `parse_market_brief(file_path)` | Extract structured sections from Performa's market commentary doc (headings, bullet points, key figures) |
| `fetch_market_context(quarter, source_type)` | Pluggable adapter — fetch market data from configured source (file upload, API, etc.) |
| `get_macro_indicators(date_range)` | Pull key macro data points: Fed funds rate, 10Y Treasury yield, S&P 500 return, credit spreads, unemployment rate |
| `get_index_returns(index_ids[], period)` | Retrieve benchmark index returns for the reporting period |
| `list_templates(prefix)` | List available market update slide templates |
| `write_json(bucket, key, data)` | Store processed market context output |

#### Input

The Market Data Agent accepts **one or both** of:

1. **Uploaded market context file** (storage key) — Performa's authored quarterly brief
   - Could be .docx, .pdf, or structured .json
   - Contains: narrative commentary, key themes, "Where We Are" summary, "Things to Watch" outlook
2. **Structured market data** (fetched via adapter tool) — numerical data points
   - Index returns for the period (S&P 500, Bloomberg IG, HY indices, etc.)
   - Yield curve data (3M, 2Y, 5Y, 10Y Treasury)
   - Credit spreads (IG OAS, HY OAS)
   - Fed funds rate / latest FOMC decision
   - Employment data (NFP, unemployment rate, initial claims)

#### Output

```json
{
  "quarter": "Q3-2025",
  "as_of_date": "2025-09-30",
  "source_type": "manual_upload+fred_api",
  "source_hash": "sha256:...",

  "narrative": {
    "summary_title": "2025 HAS BEEN A WILD RIDE, ONE QUARTER TO GO",
    "where_we_are": [
      "Uncertainty has weighed on economic activity",
      "After the initial tariff-related volatility, markets have performed quite well YTD",
      "Job creation has slowed but firings are historically low"
    ],
    "things_to_watch": [
      "The impact of tariffs on inflation",
      "Oil prices",
      "Labor market data remains key",
      "Evidence of slowing U.S. consumer demand",
      "Delinquency rates for signs of consumer stress"
    ],
    "commentary_sections": [
      {
        "title": "ELEVATED VOLATILITY DURING FIRST HALF, BUT GOOD MARKET OUTCOMES SINCE",
        "body": "..."
      },
      {
        "title": "FED EASED 25 BPS IN SEPT & OCT",
        "body": "..."
      }
    ]
  },

  "structured_data": {
    "equity_returns": { "sp500_ytd": 0.182, "sp500_qtd": 0.054 },
    "fixed_income": { "treasury_3m_yield": 0.0435, "treasury_10y_yield": 0.0382, "ig_oas": 70, "hy_oas": 320 },
    "economic": { "fed_funds_rate": 0.0475, "unemployment_rate": 0.042, "nfp_3mo_avg": 29000, "cpi_yoy": 0.027 }
  },

  "market_update_template_key": "performa-deck-gen/templates/market-update/Q3-2025.pptx",
  "template_is_current": true,

  "warnings": [],
  "notes": ["Narrative sourced from uploaded brief. Structured data from FRED API."]
}
```

#### How Market Context flows through the system

```
Market Context Source(s)
        │
        ▼
┌──────────────────┐
│ Market Data Agent │
│                   │
│ 1. Ingest market  │──▶ narrative sections → Deck Builder (Slides 4-9 content)
│    brief + data   │──▶ structured data    → Deck Builder (chart data points)
│ 2. Parse/structure│──▶ template key       → Deck Builder (which template to use)
│ 3. Validate       │──▶ market context     → Compliance Agent (is commentary
│    currency       │    JSON                  consistent with portfolio reality?)
│ 4. Output JSON    │
└──────────────────┘
```

**Key insight:** Market context is NOT just "pick a template." It feeds downstream:
- **Deck Builder** uses the narrative for slide content and structured data for charts
- **Compliance Agent** can cross-reference market commentary against portfolio reality (e.g., if commentary says "we reduced equity exposure" but allocation shows equity increased, flag it)
- In **batch mode**, Market Data Agent runs ONCE and its output is shared across all client deck generations for that quarter

#### Phase 2+ expansion

As the market context source matures, this agent absorbs:
- **Auto-generated commentary:** Given structured market data + Performa's historical commentary style, draft new quarter's commentary for human review
- **Fed Translation Dashboard automation:** Ingest FOMC statements and generate the "what this means for captives" briefing
- **Client-specific market context:** "Given this client's 65% fixed income allocation, the rate cut is particularly relevant because..."
- **Chart data refresh:** Automatically pull updated data for the market update charts instead of relying on manually-built slides

---

### 4. Compliance Agent

**Runtime:** Containerized (Docker/Kubernetes)
**Framework:** Agent Strands
**Model:** Claude Sonnet via LLM Provider (may upgrade to Opus for complex reasoning on rule interactions)

**This is the highest-value agent in the system.** Compliance checking for captive insurance portfolios is combinatorial and context-dependent — exactly where LLM reasoning outperforms a rule engine.

**Responsibility:**
- Validate the generated portfolio data against the client's IPS (Investment Policy Statement) constraints
- Check domicile-specific regulatory limits (Vermont RRG rules, Bermuda rules, etc.)
- Verify NAIC rating category limits
- Flag allocation drift (actual vs target exceeds tolerance)
- Validate that the deck itself contains required disclosures
- Generate a compliance report with pass/warn/fail per check

**Tools available:**

| Tool | Purpose |
|------|---------|
| `read_client_config(client_id)` | IPS constraints, domicile, entity type |
| `read_compliance_rules(domicile, entity_type)` | Regulatory limits from document database |
| `read_portfolio_data(storage_key)` | Parsed portfolio JSON from Portfolio Agent |
| `read_pptx_text(storage_key)` | Extract all text from generated deck for disclosure checks |

**Compliance rules (from sample data — Vermont RRG example):**

```yaml
vermont_rrg:
  ig_fixed_income_and_cash:
    max_pct: 1.00        # NAIC 1 or 2 — up to 100%
    per_issuer_max: 0.10  # 10% per issuer (except mutual funds & NAIC-approved ETFs)
  below_ig_bonds:
    max_pct: 0.20         # NAIC 3-6 combined — max 20%
    naic_4_to_6_max: 0.10 # NAIC 4-6 — max 10%
  equities:
    max_pct: 0.25         # Max 25% equities
  govt_obligations:
    per_issuer_max: 0.10
  govt_money_market:
    per_issuer_max: 0.10
```

**Agent reasoning examples:**
- "Client CAPE-21 is a Vermont RRG. Equity allocation is 25.5% which exceeds the 25% statutory limit. However, the overage is 0.5% and falls within normal market fluctuation. Flagging as WARNING, not FAIL — recommend rebalancing at next opportunity."
- "ANGL ETF (VanEck Fallen Angel) was downgraded from NAIC 3 to NAIC 4. Current NAIC 4-6 exposure including ANGL is 12.3%, exceeding the 10% limit. Flagging as FAIL — this is a compliance breach that requires action."
- "Performance disclosure on Slide 33 references index composition 'from 6/1/2025 to the present' — verified that this matches client's current benchmark assignment in config. PASS."
- "Portfolio roll forward shows ending MV of $175.6M but allocation table sums to $175.6M — values are consistent. PASS."

**Output:**
```json
{
  "client_id": "CAPE-21",
  "overall_status": "WARNING",
  "checks": [
    {
      "rule": "equity_allocation_limit",
      "status": "WARNING",
      "detail": "Equity allocation 25.5% exceeds 25% statutory limit by 0.5%",
      "recommendation": "Rebalance at next opportunity. Within normal market fluctuation."
    },
    {
      "rule": "naic_4_6_limit",
      "status": "FAIL",
      "detail": "NAIC 4-6 exposure is 12.3% (limit: 10%). ANGL ETF reclassified to NAIC 4.",
      "recommendation": "Position reduction required. Proposal on Slide 11 to sell ANGL and redistribute."
    },
    {
      "rule": "disclosure_completeness",
      "status": "PASS",
      "detail": "All required disclosures present on Slides 33-34."
    },
    {
      "rule": "data_consistency",
      "status": "PASS",
      "detail": "Allocation table totals match roll forward ending MV."
    }
  ],
  "notes": ["Compliance check ran against Vermont RRG rules (8 V.S.A. Chapter 141, Section 6010)"]
}
```

---

### 5. Deck Builder Agent

**Runtime:** Containerized (Docker/Kubernetes)
**Framework:** Agent Strands
**Model:** Claude Sonnet via LLM Provider

**Responsibility:** Assemble the final .pptx from merged agent outputs. Receives **three inputs**: portfolio data (from Portfolio Agent), market context (from Market Data Agent), and client config (from document database). The agent makes decisions about layout and structure; its tools handle the mechanical PPTX generation.

**Tools available:**

| Tool | Purpose |
|------|---------|
| `clone_template(template_key)` | Copy master .pptx from object storage as starting point |
| `insert_market_slides(deck, market_context)` | Build market update slides from market context data (narrative + charts) |
| `build_market_chart(deck, chart_type, data_points)` | Create market charts (yield curves, equity returns, spreads) from structured market data |
| `build_allocation_slide(deck, allocation_data, chart_type)` | Create allocation table + pie chart |
| `build_performance_slide(deck, performance_data)` | Create performance comparison bar charts |
| `build_rollforward_slide(deck, rollforward_data)` | Create portfolio roll forward table |
| `build_sma_statistics_slide(deck, sma_summary)` | Create SMA stats tables + allocation pies |
| `build_sma_performance_slide(deck, perf_data)` | Create SMA performance tables + charts |
| `build_holdings_slides(deck, holdings[], per_page)` | Create paginated holdings tables |
| `build_cashflow_slide(deck, cashflow_data)` | Create cash flow projections table |
| `insert_static_section(deck, section_key)` | Insert ETF overviews, VT restrictions, disclaimers |
| `set_slide_metadata(deck, slide_idx, title, date)` | Set headers, footers, slide numbers |
| `write_pptx(deck, bucket, key)` | Save final deck to object storage |
| `parameterize_title_slide(deck, client_name, date, presenters[])` | Fill in title slide fields |

**Agent reasoning examples:**
- "Client is AGG+SMA type. Including sections: market update, allocation (AGG), performance (AGG), roll forward, SMA statistics, SMA performance, attribution, ETF overviews (has high yield + equity ETFs), VT restrictions (is a Vermont RRG), holdings, disclosures."
- "Client has 112 SMA holdings. At 25 holdings per slide, that's 5 slides. Grouping by sector: ABS first, then Financials, then Government, then Industrials, then Treasuries."
- "Cash flow data not provided in this upload. Skipping Slide 35 and noting in warnings."
- "Client has 3 presenters but title slide template has space for 2. Using multi-line text box format."

**Output:**
```json
{
  "deck_storage_key": "performa-deck-gen/generated/2025/CAPE-21/gen-20260315-001.pptx",
  "total_slides": 33,
  "sections_included": ["market_update", "allocation", "performance", "rollforward", "sma_detail", "etf_overviews", "vt_restrictions", "holdings", "disclosures"],
  "sections_skipped": ["cashflow"],
  "warnings": ["Cash flow data not provided — slide omitted"]
}
```

---

## Analyst Prompt — Human Intent as Input

The analyst prompt is effectively a **4th input** alongside the three data sources. It's the mechanism through which the human communicates intent, preferences, and context that can't be derived from data alone.

### What the Analyst Prompt Contains

The prompt is a free-text field in the web app's "Configure" screen. It can include any combination of:

| Category | Examples |
|----------|---------|
| **Deck type / audience** | "This is for a board meeting — keep it high-level, no individual holdings" |
| | "Annual review for a new board member — include extra context on our approach" |
| | "Quick mid-quarter check-in — just allocation and performance, skip market update" |
| **Visual preferences** | "Use bar charts instead of pie charts for allocation" |
| | "Make the performance chart full-width — they project this on a large screen" |
| | "Include the benchmark comparison table, not just the chart" |
| **Content emphasis** | "Highlight the equity outperformance this quarter" |
| | "Emphasize the duration positioning — David wants to discuss the yield curve trade" |
| | "They're concerned about high yield exposure — make sure NAIC rating breakdown is prominent" |
| **Section customization** | "Skip ETF overviews — they know these funds well" |
| | "Add a cash flow projection page" |
| | "Include the VT restrictions appendix — new board member needs to see it" |
| **Override defaults** | "Use the Q2 market update slides — Q3 not ready yet" |
| | "Show Warren Miller as sole presenter, not David" |
| | "Report through October only, not full quarter" |
| **Client-specific context** | "They just added $5M — mention the contribution in the rollforward narrative" |
| | "They're considering selling ANGL — flag the NAIC downgrade prominently" |

### How the Prompt Flows Through the System

The analyst prompt is **not consumed by a single agent** — it's passed as context to every agent that needs it:

```
Analyst Prompt
      │
      ├──▶ Orchestrator Agent
      │    Interprets high-level intent:
      │    - Which sections to include/skip (overrides client-config defaults)
      │    - Which agents to invoke
      │    - Whether this is a full generation or a targeted update
      │
      ├──▶ Market Data Agent
      │    (via Orchestrator)
      │    - Which market template/quarter to use
      │    - What market themes to emphasize
      │
      ├──▶ Portfolio Agent
      │    (via Orchestrator)
      │    - Date range overrides
      │    - Specific metrics to highlight or compute
      │
      ├──▶ Deck Builder Agent
      │    (via Orchestrator)
      │    - Visual preferences (chart types, layout)
      │    - Section ordering and inclusion
      │    - Content emphasis and tone
      │    - Presenter names override
      │
      └──▶ Compliance Agent
           (via Orchestrator)
           - Specific compliance concerns to check
           - Known issues to flag (e.g., "check the ANGL NAIC downgrade")
```

### Generation Request Schema

Every generation starts with a `GenerationRequest` object:

```json
{
  "client_id": "CAPE-21",
  "report_period": "2024-12-01/2025-11-30",
  "requested_by": "analyst@performa.com",

  "uploaded_files": {
    "clearwater_board_report": "performa-deck-gen/uploads/2026-03-15/upload-001/board-report.xlsx",
    "clearwater_sma_holdings": "performa-deck-gen/uploads/2026-03-15/upload-001/sma-holdings.xlsx",
    "market_context_brief": "performa-deck-gen/uploads/2026-03-15/upload-001/market-brief.docx"
  },

  "analyst_prompt": "Board meeting prep for CAPE-21. Highlight the equity outperformance this quarter. They're considering selling ANGL due to the NAIC downgrade — make sure the compliance impact is clearly shown on the allocation slide. Use bar charts for allocation, not pie. Skip ETF overviews — board knows these well. David and Warren presenting.",

  "overrides": {
    "presenters": ["DAVID KILBORN, CFA", "WARREN MILLER"],
    "sections_include": ["market_update", "allocation", "performance", "rollforward", "sma_detail", "holdings", "vt_restrictions", "disclosures"],
    "sections_exclude": ["etf_overviews"],
    "market_update_quarter": null
  }
}
```

### Prompt Presets

For common deck types, the UI offers saved presets that pre-fill the prompt and overrides:

| Preset | Pre-filled prompt | Sections |
|--------|------------------|----------|
| **Full Quarterly Review** | (default — all sections, standard format) | All |
| **Board Meeting** | "High-level board presentation. Allocation, performance, and compliance focus." | allocation, performance, rollforward, compliance summary |
| **Quick Check-in** | "Mid-quarter portfolio review. Just allocation and performance." | allocation, performance |
| **New Client Onboarding** | "First review for new client. Include full appendix with explanatory context." | All + extra context |
| **SMA Deep Dive** | "Focus on fixed income SMA detail. Full holdings and attribution." | sma_detail, sma_performance, attribution, holdings |

---

## Human-in-the-Loop — Review & Refinement Workflow

The system does NOT produce a final deck in one shot. Every generation enters a review loop where the analyst can approve, reject, or iteratively refine until satisfied.

### Workflow State Machine

```
┌─────────────┐
│  GENERATING  │ ← Agents are working (Orchestrator dispatching)
└──────┬──────┘
       │ generation complete
       ▼
┌─────────────┐     ┌─────────────────────────────────────────────────────┐
│  PENDING     │     │  Review Screen (Web App)                            │
│  REVIEW      │────▶│                                                     │
└─────────────┘     │  Deck Preview + Generation Summary + Compliance     │
                     │  Report + Data Comparison                           │
                     └──────────┬──────────────────────────────────────────┘
                                │
                 ┌──────────────┼──────────────┐
                 ▼              ▼              ▼
          ┌──────────┐  ┌─────────────┐  ┌──────────┐
          │ APPROVE  │  │  REQUEST    │  │ REJECT   │
          └────┬─────┘  │  CHANGES    │  └────┬─────┘
               │        └──────┬──────┘       │
               ▼               ▼              ▼
        ┌──────────┐  ┌──────────────┐  ┌──────────┐
        │ APPROVED │  │ REFINING     │  │ REJECTED │
        │ (locked) │  │ (surgical    │  │ (logged) │
        └──────────┘  │  rebuild)    │  └──────────┘
                      └──────┬───────┘
                             │ refined deck ready
                             ▼
                      ┌─────────────┐
                      │  PENDING     │ ← back to review
                      │  REVIEW      │   (new version)
                      └─────────────┘
```

### Refinement Design

Refinement is **surgical, not full regeneration.** The Orchestrator classifies feedback scope and re-invokes only affected agents:

| Feedback Type | Agents Re-invoked |
|--------------|-------------------|
| Visual change (chart type, spacing) | Deck Builder only |
| Content reorder (narrative emphasis) | Market Data + Deck Builder |
| Data correction | Portfolio Agent (requires new data upload) |
| Section toggle (add/remove) | Orchestrator re-plans + Deck Builder |
| Compliance concern | Compliance Agent re-check |

**Guardrails:** Max 10 refinement rounds. Data immutability (system cannot fabricate financial numbers). Compliance re-check on every round. Approval locks the deck. Full audit trail — every round is a separate, immutable record traceable by the SEC.

---

## Containerized Deployment

### Deployment Model

```
┌───────────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (Docker containers)                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  Deployment Manifest — Agent Services                  │     │
│  │                                                         │     │
│  │  orchestrator-agent     v1.2   Claude Sonnet   Running │     │
│  │  portfolio-agent        v1.1   Claude Sonnet   Running │     │
│  │  market-data-agent      v1.0   Claude Sonnet   Running │     │
│  │  compliance-agent       v1.3   Claude Sonnet   Running │     │
│  │  deck-builder-agent     v1.1   Claude Sonnet   Running │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  Runtime                                                │     │
│  │                                                         │     │
│  │  - HPA auto-scaling per agent (min 0, max configurable)│     │
│  │  - Concurrency control for batch mode                  │     │
│  │  - Built-in retry with exponential backoff             │     │
│  │  - Agent-to-agent invocation via Strands SDK           │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │  Observability                                          │     │
│  │                                                         │     │
│  │  - Full agent trace: every LLM call + tool invocation  │     │
│  │  - Latency breakdown per agent per tool                │     │
│  │  - Token usage tracking (cost attribution)             │     │
│  │  - Error rates and retry metrics                       │     │
│  │  - Exported via OpenTelemetry to observability stack   │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
└───────────────────────────────────────────────────────────────┘
```

### Strands Agent Definition (Example — Portfolio Agent)

```python
from strands import Agent, tool
from strands.models import AnthropicModel

@tool
def parse_excel(file_path: str, sheet_name: str) -> dict:
    """Parse a Clearwater Analytics Excel export and return structured cell data."""
    import openpyxl
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb[sheet_name]
    # ... parsing logic ...
    return structured_data

@tool
def read_client_config(client_id: str) -> dict:
    """Read client configuration from document database."""
    from db_client import get_document_db
    db = get_document_db()
    return db.collection("client-config").get(client_id)

@tool
def write_parsed_output(client_id: str, period: str, data: dict) -> str:
    """Write normalized portfolio data to object storage as JSON."""
    from storage_client import get_object_store
    import json
    key = f"parsed/{period}/{client_id}.json"
    store = get_object_store()
    store.put_object(
        bucket="performa-deck-gen", key=key,
        body=json.dumps(data)
    )
    return f"performa-deck-gen/{key}"

portfolio_agent = Agent(
    model=AnthropicModel(model_id="claude-sonnet-4-6-20250514"),
    system_prompt="""You are a Portfolio Data Agent for Performa LTD's deck generation system.

Your job is to parse Clearwater Analytics Excel exports and produce normalized,
structured portfolio data. You handle two types of exports:

1. Board Reports (AGG clients) — wide-format Excel with performance, market value
   history, strategy contributions, and allocation vs guidelines sections.
2. SMA Holdings — per-bond holdings with issuer, sector, duration, yield, ratings,
   maturity, and market value.

IMPORTANT:
- Clearwater exports have inconsistent formatting. Reason about the structure you
  see rather than assuming fixed column positions.
- Returns are raw decimals (0.097 = 9.7%). Preserve raw values in output.
- Dates may be datetime objects or strings. Normalize to ISO 8601.
- "---" means data is unavailable (e.g., trailing 10yr when inception < 10yr).
  Set to null, do not skip.
- Always hash source files for audit trail.
- Flag any data that looks anomalous with a warning, do not silently drop it.
""",
    tools=[parse_excel, read_client_config, write_parsed_output],
)
```

---

## Data Flow — Batch Mode (Quarter-End, 100+ Clients)

```
 Analyst uploads:                  Orchestrator               Per-Client Agents
 - Bulk Clearwater data
 - Market Context (once)
 - Selects client list
                                                     ┌──────────────────────────────────────┐
                              ──▶  Market Data Agent ─┤ runs ONCE (shared across batch)       │
                                   │                  │ market_context.json cached in storage │
                                   │                  └──────────────────────────────────────┘
                                   │
                                   │  market_context.json shared ──▶ all Deck Builders
                                   │
                                   ├─▶ Fan-out: Client 1 ──▶ Portfolio → Deck Builder → Compliance
                                   ├─▶ Fan-out: Client 2 ──▶ Portfolio → Deck Builder → Compliance
                                   ├─▶ Fan-out: Client 3 ──▶ Portfolio → Deck Builder → Compliance
                                   │   ...
                                   ├─▶ Fan-out: Client N ──▶ Portfolio → Deck Builder → Compliance
                                   │
                                   └─▶ Collect all results
                                       Generate batch summary
                                       Notify analyst
```

**Kubernetes handles:** Concurrency limits, queuing, retry logic, resource allocation across parallel agent invocations.

---

## Storage Design

### Object Storage Structure
```
performa-deck-gen/
├── templates/
│   ├── master/v{N}.pptx
│   ├── market-update/Q{N}-{YYYY}.pptx
│   └── static-sections/{section-name}/
├── uploads/{YYYY-MM-DD}/{upload-id}/
│   ├── board-report.xlsx           # Clearwater — Portfolio Agent
│   ├── sma-holdings.xlsx           # Clearwater — Portfolio Agent
│   └── market-brief.docx           # Market Context — Market Data Agent (if uploaded)
├── market-context/
│   └── Q{N}-{YYYY}/
│       ├── raw/                     # Raw uploaded brief or API response
│       └── market-context.json      # Processed output from Market Data Agent
├── parsed/{period}/{client-id}.json  # Portfolio Agent output
├── generated/{YYYY}/{client-id}/{gen-id}.pptx
└── audit/{YYYY}/{gen-id}.json
```

### Database Collections

**client-config** (Primary key: `client_id`)
```json
{
  "client_id": "CAPE-21",
  "client_name": "Cape Insurance Company",
  "client_type": "AGG+SMA",
  "presenters": ["DAVID KILBORN, CFA", "WARREN MILLER"],
  "strategies": [
    {"name": "CASH & INVESTMENT GRADE BONDS", "target": 0.65, "range": [0.55, 0.80]},
    {"name": "HIGH YIELD BONDS", "target": 0.10, "range": [0.05, 0.20]},
    {"name": "EQUITIES", "target": 0.25, "range": [0.15, 0.25]}
  ],
  "sub_strategies": [],
  "benchmark_description": "65% Bloomberg Intermediate U.S. Govt/Credit...",
  "inception_date": "2019-07-01",
  "include_sections": ["market_update", "allocation", "performance", "rollforward", "sma_detail", "etf_overviews", "holdings"],
  "domicile": "VT",
  "entity_type": "RRG"
}
```

**compliance-rules** (Primary key: `domicile#entity_type`)
```json
{
  "rule_key": "VT#RRG",
  "description": "Vermont Risk Retention Group (8 V.S.A. Chapter 141, Section 6010)",
  "rules": {
    "ig_fixed_income_max_pct": 1.00,
    "below_ig_max_pct": 0.20,
    "naic_4_to_6_max_pct": 0.10,
    "equity_max_pct": 0.25,
    "per_issuer_max_pct": 0.10,
    "per_issuer_exemptions": ["mutual_funds", "naic_approved_etfs"]
  }
}
```

**generation-log** (Primary key: `gen_id`, Secondary index: `client_id + timestamp`)
```json
{
  "gen_id": "gen-20260315-cape21-002",
  "client_id": "CAPE-21",
  "report_period": "2024-12-01/2025-11-30",
  "version": 2,
  "parent_gen_id": "gen-20260315-cape21-001",
  "refinement_round": 2,
  "analyst_prompt": "Board meeting prep. Highlight equity outperformance...",
  "refinement_prompt": "Space out performance chart bars. Add ANGL callout. Tariffs first.",
  "structured_feedback": { "slide_flags": [], "chart_changes": [] },
  "agents_invoked": ["market-data-agent", "deck-builder-agent", "compliance-agent"],
  "slides_modified": [9, 11, 12],
  "source_files_hash": "sha256:abc123...",
  "output_file_hash": "sha256:def456...",
  "agent_trace_id": "trace-xyz789",
  "compliance_status": "WARNING",
  "status": "pending_review",
  "generated_at": "2026-03-15T15:10:00Z",
  "generated_by": "analyst@performa.com",
  "reviewed_at": null,
  "reviewed_by": null,
  "review_action": null
}
```

---

## Security Architecture

```
┌───────────────────────────────────────────────────┐
│  Private Network                                    │
│  ┌───────────────────────────────────────────┐     │
│  │  Private Subnets                           │     │
│  │  - Containerized agent runtime             │     │
│  │  - Private endpoints:                     │     │
│  │    - Object Storage                       │     │
│  │    - Document Database                    │     │
│  │    - LLM Provider                         │     │
│  │    - Observability stack                  │     │
│  │  - No internet egress                     │     │
│  └───────────────────────────────────────────┘     │
│  ┌───────────────────────────────────────────┐     │
│  │  Public-facing tier                        │     │
│  │  - CDN distribution                       │     │
│  │  - API Gateway endpoint                   │     │
│  └───────────────────────────────────────────┘     │
└───────────────────────────────────────────────────┘
```

- **Encryption:** Object storage encryption at rest (customer-managed keys). Document database encryption at rest.
- **Auth:** Identity Provider JWT validated at API Gateway. Service-level RBAC per agent (least privilege).
- **LLM data policy:** No model training on input data. Invocations logged to observability stack (OpenTelemetry).
- **Data retention:** Generated decks + audit logs retained 7 years (SEC Rule 204-2 for investment advisers).
- **Network:** All agent execution in private network. Private endpoints for all service calls. Zero public internet access from compute.

---

## Architecture Trade-offs

### Multi-Agent vs Deterministic Pipeline

| Dimension | Multi-Agent (chosen) | Workflow Engine + Serverless Functions |
|-----------|---------------------|---------------------------------------|
| Edge case handling | Agents reason through format variations | Rigid parsers break on unexpected input |
| Compliance checking | LLM reasons about rule interactions | Rule engine requires exhaustive coding |
| Extensibility | New capabilities = new agent or new tools | New capabilities = new function + state changes |
| Cost per deck | Higher (LLM invocations) | Lower (pure compute) |
| Determinism | Non-deterministic (mitigated by tool-based precision) | Fully deterministic |
| Observability | Rich agent traces | Workflow engine visual history |
| Time to build | Faster (less edge-case code) | Slower (must code every edge case) |

**Mitigation for non-determinism:** All financial data flows through deterministic tools. Agents decide *what* to do; tools execute *how* to do it. Numbers in the final deck come from tools (python-pptx), not from LLM text generation.

### Why Not a Single Agent?

A monolithic agent would have too many tools and too much context, leading to:
- Longer prompts = higher latency and cost
- Tool selection confusion at scale
- No parallelism (Market Data + Portfolio must run sequentially)
- Harder to version and test independently

---

## Estimated Cost (Steady State)

| Component | Usage | Est. Monthly Cost |
|-----------|-------|-------------------|
| Kubernetes cluster | 5 agent services, auto-scaling | ~$50-150 |
| LLM Provider (Claude Sonnet) | ~665 agent invocations/mo, ~2K tokens avg | ~$30-60 |
| Object Storage | ~10GB stored | < $5 |
| Document Database | On-demand, ~1000 reads + 500 writes/mo | < $5 |
| CDN + API Gateway | Minimal traffic (internal tool) | < $10 |
| Identity Provider | < 50 MAU | Free tier or < $5 |
| Observability stack (OpenTelemetry) | Logs + metrics + traces | ~$10-20 |
| **Total** | | **~$120-260/mo** |

Slightly higher than a pure serverless pipeline (~$100/mo) but the agent architecture absorbs Phase 2 capabilities (commentary, reconciliation, anomaly detection) without infrastructure changes.
