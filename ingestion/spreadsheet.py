"""
Parse Excel / CSV files and bulk-insert records into the database.

Expected column names are flexible — we normalise common variations.
"""
from __future__ import annotations

import io
import re
from datetime import date
from typing import Any

import pandas as pd

import database as db

# Column name aliases (lowercase → canonical field name)
_COL_ALIASES: dict[str, str] = {
    # product
    "product": "product_name",
    "item": "product_name",
    "product name": "product_name",
    "product_name": "product_name",
    "sku": "sku",
    "part number": "sku",
    "part_number": "sku",
    # customer
    "customer": "customer_name",
    "customer name": "customer_name",
    "customer_name": "customer_name",
    "customer type": "customer_type",
    "customer_type": "customer_type",
    "type": "customer_type",
    "industry": "customer_industry",
    "customer industry": "customer_industry",
    "customer_industry": "customer_industry",
    "size": "customer_size",
    "customer size": "customer_size",
    "customer_size": "customer_size",
    # pricing
    "gross price": "gross_price",
    "gross_price": "gross_price",
    "list price": "gross_price",
    "list_price": "gross_price",
    "price": "gross_price",
    "discount": "discount_pct",
    "discount %": "discount_pct",
    "discount_pct": "discount_pct",
    "net price": "net_price",
    "net_price": "net_price",
    "net": "net_price",
    "qty": "quantity",
    "quantity": "quantity",
    # dates
    "date": "sale_date",
    "sale date": "sale_date",
    "sale_date": "sale_date",
    "quote date": "quote_date",
    "quote_date": "quote_date",
    # quote-specific
    "status": "status",
    "won/lost": "status",
    "won lost": "status",
    "lost to": "lost_to_competitor",
    "lost_to_competitor": "lost_to_competitor",
    "competitor": "lost_to_competitor",
    "reason": "win_loss_reason",
    "win loss reason": "win_loss_reason",
    "win_loss_reason": "win_loss_reason",
    # competitor
    "competitor name": "competitor_name",
    "competitor_name": "competitor_name",
    "listed price": "listed_price",
    "listed_price": "listed_price",
    "source": "source_type",
    "source type": "source_type",
    "source_type": "source_type",
    "url": "source_url",
    "source url": "source_url",
    "source_url": "source_url",
    "observed": "observed_date",
    "observed date": "observed_date",
    "observed_date": "observed_date",
    # distributor
    "distributor": "distributor_name",
    "distributor name": "distributor_name",
    "distributor_name": "distributor_name",
    "street price": "street_price",
    "street_price": "street_price",
    "our cost": "our_cost",
    "our_cost": "our_cost",
    "cost": "our_cost",
    # logistics
    "shipping": "shipping_cost_per_unit",
    "shipping cost": "shipping_cost_per_unit",
    "shipping_cost_per_unit": "shipping_cost_per_unit",
    "warehousing": "warehousing_cost_per_unit",
    "warehousing cost": "warehousing_cost_per_unit",
    "warehousing_cost_per_unit": "warehousing_cost_per_unit",
    "other cost": "other_cost_per_unit",
    "other_cost_per_unit": "other_cost_per_unit",
    "notes": "notes",
}


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [
        _COL_ALIASES.get(c.strip().lower(), c.strip().lower())
        for c in df.columns
    ]
    return df


def _safe_float(val: Any) -> float | None:
    if pd.isna(val):
        return None
    s = str(val).replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _safe_int(val: Any) -> int | None:
    f = _safe_float(val)
    return int(f) if f is not None else None


def _safe_date(val: Any) -> str | None:
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return str(val)


def _infer_table(df: pd.DataFrame) -> str:
    """Guess which table the DataFrame belongs to based on columns present."""
    cols = set(df.columns)
    if "competitor_name" in cols or "listed_price" in cols:
        return "competitor_prices"
    if "distributor_name" in cols or "street_price" in cols:
        return "distributor_prices"
    if "shipping_cost_per_unit" in cols or "warehousing_cost_per_unit" in cols:
        return "logistics_costs"
    if "status" in cols or "lost_to_competitor" in cols or "win_loss_reason" in cols:
        return "quotes"
    return "sales"


