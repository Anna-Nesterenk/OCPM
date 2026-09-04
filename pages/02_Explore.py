"""
pages/02_Explore.py
====================
"Explore by Object" (ТЗ §7.1): pick an object type, pick an instance, get an
instant KPI/anomaly/insight preview, then jump to the full 360 page. This is
the generic entry point the four Obligatory Object Navigation scenarios
(ТЗ §8.1-8.4) all start from; Batch 360 (§8.5) has its own dedicated page.
"""
import pandas as pd
import streamlit as st

import ui
from analytics.batch import batch_table
from analytics.category import category_list
from analytics.channel import channel_list
from analytics.customer import customer_list
from analytics.product import product_list
from analytics.supplier import supplier_list
from data_model import ENTRY_OBJECT_TYPES, badge_html, chain_html
from insights import generate_insights
from metrics import fmt_days, fmt_money, fmt_num, fmt_pct
from navigation import go_to

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]
sales_full = st.session_state["filtered_sales_full"]

ui.page_chrome(
    "Explore by Object",
    "Оберіть точку входу в дослідження",
    "Той самий процес виглядає по-різному залежно від того, з якого об'єкта ви почали. "
    "Оберіть тип об'єкта і конкретний екземпляр, щоб побачити його 360°-контекст.",
)

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії. Скиньте фільтри в сайдбарі.")
    st.stop()

c1, c2 = st.columns([1, 2])
object_type = c1.selectbox("Тип об'єкта", ENTRY_OBJECT_TYPES,
                            index=ENTRY_OBJECT_TYPES.index(st.session_state.get("explore_object_type", "Supplier")))
st.session_state["explore_object_type"] = object_type

PAGE_MAP = {
    "Supplier": ("Supplier", "supplier_id", "supplier_name"),
    "Product": ("Product", "product_id", "product_name"),
    "Batch": ("Batch", "batch_id", "batch_id"),
    "Customer": ("Customer", "customer_id", "customer_name"),
    "Product Category": ("Explore", "category_name", "category_name"),
    "Supply Channel": ("Supply Channel", "channel_id", "channel_name"),
}


def _options_for(object_type: str):
    if object_type == "Supplier":
        df = supplier_list(batch_full)
        return df, "supplier_id", "supplier_name"
    if object_type == "Product":
        df = product_list(batch_full)
        return df, "product_id", "product_name"
    if object_type == "Batch":
        df = batch_table(batch_full)
        return df, "batch_id", "batch_id"
    if object_type == "Customer":
        df = customer_list(sales_full, bundle.returns, bundle.customers)
        return df, "customer_id", "customer_name"
    if object_type == "Product Category":
        df = category_list(batch_full)
        return df, "category_name", "category_name"
    if object_type == "Supply Channel":
        df = channel_list(batch_full)
        return df, "channel_id", "channel_name"
    raise ValueError(object_type)


opt_df, id_col, name_col = _options_for(object_type)
if opt_df.empty:
    st.info("Немає об'єктів цього типу в поточному зрізі даних.")
    st.stop()

opt_df = opt_df.sort_values("revenue", ascending=False) if "revenue" in opt_df.columns else opt_df
labels = [f"{r[name_col]}" + (f"  ({r[id_col]})" if name_col != id_col else "") for _, r in opt_df.iterrows()]
sel_idx = c2.selectbox("Об'єкт", range(len(labels)), format_func=lambda i: labels[i])
sel_row = opt_df.iloc[sel_idx]
sel_id = sel_row[id_col]

st.markdown(badge_html(object_type, str(sel_row[name_col])), unsafe_allow_html=True)
st.write("")

# ---- generic 360 preview -------------------------------------------------
if object_type == "Supplier":
    scope = batch_full[batch_full["supplier_id"] == sel_id]
    ui.kpi_row([
        ("Products", fmt_num(scope["product_id"].nunique())),
        ("Batches", fmt_num(scope["batch_id"].nunique())),
        ("Avg Price", fmt_money(scope["purchase_unit_price"].mean(), 2)),
        ("Delay Rate", fmt_pct((scope["delay_days"] > 0).mean() * 100)),
        ("Revenue", fmt_money(scope["revenue_total"].sum())),
        ("Net Contribution", fmt_money(scope["net_contribution"].sum())),
    ])
