"""
Claude API integration for pricing analysis.

Sends structured statistical summaries to claude-opus-4-6 with adaptive thinking.
All calls use streaming so results can be displayed incrementally in Streamlit.
"""
from __future__ import annotations

import json
import os
from typing import Generator

import anthropic
import pandas as pd

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Add it to your .env file or environment variables."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


_SYSTEM = """You are a pricing intelligence analyst. You receive structured
statistical summaries of pricing data — sales history, quotes, competitor
prices, distributor prices, and logistics costs — and produce clear,
evidence-backed pricing recommendations.

Guidelines:
- Always cite specific data points (e.g. "avg net price $X across N sales").
- Quantify your recommendations: floor / target / ceiling prices.
- Be honest about data gaps.
- Keep responses concise and actionable.
- Use markdown formatting with headers and bullet points."""


def stream_price_recommendation(stats: dict) -> Generator[str, None, None]:
    """
    Generate a price range recommendation for a single product.
    Yields text chunks as they arrive.
    """
    # Build a clean summary — don't dump raw DB rows
    summary = _build_product_summary(stats)
    prompt = f"""Based on the following pricing data summary, provide:

1. **Recommended Price Range** (floor / target / ceiling) for each channel
   (direct end-user, reseller, distributor).
2. **Key Drivers** — what's pushing prices up or down.
3. **Risk Flags** — e.g. margin squeeze, competitive exposure.

Data summary:
{summary}"""

    yield from _stream(prompt)


def stream_win_loss_analysis(wl_data: dict) -> Generator[str, None, None]:
    """Analyse win/loss patterns across all products."""
    summary = {
        "overall_win_rate": wl_data.get("overall_win_rate"),
        "total_quotes": wl_data.get("records"),
        "by_product": wl_data.get("by_product"),
        "lost_most_to": wl_data.get("by_competitor"),
        "by_customer_segment": wl_data.get("by_segment"),
    }
    prompt = f"""Analyse the following win/loss summary and provide:

1. **Key Findings** — where are we winning and losing?
2. **Pricing Thresholds** — at what price points do win rates drop?
3. **Competitor Exposure** — which competitors are taking the most deals?
4. **Segment Recommendations** — which segments to prioritise?

Win/Loss Data:
{json.dumps(summary, indent=2, default=str)}"""

    yield from _stream(prompt)


def stream_competitor_analysis(comp_data: dict) -> Generator[str, None, None]:
    """Compare our prices against competitor prices."""
    our = comp_data["our_prices"].to_dict(orient="records") if not comp_data["our_prices"].empty else []
    comps = comp_data["competitor_prices"].to_dict(orient="records") if not comp_data["competitor_prices"].empty else []

    prompt = f"""Compare our pricing against competitors and provide:

1. **Competitive Position** — are we priced above, at, or below market?
2. **Products at Risk** — where are we most exposed?
3. **Pricing Opportunities** — where can we raise prices?
4. **Recommendations** — specific price adjustments by product.

Our Average Net Prices:
{json.dumps(our, indent=2, default=str)}

Competitor Prices (by product and competitor):
{json.dumps(comps, indent=2, default=str)}"""

    yield from _stream(prompt)


def stream_margin_analysis(margin_data: dict) -> Generator[str, None, None]:
    """Analyse margins including logistics costs."""
    sales = margin_data["sales"].to_dict(orient="records") if not margin_data["sales"].empty else []
    landed = margin_data["landed"].to_dict(orient="records") if not margin_data.get("landed", pd.DataFrame()).empty else []
    costs = margin_data["costs"].to_dict(orient="records") if not margin_data["costs"].empty else []
    logistics = margin_data["logistics"].to_dict(orient="records") if not margin_data["logistics"].empty else []

    cost_section = (
        f"Explicit Landed Costs per Unit (preferred, all-in):\n{json.dumps(landed, indent=2, default=str)}"
        if landed else
        f"Cost Basis (distributor our-cost):\n{json.dumps(costs, indent=2, default=str)}\n\n"
        f"Logistics Costs per Unit:\n{json.dumps(logistics, indent=2, default=str)}"
    )

    prompt = f"""Analyse product margins and provide:

1. **Margin Summary** — effective margin per product/channel after all costs.
2. **Margin Erosion** — products or segments with declining or negative margin.
3. **Channel Comparison** — direct vs distributor channel profitability.
4. **Recommendations** — price floors to protect margin.

Sales (avg net price by product + customer type):
{json.dumps(sales, indent=2, default=str)}

{cost_section}"""

    yield from _stream(prompt)


