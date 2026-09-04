"""
pages/01_Overview.py
=====================
Process Overview (ТЗ §9): global KPIs, the end-to-end chain, and the Object
Relationship Graph -- the "one glance" landing page.
"""
import streamlit as st

import ui
from data_model import badge_html
from metrics import fmt_days, fmt_money, fmt_num, fmt_pct, overview_kpis
from ocpm_graph import build_graph, degree_table, plot_object_graph

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]

ui.page_chrome(
    "Process Overview",
    "Supply-to-Customer: один процес, шість перспектив",
    "Один і той самий бізнес-процес — Supplier → Purchase Order → PO Item → Delivery → Batch → "
    "Warehouse → Sale → Customer → Return — можна дослідити з різних точок входу. "
    "Оберіть об'єкт на сторінці **Explore by Object**, щоб почати дослідження.",
)

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії. Скиньте фільтри в сайдбарі.")
    st.stop()

k = overview_kpis(batch_full, bundle)
ui.kpi_row([
    ("Products", fmt_num(k["n_products"])),
    ("Suppliers", fmt_num(k["n_suppliers"])),
    ("Batches", fmt_num(k["n_batches"])),
    ("Customers", fmt_num(k["n_customers"])),
    ("Sales", fmt_num(k["n_sales"])),
    ("Returns", fmt_num(k["n_returns"])),
    ("Revenue", fmt_money(k["revenue"])),
    ("Net Contribution", fmt_money(k["net_contribution"])),
    ("Заморожено в запасах", fmt_money(k["inventory_value_unsold"])),
    ("Return Rate", fmt_pct(k["return_rate_pct"])),
    ("Delay Rate", fmt_pct(k["delay_rate_pct"])),
    ("Сер. E2E цикл", fmt_days(k["avg_e2e_days"])),
])

st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
st.markdown("#### Наскрізний ланцюг процесу")
chain_types = ["Supplier", "Purchase Order", "PO Item", "Delivery", "Batch", "Warehouse", "Sale", "Customer", "Return"]
st.markdown(
    '<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">' +
    "".join(
        badge_html(t) + ('<span style="color:#9a9890;">&rarr;</span>' if i < len(chain_types) - 1 else "")
        for i, t in enumerate(chain_types)
    ) + "</div>",
    unsafe_allow_html=True,
)
st.caption("Batch — критичний об'єкт лінеджу: єдина сутність, що фізично пронизує процес від закупівлі до конкретного клієнта.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
st.markdown("#### Object Relationship Graph")
G = build_graph()
st.plotly_chart(plot_object_graph(G), use_container_width=True, config={"displayModeBar": False})
st.caption(
    "Товщина зв'язку відповідає кількості записів-зв'язків, розмір вузла — його degree (кількості "
    "прямих зв'язків з іншими типами об'єктів). Product, Batch і Sale — найбільш зв'язані об'єкти моделі."
)
with st.expander("Ступінь зв'язності об'єктів (degree)"):
    st.dataframe(degree_table(G), use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
    st.markdown("#### Куди далі")
    st.markdown(
        "- **Explore by Object** — оберіть Supplier / Product / Batch / Customer / Category / Channel і "
        "отримайте 360° огляд.\n"
        "- **Insights** — автоматично знайдені аномалії та ризики на поточному зрізі даних.\n"
        "- **Methodology** — чому Object-Centric, а не Case-Centric."
    )
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
    st.markdown("#### Стан запасів")
    st.metric("Партій без жодного продажу", f"{k['pct_batches_untouched']:.1f}%")
    st.progress(min(1.0, k["pct_batches_untouched"] / 100))
    st.caption("Дивіться сторінку **Insights → Slow Inventory** для деталізації.")
    st.markdown("</div>", unsafe_allow_html=True)
