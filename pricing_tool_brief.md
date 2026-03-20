# Pricing Intelligence Tool — Project Brief for Claude Code

## Overview

Build a **web-based pricing intelligence tool** (Python prototype) that helps a small team (2–5 users) make evidence-based pricing decisions. The tool ingests diverse pricing data — from internal sales history to competitor listings — stores it persistently, and uses an **LLM (Claude API)** to generate actionable pricing recommendations.

---

## Core Problem

The team needs a centralized system that can:

1. Absorb pricing data from multiple sources and formats.
2. Understand the **context** behind each data point (customer type, industry, discounts, channel).
3. Produce clear, objective, evidence-backed pricing guidance — not gut feelings.

---

## Data Inputs

The tool must accept data through **four ingestion methods**:

| Method | Description |
|--------|-------------|
| **Manual entry** | Form-based input for individual data points (a sale, a quote, a competitor price, etc.) |
| **Excel / CSV upload** | Bulk import of sales history, quote logs, or pricing sheets |
| **PDF upload** | Parse pricing from distributor price lists, quote documents, or invoices |
| **URL / product page scrape** | Paste a competitor or distributor product page URL and extract pricing |

### Data Categories to Ingest

Each record should capture as much of the following context as applicable:

#### 1. Internal Sales Data
- Product name / SKU
- Customer name or ID
- **Customer type**: end-user vs. reseller
- **Customer industry** (e.g., manufacturing, healthcare, government)
- **Customer size** (e.g., small business, mid-market, enterprise)
- Gross price, discount(s) applied, **net price**
- Quantity sold
- Date of sale

#### 2. Quotes (Won & Lost)
- All fields from Internal Sales Data above
- **Quote status**: won, lost, or pending
- Competitor the deal was lost to (if known)
- Reason for win/loss (free text, optional)

#### 3. Competitor Pricing
- Competitor name
- Product name (their equivalent / direct substitute)
- Listed price
- Source (URL, catalog, hearsay)
- Date observed

#### 4. Distributor Pricing
- Distributor name
- Product name / SKU
- **Distributor's price to their end-user** (street price)
- Your cost from the distributor (if applicable)
- Date observed

#### 5. Cost & Logistics Context
- **Shipping cost** per unit or per order (average or actual)
- **Warehousing / handling cost** per unit (average or actual)
- Any other landed-cost components

---

## Outputs & Analysis

The tool should produce four primary types of analysis, powered by the Claude API:

### 1. Recommended Price Ranges
- For each product, suggest a **floor, target, and ceiling price**.
- Factor in: customer type, customer size/industry, channel (direct vs. distributor), volume, and competitive landscape.
- Justify recommendations with citations to the ingested data.

### 2. Win/Loss Analysis on Quotes
- Show win rate by product, customer segment, price band, and discount level.
- Identify pricing thresholds where win rates drop off.
- Highlight quotes lost to specific competitors and at what price delta.

### 3. Competitor Price Comparisons
- Side-by-side comparison of your pricing vs. each competitor's for equivalent products.
- Track competitor price changes over time.
- Flag products where you are significantly above or below the market.

### 4. Margin Analysis (Including Shipping & Warehousing)
- Calculate effective margin after shipping and warehousing costs.
- Compare margin by channel: direct-to-end-user vs. through-distributor.
- Identify products or customer segments with margin erosion.

---

## Technical Requirements

### Stack
- **Language**: Python 3.10+
- **Web framework**: Streamlit (preferred for rapid prototyping) or Flask
- **LLM integration**: Anthropic Claude API (claude-sonnet-4-20250514 or later)
- **Data storage**: Developer's choice — SQLite is fine for a prototype; should persist between sessions
- **PDF parsing**: PyMuPDF, pdfplumber, or similar
- **Web scraping**: BeautifulSoup + requests, or similar lightweight approach
- **Excel/CSV**: openpyxl / pandas

### Architecture Guidance

```
┌─────────────────────────────────────────────────┐
│                   Web UI (Streamlit)             │
│  ┌───────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ Data Entry│ │  Upload   │ │  URL Scraper  │  │
│  │   Forms   │ │ (XLS/PDF) │ │               │  │
│  └─────┬─────┘ └─────┬─────┘ └──────┬────────┘  │
│        └──────────────┼──────────────┘           │
│                       ▼                          │
│            ┌─────────────────────┐               │
│            │  Ingestion Engine   │               │
│            │  (normalize, tag,   │               │
│            │   validate, store)  │               │
│            └─────────┬───────────┘               │
│                      ▼                           │
│            ┌─────────────────────┐               │
│            │   Data Store (DB)   │               │
│            └─────────┬───────────┘               │
│                      ▼                           │
│            ┌─────────────────────┐               │
│            │  Analysis Engine    │               │
│            │  (Claude API calls  │               │
│            │   + local stats)    │               │
│            └─────────┬───────────┘               │
│                      ▼                           │
│            ┌─────────────────────┐               │
│            │  Output / Reports   │               │
│            │  (tables, charts,   │               │
│            │   recommendations)  │               │
│            └─────────────────────┘               │
└─────────────────────────────────────────────────┘
```

### Key Design Principles
1. **Context is king** — every data point should carry metadata (customer type, industry, size, channel, date) so the LLM can reason about it.
2. **Separation of concerns** — keep ingestion, storage, analysis, and presentation in separate modules.
3. **LLM-augmented, not LLM-dependent** — use basic statistics (averages, medians, percentiles, win rates) locally, and send structured summaries to Claude for interpretation and recommendation. Don't send raw dumps.
4. **Incremental data** — the tool should allow adding data over time, not require everything upfront.

---

## User Experience (Prototype)

### Pages / Views
1. **Dashboard** — high-level pricing health: average margins, win rate trend, competitive position summary.
2. **Data Ingestion** — forms, file upload, URL input. Show recent imports.
3. **Product Pricing View** — select a product, see all data (sales, quotes, competitor, distributor) and the AI-generated recommended price range.
4. **Quote Analyzer** — upload or enter a new quote, get a quick AI assessment of likelihood to win and suggested adjustments.
5. **Reports** — generate the four analysis types listed above on demand.

### Authentication
- Not required for prototype. Assume all users on the same local network or instance.

---

## Out of Scope (for Prototype)
- Real-time competitor price monitoring / automated scraping schedules
- Role-based access control
- ERP / CRM integrations
- Email notifications or alerts
- Multi-currency support (assume single currency)

---

## Getting Started Prompt for Claude Code

> Build a Python web application (Streamlit preferred) for pricing intelligence. The app should:
>
> 1. Accept pricing data via manual forms, Excel/CSV upload, PDF upload, and URL scraping of product pages.
> 2. Store all data in a persistent database (SQLite is fine) with full context: customer type (end-user vs. reseller), customer industry, customer size, discounts, quantities, quote win/loss status, competitor prices, distributor street prices, and shipping/warehousing costs.
> 3. Use the Anthropic Claude API to analyze the stored data and produce: recommended price ranges per product, win/loss analysis on quotes, competitor price comparisons, and margin analysis inclusive of logistics costs.
> 4. Present results in a clean Streamlit UI with a dashboard, data ingestion page, per-product pricing view, quote analyzer, and reports section.
>
> Start by scaffolding the project structure, defining the database schema, and building the data ingestion layer. Then add the analysis engine and UI.
