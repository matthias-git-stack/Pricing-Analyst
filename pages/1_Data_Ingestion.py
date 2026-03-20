"""
Data Ingestion page — manual entry, file upload, PDF upload, URL scrape.
"""
import io
from datetime import date

import streamlit as st

import database as db
from ingestion import spreadsheet, pdf_parser, scraper

st.set_page_config(page_title="Data Ingestion", page_icon="📥", layout="wide")
st.title("📥 Data Ingestion")
st.caption("Add pricing data via manual entry, file upload, PDF, or URL scrape.")

tab_manual, tab_file, tab_pdf, tab_url = st.tabs(
    ["✏️ Manual Entry", "📊 Excel / CSV Upload", "📄 PDF Upload", "🌐 URL Scrape"]
)

# ── TAB 1: Manual Entry ────────────────────────────────────────────────────────
with tab_manual:
    record_type = st.selectbox(
        "Record type",
        ["Sale", "Quote", "Competitor Price", "Distributor Price", "Logistics Cost"],
    )

    with st.form("manual_entry_form"):
        if record_type == "Sale":
            c1, c2 = st.columns(2)
            product_name = c1.text_input("Product Name *")
            sku = c2.text_input("SKU (optional)")

            c1, c2, c3 = st.columns(3)
            customer_name = c1.text_input("Customer Name")
            customer_type = c2.selectbox("Customer Type", ["", "end-user", "reseller"])
            customer_industry = c3.text_input("Industry (e.g. manufacturing)")

            c1, c2 = st.columns(2)
            customer_size = c1.selectbox("Customer Size", ["", "small", "mid-market", "enterprise"])
            sale_date = c2.date_input("Sale Date", value=date.today())

            c1, c2, c3 = st.columns(3)
            gross_price = c1.number_input("Gross / List Price ($)", min_value=0.0, format="%.2f")
            discount_pct = c2.number_input("Discount (%)", min_value=0.0, max_value=100.0, format="%.1f")
            quantity = c3.number_input("Quantity", min_value=1, value=1)
            net_price = gross_price * (1 - discount_pct / 100) if gross_price > 0 else 0.0
            st.metric("Calculated Net Price", f"${net_price:.2f}")
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Sale", type="primary")
            if submitted:
                if not product_name.strip():
                    st.error("Product name is required.")
                else:
                    db.insert_sale({
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
                        "sale_date": sale_date.isoformat(),
                        "notes": notes or None,
                        "source": "manual",
                    })
                    db.log_ingestion("manual", f"Sale: {product_name}", 1)
                    st.success(f"Sale saved for **{product_name}** — net price ${net_price:.2f}")

        elif record_type == "Quote":
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
            gross_price = c1.number_input("Gross Price ($)", min_value=0.0, format="%.2f")
            discount_pct = c2.number_input("Discount (%)", min_value=0.0, max_value=100.0, format="%.1f")
            quantity = c3.number_input("Quantity", min_value=1, value=1)
            net_price = gross_price * (1 - discount_pct / 100) if gross_price > 0 else 0.0
            st.metric("Calculated Net Price", f"${net_price:.2f}")

            c1, c2 = st.columns(2)
            status = c1.selectbox("Quote Status *", ["pending", "won", "lost"])
            lost_to = c2.text_input("Lost to Competitor (if lost)")
            reason = st.text_area("Win/Loss Reason")
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Quote", type="primary")
            if submitted:
                if not product_name.strip():
                    st.error("Product name is required.")
                else:
                    db.insert_quote({
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
                        "status": status,
                        "lost_to_competitor": lost_to or None,
                        "win_loss_reason": reason or None,
                        "notes": notes or None,
                        "source": "manual",
                    })
                    db.log_ingestion("manual", f"Quote: {product_name} ({status})", 1)
                    st.success(f"Quote saved — **{product_name}** ({status})")

        elif record_type == "Competitor Price":
            c1, c2 = st.columns(2)
            competitor_name = c1.text_input("Competitor Name *")
            product_name = c2.text_input("Their Product Name *")

            c1, c2, c3 = st.columns(3)
            listed_price = c1.number_input("Listed Price ($)", min_value=0.0, format="%.2f")
            source_type = c2.selectbox("Source Type", ["hearsay", "catalog", "url", "pdf"])
            observed_date = c3.date_input("Date Observed", value=date.today())
            source_url = st.text_input("Source URL (if applicable)")
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Competitor Price", type="primary")
            if submitted:
                if not competitor_name.strip() or not product_name.strip():
                    st.error("Competitor name and product name are required.")
                else:
                    db.insert_competitor_price({
                        "competitor_name": competitor_name.strip(),
                        "product_name": product_name.strip(),
                        "listed_price": listed_price if listed_price > 0 else None,
                        "source_type": source_type,
                        "source_url": source_url or None,
                        "observed_date": observed_date.isoformat(),
                        "notes": notes or None,
                    })
                    db.log_ingestion("manual", f"Competitor: {competitor_name} — {product_name}", 1)
                    st.success("Competitor price saved.")

        elif record_type == "Distributor Price":
            c1, c2 = st.columns(2)
            distributor_name = c1.text_input("Distributor Name *")
            product_name = c2.text_input("Product Name *")

            c1, c2 = st.columns(2)
            sku = c1.text_input("SKU (optional)")
            observed_date = c2.date_input("Date Observed", value=date.today())

            c1, c2 = st.columns(2)
            street_price = c1.number_input("Their Street Price ($)", min_value=0.0, format="%.2f")
            our_cost = c2.number_input("Our Cost from Distributor ($)", min_value=0.0, format="%.2f")
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Distributor Price", type="primary")
            if submitted:
                if not distributor_name.strip() or not product_name.strip():
                    st.error("Distributor name and product name are required.")
                else:
                    db.insert_distributor_price({
                        "distributor_name": distributor_name.strip(),
                        "product_name": product_name.strip(),
                        "sku": sku or None,
                        "street_price": street_price if street_price > 0 else None,
                        "our_cost": our_cost if our_cost > 0 else None,
                        "observed_date": observed_date.isoformat(),
                        "notes": notes or None,
                        "source": "manual",
                    })
                    db.log_ingestion("manual", f"Distributor: {distributor_name} — {product_name}", 1)
                    st.success("Distributor price saved.")

        elif record_type == "Logistics Cost":
            c1, c2 = st.columns(2)
            product_name = c1.text_input("Product Name")
            sku = c2.text_input("SKU (optional)")

            c1, c2, c3 = st.columns(3)
            shipping = c1.number_input("Shipping Cost / Unit ($)", min_value=0.0, format="%.2f")
            warehousing = c2.number_input("Warehousing / Unit ($)", min_value=0.0, format="%.2f")
            other = c3.number_input("Other Cost / Unit ($)", min_value=0.0, format="%.2f")

            effective_date = st.date_input("Effective Date", value=date.today())
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Save Logistics Cost", type="primary")
            if submitted:
                db.insert_logistics_cost({
                    "product_name": product_name.strip() or None,
                    "sku": sku or None,
                    "shipping_cost_per_unit": shipping,
                    "warehousing_cost_per_unit": warehousing,
                    "other_cost_per_unit": other,
                    "effective_date": effective_date.isoformat(),
                    "notes": notes or None,
                })
                db.log_ingestion("manual", f"Logistics: {product_name or 'general'}", 1)
                st.success("Logistics cost saved.")

