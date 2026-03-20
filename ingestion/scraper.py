"""
Scrape pricing from a competitor or distributor product page URL.

Uses requests + BeautifulSoup. Returns structured records where possible,
and raw page text for AI analysis when automatic extraction fails.
"""
from __future__ import annotations

import re
from typing import Any

try:
    import requests
    from bs4 import BeautifulSoup
    _HAS_SCRAPER = True
except ImportError:
    _HAS_SCRAPER = False

import database as db

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_PRICE_RE = re.compile(r"\$\s*(\d[\d,]*\.?\d*)")
_PRICE_BROAD = re.compile(r"(\d[\d,]+\.?\d*)")


def fetch_page(url: str, timeout: int = 15) -> tuple[str, str]:
    """
    Fetch a URL. Returns (raw_text, page_title).
    Raises requests.RequestException on failure.
    """
    if not _HAS_SCRAPER:
        raise ImportError("requests and beautifulsoup4 are required")

    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    # Strip scripts / styles for cleaner text
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else url
    text = soup.get_text(separator="\n", strip=True)
    return text, title


def _extract_prices_from_text(text: str) -> list[float]:
    return [float(m.group(1).replace(",", "")) for m in _PRICE_RE.finditer(text)]


def _find_product_title(soup: "BeautifulSoup") -> str | None:
    for selector in ["h1", ".product-title", ".product-name", "#product-title"]:
        el = soup.select_one(selector)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None


def scrape_competitor_price(
    url: str,
    competitor_name: str,
    product_name_override: str | None = None,
    observed_date: str | None = None,
) -> dict:
    """
    Scrape a single product page and attempt to extract the price.

    Returns a dict with fields ready for display / confirmation before saving.
    Call save_scraped_competitor() to persist.
    """
    if not _HAS_SCRAPER:
        return {"error": "requests / beautifulsoup4 not installed"}

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {"error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    product_name = product_name_override or _find_product_title(soup) or "Unknown Product"
    page_text = soup.get_text(separator="\n", strip=True)

    prices = _extract_prices_from_text(page_text)
    best_price = prices[0] if prices else None

    # Try common e-commerce price selectors
    for selector in [
        ".price", ".product-price", "#price", "[itemprop='price']",
        ".offer-price", ".sale-price", ".regular-price", ".current-price"
    ]:
        el = soup.select_one(selector)
        if el:
            found = _extract_prices_from_text(el.get_text())
            if found:
                best_price = found[0]
                break

    return {
        "competitor_name": competitor_name,
        "product_name": product_name,
        "listed_price": best_price,
        "source_type": "url",
        "source_url": url,
        "observed_date": observed_date,
        "page_text": page_text[:3000],  # truncated for AI context
    }


def save_scraped_competitor(record: dict) -> int:
    payload = {k: v for k, v in record.items() if k != "page_text"}
    row_id = db.insert_competitor_price(payload)
    db.log_ingestion("url_scrape", record.get("source_url", ""), 1)
    return row_id


def scrape_distributor_price(
    url: str,
    distributor_name: str,
    product_name_override: str | None = None,
    observed_date: str | None = None,
) -> dict:
    """Same as scrape_competitor_price but for distributor pages."""
    result = scrape_competitor_price(url, distributor_name, product_name_override, observed_date)
    result["distributor_name"] = result.pop("competitor_name", distributor_name)
    result["street_price"] = result.pop("listed_price", None)
    result.pop("source_type", None)
    return result


def save_scraped_distributor(record: dict) -> int:
    payload = {k: v for k, v in record.items() if k not in ("page_text",)}
    # ensure correct field names
    if "street_price" not in payload and "listed_price" in payload:
        payload["street_price"] = payload.pop("listed_price")
    payload.setdefault("source", "url_scrape")
    row_id = db.insert_distributor_price(payload)
    db.log_ingestion("url_scrape", record.get("source_url", ""), 1)
    return row_id
