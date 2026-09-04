"""
analytics/category.py
======================
Category Investigation (ТЗ §8.3): Product Category -> Product -> Supplier --
compares suppliers *within* a category on price, reliability and Return Rate.
"""
from __future__ import annotations

import pandas as pd

from metrics import aggregate_batches


def category_list(batch_full: pd.DataFrame) -> pd.DataFrame:
    agg = aggregate_batches(batch_full, "category_name")
    n_prod = batch_full.groupby("category_name")["product_id"].nunique().rename("n_products").reset_index()
    out = agg.merge(n_prod, on="category_name", how="left")
    return out.sort_values("revenue", ascending=False)


def category_360(batch_full: pd.DataFrame, category_name: str) -> dict:
    cb = batch_full[batch_full["category_name"] == category_name]
    if cb.empty:
        return {"found": False}

    row = category_list(batch_full)
    row = row[row["category_name"] == category_name]
    kpi = row.iloc[0].to_dict() if not row.empty else {}

    products = aggregate_batches(cb, "product_id").merge(
        cb.drop_duplicates("product_id")[["product_id", "product_name"]], on="product_id", how="left"
    ).sort_values("revenue", ascending=False)

    suppliers = aggregate_batches(cb, "supplier_id").merge(
        cb.drop_duplicates("supplier_id")[["supplier_id", "supplier_name"]], on="supplier_id", how="left"
    ).sort_values("revenue", ascending=False)

    return {"found": True, "kpi": kpi, "products": products, "suppliers": suppliers}