# ── TAB 2: Excel / CSV Upload ─────────────────────────────────────────────────
with tab_file:
    st.markdown("""
Upload an Excel (.xlsx) or CSV file. The tool will auto-detect which table
the data belongs to based on column names.

**Column name hints** (flexible, case-insensitive):
| Data Type | Key Columns Needed |
|---|---|
| Sales | `product_name`, `net_price` / `gross_price`, `sale_date` |
| Quotes | `product_name`, `net_price`, `status` (won/lost/pending) |
| Competitor Prices | `competitor_name`, `product_name`, `listed_price` |
| Distributor Prices | `distributor_name`, `product_name`, `street_price` |
| Logistics Costs | `product_name`, `shipping_cost_per_unit` |
""")

    uploaded_file = st.file_uploader(
        "Choose a file", type=["xlsx", "xls", "csv"], key="file_uploader"
    )
    record_type_override = st.selectbox(
        "Record type (leave on Auto-detect unless needed)",
        ["auto", "sales", "quotes", "competitor_prices", "distributor_prices", "logistics_costs"],
        key="file_record_type",
    )

    if uploaded_file and st.button("Import File", type="primary"):
        with st.spinner("Parsing file…"):
            try:
                count, warnings = spreadsheet.load_file(
                    uploaded_file,
                    record_type=record_type_override,
                    source_label=uploaded_file.name,
                )
                st.success(f"Imported **{count}** records from `{uploaded_file.name}`")
                if warnings:
                    with st.expander(f"⚠️ {len(warnings)} warnings"):
                        for w in warnings:
                            st.warning(w)
            except Exception as e:
                st.error(f"Import failed: {e}")

