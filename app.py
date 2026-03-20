"""
Pricing Intelligence Tool — Dashboard (main page)
Run with: streamlit run app.py
"""
import os
from pathlib import Path

import plotly.express as px
import streamlit as st

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import database as db

st.set_page_config(
    page_title="Pricing Intelligence",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💰 Pricing Intelligence Dashboard")
st.caption("Evidence-based pricing, powered by data + Claude AI")

# ── API key check ─────────────────────────────────────────────────────────────
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning(
        "**ANTHROPIC_API_KEY not set.** "
        "AI analysis features will be disabled. "
        "Add your key to a `.env` file or set the environment variable.",
        icon="⚠️",
    )

# ── Stats ─────────────────────────────────────────────────────────────────────
stats = db.get_dashboard_stats()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Products Tracked", stats["product_count"])
col2.metric("Sales Records", stats["total_sales"])
col3.metric("Quotes", stats["total_quotes"])
col4.metric(
    "Win Rate",
    f"{stats['win_rate']:.0f}%" if stats["win_rate"] is not None else "—",
)
col5.metric("Competitors Tracked", stats["competitor_count"])

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Win / Loss by Product")
    try:
        df_wl = db.query_df("""
            SELECT product_name, status, COUNT(*) AS count
            FROM quotes
            WHERE status IN ('won','lost')
            GROUP BY product_name, status
            ORDER BY product_name
        """)
        if not df_wl.empty:
            fig = px.bar(
                df_wl,
                x="product_name",
                y="count",
                color="status",
                color_discrete_map={"won": "#2ecc71", "lost": "#e74c3c"},
                barmode="group",
                labels={"product_name": "Product", "count": "Quotes", "status": "Outcome"},
            )
            fig.update_layout(showlegend=True, height=320, margin=dict(t=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No quote data yet. Add quotes in **Data Ingestion**.")
    except Exception as e:
        st.error(f"Chart error: {e}")

with col_right:
    st.subheader("Average Net Price by Product")
    try:
        df_price = db.query_df("""
            SELECT product_name, AVG(net_price) AS avg_net, COUNT(*) AS n
            FROM sales
            WHERE net_price IS NOT NULL
            GROUP BY product_name
            ORDER BY avg_net DESC
            LIMIT 15
        """)
        if not df_price.empty:
            df_price["avg_net"] = df_price["avg_net"].round(2)
            fig2 = px.bar(
                df_price,
                x="avg_net",
                y="product_name",
                orientation="h",
                labels={"avg_net": "Avg Net Price ($)", "product_name": "Product"},
                text="avg_net",
                color="avg_net",
                color_continuous_scale="Blues",
            )
            fig2.update_layout(showlegend=False, height=320, margin=dict(t=20))
            fig2.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No sales data yet. Add sales in **Data Ingestion**.")
    except Exception as e:
        st.error(f"Chart error: {e}")

# ── Win rate trend ─────────────────────────────────────────────────────────────
st.subheader("Win Rate Trend (monthly)")
try:
    df_trend = db.query_df("""
        SELECT
            strftime('%Y-%m', quote_date) AS month,
            SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) AS won,
            SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) AS lost
        FROM quotes
        WHERE status IN ('won','lost') AND quote_date IS NOT NULL
        GROUP BY month
        ORDER BY month
    """)
    if not df_trend.empty and len(df_trend) >= 2:
        df_trend["win_rate"] = df_trend["won"] / (df_trend["won"] + df_trend["lost"]) * 100
        fig3 = px.line(
            df_trend,
            x="month",
            y="win_rate",
            markers=True,
            labels={"month": "Month", "win_rate": "Win Rate (%)"},
        )
        fig3.update_layout(height=260, margin=dict(t=10))
        fig3.add_hline(
            y=df_trend["win_rate"].mean(),
            line_dash="dash",
            line_color="gray",
            annotation_text="average",
        )
        st.plotly_chart(fig3, use_container_width=True)
    elif not df_trend.empty:
        st.info("Need at least 2 months of quote data to show a trend.")
    else:
        st.info("No quote data yet.")
except Exception as e:
    st.error(f"Trend chart error: {e}")

# ── Recent activity ────────────────────────────────────────────────────────────
st.subheader("Recent Data Imports")
recent = db.get_recent_ingestions(10)
if recent:
    import pandas as pd
    df_recent = pd.DataFrame(recent)[["created_at", "source_type", "source_description", "records_imported"]]
    df_recent.columns = ["Imported At", "Source Type", "Description", "Records"]
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.info(
        "No data imported yet. Go to **Data Ingestion** in the sidebar to get started.",
        icon="👈",
    )

# ── Sidebar nav hint ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Navigation")
    st.markdown("""
- **Dashboard** ← you are here
- **Data Ingestion** — add data manually, upload files, or scrape URLs
- **Product Pricing** — per-product analysis + AI recommendations
- **Quote Analyzer** — assess a new quote with AI
- **Reports** — generate full analysis reports
""")
