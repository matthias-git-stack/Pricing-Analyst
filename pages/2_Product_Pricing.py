"""
Product Pricing View — all data for a selected product + AI recommendation.
"""
import streamlit as st
import plotly.express as px
import pandas as pd

import database as db
from analysis import stats as analysis_stats, claude_client

st.set_page_config(page_title="Product Pricing", page_icon="🏷️", layout="wide")
st.title("🏷️ Product Pricing View")

products = db.get_all_products()
if not products:
    st.info("No products found. Add data in **Data Ingestion** first.")
    st.stop()

selected_product = st.selectbox("Select a product", products)

if not selected_product:
    st.stop()

st.divider()

# ── Load stats ─────────────────────────────────────────────────────────────────
with st.spinner("Loading data…"):
    stats = analysis_stats.product_price_stats(selected_product)

# ── Summary metrics ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Sales Records", stats["sales_count"])
c2.metric("Quotes", stats["quote_count"])
c3.metric(
    "Win Rate",
    f"{stats['win_rate']}%" if stats["win_rate"] is not None else "—",
)
c4.metric(
    "Avg Net Price",
    f"${stats['net_price_avg']}" if stats["net_price_avg"] else "—",
)
c5.metric(
    "Est. Margin",
    f"{stats['estimated_margin_pct']}%" if stats["estimated_margin_pct"] is not None else "—",
)

# ── Data tabs ──────────────────────────────────────────────────────────────────
tab_sales, tab_quotes, tab_comp, tab_dist, tab_logistics, tab_ai = st.tabs(
    ["📈 Sales", "📋 Quotes", "⚔️ Competitors", "🏭 Distributors", "🚚 Logistics", "🤖 AI Recommendation"]
)

with tab_sales:
    sales = stats["raw_sales"]
    if sales:
        df = pd.DataFrame(sales)
        display_cols = [c for c in [
            "sale_date", "customer_name", "customer_type", "customer_industry",
            "customer_size", "gross_price", "discount_pct", "net_price", "quantity", "notes"
        ] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        if "net_price" in df.columns and df["net_price"].notna().any():
            fig = px.histogram(
                df.dropna(subset=["net_price"]),
                x="net_price",
                nbins=20,
                labels={"net_price": "Net Price ($)"},
                title="Net Price Distribution",
            )
            fig.update_layout(height=280, margin=dict(t=40))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No sales records for this product.")

with tab_quotes:
    quotes = stats["raw_quotes"]
    if quotes:
        df = pd.DataFrame(quotes)
        display_cols = [c for c in [
            "quote_date", "status", "customer_name", "customer_type",
            "gross_price", "discount_pct", "net_price", "quantity",
            "lost_to_competitor", "win_loss_reason"
        ] if c in df.columns]
        # Color rows by status
        def status_style(val):
            colors = {"won": "background-color: #d4edda", "lost": "background-color: #f8d7da", "pending": ""}
            return colors.get(val, "")

        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        # Won vs lost price comparison
        if "net_price" in df.columns and "status" in df.columns:
            df_wl = df[df["status"].isin(["won", "lost"])].dropna(subset=["net_price"])
            if not df_wl.empty:
                fig2 = px.box(
                    df_wl,
                    x="status",
                    y="net_price",
                    color="status",
                    color_discrete_map={"won": "#2ecc71", "lost": "#e74c3c"},
                    labels={"net_price": "Net Price ($)", "status": "Outcome"},
                    title="Price Distribution: Won vs Lost",
                )
                fig2.update_layout(height=280, margin=dict(t=40))
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No quotes for this product.")

with tab_comp:
    comp = stats["raw_competitors"]
    if comp:
        df = pd.DataFrame(comp)
        display_cols = [c for c in [
            "observed_date", "competitor_name", "listed_price", "source_type",
            "source_url", "notes"
        ] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        if "listed_price" in df.columns and df["listed_price"].notna().any():
            our_avg = stats.get("net_price_avg")
            comp_df = df.dropna(subset=["listed_price"])
            fig3 = px.bar(
                comp_df,
                x="competitor_name",
                y="listed_price",
                color="competitor_name",
                labels={"listed_price": "Listed Price ($)", "competitor_name": "Competitor"},
                title="Competitor Prices",
            )
            if our_avg:
                fig3.add_hline(
                    y=our_avg,
                    line_dash="dash",
                    annotation_text=f"Our avg ${our_avg}",
                    line_color="blue",
                )
            fig3.update_layout(height=300, margin=dict(t=40), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No competitor pricing for this product.")

with tab_dist:
    dist = stats["raw_distributors"]
    if dist:
        df = pd.DataFrame(dist)
        display_cols = [c for c in [
            "observed_date", "distributor_name", "street_price", "our_cost", "sku", "notes"
        ] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No distributor pricing for this product.")

with tab_logistics:
    logistics = stats["raw_logistics"]
    if logistics:
        df = pd.DataFrame(logistics)
        display_cols = [c for c in [
            "effective_date", "shipping_cost_per_unit", "warehousing_cost_per_unit",
            "other_cost_per_unit", "notes"
        ] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        total = stats.get("logistics_cost_per_unit")
        if total is not None:
            st.metric("Total Logistics Cost / Unit", f"${total:.2f}")
    else:
        st.info("No logistics cost data for this product.")

with tab_ai:
    if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
        st.warning("Set ANTHROPIC_API_KEY to enable AI recommendations.")
    else:
        enough_data = (
            stats["sales_count"] > 0
            or stats["quote_count"] > 0
            or stats.get("competitor_count", 0) > 0
        )
        if not enough_data:
            st.info("Add at least some sales, quotes, or competitor data for this product to get an AI recommendation.")
        else:
            if st.button("Generate AI Price Recommendation", type="primary"):
                st.markdown("### AI-Generated Price Recommendation")
                response_text = ""
                stream_box = st.empty()
                try:
                    for chunk in claude_client.stream_price_recommendation(stats):
                        response_text += chunk
                        stream_box.markdown(response_text + "▌")
                    stream_box.markdown(response_text)
                except Exception as e:
                    st.error(f"AI error: {e}")