# ── TAB 3: PDF Upload ─────────────────────────────────────────────────────────
with tab_pdf:
    st.markdown("""
Upload a PDF price list, quote document, or invoice.
The tool will try to extract tables automatically. If that fails, it uses
the AI to read the document and extract pricing.
""")

    pdf_type = st.radio(
        "Document type",
        ["Competitor Price List", "Distributor Price List"],
        horizontal=True,
    )
    c1, c2 = st.columns(2)
    entity_name = c1.text_input(
        "Competitor name" if "Competitor" in pdf_type else "Distributor name"
    )
    pdf_observed_date = c2.date_input("Date Observed", value=date.today(), key="pdf_date")
    pdf_url = st.text_input("Source URL (optional)")
    pdf_file = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_uploader")

    if pdf_file and st.button("Process PDF", type="primary"):
        if not entity_name.strip():
            st.error("Please enter the entity name.")
        else:
            with st.spinner("Processing PDF…"):
                try:
                    raw_bytes = pdf_file.read()
                    if "Competitor" in pdf_type:
                        count, warnings = pdf_parser.parse_competitor_pdf(
                            io.BytesIO(raw_bytes),
                            entity_name.strip(),
                            pdf_observed_date.isoformat(),
                            pdf_url or "",
                        )
                    else:
                        count, warnings = pdf_parser.parse_distributor_pdf(
                            io.BytesIO(raw_bytes),
                            entity_name.strip(),
                            pdf_observed_date.isoformat(),
                        )

                    if count > 0:
                        st.success(f"Extracted **{count}** price records.")
                    else:
                        st.warning("Automatic extraction found no tables. Using AI to read the document…")

                    if warnings or count == 0:
                        # Try AI extraction
                        text = pdf_parser.extract_text(io.BytesIO(raw_bytes))
                        if text.strip():
                            from analysis import claude_client
                            st.markdown("**AI-extracted pricing data:**")
                            result_text = ""
                            with st.spinner("AI is reading the PDF…"):
                                stream_box = st.empty()
                                for chunk in claude_client.stream_pdf_extraction_analysis(
                                    text,
                                    "competitor price list" if "Competitor" in pdf_type else "distributor price list",
                                    entity_name.strip(),
                                ):
                                    result_text += chunk
                                    stream_box.markdown(result_text + "▌")
                                stream_box.markdown(result_text)
                            st.info(
                                "AI analysis complete. "
                                "Review the output and use Manual Entry to save specific prices."
                            )
                        else:
                            st.error("Could not extract text from this PDF.")

                except Exception as e:
                    st.error(f"PDF processing error: {e}")

# ── TAB 4: URL Scrape ─────────────────────────────────────────────────────────
with tab_url:
    st.markdown("""
Paste a competitor or distributor product page URL to extract pricing.
The tool attempts automatic extraction; review before saving.
""")

    scrape_type = st.radio(
        "Page type", ["Competitor Product Page", "Distributor Product Page"], horizontal=True
    )
    c1, c2 = st.columns(2)
    scrape_url = c1.text_input("Product Page URL")
    scrape_entity = c2.text_input(
        "Competitor name" if "Competitor" in scrape_type else "Distributor name"
    )
    c1, c2 = st.columns(2)
    scrape_product_override = c1.text_input("Product Name (override auto-detected name)")
    scrape_date = c2.date_input("Date Observed", value=date.today(), key="scrape_date")

    if st.button("Scrape URL", type="primary"):
        if not scrape_url.strip() or not scrape_entity.strip():
            st.error("URL and entity name are required.")
        else:
            with st.spinner(f"Fetching {scrape_url}…"):
                try:
                    if "Competitor" in scrape_type:
                        result = scraper.scrape_competitor_price(
                            scrape_url.strip(),
                            scrape_entity.strip(),
                            scrape_product_override.strip() or None,
                            scrape_date.isoformat(),
                        )
                    else:
                        result = scraper.scrape_distributor_price(
                            scrape_url.strip(),
                            scrape_entity.strip(),
                            scrape_product_override.strip() or None,
                            scrape_date.isoformat(),
                        )

                    if "error" in result:
                        st.error(f"Scrape error: {result['error']}")
                    else:
                        st.success("Page scraped successfully. Review and save:")

                        # Editable form for the scraped result
                        with st.form("confirm_scrape"):
                            price_field = "listed_price" if "Competitor" in scrape_type else "street_price"
                            prod_val = st.text_input("Product Name", value=result.get("product_name", ""))
                            price_val = st.number_input(
                                "Price ($)",
                                value=float(result.get(price_field) or 0),
                                min_value=0.0,
                                format="%.2f",
                            )

                            if "Competitor" not in scrape_type:
                                our_cost_val = st.number_input(
                                    "Our Cost ($, if known)",
                                    min_value=0.0,
                                    format="%.2f",
                                )

                            save_btn = st.form_submit_button("Save Record", type="primary")
                            if save_btn:
                                result["product_name"] = prod_val
                                result[price_field] = price_val if price_val > 0 else None
                                if "Competitor" in scrape_type:
                                    scraper.save_scraped_competitor(result)
                                else:
                                    result["our_cost"] = our_cost_val if our_cost_val > 0 else None
                                    scraper.save_scraped_distributor(result)
                                st.success(f"Record saved for **{prod_val}**.")

                        page_text = result.get("page_text", "")
                        if page_text:
                            with st.expander("Raw page text (first 1000 chars)"):
                                st.text(page_text[:1000])

                except Exception as e:
                    st.error(f"Scrape failed: {e}")

# ── Recent ingestions ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Recent Imports")
recent = db.get_recent_ingestions(15)
if recent:
    import pandas as pd
    df_r = pd.DataFrame(recent)[["created_at", "source_type", "source_description", "records_imported"]]
    df_r.columns = ["Time", "Type", "Description", "Records"]
    st.dataframe(df_r, use_container_width=True, hide_index=True)
else:
    st.info("No imports yet.")
