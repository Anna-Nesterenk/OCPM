"""
data_loader.py
===============
Single source of truth for reading the OCPM Supply-to-Customer dataset and
turning it into an analysis-ready, object-centric shape.

Every other module (metrics.py, analytics/*, insights.py, pages/*) works off
the DataFrames returned here -- nothing else in the app reads a CSV directly.

The central artifact produced here is `batch_full`: one row per Batch, with
every object on its lineage (Supplier -> PO -> PO Item -> Delivery -> Batch ->
Warehouse -> Sale -> Customer -> Return) joined in, plus derived lead times
and a documented cost allocation (see `_allocate_costs`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

REQUIRED_FILES = [
    "products.csv", "product_categories.csv", "suppliers.csv", "supply_channels.csv",
    "warehouses.csv", "customers.csv", "purchase_orders.csv", "purchase_order_items.csv",
    "deliveries.csv", "delivery_items.csv", "batches.csv", "sales_orders.csv",
    "sales_order_items.csv", "sales.csv", "returns.csv", "events.csv", "objects.csv",
    "event_object_relations.csv",
]


@dataclass
class Bundle:
    """Container for every raw + derived table the app needs."""
    products: pd.DataFrame
    categories: pd.DataFrame
    suppliers: pd.DataFrame
    channels: pd.DataFrame
    warehouses: pd.DataFrame
    customers: pd.DataFrame
    purchase_orders: pd.DataFrame
    po_items: pd.DataFrame
    deliveries: pd.DataFrame
    delivery_items: pd.DataFrame
    batches: pd.DataFrame
    sales_orders: pd.DataFrame
    sales_order_items: pd.DataFrame
    sales: pd.DataFrame
    returns: pd.DataFrame
    events: pd.DataFrame
    objects: pd.DataFrame
    event_object_relations: pd.DataFrame
    batch_full: pd.DataFrame
    sales_full: pd.DataFrame


def data_files_present(data_dir: str = DATA_DIR) -> list[str]:
    """Return the list of required files that are missing from data_dir."""
    if not os.path.isdir(data_dir):
        return REQUIRED_FILES
    have = set(os.listdir(data_dir))
    return [f for f in REQUIRED_FILES if f not in have]


@st.cache_data(show_spinner="Завантаження OCPM датасету…")
def load_bundle(data_dir: str = DATA_DIR) -> Bundle:
    r = lambda name, **kw: pd.read_csv(os.path.join(data_dir, name), **kw)

    products = r("products.csv")
    categories = r("product_categories.csv")
    suppliers = r("suppliers.csv")
    channels = r("supply_channels.csv")
    warehouses = r("warehouses.csv")
    customers = r("customers.csv")
    purchase_orders = r("purchase_orders.csv", parse_dates=["order_date", "expected_delivery_date"])
    po_items = r("purchase_order_items.csv")
    deliveries = r("deliveries.csv", parse_dates=["dispatch_date", "expected_arrival_date", "actual_arrival_date"])
    delivery_items = r("delivery_items.csv")
    batches = r("batches.csv", parse_dates=["received_date"])
    sales_orders = r("sales_orders.csv", parse_dates=["order_date"])
    sales_order_items = r("sales_order_items.csv")
    sales = r("sales.csv", parse_dates=["sale_date"])
    returns = r("returns.csv", parse_dates=["return_date"])
    events = r("events.csv", parse_dates=["timestamp"])
    objects = r("objects.csv")
    event_object_relations = r("event_object_relations.csv")

    batch_full = _build_batch_full(
        products, suppliers, channels, warehouses,
        purchase_orders, po_items, deliveries, delivery_items, batches, sales, returns,
    )
    sales_full = _build_sales_full(sales, batch_full, sales_order_items, sales_orders, customers)

    return Bundle(
        products=products, categories=categories, suppliers=suppliers, channels=channels,
        warehouses=warehouses, customers=customers, purchase_orders=purchase_orders,
        po_items=po_items, deliveries=deliveries, delivery_items=delivery_items, batches=batches,
        sales_orders=sales_orders, sales_order_items=sales_order_items, sales=sales, returns=returns,
        events=events, objects=objects, event_object_relations=event_object_relations,
        batch_full=batch_full, sales_full=sales_full,
    )


def _build_batch_full(products, suppliers, channels, warehouses,
                       purchase_orders, po_items, deliveries, delivery_items, batches, sales, returns
                       ) -> pd.DataFrame:
    """One row per Batch, with its full lineage joined in and derived metrics computed."""

    # transportation cost of a delivery, split across its delivery_items by received quantity
    di_cost = delivery_items.merge(deliveries[["delivery_id", "transportation_cost"]], on="delivery_id")
    di_cost["qty_share"] = di_cost.groupby("delivery_id")["quantity"].transform(lambda s: s / s.sum())
    di_cost["transportation_cost_allocated"] = di_cost["qty_share"] * di_cost["transportation_cost"]

    b = batches.copy()
    b = b.merge(delivery_items[["delivery_item_id", "delivery_id"]], on="delivery_item_id", how="left")
    b = b.merge(
        deliveries[["delivery_id", "channel_id", "dispatch_date", "expected_arrival_date",
                     "actual_arrival_date", "delay_days", "transportation_cost"]],
        on="delivery_id", how="left",
    )
    b = b.merge(di_cost[["delivery_item_id", "transportation_cost_allocated"]], on="delivery_item_id", how="left")
    b = b.merge(po_items[["po_item_id", "po_id", "ordered_quantity"]], on="po_item_id", how="left")
    b = b.merge(purchase_orders[["po_id", "order_date", "expected_delivery_date"]], on="po_id", how="left")
    b = b.merge(products[["product_id", "product_name", "category_id", "category_name", "brand", "standard_cost"]],
                on="product_id", how="left")
    b = b.merge(suppliers[["supplier_id", "supplier_name", "country", "supplier_type", "rating"]],
                on="supplier_id", how="left")
    b = b.merge(channels[["channel_id", "channel_name", "target_lead_days", "delay_probability"]],
                on="channel_id", how="left")
    b = b.merge(warehouses[["warehouse_id", "warehouse_name", "region"]], on="warehouse_id", how="left")

    b["quantity_sold"] = b["quantity_received"] - b["quantity_remaining"]
    b["pct_sold"] = np.where(b["quantity_received"] > 0, b["quantity_sold"] / b["quantity_received"] * 100, 0)

    sales_agg = sales.groupby("batch_id").agg(
        first_sale_date=("sale_date", "min"), last_sale_date=("sale_date", "max"),
        revenue_total=("revenue", "sum"), qty_sold_txn=("quantity", "sum"),
        n_sale_txns=("sale_id", "count"), n_distinct_customers=("customer_id", "nunique"),
        avg_selling_price=("selling_unit_price", "mean"),
    ).reset_index()
    b = b.merge(sales_agg, on="batch_id", how="left")

    ret_agg = returns.groupby("batch_id").agg(
        return_qty=("quantity", "sum"), return_count=("return_id", "count"), return_cost_total=("return_cost", "sum"),
    ).reset_index()
    b = b.merge(ret_agg, on="batch_id", how="left")
    for c in ["return_qty", "return_count", "return_cost_total", "revenue_total", "qty_sold_txn",
              "n_sale_txns", "n_distinct_customers"]:
        b[c] = b[c].fillna(0)

    b["supply_lead_days"] = (b["actual_arrival_date"] - b["dispatch_date"]).dt.days
    b["procurement_lead_days"] = (b["actual_arrival_date"] - b["order_date"]).dt.days
    b["days_to_first_sale"] = (b["first_sale_date"] - b["received_date"]).dt.days
    b["e2e_days_order_to_first_sale"] = (b["first_sale_date"] - b["order_date"]).dt.days
    b["is_fully_sold"] = b["quantity_remaining"] == 0
    b["is_untouched"] = b["quantity_remaining"] == b["quantity_received"]
    b["days_full_sellthrough"] = np.where(
        b["is_fully_sold"], (b["last_sale_date"] - b["received_date"]).dt.days, np.nan
    )

    b = _allocate_costs(b)
    b["return_rate_qty"] = np.where(b["qty_sold_txn"] > 0, b["return_qty"] / b["qty_sold_txn"] * 100, 0)
    b["delayed"] = b["delay_days"] > 0
    return b


def _allocate_costs(b: pd.DataFrame) -> pd.DataFrame:
    """
    Documented cost-allocation rule (see Methodology page for the full writeup):

    1. A delivery's transportation_cost is split across its delivery_items (=batches)
       proportional to received quantity (`transportation_cost_allocated`, done upstream).
    2. For P&L (`net_contribution`), only the SOLD share of a batch's transportation
       cost is expensed against revenue -- the unsold share is capitalised into
       on-hand inventory value rather than expensed with no matching revenue.
    3. COGS = purchase_unit_price x quantity actually sold.
    4. Net Contribution = Revenue - COGS - Transportation(sold share) - Return Cost.
    """
    b = b.copy()
    b["cogs"] = b["purchase_unit_price"] * b["quantity_sold"]
    b["purchase_value_received"] = b["purchase_unit_price"] * b["quantity_received"]
    b["transportation_cost_allocated"] = b["transportation_cost_allocated"].fillna(0)
    b["transportation_cost_expensed"] = b["transportation_cost_allocated"] * (b["pct_sold"] / 100.0)
    b["transportation_cost_capitalized_unsold"] = b["transportation_cost_allocated"] - b["transportation_cost_expensed"]
    b["inventory_value_unsold"] = b["quantity_remaining"] * b["purchase_unit_price"] + b["transportation_cost_capitalized_unsold"]
    b["net_contribution"] = b["revenue_total"] - b["cogs"] - b["transportation_cost_expensed"] - b["return_cost_total"]
    return b


def _build_sales_full(sales, batch_full, sales_order_items, sales_orders, customers) -> pd.DataFrame:
    cols = ["batch_id", "product_id", "product_name", "category_id", "category_name",
            "supplier_id", "supplier_name", "channel_id", "channel_name", "warehouse_id", "warehouse_name"]
    s = sales.merge(batch_full[cols], on="batch_id", how="left")
    s = s.merge(sales_order_items[["sales_order_item_id", "sales_order_id"]], on="sales_order_item_id", how="left")
    s = s.merge(sales_orders[["sales_order_id", "sales_channel"]], on="sales_order_id", how="left")
    s = s.merge(customers, on="customer_id", how="left")
    return s
