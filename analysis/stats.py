"""
Local statistics — computed without calling the LLM.
Feeds structured summaries to the Claude analysis module.
"""
from __future__ import annotations

import statistics
from typing import Any

import database as db


def _pct(a: int, b: int) -> float | None:
    return round(a / b * 100, 1) if b > 0 else None


# ── Per-product stats ──────────────────────────────────────────────────────────

def product_price_stats(product_name: str) -> dict:
    """Return price statistics for a specific product."""
    sales = db.get_sales_for_product(product_name)
    quotes = db.get_quotes_for_product(product_name)
    comp = db.get_competitor_prices_for_product(product_name)
    dist = db.get_distributor_prices_for_product(product_name)
    logistics = db.get_logistics_for_product(product_name)

    net_prices = [s["net_price"] for s in sales if s.get("net_price")]
    disc_pcts = [s["discount_pct"] for s in sales if s.get("discount_pct") is not None]
    comp_prices = [c["listed_price"] for c in comp if c.get("listed_price")]
    street_prices = [d["street_price"] for d in dist if d.get("street_price")]
    our_costs = [d["our_cost"] for d in dist if d.get("our_cost")]

    logistics_cost = 0.0
    if logistics:
        l = logistics[0]  # most recent
        logistics_cost = (
            (l.get("shipping_cost_per_unit") or 0)
            + (l.get("warehousing_cost_per_unit") or 0)
            + (l.get("other_cost_per_unit") or 0)
        )

    # Win/loss
    won_quotes = [q for q in quotes if q.get("status") == "won"]
    lost_quotes = [q for q in quotes if q.get("status") == "lost"]
    won_prices = [q["net_price"] for q in won_quotes if q.get("net_price")]
    lost_prices = [q["net_price"] for q in lost_quotes if q.get("net_price")]

    # Margin calculation (vs distributor cost when available)
    base_cost = statistics.mean(our_costs) if our_costs else None
    avg_net = statistics.mean(net_prices) if net_prices else None
    margin_pct = None
    if avg_net and base_cost and avg_net > 0:
        effective_cost = base_cost + logistics_cost
        margin_pct = round((avg_net - effective_cost) / avg_net * 100, 1)

    return {
        "product_name": product_name,
        "sales_count": len(sales),
        "quote_count": len(quotes),
        "won_count": len(won_quotes),
        "lost_count": len(lost_quotes),
        "win_rate": _pct(len(won_quotes), len(won_quotes) + len(lost_quotes)),
        # Net price stats
        "net_price_min": min(net_prices) if net_prices else None,
        "net_price_max": max(net_prices) if net_prices else None,
        "net_price_avg": round(statistics.mean(net_prices), 2) if net_prices else None,
        "net_price_median": round(statistics.median(net_prices), 2) if net_prices else None,
        "net_price_p25": _percentile(net_prices, 25),
        "net_price_p75": _percentile(net_prices, 75),
        # Discount stats
        "avg_discount_pct": round(statistics.mean(disc_pcts), 1) if disc_pcts else None,
        "max_discount_pct": max(disc_pcts) if disc_pcts else None,
        # Won vs lost pricing
        "avg_won_price": round(statistics.mean(won_prices), 2) if won_prices else None,
        "avg_lost_price": round(statistics.mean(lost_prices), 2) if lost_prices else None,
        # Competitor
        "competitor_price_avg": round(statistics.mean(comp_prices), 2) if comp_prices else None,
        "competitor_price_min": min(comp_prices) if comp_prices else None,
        "competitor_price_max": max(comp_prices) if comp_prices else None,
        "competitor_count": len(set(c["competitor_name"] for c in comp)),
        # Distributor
        "distributor_street_avg": round(statistics.mean(street_prices), 2) if street_prices else None,
        "our_cost_avg": round(statistics.mean(our_costs), 2) if our_costs else None,
        # Logistics
        "logistics_cost_per_unit": logistics_cost if logistics else None,
        # Margin
        "estimated_margin_pct": margin_pct,
        # Raw lists for AI
        "raw_sales": sales,
        "raw_quotes": quotes,
        "raw_competitors": comp,
        "raw_distributors": dist,
        "raw_logistics": logistics,
    }


# ── Portfolio-level stats (for reports) ───────────────────────────────────────

def win_loss_summary() -> dict:
    """Aggregate win/loss data across all products."""
    df = db.query_df("""
        SELECT
            product_name,
            status,
            customer_type,
            customer_industry,
            customer_size,
            net_price,
            discount_pct,
            lost_to_competitor,
            quote_date
        FROM quotes
        WHERE status IN ('won','lost')
        ORDER BY quote_date
    """)
    if df.empty:
        return {"records": 0}

    total = len(df)
    won = len(df[df["status"] == "won"])
    lost = len(df[df["status"] == "lost"])

    by_product = (
        df.groupby("product_name")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )
    by_competitor = (
        df[df["lost_to_competitor"].notna()]
        .groupby("lost_to_competitor")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .to_dict()
    )
    by_segment = (
        df.groupby("customer_type")["status"]
        .value_counts()
        .unstack(fill_value=0)
        .to_dict(orient="index")
    )

    return {
        "records": total,
        "won": won,
        "lost": lost,
        "overall_win_rate": _pct(won, total),
        "by_product": by_product,
        "by_competitor": by_competitor,
        "by_segment": by_segment,
        "df": df,
    }


def competitor_comparison_summary() -> dict:
    """Compare your net prices vs competitor prices per product."""
    our_df = db.query_df("""
        SELECT product_name, AVG(net_price) AS our_avg_price
        FROM sales
        WHERE net_price IS NOT NULL
        GROUP BY product_name
    """)
    comp_df = db.query_df("""
        SELECT product_name, competitor_name,
               AVG(listed_price) AS comp_avg_price,
               MAX(observed_date) AS last_observed
        FROM competitor_prices
        WHERE listed_price IS NOT NULL
        GROUP BY product_name, competitor_name
    """)
    return {"our_prices": our_df, "competitor_prices": comp_df}


def margin_summary() -> dict:
    """Calculate margin by product and channel."""
    df = db.query_df("""
        SELECT
            s.product_name,
            s.customer_type,
            AVG(s.net_price) AS avg_net_price,
            AVG(s.discount_pct) AS avg_discount,
            COUNT(*) AS sale_count
        FROM sales s
        WHERE s.net_price IS NOT NULL
        GROUP BY s.product_name, s.customer_type
    """)
    cost_df = db.query_df("""
        SELECT product_name,
               AVG(our_cost) AS avg_our_cost
        FROM distributor_prices
        WHERE our_cost IS NOT NULL
        GROUP BY product_name
    """)
    logistics_df = db.query_df("""
        SELECT product_name,
               MAX(effective_date),
               AVG(shipping_cost_per_unit + warehousing_cost_per_unit + other_cost_per_unit)
                   AS total_logistics
        FROM logistics_costs
        GROUP BY product_name
    """)
    return {"sales": df, "costs": cost_df, "logistics": logistics_df}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _percentile(data: list[float], pct: int) -> float | None:
    if not data:
        return None
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_data) - 1)
    return round(sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo), 2)
