"""
analytics/batch.py
===================
Batch 360 (ТЗ §13) -- the most important scenario: Batch is the object that
physically carries the whole lineage Supplier -> PO -> Delivery -> Batch ->
Warehouse -> Sale -> Customer -> Return, so this module also hosts the
anomaly detectors (fastest/slowest/high-return/no-sale) reused by the
Insight Engine.
"""
from __future__ import annotations

import pandas as pd

BATCH_TABLE_COLS = [
    "batch_id", "product_id", "product_name", "category_name", "supplier_id", "supplier_name",
    "channel_name", "warehouse_name", "received_date", "quantity_received", "quantity_sold",
    "quantity_remaining", "pct_sold", "purchase_unit_price", "revenue_total", "net_contribution",
    "return_rate_qty", "supply_lead_days", "delay_days", "days_to_first_sale",
]


def batch_table(batch_full: pd.DataFrame) -> pd.DataFrame:
    return batch_full[BATCH_TABLE_COLS].copy()


def batch_360(batch_full: pd.DataFrame, batch_id: str) -> dict:
    row = batch_full[batch_full["batch_id"] == batch_id]
    if row.empty:
        return {"found": False}
    return {"found": True, "row": row.iloc[0]}


def fastest_batches(batch_full: pd.DataFrame, n=10) -> pd.DataFrame:
    d = batch_full[(batch_full["quantity_sold"] > 0) & batch_full["days_to_first_sale"].notna()]
    return d.sort_values("days_to_first_sale").head(n)[BATCH_TABLE_COLS]


def slowest_batches(batch_full: pd.DataFrame, n=10) -> pd.DataFrame:
    d = batch_full[(batch_full["quantity_sold"] > 0) & batch_full["days_to_first_sale"].notna()]
    return d.sort_values("days_to_first_sale", ascending=False).head(n)[BATCH_TABLE_COLS]


def high_return_batches(batch_full: pd.DataFrame, min_sold=5, n=10) -> pd.DataFrame:
    d = batch_full[batch_full["qty_sold_txn"] >= min_sold]
    return d.sort_values("return_rate_qty", ascending=False).head(n)[BATCH_TABLE_COLS]


def no_sale_batches(batch_full: pd.DataFrame) -> pd.DataFrame:
    return batch_full[batch_full["is_untouched"]][BATCH_TABLE_COLS]


def negative_contribution_batches(batch_full: pd.DataFrame, n=10) -> pd.DataFrame:
    d = batch_full[batch_full["quantity_sold"] > 0]
    return d.sort_values("net_contribution").head(n)[BATCH_TABLE_COLS]
