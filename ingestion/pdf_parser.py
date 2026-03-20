"""
Extract pricing data from PDF files using pdfplumber.

Attempts to find price tables and structured data.
Returns raw extracted text and any structured records found.
"""
from __future__ import annotations

import io
import re
from typing import Any

try:
    import pdfplumber
    _HAS_PDF = True
except ImportError:
    _HAS_PDF = False

import database as db


def extract_text(file_obj) -> str:
    """Return all text content from a PDF."""
    if not _HAS_PDF:
        return "pdfplumber not installed. Run: pip install pdfplumber"
    data = file_obj.read() if not isinstance(file_obj, bytes) else file_obj
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def extract_tables(file_obj) -> list[list[list[str]]]:
    """Return all tables from a PDF as list-of-rows-of-cells."""
    if not _HAS_PDF:
        return []
    data = file_obj.read() if not isinstance(file_obj, bytes) else file_obj
    all_tables = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tbl in tables:
                if tbl:
                    all_tables.append(tbl)
    return all_tables


_PRICE_RE = re.compile(r"\$?\s*(\d[\d,]*\.?\d*)")


def _clean_price(s: str | None) -> float | None:
    if not s:
        return None
    m = _PRICE_RE.search(str(s))
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def parse_competitor_pdf(
    file_obj,
    competitor_name: str,
    observed_date: str,
    source_url: str = "",
) -> tuple[int, list[str]]:
    """
    Try to extract competitor pricing rows from a PDF.
    Returns (count_inserted, warnings).
    """
    if not _HAS_PDF:
        return 0, ["pdfplumber not installed"]

    data = file_obj.read() if not isinstance(file_obj, bytes) else file_obj
    warnings: list[str] = []
    inserted = 0

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            for tbl in page.extract_tables() or []:
                if not tbl:
                    continue
                headers = [str(c).strip().lower() if c else "" for c in tbl[0]]
                # Try to find product + price columns
                prod_col = next(
                    (i for i, h in enumerate(headers)
                     if any(kw in h for kw in ["product", "item", "description", "name", "part"])),
                    None,
                )
                price_col = next(
                    (i for i, h in enumerate(headers)
                     if any(kw in h for kw in ["price", "cost", "rate", "msrp", "list"])),
                    None,
                )
                if prod_col is None or price_col is None:
                    continue

                for row in tbl[1:]:
                    if not row or len(row) <= max(prod_col, price_col):
                        continue
                    prod = str(row[prod_col] or "").strip()
                    price = _clean_price(row[price_col])
                    if not prod or not price:
                        continue
                    record = {
                        "competitor_name": competitor_name,
                        "product_name": prod,
                        "listed_price": price,
                        "source_type": "pdf",
                        "source_url": source_url,
                        "observed_date": observed_date,
                    }
                    db.insert_competitor_price(record)
                    inserted += 1

    db.log_ingestion("pdf", f"Competitor PDF: {competitor_name}", inserted)
    if inserted == 0:
        warnings.append(
            "No structured price tables found. "
            "Use the extracted text with the AI analysis instead."
        )
    return inserted, warnings


def parse_distributor_pdf(
    file_obj,
    distributor_name: str,
    observed_date: str,
) -> tuple[int, list[str]]:
    """
    Try to extract distributor pricing rows from a PDF.
    Returns (count_inserted, warnings).
    """
    if not _HAS_PDF:
        return 0, ["pdfplumber not installed"]

    data = file_obj.read() if not isinstance(file_obj, bytes) else file_obj
    warnings: list[str] = []
    inserted = 0

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            for tbl in page.extract_tables() or []:
                if not tbl:
                    continue
                headers = [str(c).strip().lower() if c else "" for c in tbl[0]]
                prod_col = next(
                    (i for i, h in enumerate(headers)
                     if any(kw in h for kw in ["product", "item", "description", "name", "part"])),
                    None,
                )
                street_col = next(
                    (i for i, h in enumerate(headers)
                     if any(kw in h for kw in ["street", "retail", "end user", "msrp", "resale"])),
                    None,
                )
                cost_col = next(
                    (i for i, h in enumerate(headers)
                     if any(kw in h for kw in ["cost", "dealer", "your price", "net"])),
                    None,
                )
                if prod_col is None:
                    continue
                price_col = street_col if street_col is not None else cost_col
                if price_col is None:
                    continue

                for row in tbl[1:]:
                    if not row or len(row) <= max(prod_col, price_col):
                        continue
                    prod = str(row[prod_col] or "").strip()
                    street = _clean_price(row[street_col]) if street_col is not None else None
                    cost = _clean_price(row[cost_col]) if cost_col is not None else None
                    if not prod:
                        continue
                    record = {
                        "distributor_name": distributor_name,
                        "product_name": prod,
                        "street_price": street,
                        "our_cost": cost,
                        "observed_date": observed_date,
                        "source": "pdf",
                    }
                    db.insert_distributor_price(record)
                    inserted += 1

    db.log_ingestion("pdf", f"Distributor PDF: {distributor_name}", inserted)
    if inserted == 0:
        warnings.append(
            "No structured price tables detected. "
            "Consider using the extracted text with AI analysis."
        )
    return inserted, warnings
