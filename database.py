"""
Database layer — SQLite schema, CRUD helpers, and query functions.
All data access goes through this module.
"""
import sqlite3
from pathlib import Path
from datetime import date
from typing import Any

DB_PATH = Path(__file__).parent / "pricing_data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku  TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS sales (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name          TEXT NOT NULL,
    sku                   TEXT,
    customer_name         TEXT,
    customer_type         TEXT,   -- 'end-user' | 'reseller'
    customer_industry     TEXT,
    customer_size         TEXT,   -- 'small' | 'mid-market' | 'enterprise'
    gross_price           REAL,
    discount_pct          REAL DEFAULT 0,
    net_price             REAL,
    quantity              INTEGER DEFAULT 1,
    sale_date             DATE,
    notes                 TEXT,
    source                TEXT DEFAULT 'manual',
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quotes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name          TEXT NOT NULL,
    sku                   TEXT,
    customer_name         TEXT,
    customer_type         TEXT,
    customer_industry     TEXT,
    customer_size         TEXT,
    gross_price           REAL,
    discount_pct          REAL DEFAULT 0,
    net_price             REAL,
    quantity              INTEGER DEFAULT 1,
    quote_date            DATE,
    status                TEXT,   -- 'won' | 'lost' | 'pending'
    lost_to_competitor    TEXT,
    win_loss_reason       TEXT,
    notes                 TEXT,
    source                TEXT DEFAULT 'manual',
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS competitor_prices (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    competitor_name TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    listed_price    REAL,
    source_type     TEXT,   -- 'url' | 'catalog' | 'hearsay' | 'pdf'
    source_url      TEXT,
    observed_date   DATE,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS distributor_prices (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    distributor_name TEXT NOT NULL,
    product_name     TEXT NOT NULL,
    sku              TEXT,
    street_price     REAL,
    our_cost         REAL,
    observed_date    DATE,
    notes            TEXT,
    source           TEXT DEFAULT 'manual',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logistics_costs (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name               TEXT,
    sku                        TEXT,
    shipping_cost_per_unit     REAL DEFAULT 0,
    warehousing_cost_per_unit  REAL DEFAULT 0,
    other_cost_per_unit        REAL DEFAULT 0,
    notes                      TEXT,
    effective_date             DATE,
    created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type        TEXT,
    source_description TEXT,
    records_imported   INTEGER,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


# ── Product helpers ────────────────────────────────────────────────────────────

def upsert_product(name: str, sku: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO products (name, sku) VALUES (?, ?)",
            (name.strip(), sku),
        )


def get_all_products() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT product_name FROM sales "
            "UNION SELECT DISTINCT product_name FROM quotes "
            "UNION SELECT DISTINCT product_name FROM competitor_prices "
            "UNION SELECT DISTINCT product_name FROM distributor_prices "
            "ORDER BY product_name"
        ).fetchall()
    return [r[0] for r in rows]


# ── Insert helpers ─────────────────────────────────────────────────────────────

def insert_sale(data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO sales ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        return cur.lastrowid


def insert_quote(data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO quotes ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        return cur.lastrowid


def insert_competitor_price(data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO competitor_prices ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        return cur.lastrowid


def insert_distributor_price(data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO distributor_prices ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        return cur.lastrowid


def insert_logistics_cost(data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO logistics_costs ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        return cur.lastrowid


def log_ingestion(source_type: str, description: str, count: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO ingestion_log (source_type, source_description, records_imported) VALUES (?,?,?)",
            (source_type, description, count),
        )


# ── Query helpers ──────────────────────────────────────────────────────────────

def query_df(sql: str, params: tuple = ()) -> "pd.DataFrame":
    import pandas as pd
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_sales_for_product(product_name: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sales WHERE LOWER(product_name)=LOWER(?) ORDER BY sale_date DESC",
            (product_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_quotes_for_product(product_name: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM quotes WHERE LOWER(product_name)=LOWER(?) ORDER BY quote_date DESC",
            (product_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_competitor_prices_for_product(product_name: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM competitor_prices WHERE LOWER(product_name)=LOWER(?) ORDER BY observed_date DESC",
            (product_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_distributor_prices_for_product(product_name: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM distributor_prices WHERE LOWER(product_name)=LOWER(?) ORDER BY observed_date DESC",
            (product_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_logistics_for_product(product_name: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM logistics_costs WHERE LOWER(product_name)=LOWER(?) ORDER BY effective_date DESC",
            (product_name,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_ingestions(limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM ingestion_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_dashboard_stats() -> dict:
    """Aggregate statistics for the dashboard."""
    with get_conn() as conn:
        total_sales = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
        total_quotes = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        won = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE status='won'"
        ).fetchone()[0]
        lost = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE status='lost'"
        ).fetchone()[0]
        avg_discount = conn.execute(
            "SELECT AVG(discount_pct) FROM sales WHERE discount_pct IS NOT NULL"
        ).fetchone()[0]
        competitor_count = conn.execute(
            "SELECT COUNT(DISTINCT competitor_name) FROM competitor_prices"
        ).fetchone()[0]
        product_count = conn.execute(
            "SELECT COUNT(*) FROM ("
            "SELECT product_name FROM sales UNION SELECT product_name FROM quotes"
            ")"
        ).fetchone()[0]

    win_rate = (won / (won + lost) * 100) if (won + lost) > 0 else None
    return {
        "total_sales": total_sales,
        "total_quotes": total_quotes,
        "won": won,
        "lost": lost,
        "win_rate": win_rate,
        "avg_discount": avg_discount,
        "competitor_count": competitor_count,
        "product_count": product_count,
    }


# Initialise on import
init_db()
