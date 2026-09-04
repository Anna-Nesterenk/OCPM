"""
navigation.py
=============
Centralised session-state handling: global filters, cross-page context
(selected_supplier / selected_product / selected_batch / ...) and the
drill-down mechanism pages use to send the user to another page with an
object already selected (ТЗ §19).

Streamlit's native multipage navigation (`st.switch_page`) changes the script
that runs, so state has to survive in `st.session_state` -- that's the whole
job of this module.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from data_model import SESSION_DEFAULTS, Filters

PAGES = {
    "Overview": "app.py",
    "Explore": "pages/02_Explore.py",
    "Product": "pages/03_Product.py",
    "Supplier": "pages/04_Supplier.py",
    "Batch": "pages/05_Batch.py",
    "Supply Channel": "pages/06_Supply_Channel.py",
    "Customer": "pages/07_Customer.py",
    "Insights": "pages/08_Insights.py",
    "Methodology": "pages/09_Methodology.py",
}


def init_session():
    for k, v in SESSION_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if "filters" not in st.session_state:
        st.session_state["filters"] = Filters()


def go_to(page_key: str, **context):
    """Drill-down: stash context (e.g. selected_supplier=...) and switch page."""
    for k, v in context.items():
        st.session_state[k] = v
    st.switch_page(PAGES[page_key])


def select_and_go(object_type: str, object_id: str):
    """Generic drill-down used by the graph / tables: click an object, land on its 360 page."""
    mapping = {
        "Supplier": ("Supplier", "selected_supplier"),
        "Product": ("Product", "selected_product"),
        "Batch": ("Batch", "selected_batch"),
        "Customer": ("Customer", "selected_customer"),
        "Product Category": ("Explore", "selected_category"),
        "Supply Channel": ("Supply Channel", "selected_channel"),
    }
    if object_type not in mapping:
        return
    page_key, state_key = mapping[object_type]
    go_to(page_key, **{state_key: object_id})


# ---------------------------------------------------------------------------
# Global filters
# ---------------------------------------------------------------------------
def render_global_filters(bundle, location=st.sidebar) -> Filters:
    """Draws the global filter widgets (ТЗ §18) and returns the current Filters."""
    f: Filters = st.session_state["filters"]
    location.markdown("#### Глобальні фільтри")

    min_d = pd.to_datetime(bundle.batches["received_date"]).min().date()
    max_d = pd.to_datetime(bundle.sales["sale_date"]).max().date()
    date_range = location.date_input(
        "Період (за датою отримання партії)", value=(f.date_from or min_d, f.date_to or max_d),
        min_value=min_d, max_value=max_d, key="flt_dates",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        f.date_from, f.date_to = date_range

    f.categories = location.multiselect(
        "Product Category", sorted(bundle.categories["category_name"].unique()), default=f.categories, key="flt_cat"
    )
    f.suppliers = location.multiselect(
        "Supplier", sorted(bundle.suppliers["supplier_name"].unique()), default=f.suppliers, key="flt_sup"
    )
    f.channels = location.multiselect(
        "Supply Channel", sorted(bundle.channels["channel_name"].unique()), default=f.channels, key="flt_ch"
    )
    f.warehouses = location.multiselect(
        "Warehouse", sorted(bundle.warehouses["warehouse_name"].unique()), default=f.warehouses, key="flt_wh"
    )
    f.segments = location.multiselect(
        "Customer Segment", sorted(bundle.customers["customer_segment"].unique()), default=f.segments, key="flt_seg"
    )
    if location.button("Скинути фільтри", use_container_width=True):
        st.session_state["filters"] = Filters()
        st.rerun()

    st.session_state["filters"] = f
    return f


def apply_filters(batch_full: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    """Filter the batch-level table by the current global filter selection."""
    df = batch_full
    if filters.date_from is not None:
        df = df[df["received_date"] >= pd.Timestamp(filters.date_from)]
    if filters.date_to is not None:
        df = df[df["received_date"] <= pd.Timestamp(filters.date_to)]
    if filters.categories:
        df = df[df["category_name"].isin(filters.categories)]
    if filters.suppliers:
        df = df[df["supplier_name"].isin(filters.suppliers)]
    if filters.channels:
        df = df[df["channel_name"].isin(filters.channels)]
    if filters.warehouses:
        df = df[df["warehouse_name"].isin(filters.warehouses)]
    return df


def apply_filters_to_sales(sales_full: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    df = sales_full
    if filters.date_from is not None:
        df = df[df["sale_date"] >= pd.Timestamp(filters.date_from)]
    if filters.date_to is not None:
        df = df[df["sale_date"] <= pd.Timestamp(filters.date_to)]
    if filters.categories:
        df = df[df["category_name"].isin(filters.categories)]
    if filters.suppliers:
        df = df[df["supplier_name"].isin(filters.suppliers)]
    if filters.channels:
        df = df[df["channel_name"].isin(filters.channels)]
    if filters.warehouses:
        df = df[df["warehouse_name"].isin(filters.warehouses)]
    if filters.segments:
        df = df[df["customer_segment"].isin(filters.segments)]
    return df


def sidebar_object_jump(bundle, key_prefix: str = "jump"):
    """A small 'jump to object' utility shown at the top of every 360 page's sidebar."""
    st.sidebar.markdown("#### Перейти до об'єкта")
    ot = st.sidebar.selectbox("Тип об'єкта", list(PAGES.keys())[2:7], key=f"{key_prefix}_type")
    st.sidebar.caption("Або скористайтесь Explore by Object на головній / сторінці Explore.")
