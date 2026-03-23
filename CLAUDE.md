# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Slide Deck Generator** — Automated generation of personalized quarterly client meeting PowerPoint decks for Performa LTD, a boutique asset management firm serving 100+ captive insurance clients.

**Delivery partner:** Provectus. **Architecture:** Cloud-agnostic multi-agent system.

## Key Documents

| File | Purpose |
|------|---------|
| `BUSINESS_REQUIREMENTS.md` | Client context, problem statement, scope, compliance constraints, success criteria |
| `TECHNICAL_SPEC.md` | Deck "sandwich" structure, client types (AGG vs SMA), Clearwater data schemas, PPTX output spec, data mapping |
| `ARCHITECTURE.md` | High-level multi-agent architecture: 5 agents, 4 inputs, tools, data flow, review & refinement loop |
| `Pre-Sale/SAMPLE CLIENT DECK.pptx` | 35-slide reference deck — the target output format |
| `Pre-Sale/SAMPLE HOLDINGS REPORT.xlsx` | SMA holdings data (per-bond rows: issuer, sector, duration, yield, ratings, maturity, market value) |
| `Pre-Sale/SAMPLE REPORT DATA AGG 2.xlsx` | AGG client Board Report (performance, market value history, strategy contributions) |
| `Pre-Sale/SAMPLE REPORT DATA SMA 2.xlsx` | SMA client Board Report (same structure, fixed-income only) |

## Core Concept — The "Sandwich"

Decks are a sandwich of static "bread" and dynamic "meat":
- **Bread (static):** Market update commentary, section dividers, ETF overviews, disclaimers — from versioned master template, updated quarterly
- **Meat (dynamic):** Asset allocation tables + pie charts, performance charts, portfolio roll forward, SMA holdings — generated per-client from Clearwater Excel exports

## System Inputs

1. **Clearwater Analytics** (Excel upload) — portfolio data → Portfolio Agent
2. **IPS Parameters** (database) — client constraints → Compliance Agent
3. **Market Context** (source TBD — manual upload, data feed) → Market Data Agent
4. **Analyst Prompt** (free-text) — human intent: deck type, visual prefs, emphasis, overrides → Orchestrator → all agents

## Human-in-the-Loop

Every generated deck enters a **review & refinement loop** (not just approve/reject):
- Analyst reviews draft → can **Approve**, **Request Changes** (with feedback prompt), or **Reject**
- Refinement is surgical: Orchestrator re-invokes only the agents whose output needs to change
- Each round creates a new immutable version with full audit trail
- Max 10 refinement rounds; approval locks the deck

## Critical Constraints

- **Cloud-agnostic** — no dependency on a specific cloud provider
- **No Clearwater API** — data enters via manual Excel upload
- **SEC compliance** — full audit trail on every generated artifact, including all refinement rounds and analyst prompts
- **Data sensitivity** — client portfolio data must not leave controlled infrastructure; LLM provider must not train on customer data
