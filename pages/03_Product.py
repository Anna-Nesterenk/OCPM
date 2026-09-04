"""
pages/03_Product.py
====================
Product 360° (ТЗ §10): procurement view, sales view, and the Product
Profitability Matrix (Margin × Turnover).
"""
import streamlit as st

import ui
import visualizations as viz
from analytics.batch import batch_table
from analytics.product import product_360, product_list
from data_model import badge_html
from metrics import fmt_days, fmt_money, fmt_num, fmt_pct

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]
sales_full = st.session_state["filtered_sales_full"]

ui.page_chrome("Product 360°", "Product-Centric Analysis",
                "Закупівля, постачання, продажі, повернення і прибутковість — для одного товару.")

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії.")
    st.stop()

plist = product_list(batch_full)
ids = plist["product_id"].tolist()
names = dict(zip(plist["product_id"], plist["product_name"]))
default = st.session_state.get("selected_product")
idx = ids.index(default) if default in ids else 0
sel = st.selectbox("Товар", ids, index=idx, format_func=lambda i: f"{names[i]} ({i})")
st.session_state["selected_product"] = sel

data = product_360(batch_full, sales_full, sel)
if not data["found"]:
    st.info("Немає даних для цього товару в поточному зрізі фільтрів.")
    st.stop()

k = data["kpi"]
st.markdown(badge_html("Product", k["product_name"]) + "&nbsp;&nbsp;" + badge_html("Product Category", k["category_name"]),
            unsafe_allow_html=True)
ui.kpi_row([
    ("Suppliers", fmt_num(k["n_suppliers"])), ("Batches", fmt_num(k["n_batches"])),
    ("Закупівельний обсяг", fmt_money(k["purchase_value_received"])),
    ("Revenue", fmt_money(k["revenue"])), ("Net Contribution", fmt_money(k["net_contribution"])),
    ("Margin", fmt_pct(k["margin_pct"])), ("Return Rate", fmt_pct(k["return_rate_pct"])),
    ("Lead Time", fmt_days(k["avg_supply_lead_days"])),
    ("До 1-го продажу", fmt_days(k["avg_days_to_first_sale"])),
    ("Оборотність", fmt_pct(k["pct_sold"])), ("Клієнтів", fmt_num(data["n_customers"])),
])

tabs = st.tabs(["Procurement", "Sales", "Profitability Matrix", "Партії"])

with tabs[0]:
    st.markdown("###### Постачальники цього товару")
    st.dataframe(data["procurement"], use_container_width=True, hide_index=True)
    if data["cheapest_is_most_reliable"] is not None:
        if data["cheapest_is_most_reliable"]:
            st.success("Для цього товару найдешевший постачальник **також** має найнижчий Delay Rate.")
        else:
            st.warning("Для цього товару найдешевший постачальник **не є** найнадійнішим (найнижчий Delay Rate) — "
                       "класичний патерн 'дешевше ≠ ефективніше', див. сторінку Insights.")

with tabs[1]:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("###### За сегментом")
        st.plotly_chart(viz.bar(data["sales_by_segment"], "customer_segment", "revenue", horizontal=True, height=280),
                         use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown("###### За регіоном")
        st.plotly_chart(viz.bar(data["sales_by_region"], "region", "revenue", horizontal=True, height=280),
                         use_container_width=True, config={"displayModeBar": False})
    with c3:
        st.markdown("###### За каналом продажу")
        st.plotly_chart(viz.bar(data["sales_by_channel"], "sales_channel", "revenue", horizontal=True, height=280),
                         use_container_width=True, config={"displayModeBar": False})

with tabs[2]:
    st.caption("Margin × Turnover для всіх товарів у поточному зрізі. Обраний товар виділено розміром і кольором.")
    all_products = plist.copy()
    st.plotly_chart(viz.profitability_matrix(all_products), use_container_width=True)
    st.caption("Пунктирні лінії — медіана по вибірці. Верхній правий квадрант = прибуткові товари з високою "
               "оборотністю; нижній лівий = товари, що потенційно заморожують капітал.")

with tabs[3]:
    ui.data_table(data["batches"], key="product_batches", search_cols=["batch_id", "supplier_name"],
                  download_name=f"batches_{sel}")

st.divider()
with st.expander("Показати всі товари (Product 360° — повна таблиця)"):
    ui.data_table(plist, key="product_all", search_cols=["product_id", "product_name", "category_name", "brand"],
                  download_name="products")
