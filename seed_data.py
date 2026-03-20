"""
Seed the database with realistic sample pricing data.
Run once to populate the tool for a demo or first-time setup.

    python seed_data.py

Add --reset flag to wipe and re-seed:

    python seed_data.py --reset
"""
import sys
import sqlite3
from pathlib import Path

import database as db

RESET = "--reset" in sys.argv


def main():
    if RESET:
        print("Resetting database…")
        with db.get_conn() as conn:
            for tbl in ["sales", "quotes", "competitor_prices",
                        "distributor_prices", "logistics_costs", "ingestion_log"]:
                conn.execute(f"DELETE FROM {tbl}")
        print("All tables cleared.")

    # ── Products ────────────────────────────────────────────────────────────────
    products = [
        ("Industrial Pump X200", "PUMP-X200"),
        ("Flow Sensor Pro", "FS-PRO-10"),
        ("Valve Controller V5", "VC-V5-01"),
        ("Pressure Gauge PG80", "PG-80"),
        ("Filter Assembly FA3", "FA-3"),
    ]
    for name, sku in products:
        db.upsert_product(name, sku)

    # ── Sales ───────────────────────────────────────────────────────────────────
    sales = [
        # Industrial Pump X200 — direct end-user sales
        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "Apex Manufacturing", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "enterprise",
         "gross_price": 4800.00, "discount_pct": 10.0, "net_price": 4320.00,
         "quantity": 2, "sale_date": "2024-11-15", "source": "seed"},

        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "City Water Dept.", "customer_type": "end-user",
         "customer_industry": "government", "customer_size": "enterprise",
         "gross_price": 4800.00, "discount_pct": 5.0, "net_price": 4560.00,
         "quantity": 4, "sale_date": "2024-12-03", "source": "seed"},

        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "QuickFix Solutions", "customer_type": "reseller",
         "customer_industry": "distribution", "customer_size": "small",
         "gross_price": 4800.00, "discount_pct": 20.0, "net_price": 3840.00,
         "quantity": 5, "sale_date": "2025-01-10", "source": "seed"},

        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "BioPharm Inc.", "customer_type": "end-user",
         "customer_industry": "healthcare", "customer_size": "mid-market",
         "gross_price": 4800.00, "discount_pct": 8.0, "net_price": 4416.00,
         "quantity": 1, "sale_date": "2025-02-01", "source": "seed"},

        # Flow Sensor Pro
        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "customer_name": "Apex Manufacturing", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "enterprise",
         "gross_price": 1200.00, "discount_pct": 12.0, "net_price": 1056.00,
         "quantity": 10, "sale_date": "2024-10-20", "source": "seed"},

        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "customer_name": "OilStream Partners", "customer_type": "end-user",
         "customer_industry": "energy", "customer_size": "enterprise",
         "gross_price": 1200.00, "discount_pct": 7.0, "net_price": 1116.00,
         "quantity": 6, "sale_date": "2025-01-25", "source": "seed"},

        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "customer_name": "IndMart Supplies", "customer_type": "reseller",
         "customer_industry": "distribution", "customer_size": "mid-market",
         "gross_price": 1200.00, "discount_pct": 22.0, "net_price": 936.00,
         "quantity": 20, "sale_date": "2025-02-10", "source": "seed"},

        # Valve Controller V5
        {"product_name": "Valve Controller V5", "sku": "VC-V5-01",
         "customer_name": "ChemCore Ltd.", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "mid-market",
         "gross_price": 2200.00, "discount_pct": 10.0, "net_price": 1980.00,
         "quantity": 3, "sale_date": "2024-11-05", "source": "seed"},

        {"product_name": "Valve Controller V5", "sku": "VC-V5-01",
         "customer_name": "SafeFlow Systems", "customer_type": "reseller",
         "customer_industry": "distribution", "customer_size": "small",
         "gross_price": 2200.00, "discount_pct": 18.0, "net_price": 1804.00,
         "quantity": 8, "sale_date": "2025-01-14", "source": "seed"},

        # Pressure Gauge PG80
        {"product_name": "Pressure Gauge PG80", "sku": "PG-80",
         "customer_name": "Apex Manufacturing", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "enterprise",
         "gross_price": 340.00, "discount_pct": 5.0, "net_price": 323.00,
         "quantity": 25, "sale_date": "2025-01-08", "source": "seed"},

        # Filter Assembly FA3
        {"product_name": "Filter Assembly FA3", "sku": "FA-3",
         "customer_name": "BioPharm Inc.", "customer_type": "end-user",
         "customer_industry": "healthcare", "customer_size": "mid-market",
         "gross_price": 870.00, "discount_pct": 0.0, "net_price": 870.00,
         "quantity": 12, "sale_date": "2025-02-18", "source": "seed"},
    ]
    for s in sales:
        db.insert_sale(s)
    db.log_ingestion("seed", "Sample sales records", len(sales))
    print(f"  Inserted {len(sales)} sales records.")

    # ── Quotes ──────────────────────────────────────────────────────────────────
    quotes = [
        # Industrial Pump X200 — won
        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "Midwest Energy Co.", "customer_type": "end-user",
         "customer_industry": "energy", "customer_size": "enterprise",
         "gross_price": 4800.00, "discount_pct": 10.0, "net_price": 4320.00,
         "quantity": 3, "quote_date": "2024-10-01",
         "status": "won", "win_loss_reason": "Best delivery time + good price",
         "source": "seed"},

        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "Harbor Dock Auth.", "customer_type": "end-user",
         "customer_industry": "government", "customer_size": "enterprise",
         "gross_price": 4800.00, "discount_pct": 8.0, "net_price": 4416.00,
         "quantity": 2, "quote_date": "2024-12-15",
         "status": "won", "win_loss_reason": "Approved vendor + pricing within budget",
         "source": "seed"},

        # Industrial Pump X200 — lost
        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "Steel Works Corp.", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "enterprise",
         "gross_price": 4800.00, "discount_pct": 10.0, "net_price": 4320.00,
         "quantity": 10, "quote_date": "2024-11-20",
         "status": "lost", "lost_to_competitor": "FlowTech Industries",
         "win_loss_reason": "FlowTech offered 15% lower price on volume order",
         "source": "seed"},

        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "AquaPure LLC", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "mid-market",
         "gross_price": 4800.00, "discount_pct": 12.0, "net_price": 4224.00,
         "quantity": 2, "quote_date": "2025-01-28",
         "status": "lost", "lost_to_competitor": "PumpMaster Pro",
         "win_loss_reason": "PumpMaster matched our spec at $3,900 net",
         "source": "seed"},

        # Industrial Pump X200 — pending
        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "customer_name": "Pacific Utilities", "customer_type": "end-user",
         "customer_industry": "government", "customer_size": "enterprise",
         "gross_price": 4800.00, "discount_pct": 10.0, "net_price": 4320.00,
         "quantity": 6, "quote_date": "2025-03-01",
         "status": "pending", "notes": "Awaiting budget approval",
         "source": "seed"},

        # Flow Sensor Pro — won
        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "customer_name": "TurbineGen Systems", "customer_type": "end-user",
         "customer_industry": "energy", "customer_size": "enterprise",
         "gross_price": 1200.00, "discount_pct": 10.0, "net_price": 1080.00,
         "quantity": 15, "quote_date": "2024-10-10",
         "status": "won", "win_loss_reason": "Technical superiority over competing sensor",
         "source": "seed"},

        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "customer_name": "ChemCore Ltd.", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "mid-market",
         "gross_price": 1200.00, "discount_pct": 8.0, "net_price": 1104.00,
         "quantity": 5, "quote_date": "2025-01-15",
         "status": "won", "source": "seed"},

        # Flow Sensor Pro — lost
        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "customer_name": "DataFlow Inc.", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "small",
         "gross_price": 1200.00, "discount_pct": 5.0, "net_price": 1140.00,
         "quantity": 2, "quote_date": "2024-12-01",
         "status": "lost", "lost_to_competitor": "SensorTek",
         "win_loss_reason": "SensorTek cheaper and faster delivery",
         "source": "seed"},

        # Valve Controller V5 — won
        {"product_name": "Valve Controller V5", "sku": "VC-V5-01",
         "customer_name": "GasPipe National", "customer_type": "end-user",
         "customer_industry": "energy", "customer_size": "enterprise",
         "gross_price": 2200.00, "discount_pct": 12.0, "net_price": 1936.00,
         "quantity": 5, "quote_date": "2024-11-10",
         "status": "won", "win_loss_reason": "Safety cert required — only qualified vendor",
         "source": "seed"},

        # Valve Controller V5 — lost
        {"product_name": "Valve Controller V5", "sku": "VC-V5-01",
         "customer_name": "AutoLine Corp.", "customer_type": "end-user",
         "customer_industry": "manufacturing", "customer_size": "enterprise",
         "gross_price": 2200.00, "discount_pct": 10.0, "net_price": 1980.00,
         "quantity": 12, "quote_date": "2025-01-20",
         "status": "lost", "lost_to_competitor": "FlowTech Industries",
         "win_loss_reason": "FlowTech offered $1,750 net with extended warranty",
         "source": "seed"},

        # Pressure Gauge PG80 — won / lost
        {"product_name": "Pressure Gauge PG80", "sku": "PG-80",
         "customer_name": "MedDevice Co.", "customer_type": "end-user",
         "customer_industry": "healthcare", "customer_size": "mid-market",
         "gross_price": 340.00, "discount_pct": 0.0, "net_price": 340.00,
         "quantity": 50, "quote_date": "2024-10-25",
         "status": "won", "win_loss_reason": "Spec matched, price competitive",
         "source": "seed"},

        {"product_name": "Pressure Gauge PG80", "sku": "PG-80",
         "customer_name": "BuildRight Contractors", "customer_type": "end-user",
         "customer_industry": "construction", "customer_size": "small",
         "gross_price": 340.00, "discount_pct": 5.0, "net_price": 323.00,
         "quantity": 10, "quote_date": "2025-02-05",
         "status": "lost", "lost_to_competitor": "GaugePro Direct",
         "win_loss_reason": "GaugePro offered $280 with free shipping",
         "source": "seed"},
    ]
    for q in quotes:
        db.insert_quote(q)
    db.log_ingestion("seed", "Sample quote records", len(quotes))
    print(f"  Inserted {len(quotes)} quote records.")

    # ── Competitor Prices ───────────────────────────────────────────────────────
    competitor_prices = [
        # FlowTech Industries
        {"competitor_name": "FlowTech Industries", "product_name": "Industrial Pump X200",
         "listed_price": 4100.00, "source_type": "catalog",
         "observed_date": "2024-11-01", "notes": "Published catalog price"},
        {"competitor_name": "FlowTech Industries", "product_name": "Industrial Pump X200",
         "listed_price": 4050.00, "source_type": "hearsay",
         "observed_date": "2025-02-15", "notes": "Reported by customer after competitive bid"},
        {"competitor_name": "FlowTech Industries", "product_name": "Valve Controller V5",
         "listed_price": 1850.00, "source_type": "catalog",
         "observed_date": "2024-12-01"},

        # PumpMaster Pro
        {"competitor_name": "PumpMaster Pro", "product_name": "Industrial Pump X200",
         "listed_price": 3900.00, "source_type": "url",
         "observed_date": "2025-01-28", "notes": "Found on their website product page"},
        {"competitor_name": "PumpMaster Pro", "product_name": "Flow Sensor Pro",
         "listed_price": 990.00, "source_type": "catalog",
         "observed_date": "2024-10-01"},

        # SensorTek
        {"competitor_name": "SensorTek", "product_name": "Flow Sensor Pro",
         "listed_price": 950.00, "source_type": "url",
         "observed_date": "2024-12-01"},
        {"competitor_name": "SensorTek", "product_name": "Flow Sensor Pro",
         "listed_price": 970.00, "source_type": "hearsay",
         "observed_date": "2025-01-10", "notes": "Price increase per sales rep intel"},

        # GaugePro Direct
        {"competitor_name": "GaugePro Direct", "product_name": "Pressure Gauge PG80",
         "listed_price": 280.00, "source_type": "url",
         "observed_date": "2025-02-05"},
        {"competitor_name": "GaugePro Direct", "product_name": "Filter Assembly FA3",
         "listed_price": 740.00, "source_type": "catalog",
         "observed_date": "2024-11-15"},
    ]
    for cp in competitor_prices:
        db.insert_competitor_price(cp)
    db.log_ingestion("seed", "Sample competitor prices", len(competitor_prices))
    print(f"  Inserted {len(competitor_prices)} competitor price records.")

    # ── Distributor Prices ──────────────────────────────────────────────────────
    distributor_prices = [
        {"distributor_name": "Industrial Parts Direct", "product_name": "Industrial Pump X200",
         "sku": "PUMP-X200", "street_price": 5200.00, "our_cost": 2900.00,
         "observed_date": "2025-01-15", "source": "seed"},
        {"distributor_name": "Industrial Parts Direct", "product_name": "Flow Sensor Pro",
         "sku": "FS-PRO-10", "street_price": 1350.00, "our_cost": 650.00,
         "observed_date": "2025-01-15", "source": "seed"},
        {"distributor_name": "Industrial Parts Direct", "product_name": "Valve Controller V5",
         "sku": "VC-V5-01", "street_price": 2450.00, "our_cost": 1100.00,
         "observed_date": "2025-01-15", "source": "seed"},

        {"distributor_name": "TechSupply Co.", "product_name": "Industrial Pump X200",
         "sku": "PUMP-X200", "street_price": 5100.00, "our_cost": 2850.00,
         "observed_date": "2025-02-01", "source": "seed"},
        {"distributor_name": "TechSupply Co.", "product_name": "Pressure Gauge PG80",
         "sku": "PG-80", "street_price": 390.00, "our_cost": 180.00,
         "observed_date": "2025-02-01", "source": "seed"},
        {"distributor_name": "TechSupply Co.", "product_name": "Filter Assembly FA3",
         "sku": "FA-3", "street_price": 990.00, "our_cost": 450.00,
         "observed_date": "2025-02-01", "source": "seed"},
    ]
    for dp in distributor_prices:
        db.insert_distributor_price(dp)
    db.log_ingestion("seed", "Sample distributor prices", len(distributor_prices))
    print(f"  Inserted {len(distributor_prices)} distributor price records.")

    # ── Logistics Costs ─────────────────────────────────────────────────────────
    logistics = [
        {"product_name": "Industrial Pump X200", "sku": "PUMP-X200",
         "shipping_cost_per_unit": 85.00, "warehousing_cost_per_unit": 40.00,
         "other_cost_per_unit": 15.00, "effective_date": "2025-01-01",
         "notes": "Includes LTL freight estimate"},
        {"product_name": "Flow Sensor Pro", "sku": "FS-PRO-10",
         "shipping_cost_per_unit": 18.00, "warehousing_cost_per_unit": 8.00,
         "other_cost_per_unit": 5.00, "effective_date": "2025-01-01"},
        {"product_name": "Valve Controller V5", "sku": "VC-V5-01",
         "shipping_cost_per_unit": 35.00, "warehousing_cost_per_unit": 15.00,
         "other_cost_per_unit": 5.00, "effective_date": "2025-01-01"},
        {"product_name": "Pressure Gauge PG80", "sku": "PG-80",
         "shipping_cost_per_unit": 6.00, "warehousing_cost_per_unit": 3.00,
         "other_cost_per_unit": 1.00, "effective_date": "2025-01-01"},
        {"product_name": "Filter Assembly FA3", "sku": "FA-3",
         "shipping_cost_per_unit": 22.00, "warehousing_cost_per_unit": 10.00,
         "other_cost_per_unit": 3.00, "effective_date": "2025-01-01"},
    ]
    for lc in logistics:
        db.insert_logistics_cost(lc)
    db.log_ingestion("seed", "Sample logistics costs", len(logistics))
    print(f"  Inserted {len(logistics)} logistics cost records.")

    print("\nSeed complete. Start the app with: streamlit run app.py")


if __name__ == "__main__":
    main()
