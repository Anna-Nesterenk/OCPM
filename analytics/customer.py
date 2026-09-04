"""
analytics/customer.py
======================
Customer 360 (ТЗ §14) and the Customer -> Category -> Supplier drill-down
(ТЗ §8.4).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def customer_list(sales_full: pd.DataFrame, returns: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    agg = sales_full.groupby(["customer_id", "customer_name", "customer_segment", "region"]).agg(
        n_purchases=("sale_id", "count"), n_products=("product_id", "nunique"),
        n_categories=("category_id", "nunique"), n_suppliers=("supplier_id", "nunique"),
        revenue=("revenue", "sum"), units=("quantity", "sum"),
    ).reset_index()
    ret = returns.groupby("customer_id").agg(
        return_qty=("quantity", "sum"), return_count=("return_id", "count"), return_cost=("return_cost", "sum")
    ).reset_index()
    out = agg.merge(ret, on="customer_id", how="left")
    for c in ["return_qty", "return_count", "return_cost"]:
        out[c] = out[c].fillna(0)
    out["return_rate_pct"] = np.where(out["units"] > 0, out["return_qty"] / out["units"] * 100, 0)
    # include customers with zero purchases in the current filter scope, if any
    missing = customers[~customers["customer_id"].isin(out["customer_id"])]
    if not missing.empty:
        pad = missing[["customer_id", "customer_name", "customer_segment", "region"]].copy()
        for c in ["n_purchases", "n_products", "n_categories", "n_suppliers", "revenue", "units",
                  "return_qty", "return_count", "return_cost", "return_rate_pct"]:
            pad[c] = 0
        out = pd.concat([out, pad], ignore_index=True)
    return out.sort_values("revenue", ascending=False)


def customer_360(sales_full: pd.DataFrame, returns: pd.DataFrame, customer_id: str) -> dict:
    cs = sales_full[sales_full["customer_id"] == customer_id]
    if cs.empty:
        return {"found": False}

    kpi = dict(
        n_purchases=int(len(cs)), n_products=int(cs["product_id"].nunique()),
        n_categories=int(cs["category_id"].nunique()), n_suppliers=int(cs["supplier_id"].nunique()),
        revenue=float(cs["revenue"].sum()), units=float(cs["quantity"].sum()),
        segment=cs["customer_segment"].iloc[0], region=cs["region"].iloc[0],
        name=cs["customer_name"].iloc[0],
    )
    cr = returns[returns["customer_id"] == customer_id]
    kpi["return_qty"] = float(cr["quantity"].sum())
    kpi["return_count"] = int(len(cr))
    kpi["return_rate_pct"] = float(kpi["return_qty"] / kpi["units"] * 100) if kpi["units"] else 0.0

    # Customer -> Category -> Supplier chain
    chain = cs.groupby(["category_name", "supplier_name"]).agg(
        revenue=("revenue", "sum"), units=("quantity", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    by_category = cs.groupby("category_name")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)
    purchases = cs[["sale_id", "sale_date", "product_name", "category_name", "supplier_name", "quantity",
                     "selling_unit_price", "revenue"]].sort_values("sale_date", ascending=False)

    return {"found": True, "kpi": kpi, "chain": chain, "by_category": by_category, "purchases": purchases}
