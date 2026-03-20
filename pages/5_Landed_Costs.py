"""
Landed Costs — manage all-in per-unit cost per SKU, effective by date.
These costs feed directly into margin calculations across the app.
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

import database as db

st.set_page_config(page_title="Landed Costs", page_icon="🏷️", layout="wide")
st.title("🏷️ Landed Costs")
st.caption(
    "Record the all-in landed cost per unit for each SKU as of a specific date. "
    "The most recent entry per SKU is used throughout margin and pricing calculations."
)

# ── Current Cost Grid ──────────────────────────────────────────────────────────
st.subheader("Current Landed Costs")

current = db.get_current_landed_costs()
all_products = db.get_all_products()

if current:
    df_current = pd.DataFrame(current)

    # Merge in products we know about but have no cost yet
    known_costs = set(df_current["product_name"].str.lower())
    missing = [p for p in all_products if p.lower() not in known_costs]

    display = df_current[
        [c for c in ["product_name", "sku", "landed_cost", "effective_date", "notes"]
         if c in df_current.columns]
    ].rename(columns={
        "product_name": "Product",
        "sku": "SKU",
        "landed_cost": "Landed Cost ($)",
        "effective_date": "Effective Date",
        "notes": "Notes",
    })
    display["Landed Cost ($)"] = display["Landed Cost ($)"].map("${:,.2f}".format)

    st.dataframe(display, use_container_width=True, hide_index=True)

    if missing:
        st.info(
            f"**{len(missing)} product(s) have no landed cost yet:** "
            + ", ".join(f"`{p}`" for p in missing[:8])
            + (" …" if len(missing) > 8 else "")
        )

    # Bar chart
    df_chart = df_current.copy()
    fig = px.bar(
        df_chart.sort_values("landed_cost"),
        x="landed_cost",
        y="product_name",
        orientation="h",
        labels={"landed_cost": "Landed Cost ($)", "product_name": "Product"},
        text="landed_cost",
        color="landed_cost",
        color_continuous_scale="Blues",
    )
    fig.update_traces(texttemplate="$%{text:,.2f}", textposition="outside")
    fig.update_layout(height=max(220, len(df_chart) * 42), margin=dict(t=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No landed costs recorded yet. Add your first entry below.")
    if all_products:
        st.info(
            f"Products in the database with no cost: "
            + ", ".join(f"`{p}`" for p in all_products[:10])
        )

st.divider()

# ── Add / Update Form ──────────────────────────────────────────────────────────
st.subheader("Add / Update Landed Cost")
st.caption(
    "Enter the **total all-in cost per unit** (product cost + freight + duties + any other "
    "landed costs). Each entry is dated so you can track cost changes over time."
)

with st.form("landed_cost_form", clear_on_submit=True):
    c1, c2 = st.columns(2)

    # Product name — allow free-text or pick from known products
    product_options = ["— type a new product —"] + all_products
    product_choice = c1.selectbox("Product (select existing or type new)", product_options)
    product_name_manual = c1.text_input(
        "Product Name (if typing new)",
        placeholder="Leave blank to use the selection above",
    )
    sku = c2.text_input("SKU", placeholder="e.g. PUMP-X200")

    c1, c2, c3 = st.columns(3)
    landed_cost = c1.number_input(
        "Landed Cost per Unit ($) *",
        min_value=0.0,
        format="%.4f",
        help="Total all-in cost: product purchase price + inbound freight + duties + handling",
    )
    effective_date = c2.date_input("Effective Date *", value=date.today())
    notes = c3.text_input("Notes", placeholder="e.g. Q1 2025 price list, includes import duty")

    submitted = st.form_submit_button("Save Landed Cost", type="primary")

    if submitted:
        # Resolve product name
        product_name = product_name_manual.strip() or (
            "" if product_choice.startswith("—") else product_choice
        )
        if not product_name:
            st.error("Select a product or type a new product name.")
        elif landed_cost <= 0:
            st.error("Landed cost must be greater than $0.00.")
        else:
            db.insert_landed_cost({
                "product_name": product_name,
                "sku": sku.strip() or None,
                "landed_cost": round(landed_cost, 4),
                "effective_date": effective_date.isoformat(),
                "notes": notes.strip() or None,
            })
            st.success(
                f"Landed cost **${landed_cost:,.4f}** saved for **{product_name}** "
                f"(effective {effective_date})."
            )
            st.rerun()

st.divider()

# ── History per product ────────────────────────────────────────────────────────
st.subheader("Cost History by Product")

products_with_costs = list({r["product_name"] for r in current}) if current else []

if not products_with_costs:
    st.info("No history yet.")
else:
    selected_product = st.selectbox("Select product", sorted(products_with_costs))
    history = db.get_landed_cost_history(selected_product)

    if history:
        df_hist = pd.DataFrame(history)

        # Show table with delete option
        display_hist = df_hist[
            [c for c in ["id", "effective_date", "sku", "landed_cost", "notes", "created_at"]
             if c in df_hist.columns]
        ].rename(columns={
            "id": "ID",
            "effective_date": "Effective Date",
            "sku": "SKU",
            "landed_cost": "Landed Cost ($)",
            "notes": "Notes",
            "created_at": "Recorded At",
        })
        display_hist["Landed Cost ($)"] = display_hist["Landed Cost ($)"].map("${:,.4f}".format)
        st.dataframe(display_hist, use_container_width=True, hide_index=True)

        # Cost-over-time chart (if multiple entries)
        if len(df_hist) > 1:
            fig_hist = px.line(
                df_hist.sort_values("effective_date"),
                x="effective_date",
                y="landed_cost",
                markers=True,
                labels={"effective_date": "Effective Date", "landed_cost": "Landed Cost ($)"},
                title=f"Cost History — {selected_product}",
            )
            fig_hist.update_layout(height=260, margin=dict(t=40))
            st.plotly_chart(fig_hist, use_container_width=True)

        # Delete entry
        with st.expander("Delete an entry"):
            del_id = st.number_input(
                "Entry ID to delete", min_value=1, step=1, key="del_landed_id"
            )
            if st.button("Delete", type="secondary"):
                db.delete_landed_cost(int(del_id))
                st.success(f"Entry {int(del_id)} deleted.")
                st.rerun()