def stream_quote_assessment(quote: dict, stats: dict) -> Generator[str, None, None]:
    """Assess a new quote against historical data."""
    summary = _build_product_summary(stats)
    prompt = f"""Assess this pricing quote and provide:

1. **Win Probability** — likelihood of winning at this price (high/medium/low).
2. **Price Assessment** — is the quoted price appropriate, too high, or too low?
3. **Suggested Adjustments** — specific price or discount recommendations.
4. **Competitive Context** — how does this compare to what we know about competitors?

Proposed Quote:
{json.dumps(quote, indent=2, default=str)}

Historical Data for this Product:
{summary}"""

    yield from _stream(prompt)


def stream_pdf_extraction_analysis(
    extracted_text: str,
    document_type: str,
    entity_name: str,
) -> Generator[str, None, None]:
    """Ask Claude to extract pricing from raw PDF text."""
    prompt = f"""Extract all pricing information from this {document_type} document for {entity_name}.

For each product/item found, identify:
- Product name / SKU
- Price (and whether it's list, street, cost, or discounted price)
- Any applicable notes (e.g. volume breaks, effective dates)

Present the results as a structured markdown table, then summarise what you found.

Document text (first 4000 chars):
{extracted_text[:4000]}"""

    yield from _stream(prompt, max_tokens=2048)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _stream(prompt: str, max_tokens: int = 4096) -> Generator[str, None, None]:
    client = _get_client()
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def _build_product_summary(stats: dict) -> str:
    """Convert stats dict to a clean text summary for the prompt."""
    lines = [
        f"Product: {stats['product_name']}",
        f"Sales records: {stats['sales_count']}",
        f"Quote records: {stats['quote_count']} "
        f"(won: {stats['won_count']}, lost: {stats['lost_count']}, "
        f"win rate: {stats['win_rate']}%)" if stats['win_rate'] is not None
        else f"Quote records: {stats['quote_count']}",
    ]

    if stats.get("net_price_avg"):
        lines.append(
            f"Net price — avg: ${stats['net_price_avg']}, "
            f"median: ${stats['net_price_median']}, "
            f"range: ${stats['net_price_min']}–${stats['net_price_max']}"
        )
    if stats.get("avg_discount_pct") is not None:
        lines.append(
            f"Discounts — avg: {stats['avg_discount_pct']}%, max: {stats['max_discount_pct']}%"
        )
    if stats.get("avg_won_price"):
        lines.append(f"Average price of WON quotes: ${stats['avg_won_price']}")
    if stats.get("avg_lost_price"):
        lines.append(f"Average price of LOST quotes: ${stats['avg_lost_price']}")
    if stats.get("competitor_price_avg"):
        lines.append(
            f"Competitor prices — avg: ${stats['competitor_price_avg']}, "
            f"range: ${stats['competitor_price_min']}–${stats['competitor_price_max']} "
            f"({stats['competitor_count']} competitors)"
        )
    if stats.get("distributor_street_avg"):
        lines.append(f"Distributor street price avg: ${stats['distributor_street_avg']}")
    if stats.get("our_cost_avg"):
        lines.append(f"Our distributor cost avg: ${stats['our_cost_avg']}")
    if stats.get("landed_cost") is not None:
        lines.append(f"Landed cost per unit (explicit): ${stats['landed_cost']:.4f}")
    elif stats.get("logistics_cost_per_unit") is not None:
        lines.append(f"Logistics cost per unit: ${stats['logistics_cost_per_unit']:.2f}")
    if stats.get("effective_cost_used") is not None:
        lines.append(f"Effective cost used for margin: ${stats['effective_cost_used']:.2f}")
    if stats.get("estimated_margin_pct") is not None:
        lines.append(f"Estimated margin: {stats['estimated_margin_pct']}%")

    # Add a few sample quotes for context
    quotes = stats.get("raw_quotes", [])
    if quotes:
        lines.append("\nSample recent quotes:")
        for q in quotes[:5]:
            status = q.get("status", "?")
            price = q.get("net_price", "?")
            ctype = q.get("customer_type", "?")
            competitor = q.get("lost_to_competitor", "")
            lost_note = f" (lost to {competitor})" if competitor else ""
            lines.append(f"  • {status.upper()}{lost_note} — ${price} — {ctype}")

    # Competitor detail
    comps = stats.get("raw_competitors", [])
    if comps:
        lines.append("\nCompetitor price data points:")
        for c in comps[:8]:
            lines.append(
                f"  • {c['competitor_name']}: ${c.get('listed_price','?')} "
                f"(observed {c.get('observed_date','?')})"
            )

    return "\n".join(lines)
