"""
pages/07_Customer.py
======================
Customer 360° (ТЗ §14) + the Customer Investigation drill-down
Customer → Product Category → Product → Supplier (ТЗ §8.4).
"""
import streamlit as st

import ui
import visualizations as viz
from analytics.customer import customer_360, customer_list
from data_model import badge_html, chain_html
from metrics import fmt_money, fmt_num, fmt_pct

bundle = st.session_state["bundle"]
sales_full = st.session_state["filtered_sales_full"]

ui.page_chrome("Customer 360°", "Customer-Centric Analysis",
                "Клієнти через товари, категорії та постачальників, що стоять за їхніми покупками.")

if sales_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодного продажу.")
    st.stop()

clist = customer_list(sales_full, bundle.returns, bundle.customers)
clist = clist[clist["revenue"] > 0] if (clist["revenue"] > 0).any() else clist
ids = clist["customer_id"].tolist()
names = dict(zip(clist["customer_id"], clist["customer_name"]))
default = st.session_state.get("selected_customer")
idx = ids.index(default) if default in ids else 0
sel = st.selectbox("Клієнт", ids, index=idx, format_func=lambda i: f"{names[i]} ({i})")
st.session_state["selected_customer"] = sel

data = customer_360(sales_full, bundle.returns, sel)
if not data["found"]:
    st.info("Немає покупок цього клієнта в поточному зрізі фільтрів.")
    st.stop()
k = data["kpi"]

st.markdown(badge_html("Customer", k["name"]) +
            f'&nbsp;&nbsp;<span style="color:#8a8779;font-size:13px;">{k["segment"]} · {k["region"]}</span>',
            unsafe_allow_html=True)
ui.kpi_row([
    ("Purchases", fmt_num(k["n_purchases"])), ("Products", fmt_num(k["n_products"])),
    ("Categories", fmt_num(k["n_categories"])), ("Suppliers", fmt_num(k["n_suppliers"])),
    ("Revenue", fmt_money(k["revenue"])), ("Returns", fmt_num(k["return_count"])),
    ("Return Rate", fmt_pct(k["return_rate_pct"])),
])

st.markdown("###### Customer → Category → Supplier")
tabs = st.tabs(["Ланцюг постачання", "За категоріями", "Історія покупок"])
with tabs[0]:
    ui.data_table(data["chain"], key="cust_chain", search_cols=["category_name", "supplier_name"], download_name=f"{sel}_chain")
    st.caption("Мета — перевірити, чи існують стійкі ланцюги Customer Segment → Product Category → Supplier "
               "для цього клієнта чи його сегмента.")
with tabs[1]:
    st.plotly_chart(viz.bar(data["by_category"], "category_name", "revenue", horizontal=True, height=320),
                     use_container_width=True, config={"displayModeBar": False})
with tabs[2]:
    ui.data_table(data["purchases"], key="cust_purchases", search_cols=["product_name", "supplier_name"],
                  download_name=f"{sel}_purchases")

st.divider()
with st.expander("Показати всіх клієнтів (Customer 360° — повна таблиця)"):
    ui.data_table(clist, key="cust_all", search_cols=["customer_id", "customer_name", "customer_segment", "region"],
                  download_name="customers")
