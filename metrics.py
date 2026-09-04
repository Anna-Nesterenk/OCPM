"""
metrics.py
==========
Small, dependency-free helpers shared by every analytics/*.py module and by
the pages themselves: safe division/formatting, the generic "aggregate
batch_full by some key" routine, and the global Process Overview KPI set
(ТЗ §9.1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def safe_div(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(b != 0, a / b, np.nan)
    return out


def fmt_money(x, decimals=0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"${x:,.{decimals}f}"


def fmt_pct(x, decimals=1) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{decimals}f}%"


def fmt_days(x, decimals=1) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{decimals}f} дн."


def fmt_num(x, decimals=0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{decimals}f}"


AGG_MAP = dict(
    n_batches=("batch_id", "nunique"),
    n_suppliers=("supplier_id", "nunique"),
    n_products=("product_id", "nunique"),
    qty_received=("quantity_received", "sum"),
    qty_sold=("quantity_sold", "sum"),
    qty_remaining=("quantity_remaining", "sum"),
    avg_purchase_price=("purchase_unit_price", "mean"),
    min_purchase_price=("purchase_unit_price", "min"),
    max_purchase_price=("purchase_unit_price", "max"),
    revenue=("revenue_total", "sum"),
    cogs=("cogs", "sum"),
    purchase_value_received=("purchase_value_received", "sum"),
    transportation_cost_expensed=("transportation_cost_expensed", "sum"),
    return_cost=("return_cost_total", "sum"),
    net_contribution=("net_contribution", "sum"),
    return_qty=("return_qty", "sum"),
    avg_supply_lead_days=("supply_lead_days", "mean"),
    std_supply_lead_days=("supply_lead_days", "std"),
    avg_procurement_lead_days=("procurement_lead_days", "mean"),
    avg_days_to_first_sale=("days_to_first_sale", "mean"),
    avg_e2e_days=("e2e_days_order_to_first_sale", "mean"),
    median_e2e_days=("e2e_days_order_to_first_sale", "median"),
    inventory_value_unsold=("inventory_value_unsold", "sum"),
)


def aggregate_batches(batch_full: pd.DataFrame, by) -> pd.DataFrame:
    """Generic groupby(by) over batch_full producing the standard KPI set used
    across Product/Category/Supplier/Channel/Warehouse 360 views."""
    if batch_full.empty:
        cols = ([by] if isinstance(by, str) else list(by)) + list(AGG_MAP.keys())
        return pd.DataFrame(columns=cols)

    g = batch_full.groupby(by, dropna=False)
    out = g.agg(**AGG_MAP).reset_index()

    delay = g.apply(
        lambda x: pd.Series({
            "delay_rate_pct": (x["delay_days"] > 0).mean() * 100,
            "avg_delay_when_delayed": x.loc[x["delay_days"] > 0, "delay_days"].mean()
            if (x["delay_days"] > 0).any() else 0.0,
        }),
        include_groups=False,
    ).reset_index()
    out = out.merge(delay, on=([by] if isinstance(by, str) else list(by)))

    out["pct_sold"] = np.where(out["qty_received"] > 0, out["qty_sold"] / out["qty_received"] * 100, 0)
    out["return_rate_pct"] = np.where(out["qty_sold"] > 0, out["return_qty"] / out["qty_sold"] * 100, 0)
    out["margin_pct"] = np.where(out["revenue"] > 0, out["net_contribution"] / out["revenue"] * 100, np.nan)
    out["turnover_ratio"] = np.where(out["qty_received"] > 0, out["qty_sold"] / out["qty_received"], 0)
    return out


def overview_kpis(batch_full: pd.DataFrame, bundle) -> dict:
    """The global KPI row for the Process Overview page (ТЗ §9.1)."""
    sold = batch_full[batch_full["quantity_sold"] > 0]
    total_qty_sold = batch_full["quantity_sold"].sum()
    total_return_qty = batch_full["return_qty"].sum()
    n_customers_in_scope = int(bundle.sales_full.loc[
        bundle.sales_full["batch_id"].isin(batch_full["batch_id"]), "customer_id"
    ].nunique()) if not batch_full.empty else 0

    return dict(
        n_products=int(batch_full["product_id"].nunique()),
        n_suppliers=int(batch_full["supplier_id"].nunique()),
        n_batches=int(batch_full["batch_id"].nunique()),
        n_customers=n_customers_in_scope,
        n_sales=int(batch_full["n_sale_txns"].sum()),
        n_returns=int(batch_full["return_count"].sum()),
        revenue=float(batch_full["revenue_total"].sum()),
        net_contribution=float(batch_full["net_contribution"].sum()),
        inventory_value_unsold=float(batch_full["inventory_value_unsold"].sum()),
        avg_e2e_days=float(sold["e2e_days_order_to_first_sale"].mean()) if len(sold) else float("nan"),
        return_rate_pct=float(safe_div(total_return_qty, total_qty_sold) * 100) if total_qty_sold else 0.0,
        delay_rate_pct=float((batch_full["delay_days"] > 0).mean() * 100) if len(batch_full) else 0.0,
        pct_batches_untouched=float((batch_full["is_untouched"]).mean() * 100) if len(batch_full) else 0.0,
    )


def cycle_by(batch_full: pd.DataFrame, by) -> pd.DataFrame:
    """Procurement / Supply / Inventory / E2E cycle averages grouped by `by` (ТЗ §15)."""
    if batch_full.empty:
        return pd.DataFrame()
    g = batch_full.groupby(by, dropna=False)
    out = g.agg(
        n=("batch_id", "nunique"),
        avg_procurement_lead=("procurement_lead_days", "mean"),
        avg_supply_lead=("supply_lead_days", "mean"),
        avg_days_to_first_sale=("days_to_first_sale", "mean"),
        avg_e2e=("e2e_days_order_to_first_sale", "mean"),
        median_e2e=("e2e_days_order_to_first_sale", "median"),
    ).reset_index()
    return out
