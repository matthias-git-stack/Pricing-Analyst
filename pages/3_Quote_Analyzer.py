"""
Quote Analyzer — enter a new or existing quote and get an AI assessment.
"""
from datetime import date

import streamlit as st

import database as db
from analysis import stats as analysis_stats, claude_client

st.set_page_config(page_title="Quote Analyzer", page_icon="🎯", layout="wide")
st.title("🎯 Quote Analyzer")
st.caption("Enter quote details to get an AI assessment of win likelihood and pricing.")

if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
    st.warning("Set ANTHROPIC_API_KEY to enable AI analysis.", icon="⚠️")

# ── Quote Input ────────────────────────────────────────────────────────────────
with st.form("quote_form"):
    st.subheader("Quote Details")

    c1, c2 = st.columns(2)
    product_name = c1.text_input("Product Name *")
    sku = c2.text_input("SKU (optional)")

    c1, c2, c3 = st.columns(3)
    customer_name = c1.text_input("Customer Name")
    customer_type = c2.selectbox("Customer Type", ["", "end-user", "reseller"])
    customer_industry = c3.text_input("Industry")

    c1, c2 = st.columns(2)
    customer_size = c1.selectbox("Customer Size", ["", "small", "mid-market", "enterprise"])
    quote_date = c2.date_input("Quote Date", value=date.today())

    c1, c2, c3 = st.columns(3)
    gross_price = c1.number_input("Gross / List Price ($)", min_value=0.0, format="%.2f")
    discount_pct = c2.number_input("Proposed Discount (%)", min_value=0.0, max_value=100.0, format="%.1f")
    quantity = c3.number_input("Quantity", min_value=1, value=1)

    net_price = gross_price * (1 - discount_pct / 100) if gross_price > 0 else 0.0
    st.metric("Proposed Net Price", f"${net_price:.2f}")

    competitor_context = st.text_input(
        "Known competitor in this deal (if any)", placeholder="e.g. Acme Corp"
    )
    additional_context = st.text_area(
        "Additional context",
        placeholder="e.g. customer mentioned they're also evaluating X, budget is Y, decision timeline is Z",
    )

    c1, c2 = st.columns(2)
    save_quote = c1.checkbox("Also save this quote to the database", value=True)
    submitted = st.form_submit_button("Analyse Quote", type="primary")

if submitted:
    if not product_name.strip():
        st.error("Product name is required.")
        st.stop()

    quote = {
        "product_name": product_name.strip(),
        "sku": sku or None,
        "customer_name": customer_name or None,
        "customer_type": customer_type or None,
        "customer_industry": customer_industry or None,
        "customer_size": customer_size or None,
        "gross_price": gross_price if gross_price > 0 else None,
        "discount_pct": discount_pct,
        "net_price": round(net_price, 2) if net_price > 0 else None,
        "quantity": quantity,
        "quote_date": quote_date.isoformat(),
        "competitor_context": competitor_context or None,
        "additional_context": additional_context or None,
    }

    # Save to DB if requested (as pending)
    if save_quote:
        save_payload = {k: v for k, v in quote.items()
                       if k not in ("competitor_context", "additional_context")}
        save_payload["status"] = "pending"
        if competitor_context:
            save_payload["notes"] = f"Competitor: {competitor_context}. {additional_context or ''}"
        db.insert_quote(save_payload)
        db.log_ingestion("manual", f"Quote (pending): {product_name}", 1)
        st.success(f"Quote saved to database as **pending**.")

    # Load historical stats for this product
    with st.spinner("Loading historical data…"):
        product_stats = analysis_stats.product_price_stats(product_name.strip())

    # Show context
    st.divider()
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("Historical Context")
        if product_stats["sales_count"] > 0 or product_stats["quote_count"] > 0:
            st.metric("Sales Records", product_stats["sales_count"])
            st.metric("Avg Net Price (historical)",
                     f"${product_stats['net_price_avg']}" if product_stats["net_price_avg"] else "—")
            st.metric("Win Rate",
                     f"{product_stats['win_rate']}%" if product_stats["win_rate"] is not None else "—")
            st.metric("Avg Won Price",
                     f"${product_stats['avg_won_price']}" if product_stats["avg_won_price"] else "—")
            st.metric("Avg Lost Price",
                     f"${product_stats['avg_lost_price']}" if product_stats["avg_lost_price"] else "—")
            if product_stats["competitor_price_avg"]:
                st.metric("Competitor Avg Price", f"${product_stats['competitor_price_avg']}")
        else:
            st.info("No historical data for this product yet.")

    with col_r:
        st.subheader("AI Assessment")
        if not __import__("os").environ.get("ANTHROPIC_API_KEY"):
            st.warning("Set ANTHROPIC_API_KEY to enable AI analysis.")
        else:
            response_text = ""
            stream_box = st.empty()
            try:
                for chunk in claude_client.stream_quote_assessment(quote, product_stats):
                    response_text += chunk
                    stream_box.markdown(response_text + "▌")
                stream_box.markdown(response_text)
            except Exception as e:
                st.error(f"AI error: {e}")

# ── Pending Quotes ─────────────────────────────────────────────────────────────
st.divider()
st.subheader("Pending Quotes")
df_pending = db.query_df(
    "SELECT * FROM quotes WHERE status='pending' ORDER BY quote_date DESC LIMIT 20"
)
if not df_pending.empty:
    display_cols = [c for c in [
        "quote_date", "product_name", "customer_name", "customer_type",
        "net_price", "discount_pct", "notes"
    ] if c in df_pending.columns]
    st.dataframe(df_pending[display_cols], use_container_width=True, hide_index=True)

    st.markdown("**Update quote status:**")
    col_a, col_b, col_c = st.columns(3)
    quote_id = col_a.number_input("Quote ID", min_value=1, step=1, key="update_id")
    new_status = col_b.selectbox("New Status", ["won", "lost"], key="update_status")
    lost_to = col_c.text_input("Lost to (if lost)", key="update_lost_to")
    if st.button("Update Status"):
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE quotes SET status=?, lost_to_competitor=? WHERE id=?",
                (new_status, lost_to or None, int(quote_id)),
            )
        st.success(f"Quote {int(quote_id)} updated to **{new_status}**.")
        st.rerun()
else:
    st.info("No pending quotes.")
