"""
Reports page — generate the four core analysis types on demand.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

import database as db
from analysis import stats as analysis_stats, claude_client

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")
st.title("📊 Reports")
st.caption("Generate evidence-backed analyses powered by data + Claude AI.")

if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
    st.warning("Set ANTHROPIC_API_KEY to enable AI analysis.", icon="⚠️")

report_type = st.radio(
    "Select report",
    [
        "1. Recommended Price Ranges",
        "2. Win / Loss Analysis",
        "3. Competitor Price Comparison",
        "4. Margin Analysis",
    ],
    horizontal=True,
)

st.divider()

# ── 1. Recommended Price Ranges ────────────────────────────────────────────────
if report_type.startswith("1"):
    st.subheader("Recommended Price Ranges")
    products = db.get_all_products()
    if not products:
        st.info("No product data yet.")
        st.stop()

    selected = st.multiselect(
        "Products to include (leave empty for all)",
        products,
        placeholder="Select products or leave empty for all…",
    )
    target_products = selected if selected else products

    if st.button("Generate Price Range Report", type="primary"):
        for product in target_products:
            with st.expander(f"**{product}**", expanded=True):
                with st.spinner(f"Analysing {product}…"):
                    product_stats = analysis_stats.product_price_stats(product)

                # Quick stats
                cols = st.columns(4)
                cols[0].metric("Avg Net Price", f"${product_stats['net_price_avg']}" if product_stats["net_price_avg"] else "—")
                cols[1].metric("Win Rate", f"{product_stats['win_rate']}%" if product_stats["win_rate"] is not None else "—")
                cols[2].metric("Competitor Avg", f"${product_stats['competitor_price_avg']}" if product_stats["competitor_price_avg"] else "—")
                cols[3].metric("Est. Margin", f"{product_stats['estimated_margin_pct']}%" if product_stats["estimated_margin_pct"] is not None else "—")

                if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
                    st.warning("AI disabled — set ANTHROPIC_API_KEY.")
                else:
                    response_text = ""
                    stream_box = st.empty()
                    try:
                        for chunk in claude_client.stream_price_recommendation(product_stats):
                            response_text += chunk
                            stream_box.markdown(response_text + "▌")
                        stream_box.markdown(response_text)
                    except Exception as e:
                        st.error(f"AI error: {e}")


# ── 2. Win / Loss Analysis ─────────────────────────────────────────────────────
elif report_type.startswith("2"):
    st.subheader("Win / Loss Analysis")

    wl = analysis_stats.win_loss_summary()
    if wl.get("records", 0) == 0:
        st.info("No won/lost quotes found. Add quote data with win/loss status first.")
        st.stop()

    # Overview metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Quoted", wl["records"])
    c2.metric("Won", wl["won"])
    c3.metric("Lost", wl["lost"])
    c4.metric("Win Rate", f"{wl['overall_win_rate']}%" if wl["overall_win_rate"] else "—")

    # Charts
    col_l, col_r = st.columns(2)

    with col_l:
        # Win rate by product
        by_product = wl.get("by_product", {})
        if by_product:
            rows = []
            for prod, counts in by_product.items():
                won = counts.get("won", 0)
                lost = counts.get("lost", 0)
                total = won + lost
                rows.append({
                    "product": prod,
                    "won": won,
                    "lost": lost,
                    "win_rate": round(won / total * 100, 1) if total > 0 else 0,
                })
            df_bp = pd.DataFrame(rows).sort_values("win_rate", ascending=True)
            fig = px.bar(
                df_bp,
                x="win_rate",
                y="product",
                orientation="h",
                labels={"win_rate": "Win Rate (%)", "product": "Product"},
                title="Win Rate by Product",
                color="win_rate",
                color_continuous_scale="RdYlGn",
                range_color=[0, 100],
            )
            fig.update_layout(height=300, margin=dict(t=40), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        # Lost to competitors
        by_comp = wl.get("by_competitor", {})
        if by_comp:
            df_comp = pd.DataFrame(
                list(by_comp.items()), columns=["competitor", "deals_lost"]
            ).sort_values("deals_lost", ascending=False)
            fig2 = px.bar(
                df_comp,
                x="deals_lost",
                y="competitor",
                orientation="h",
                labels={"deals_lost": "Deals Lost", "competitor": "Competitor"},
                title="Deals Lost By Competitor",
                color="deals_lost",
                color_continuous_scale="Reds",
            )
            fig2.update_layout(height=300, margin=dict(t=40), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # Win rate by customer segment
    by_seg = wl.get("by_segment", {})
    if by_seg:
        rows = []
        for seg, counts in by_seg.items():
            won = counts.get("won", 0)
            lost = counts.get("lost", 0)
            rows.append({"segment": seg or "unknown", "won": won, "lost": lost})
        df_seg = pd.DataFrame(rows)
        fig3 = px.bar(
            df_seg,
            x="segment",
            y=["won", "lost"],
            barmode="group",
            color_discrete_map={"won": "#2ecc71", "lost": "#e74c3c"},
            labels={"segment": "Customer Type", "value": "Quotes"},
            title="Won vs Lost by Customer Type",
        )
        fig3.update_layout(height=280, margin=dict(t=40))
        st.plotly_chart(fig3, use_container_width=True)

    # AI Analysis
    if st.button("Generate AI Win/Loss Analysis", type="primary"):
        if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
            st.warning("Set ANTHROPIC_API_KEY to enable AI analysis.")
        else:
            response_text = ""
            stream_box = st.empty()
            try:
                for chunk in claude_client.stream_win_loss_analysis(wl):
                    response_text += chunk
                    stream_box.markdown(response_text + "▌")
                stream_box.markdown(response_text)
            except Exception as e:
                st.error(f"AI error: {e}")


# ── 3. Competitor Price Comparison ─────────────────────────────────────────────
elif report_type.startswith("3"):
    st.subheader("Competitor Price Comparison")

    comp_data = analysis_stats.competitor_comparison_summary()
    our_df = comp_data["our_prices"]
    comp_df = comp_data["competitor_prices"]

    if comp_df.empty:
        st.info("No competitor pricing data found. Add data in **Data Ingestion**.")
        st.stop()

    # Merge our prices with competitor prices
    if not our_df.empty and not comp_df.empty:
        merged = comp_df.merge(our_df, on="product_name", how="left")
        merged["price_delta"] = (merged["comp_avg_price"] - merged["our_avg_price"]).round(2)
        merged["pct_diff"] = (
            (merged["comp_avg_price"] - merged["our_avg_price"]) / merged["our_avg_price"] * 100
        ).round(1)

        st.dataframe(
            merged[["product_name", "competitor_name", "comp_avg_price", "our_avg_price",
                    "price_delta", "pct_diff", "last_observed"]].rename(columns={
                "product_name": "Product",
                "competitor_name": "Competitor",
                "comp_avg_price": "Competitor Avg ($)",
                "our_avg_price": "Our Avg ($)",
                "price_delta": "Delta ($)",
                "pct_diff": "Delta (%)",
                "last_observed": "Last Observed",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Chart: our price vs competitors
        products = merged["product_name"].unique().tolist()
        selected_products = st.multiselect("Filter products", products, default=products[:5])
        filtered = merged[merged["product_name"].isin(selected_products)]

        if not filtered.empty:
            # Add our own prices as rows for comparison
            our_rows = filtered[["product_name", "our_avg_price"]].drop_duplicates()
            our_rows = our_rows.rename(columns={"our_avg_price": "price"})
            our_rows["entity"] = "OUR PRICE"
            comp_rows = filtered[["product_name", "comp_avg_price", "competitor_name"]].copy()
            comp_rows = comp_rows.rename(columns={"comp_avg_price": "price", "competitor_name": "entity"})
            all_rows = pd.concat([our_rows, comp_rows], ignore_index=True)
            all_rows = all_rows.dropna(subset=["price"])

            color_map = {"OUR PRICE": "#3498db"}
            fig = px.bar(
                all_rows,
                x="entity",
                y="price",
                facet_col="product_name",
                labels={"entity": "Entity", "price": "Price ($)"},
                color="entity",
                title="Our Price vs Competitors (by Product)",
            )
            fig.update_layout(height=380, margin=dict(t=60))
            st.plotly_chart(fig, use_container_width=True)

    # Competitor prices over time
    st.subheader("Competitor Price History")
    df_hist = db.query_df("""
        SELECT competitor_name, product_name, listed_price, observed_date
        FROM competitor_prices
        WHERE listed_price IS NOT NULL AND observed_date IS NOT NULL
        ORDER BY observed_date
    """)
    if not df_hist.empty:
        product_filter = st.selectbox("Select product for history", df_hist["product_name"].unique())
        df_prod = df_hist[df_hist["product_name"] == product_filter]
        if not df_prod.empty:
            fig_hist = px.line(
                df_prod,
                x="observed_date",
                y="listed_price",
                color="competitor_name",
                markers=True,
                labels={"observed_date": "Date", "listed_price": "Price ($)", "competitor_name": "Competitor"},
                title=f"Price History — {product_filter}",
            )
            fig_hist.update_layout(height=300)
            st.plotly_chart(fig_hist, use_container_width=True)

    # AI Analysis
    if st.button("Generate AI Competitor Analysis", type="primary"):
        if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
            st.warning("Set ANTHROPIC_API_KEY to enable AI analysis.")
        else:
            response_text = ""
            stream_box = st.empty()
            try:
                for chunk in claude_client.stream_competitor_analysis(comp_data):
                    response_text += chunk
                    stream_box.markdown(response_text + "▌")
                stream_box.markdown(response_text)
            except Exception as e:
                st.error(f"AI error: {e}")


# ── 4. Margin Analysis ─────────────────────────────────────────────────────────
elif report_type.startswith("4"):
    st.subheader("Margin Analysis (including Shipping & Warehousing)")

    margin_data = analysis_stats.margin_summary()
    sales_df = margin_data["sales"]
    costs_df = margin_data["costs"]
    logistics_df = margin_data["logistics"]

    if sales_df.empty:
        st.info("No sales data found.")
        st.stop()

    # Merge to compute margins
    merged = sales_df.copy()
    if not costs_df.empty:
        merged = merged.merge(costs_df, on="product_name", how="left")
    else:
        merged["avg_our_cost"] = None

    if not logistics_df.empty:
        merged = merged.merge(logistics_df[["product_name", "total_logistics"]], on="product_name", how="left")
    else:
        merged["total_logistics"] = 0

    merged["total_logistics"] = merged["total_logistics"].fillna(0)
    merged["avg_our_cost"] = merged["avg_our_cost"].fillna(0) if "avg_our_cost" in merged.columns else 0
    merged["effective_cost"] = merged["avg_our_cost"] + merged["total_logistics"]
    merged["gross_margin"] = (
        (merged["avg_net_price"] - merged["effective_cost"]) / merged["avg_net_price"] * 100
    ).where(merged["avg_net_price"] > 0).round(1)

    # Display table
    display = merged[[
        "product_name", "customer_type", "avg_net_price", "avg_our_cost",
        "total_logistics", "effective_cost", "gross_margin", "sale_count"
    ]].rename(columns={
        "product_name": "Product",
        "customer_type": "Channel",
        "avg_net_price": "Avg Net ($)",
        "avg_our_cost": "Avg Cost ($)",
        "total_logistics": "Logistics ($)",
        "effective_cost": "Total Cost ($)",
        "gross_margin": "Gross Margin (%)",
        "sale_count": "Sales",
    })
    # Round numeric columns
    for col in ["Avg Net ($)", "Avg Cost ($)", "Logistics ($)", "Total Cost ($)"]:
        if col in display.columns:
            display[col] = display[col].round(2)

    st.dataframe(display, use_container_width=True, hide_index=True)

    # Margin chart by product
    if "gross_margin" in merged.columns and merged["gross_margin"].notna().any():
        chart_df = merged.dropna(subset=["gross_margin"])
        fig = px.bar(
            chart_df,
            x="product_name",
            y="gross_margin",
            color="customer_type",
            barmode="group",
            labels={"product_name": "Product", "gross_margin": "Gross Margin (%)", "customer_type": "Channel"},
            title="Gross Margin by Product and Channel",
        )
        fig.add_hline(y=0, line_dash="solid", line_color="red", annotation_text="break-even")
        fig.update_layout(height=350, margin=dict(t=50))
        st.plotly_chart(fig, use_container_width=True)

    # AI Analysis
    if st.button("Generate AI Margin Analysis", type="primary"):
        if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
            st.warning("Set ANTHROPIC_API_KEY to enable AI analysis.")
        else:
            response_text = ""
            stream_box = st.empty()
            try:
                for chunk in claude_client.stream_margin_analysis(margin_data):
                    response_text += chunk
                    stream_box.markdown(response_text + "▌")
                stream_box.markdown(response_text)
            except Exception as e:
                st.error(f"AI error: {e}")
