# Business Requirements

## Client Profile

**Performa LTD** — Boutique asset management firm exclusively serving captive insurance companies.

- Founded 1992, ~11 team members
- Offices: Hamilton (Bermuda HQ), Charleston SC, Burlington VT
- 100+ captive insurance clients
- Key contact: David Kilborn, CFA — President & CIO (Charleston office)
- Referred by Johnson Lambert (major insurance-focused CPA/advisory firm)

## Problem Statement

Each quarter, Performa manually builds personalized client meeting decks in PowerPoint. The process:

1. Log into Clearwater Analytics portal, download portfolio data as Excel
2. Clean up Clearwater's broken formatting (weird Excel output, sometimes export PDF-to-Excel as workaround)
3. Extract relevant data points (allocations, performance, holdings)
4. Populate a PowerPoint template with client-specific data: tables, charts, pie charts
5. Wrap dynamic slides with static "master slides" (market commentary, appendices, disclaimers)

**Pain points:**
- Only 2 people currently build these decks — bottleneck
- Each deck takes significant manual effort (data cleaning + assembly)
- 100+ clients x 2+ times/year = 200+ decks minimum
- Senior analyst time consumed by assembly work instead of advisory work
- Quality consistency varies between the two people building decks
- Quarter-end crunch creates stress and deadline pressure

## Scope — Phase 1 (This Project)

Automate the generation of personalized client meeting PowerPoint decks from Clearwater Analytics data exports.

**In scope:**
- Ingesting Clearwater Excel exports (manual upload — no API available)
- Parsing and cleaning portfolio data
- Generating per-client "meat" slides (asset allocation, performance, portfolio roll forward, SMA holdings)
- Wrapping with static "bread" slides from master template
- Producing downloadable .pptx files for human review before client delivery
- Covering ~80% of clients with the standard deck format

**Out of scope (future phases):**
- Clearwater API integration (API not functional today)
- Operational data reconciliation & reasonableness checks
- AI-generated portfolio commentary/narratives
- IPS compliance monitoring
- Custom deck variants for the ~20% of non-standard clients

## Compliance & Security Constraints

- **SEC regulated** — Performa is an SEC-registered investment adviser. All AI usage must be documented for SEC compliance.
- **Data privacy** — Client portfolio data is highly sensitive (comparable to HIPAA-level sensitivity per David). Must not flow to third-party AI training sets.
- **Human-in-the-loop** — Every generated deck must be reviewed and approved by a human before delivery to clients.
- **Existing tech stack** — Performa is an Azure / Microsoft 365 shop. All applications are cloud-based. Bloomberg for trading/OMS.
- **AI policy in progress** — Head of compliance is writing internal AI usage policies. Investment team AI usage is locked down pending policy completion.

## Success Criteria

1. An analyst can upload Clearwater data exports and receive a draft deck for a specific client within minutes (not hours)
2. Generated decks match the formatting, branding, and structure of current manually-built decks
3. Data accuracy is maintained — numbers in the deck match source data exactly
4. The system handles both AGG (aggregate/ETF) and SMA (separately managed account) client types
5. Human review time per deck is significantly less than current full-build time

## Engagement Structure

- **Provectus** is the delivery partner (Oleg Blokhin — lead)
- Phase 1: Discovery — 4 weeks
- Phase 2: MVP/Pilot Build — estimated 12 weeks total engagement
- Estimated cost: $70K-$95K/month
- Team: Solution Architect, Solution Owner, DevOps, QA, ML Engineer, Data Engineer, App-Dev Engineer
