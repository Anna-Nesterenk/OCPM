"""
analytics/channel.py
=====================
Supply Channel Analysis (ТЗ §12) and the Channel Investigation drill-down
Supply Channel -> Batch -> Sale/Customer (ТЗ §8.2).
"""
from __future__ import annotations

import pandas as pd

from metrics import aggregate_batches


def channel_list(batch_full: pd.DataFrame) -> pd.DataFrame:
    agg = aggregate_batches(batch_full, "channel_id")
    meta = batch_full.drop_duplicates("channel_id")[
        ["channel_id", "channel_name", "target_lead_days", "delay_probability"]
    ]
    out = agg.merge(meta, on="channel_id", how="left")
    return out.sort_values("qty_received", ascending=False)


def channel_360(batch_full: pd.DataFrame, channel_id: str) -> dict:
    cb = batch_full[batch_full["channel_id"] == channel_id]
    if cb.empty:
        return {"found": False}

    row = channel_list(batch_full)
    row = row[row["channel_id"] == channel_id]
    kpi = row.iloc[0].to_dict() if not row.empty else {}

    by_supplier = aggregate_batches(cb, "supplier_id").merge(
        cb.drop_duplicates("supplier_id")[["supplier_id", "supplier_name"]], on="supplier_id", how="left"
    ).sort_values("qty_received", ascending=False)

    batches_tbl = cb[[
        "batch_id", "product_name", "supplier_name", "warehouse_name", "received_date",
        "quantity_received", "pct_sold", "revenue_total", "net_contribution",
        "supply_lead_days", "delay_days", "days_to_first_sale",
    ]].sort_values("received_date", ascending=False)

    return {"found": True, "kpi": kpi, "by_supplier": by_supplier, "batches": batches_tbl}
