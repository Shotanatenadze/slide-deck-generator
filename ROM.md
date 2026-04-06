# ROM — Rough Order of Magnitude

## Team

| Role | Focus |
|------|-------|
| **Solution Architect** | Architecture, agents, ETL, PPTX tooling, infra, backend |
| **Solution Owner** | Product, web app, QA, client alignment, UAT |

---

## Roadmap

### ➤ Validation (2 weeks)

**Goal:** Perform a technical deep-dive and stakeholder alignment to validate that the multi-agent architecture meets the firm's data accuracy, SEC compliance, and branding requirements before committing to the full build.

**Backlog Scope**
- Knowledge Transfer: Analyze 5–10 real Clearwater Excel exports to catalog format variations, edge cases, and data quirks beyond the 2 provided samples.
- PPTX Template Analysis: Reverse-engineer the 35-slide sample deck — chart types, branding elements, layout rules, parameterized vs static sections — to define the exact PPTX generation spec.
- Architecture & Security Audit: Validate that the cloud-agnostic containerized architecture supports SEC audit trail requirements, data residency constraints, and zero-egress network policy for client portfolio data.
- Stakeholder Mapping: Meet the firm's analysts (David, Clayton) to define "production-ready" criteria — what makes a generated deck acceptable vs requiring manual rework.
- Market Data Source Decision: Evaluate candidate sources (uploaded brief, FRED API, Bloomberg export, firm published content) and lock in the Phase 1 approach.
- TCO & Estimation: Finalize infrastructure costs, LLM token budget, and resource plan for the full build.

**Value realized:**
- Risk Mitigation: Identifies Clearwater format variations and PPTX complexity early — the two highest-risk items — before committing build effort.
- Alignment: Ensures the generated deck quality bar is defined by the firm, not assumed by the build team.
- Plan Validation: Validated assumptions and timelines for MVP Build & Pilot phase.

---

### ➤ MVP Build & Pilot (8–10 weeks)

**Goal:** Build, harden, and deploy a production-grade multi-agent system that generates personalized quarterly client meeting decks from Clearwater Excel uploads, with human-in-the-loop review and SEC-compliant audit trails.

**Backlog Scope**
- Data ETL Pipeline: Build robust Excel parsers for Board Reportswith normalization, anomaly flagging, and format variation handling.
- Multi-Agent System: Implement 5  agents (Orchestrator, Portfolio, Market Data, Deck Builder, Compliance) using Strands SDK with parallel execution and deterministic tool-based precision for all financial data.
- PPTX Generation Tooling: Build python-pptx tools for tables, pie charts, bar charts, slide assembly, branding, and template cloning
- Web Application: app with file upload, client configuration, analyst prompt input, generation trigger, slide preview, and compliance report display.
- Review & Refinement Loop: Implement Approve/Reject/Request Changes workflow with surgical refinement — Orchestrator re-invokes only affected agents, preserves untouched slides, maintains immutable version chain.
- Batch Generation: Multi-client fan-out for quarter-end runs (100+ clients), shared market context, K8s concurrency management.
- Observability: Deploy OpenTelemetry tracing across all agent invocations, LLM calls, and tool executions for SEC-ready audit logging.
- UAT: Pilot with real client data — validate data accuracy (deck numbers match source Excel exactly), visual fidelity, compliance correctness, and analyst workflow.

**Value realized:**


---

### ➤ Transition to Managed AI (Optional)

**Goal:** Ensure continuous performance, compliance coverage, and evolution of AI capabilities as the firm's client base and regulatory requirements change.

**Backlog Scope**
- Ongoing maintenance — Clearwater format changes, quarterly template updates, compliance rule updates.
- Phase 2 features from product backlog — AI-generated market commentary, Clearwater API integration, Fed Translation Dashboard automation, operational data reconciliation.
- Non-standard client deck variants (~20% of clients not covered by Phase 1).
- Issue resolution, enhancements, and change requests.

**Value realized:**
- Continuous support & improvement ensures the system stays accurate, compliant, and aligned with the firm's evolving needs.
- Establishes a foundation for expanding AI-assisted advisory capabilities beyond deck generation.

---

## Key Risks

| Risk | Mitigation |
|------|------------|
| PPTX generation complexity (charts, 3D pies, branded layouts) is the critical path | Template deep-dive in Validation. Budget 2+ weeks for PPTX tooling in build phase. |
| Clearwater format variations beyond the 2 sample files | Collect 5–10 real exports during Validation. Agent reasoning handles edge cases. |
| Market data source TBD | Build for "uploaded brief" first. Pluggable adapter absorbs source change later. |
| 2-person team has zero slack for blockers | Batch mode is first cut if behind. SO manages scope — bug fixes only in UAT. |
| UAT feedback expands scope | New features → Managed AI phase. Phase 1 fixes bugs only. |
