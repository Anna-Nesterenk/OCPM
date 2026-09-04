"""
pages/04_Supplier.py
=====================
Supplier 360° (ТЗ §11) + the Supplier Investigation drill-down
Supplier → Batch → Product → Customer → Return (ТЗ §8.1).
"""
import streamlit as st

import ui
import visualizations as viz
from analytics.supplier import supplier_360, supplier_list
from data_model import badge_html, chain_html
from metrics import fmt_days, fmt_money, fmt_num, fmt_pct

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]
sales_full = st.session_state["filtered_sales_full"]

ui.page_chrome("Supplier 360°", "Supplier-Centric Analysis",
                "Procurement performance і downstream business impact: що насправді відбувається "
                "з товаром цього постачальника після закупівлі.")

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії.")
    st.stop()

slist = supplier_list(batch_full)
ids = slist["supplier_id"].tolist()
names = dict(zip(slist["supplier_id"], slist["supplier_name"]))
default = st.session_state.get("selected_supplier")
idx = ids.index(default) if default in ids else 0
sel = st.selectbox("Постачальник", ids, index=idx, format_func=lambda i: f"{names[i]} ({i})")
st.session_state["selected_supplier"] = sel

data = supplier_360(batch_full, sales_full, sel)
if not data["found"]:
    st.info("Немає даних для цього постачальника в поточному зрізі фільтрів.")
    st.stop()

k = data["kpi"]
st.markdown(badge_html("Supplier", k["supplier_name"]) +
            f'&nbsp;&nbsp;<span style="color:#8a8779;font-size:13px;">{k["country"]} · {k["supplier_type"]} · rating {k["rating"]}</span>',
            unsafe_allow_html=True)
ui.kpi_row([
    ("Products", fmt_num(k["n_products"])), ("Purchase Orders", fmt_num(k["n_purchase_orders"])),
    ("Deliveries", fmt_num(k["n_deliveries"])), ("Batches", fmt_num(k["n_batches"])),
    ("Avg Price", fmt_money(k["avg_purchase_price"], 2)), ("Lead Time", fmt_days(k["avg_supply_lead_days"])),
    ("Delay Rate", fmt_pct(k["delay_rate_pct"])), ("Avg Delay", fmt_days(k["avg_delay_when_delayed"])),
    ("Revenue", fmt_money(k["revenue"])), ("Net Contribution", fmt_money(k["net_contribution"])),
    ("Return Rate", fmt_pct(k["return_rate_pct"])), ("Return Cost", fmt_money(k["return_cost"])),
])

st.markdown("###### Downstream impact")
st.markdown(chain_html([("Supplier", k["supplier_name"]), ("Batch", "Batch"), ("Product", "Product"),
                         ("Customer", "Customer"), ("Return", "Return")]), unsafe_allow_html=True)

tabs = st.tabs(["Products", "Customers", "Returns", "Партії", "Supplier Performance Matrix"])
with tabs[0]:
    ui.data_table(data["by_product"], key="sup_products", search_cols=["product_name"], download_name=f"{sel}_products")
with tabs[1]:
    ui.data_table(data["customers"], key="sup_customers", search_cols=["customer_name", "customer_segment"],
                  download_name=f"{sel}_customers")
with tabs[2]:
    if data["returns_chain"].empty:
        st.info("Повернень по цьому постачальнику в поточному зрізі немає.")
    else:
        ui.data_table(data["returns_chain"], key="sup_returns", search_cols=["product_name"], download_name=f"{sel}_returns")
        st.plotly_chart(viz.sankey_supplier_product_return(batch_full[batch_full["supplier_id"] == sel]),
                         use_container_width=True)
with tabs[3]:
    ui.data_table(data["batches"], key="sup_batches", search_cols=["batch_id", "product_name"], download_name=f"{sel}_batches")
with tabs[4]:
    st.caption("Purchase Price × Delay Rate × Return Rate для всіх постачальників у поточному зрізі. "
               "Розмір бульбашки = Return Rate. Дешевший постачальник не завжди найефективніший.")
    st.plotly_chart(viz.supplier_matrix(slist), use_container_width=True)

st.divider()
with st.expander("Показати всіх постачальників (Supplier 360° — повна таблиця)"):
    ui.data_table(slist, key="sup_all", search_cols=["supplier_id", "supplier_name", "country"], download_name="suppliers")