def load_file(file_obj, record_type: str = "auto", source_label: str = "upload") -> tuple[int, list[str]]:
    """
    Parse an Excel or CSV file and insert rows.

    Parameters
    ----------
    file_obj   : file-like object (from st.file_uploader)
    record_type: 'auto' | 'sales' | 'quotes' | 'competitor_prices' |
                 'distributor_prices' | 'logistics_costs'
    source_label: description for ingestion log

    Returns
    -------
    (count_inserted, list_of_warnings)
    """
    name = getattr(file_obj, "name", "")
    if name.endswith((".xlsx", ".xls", ".xlsm")):
        df = pd.read_excel(io.BytesIO(file_obj.read()))
    else:
        file_obj.seek(0)
        df = pd.read_csv(file_obj)

    df = _normalise_columns(df)
    table = record_type if record_type != "auto" else _infer_table(df)

    warnings: list[str] = []
    inserted = 0

    for i, row in df.iterrows():
        try:
            row_dict = {k: v for k, v in row.items() if not pd.isna(v)}
            record = _build_record(row_dict, table, source_label)
            if record is None:
                warnings.append(f"Row {i+2}: missing required fields, skipped.")
                continue
            _insert_record(table, record)
            inserted += 1
        except Exception as e:
            warnings.append(f"Row {i+2}: {e}")

    db.log_ingestion("spreadsheet", f"{source_label} → {table}", inserted)
    return inserted, warnings


def _build_record(row: dict, table: str, source: str) -> dict | None:
    if table == "sales":
        if "product_name" not in row:
            return None
        return {
            "product_name": str(row.get("product_name", "")).strip(),
            "sku": row.get("sku"),
            "customer_name": row.get("customer_name"),
            "customer_type": row.get("customer_type"),
            "customer_industry": row.get("customer_industry"),
            "customer_size": row.get("customer_size"),
            "gross_price": _safe_float(row.get("gross_price")),
            "discount_pct": _safe_float(row.get("discount_pct")) or 0,
            "net_price": _safe_float(row.get("net_price")),
            "quantity": _safe_int(row.get("quantity")) or 1,
            "sale_date": _safe_date(row.get("sale_date")),
            "notes": row.get("notes"),
            "source": source,
        }

    if table == "quotes":
        if "product_name" not in row:
            return None
        return {
            "product_name": str(row.get("product_name", "")).strip(),
            "sku": row.get("sku"),
            "customer_name": row.get("customer_name"),
            "customer_type": row.get("customer_type"),
            "customer_industry": row.get("customer_industry"),
            "customer_size": row.get("customer_size"),
            "gross_price": _safe_float(row.get("gross_price")),
            "discount_pct": _safe_float(row.get("discount_pct")) or 0,
            "net_price": _safe_float(row.get("net_price")),
            "quantity": _safe_int(row.get("quantity")) or 1,
            "quote_date": _safe_date(row.get("quote_date") or row.get("sale_date")),
            "status": row.get("status"),
            "lost_to_competitor": row.get("lost_to_competitor"),
            "win_loss_reason": row.get("win_loss_reason"),
            "notes": row.get("notes"),
            "source": source,
        }

    if table == "competitor_prices":
        if "competitor_name" not in row or "product_name" not in row:
            return None
        return {
            "competitor_name": str(row["competitor_name"]).strip(),
            "product_name": str(row["product_name"]).strip(),
            "listed_price": _safe_float(row.get("listed_price") or row.get("gross_price")),
            "source_type": row.get("source_type", "catalog"),
            "source_url": row.get("source_url"),
            "observed_date": _safe_date(row.get("observed_date") or row.get("sale_date")),
            "notes": row.get("notes"),
        }

    if table == "distributor_prices":
        if "distributor_name" not in row or "product_name" not in row:
            return None
        return {
            "distributor_name": str(row["distributor_name"]).strip(),
            "product_name": str(row["product_name"]).strip(),
            "sku": row.get("sku"),
            "street_price": _safe_float(row.get("street_price")),
            "our_cost": _safe_float(row.get("our_cost")),
            "observed_date": _safe_date(row.get("observed_date") or row.get("sale_date")),
            "notes": row.get("notes"),
            "source": source,
        }

    if table == "logistics_costs":
        return {
            "product_name": row.get("product_name"),
            "sku": row.get("sku"),
            "shipping_cost_per_unit": _safe_float(row.get("shipping_cost_per_unit")) or 0,
            "warehousing_cost_per_unit": _safe_float(row.get("warehousing_cost_per_unit")) or 0,
            "other_cost_per_unit": _safe_float(row.get("other_cost_per_unit")) or 0,
            "notes": row.get("notes"),
            "effective_date": _safe_date(row.get("effective_date") or row.get("sale_date")),
        }

    return None


def _insert_record(table: str, record: dict) -> None:
    dispatch = {
        "sales": db.insert_sale,
        "quotes": db.insert_quote,
        "competitor_prices": db.insert_competitor_price,
        "distributor_prices": db.insert_distributor_price,
        "logistics_costs": db.insert_logistics_cost,
    }
    dispatch[table](record)
