# Technical Specification

## Deck Structure — "The Sandwich"

The client deck is a ~35-slide PowerPoint with a static/dynamic sandwich structure:

```
┌──────────────────────────────────────────────────┐
│  BREAD (Static — from master template)           │
│  Slide 1:   Title slide (presenter names, date,  │
│             client name — parameterized)          │
│  Slide 2:   Table of Contents                    │
│  Slide 3:   Section 1 divider — "Market Update"  │
│  Slides 4-9: Market commentary (static per qtr)  │
├──────────────────────────────────────────────────┤
│  MEAT (Dynamic — per-client from Clearwater)     │
│  Slide 10:  Section 2 divider — "Investment Rpt" │
│  Slide 11:  Asset Allocation (table + pie chart)  │
│  Slide 12:  Performance (bar charts)             │
│  Slide 13:  Portfolio Roll Forward (table)       │
│  Slide 14:  Appendix I divider — "FI SMA"        │
│  Slide 15:  SMA Statistics (tables + pie charts)  │
│  Slide 16:  SMA Performance (tables + charts)    │
│  Slide 17:  Performance Attribution/Commentary   │
├──────────────────────────────────────────────────┤
│  APPENDIX (Mix of static and per-client)         │
│  Slides 18-23: ETF Overviews (semi-static)       │
│  Slides 24-26: VT Investment Restrictions        │
│  Slides 27-32: SMA Holdings (dynamic)           │
│  Slide 33:  Performance Disclosure (static)      │
│  Slide 34:  Disclaimers (static)                 │
│  Slide 35:  Cash Flow Projections (dynamic)      │
└──────────────────────────────────────────────────┘
```

**Key insight from transcript:** Not all clients get all sections. ~80% follow this standard format. Some clients are AGG-only (no SMA appendix), some are SMA-only. The appendix sections (ETF overviews, VT restrictions) are included only if relevant to the client's portfolio composition.

## Client Types

### Type 1: AGG (Aggregate / ETF-based)
Clients with blended portfolios: Fixed Income SMA + ETFs (equities, high yield, international).

**Dynamic data needed:**
- Allocation vs Guidelines: strategy name, market value, target %, actual %, target range
- Performance: net total return, assigned index return across periods (QTD, YTD, trailing 1/3/5/10yr, since inception)
- Market Value History: monthly ending market values over trailing 12 months
- Contribution by Strategy: strategy name, contribution to return
- Portfolio Roll Forward: beginning MV, transfers in/out, income, expenses, realized G/L, unrealized G/L change, ending MV

### Type 2: SMA (Separately Managed Account — Fixed Income only)
Clients with individual bond portfolios managed by the firm.

**Dynamic data needed:**
- Summary Statistics: market value, credit quality, yield to maturity, average duration, # holdings (vs index)
- Sector Allocation: portfolio % vs index % per sector
- Credit Quality Allocation: portfolio % vs index % per rating tier
- Performance: gross, net, index across periods
- Performance Attribution: duration/yield curve, sector allocation, security selection contributions
- Holdings: issuer, industry sector, duration, yield, S&P rating, Moody's rating, maturity, $ value, % value

## Data Sources — Clearwater Analytics Excel Exports

### File 1: Board Reports (AGG clients)
- **Sheet:** `Board Reports_updated for` (main data)
- **Structure:** Wide-format (79 columns), denormalized
- **Contains sections:**
  - Net Performance table: Period | Total Return | Assigned Index Return | Period Begin | Period End
  - Market Value History: monthly Begin Date | End Date | Base Market Value + Accrued
  - Contribution by Strategy: Strategy Short Description | Contribution
  - Allocation vs Guidelines (further down in sheet, below row 15)
- **Quirks:**
  - Dates as datetime objects, not strings
  - Returns as raw decimals (0.097 = 9.7%), need formatting
  - "---" used for unavailable periods (e.g., Trailing 10 Years when inception < 10yr)
  - Market Value in raw numbers (28298389.5015), needs formatting to "$28.3M" or "$28,298,390"
  - Some columns are spacer/empty columns

### File 2: SMA Holdings
- **Sheet:** `SMA Holdings (JJ)` (sheet name may vary per client)
- **Structure:** 14 columns, one row per holding
- **Columns:** Account, Account ID, BBG Account Code, Identifier, Description, Sector 2, Sector Category, Duration, Yield, S&P Rating, Moody's Rating, Final Maturity, Base Market Value + Accrued, % of Market Value + Accrued
- **Header rows:** Report name (row 1), Account (row 2), As of date (row 3), Base Currency (row 4), then column headers (row 5), then data
- **Quirks:**
  - Duration and Yield as raw floats
  - Maturity as datetime objects
  - Market Value as raw float (no $ formatting)
  - "NA" strings for missing ratings
  - Identifiers are CUSIP-like codes in the Identifier column, ticker-like codes in Description

### File 3: Both sheets include a `Disclaimer` sheet (static text, can be ignored for data extraction)

## PowerPoint Output Specification

### Formatting Standards (from sample deck analysis)

**Tables:**
- Asset Allocation table: 4 columns (STRATEGY | MARKET VALUE | ACTUAL ALLOCATION | TARGET RANGE) or 5 columns (adding BENCHMARK TARGET, UNREALIZED NET GAIN/LOSS for some clients)
- Performance table: 6 columns (Entity | MTD | YTD | 1YR | 3YR | INCEPTION)
- Holdings table: 8-9 columns (ISSUER | INDUSTRY SECTOR | DURATION | YIELD | RATING(s) | MATURITY | $ VALUE | % VALUE)
- Roll Forward table: 2 columns (Description | Value)

**Charts:**
- Pie charts for allocation breakdown (3D pie used in some slides)
- Bar/column charts for performance comparison (portfolio vs index)
- Line charts in market update section
- Stacked column charts for economic data

**Slide dimensions:** 9144000 x 6858000 EMU (standard 10" x 7.5" widescreen)

**Branding elements:**
- Firm logo (Picture shapes, positioned consistently)
- Color scheme from master template
- Consistent header pattern: "[Title 1]" text box + "[Line 309]" separator + "[Rectangle]" subtitle
- Slide numbers in "Slide Number Placeholder 1"
- Source footnotes at bottom of data slides (e.g., "SOURCED VIA PORTFOLIO ROLLFORWARD REPORT IN CLEARWATER")

### Data Mapping: Clearwater Export -> Slide Element

| Slide | Element | Clearwater Source | Report |
|-------|---------|-------------------|--------|
| 11 | Asset Allocation Table | Allocation vs Guidelines section | Board Reports |
| 11 | Allocation Pie Chart | Same data as table | Board Reports |
| 12 | Performance Bar Charts | Net Performance section | Board Reports |
| 13 | Roll Forward Table | Derived from MV History + flows | Board Reports |
| 15 | SMA Statistics Tables | Aggregated from holdings | SMA Holdings |
| 15 | Sector/Credit Pie Charts | Aggregated from holdings | SMA Holdings |
| 16 | SMA Performance Table | Net Performance section | Board Reports (SMA sub-account) |
| 17 | Attribution Table | External (Bloomberg + CW) | Manual / TBD |
| 28-32 | Holdings Tables | All holding rows | SMA Holdings |
| 35 | Cash Flow Table | Cash flow projections | Separate source / TBD |

### Parameterized Static Slides

Even "static" slides need light parameterization:
- **Slide 1:** Client name, date, presenter name(s) — selected from a list of team members
- **Slide 2:** Table of contents — sections vary by client type
- **Slide 33:** Performance disclosure — index composition description changes based on client's benchmark history