elif object_type == "Product":
    scope = batch_full[batch_full["product_id"] == sel_id]
    ui.kpi_row([
        ("Suppliers", fmt_num(scope["supplier_id"].nunique())),
        ("Batches", fmt_num(scope["batch_id"].nunique())),
        ("Revenue", fmt_money(scope["revenue_total"].sum())),
        ("Net Contribution", fmt_money(scope["net_contribution"].sum())),
        ("Return Rate", fmt_pct(scope["return_qty"].sum() / max(scope["quantity_sold"].sum(), 1) * 100)),
        ("Lead Time", fmt_days(scope["supply_lead_days"].mean())),
    ])
elif object_type == "Batch":
    scope = batch_full[batch_full["batch_id"] == sel_id].iloc[0]
    ui.kpi_row([
        ("Product", scope["product_name"]), ("Supplier", scope["supplier_name"]),
        ("% продано", fmt_pct(scope["pct_sold"])), ("Revenue", fmt_money(scope["revenue_total"])),
        ("Net Contribution", fmt_money(scope["net_contribution"])), ("Return Rate", fmt_pct(scope["return_rate_qty"])),
    ])
elif object_type == "Customer":
    scope = sales_full[sales_full["customer_id"] == sel_id]
    ui.kpi_row([
        ("Purchases", fmt_num(len(scope))), ("Products", fmt_num(scope["product_id"].nunique())),
        ("Categories", fmt_num(scope["category_id"].nunique())), ("Revenue", fmt_money(scope["revenue"].sum())),
    ])
elif object_type == "Product Category":
    scope = batch_full[batch_full["category_name"] == sel_id]
    ui.kpi_row([
        ("Products", fmt_num(scope["product_id"].nunique())), ("Suppliers", fmt_num(scope["supplier_id"].nunique())),
        ("Revenue", fmt_money(scope["revenue_total"].sum())), ("Net Contribution", fmt_money(scope["net_contribution"].sum())),
        ("Return Rate", fmt_pct(scope["return_qty"].sum() / max(scope["quantity_sold"].sum(), 1) * 100)),
    ])
elif object_type == "Supply Channel":
    scope = batch_full[batch_full["channel_id"] == sel_id]
    ui.kpi_row([
        ("Batches", fmt_num(scope["batch_id"].nunique())), ("Lead Time", fmt_days(scope["supply_lead_days"].mean())),
        ("Delay Rate", fmt_pct((scope["delay_days"] > 0).mean() * 100)),
        ("Days to First Sale", fmt_days(scope["days_to_first_sale"].mean())),
        ("Revenue", fmt_money(scope["revenue_total"].sum())),
    ])

# insights whose object chain touches this object
scoped_insights = [c for c in generate_insights(batch_full)
                    if any(str(sel_row[name_col]) in label or str(sel_id) in label for _, label in c["object_chain"])]
if scoped_insights:
    st.markdown("##### Пов'язані інсайти")
    for i, card in enumerate(scoped_insights[:2], 1):
        ui.render_insight_card(card, i)

page_key = PAGE_MAP[object_type][0]
extra = {}
if object_type == "Supplier":
    extra = {"selected_supplier": sel_id}
elif object_type == "Product":
    extra = {"selected_product": sel_id}
elif object_type == "Batch":
    extra = {"selected_batch": sel_id}
elif object_type == "Customer":
    extra = {"selected_customer": sel_id}
elif object_type == "Product Category":
    extra = {"selected_category": sel_id}
elif object_type == "Supply Channel":
    extra = {"selected_channel": sel_id}

if st.button(f"Відкрити повний 360° огляд →", type="primary"):
    go_to(page_key, **extra)

st.divider()
st.markdown("##### Обов'язкові сценарії Object Navigation (ТЗ §8)")
st.markdown(
    chain_html([("Supplier", "Supplier"), ("Batch", "Batch"), ("Product", "Product"),
                ("Customer", "Customer"), ("Return", "Return")]) +
    "<div style='height:8px'></div>" +
    chain_html([("Supply Channel", "Supply Channel"), ("Batch", "Batch"), ("Sale", "Sale / Customer")]) +
    "<div style='height:8px'></div>" +
    chain_html([("Product Category", "Category"), ("Product", "Product"), ("Supplier", "Supplier")]) +
    "<div style='height:8px'></div>" +
    chain_html([("Customer", "Customer"), ("Product Category", "Category"), ("Product", "Product"), ("Supplier", "Supplier")]),
    unsafe_allow_html=True,
)
st.caption("Кожен із цих ланцюгів повністю реалізований у відповідних 360°-сторінках (Supplier, Supply Channel, "
           "Product/Category, Customer) — просто оберіть об'єкт вище.")
