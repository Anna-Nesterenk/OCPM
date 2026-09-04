"""
pages/05_Batch.py
==================
Batch 360° (ТЗ §8.5, §13) -- the most important scenario. Batch is the object
that lets you walk the *entire* chain for one physical lot of stock:
Supplier → Purchase Order → Delivery → Batch → Warehouse → Sale → Customer → Return.
"""
import pandas as pd
import streamlit as st

import ui
import visualizations as viz
from analytics.batch import (batch_360, batch_table, fastest_batches, high_return_batches,
                              negative_contribution_batches, no_sale_batches, slowest_batches)
from data_model import badge_html, chain_html
from metrics import fmt_days, fmt_money, fmt_num, fmt_pct

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]

ui.page_chrome("Batch 360°", "Batch-Centric Analysis",
                "Найдеталізованіша точка дослідження: одна партія товару, простежена через увесь бізнес-ланцюг.")

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії.")
    st.stop()

ids = batch_full["batch_id"].tolist()
default = st.session_state.get("selected_batch")
idx = ids.index(default) if default in ids else 0
sel = st.selectbox("Batch ID", ids, index=idx)
st.session_state["selected_batch"] = sel

data = batch_360(batch_full, sel)
if not data["found"]:
    st.info("Цієї партії немає в поточному зрізі фільтрів.")
    st.stop()
row = data["row"]

st.markdown(badge_html("Batch", row["batch_id"]), unsafe_allow_html=True)
st.markdown(
    chain_html([
        ("Supplier", row["supplier_name"]), ("Purchase Order", row["po_id"]),
        ("Delivery", row["delivery_id"]), ("Batch", row["batch_id"]),
        ("Warehouse", row["warehouse_name"]),
        ("Sale", "Sale" if row["quantity_sold"] > 0 else "no sale"),
        ("Customer", f"{int(row['n_distinct_customers'])} клієнт(и)" if row["quantity_sold"] > 0 else "—"),
        ("Return", f"{int(row['return_count'])} повернень" if row["return_count"] > 0 else "0"),
    ]),
    unsafe_allow_html=True,
)
st.write("")

ui.kpi_row([
    ("Product", row["product_name"]), ("Category", row["category_name"]),
    ("Supply Channel", row["channel_name"]),
    ("Отримано", row["received_date"].strftime("%Y-%m-%d") if pd.notna(row["received_date"]) else "—"),
    ("К-сть отримано", fmt_num(row["quantity_received"])), ("Продано", fmt_num(row["quantity_sold"])),
    ("Залишок", fmt_num(row["quantity_remaining"])), ("% продано", fmt_pct(row["pct_sold"])),
    ("Purchase Price", fmt_money(row["purchase_unit_price"], 2)), ("Revenue", fmt_money(row["revenue_total"])),
    ("Net Contribution", fmt_money(row["net_contribution"])), ("Return Rate", fmt_pct(row["return_rate_qty"])),
    ("Lead Time", fmt_days(row["supply_lead_days"], 0)), ("Days to First Sale", fmt_days(row["days_to_first_sale"], 0)),
])

st.markdown("###### Product / Batch Journey")
if row["quantity_sold"] > 0:
    st.plotly_chart(viz.batch_journey(row), use_container_width=True, config={"displayModeBar": False})
else:
    st.info("Ця партія ще не мала жодного продажу — журні недоступний до першої події Sale.")

st.divider()
st.markdown("### Batch Anomaly Detection")
st.caption("Автоматично виділені партії поточного зрізу даних за чотирма категоріями аномалій (ТЗ §13).")

a1, a2 = st.tabs(["Fastest / Slowest", "High Return / No Sale / Negative Contribution"])
with a1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Fastest Batches** (найшвидше до 1-го продажу)")
        ui.data_table(fastest_batches(batch_full, 10), key="fastest", download_name="fastest_batches", height=320)
    with c2:
        st.markdown("**Slowest Batches** (найповільніше до 1-го продажу)")
        ui.data_table(slowest_batches(batch_full, 10), key="slowest", download_name="slowest_batches", height=320)
with a2:
    st.markdown("**High Return Rate Batches** (мін. 5 проданих одиниць)")
    ui.data_table(high_return_batches(batch_full, 5, 10), key="highret", download_name="high_return_batches", height=280)
    st.markdown("**No-Sale Batches** (жодного продажу)")
    ui.data_table(no_sale_batches(batch_full).head(200), key="nosale", download_name="no_sale_batches", height=280)
    st.markdown("**Negative / Low Net Contribution Batches**")
    ui.data_table(negative_contribution_batches(batch_full, 10), key="negnc", download_name="negative_contribution_batches", height=280)

st.divider()
st.markdown("### Реєстр партій — повна таблиця")
ui.data_table(
    batch_table(batch_full), key="batch_all",
    search_cols=["batch_id", "product_name", "supplier_name", "category_name"],
    download_name="batches", height=460,
)
