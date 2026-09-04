"""
pages/06_Supply_Channel.py
============================
Supply Channel Analysis (ТЗ §12) + the Channel Investigation drill-down
Supply Channel → Batch → Sale/Customer (ТЗ §8.2).
"""
import streamlit as st

import ui
import visualizations as viz
from analytics.channel import channel_360, channel_list
from data_model import badge_html, chain_html
from metrics import fmt_days, fmt_money, fmt_num, fmt_pct

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]

ui.page_chrome("Supply Channel", "Supply Channel Analysis",
                "Чи компенсує швидкість дорожчого каналу постачання його вищу вартість? "
                "Простежуємо канал від Delivery до фактичного Time to Sale.")

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії.")
    st.stop()

clist = channel_list(batch_full)
ids = clist["channel_id"].tolist()
names = dict(zip(clist["channel_id"], clist["channel_name"]))
default = st.session_state.get("selected_channel")
idx = ids.index(default) if default in ids else 0
sel = st.selectbox("Канал постачання", ids, index=idx, format_func=lambda i: names[i])
st.session_state["selected_channel"] = sel

data = channel_360(batch_full, sel)
if not data["found"]:
    st.info("Немає даних для цього каналу в поточному зрізі фільтрів.")
    st.stop()
k = data["kpi"]

st.markdown(badge_html("Supply Channel", k["channel_name"]) +
            f'&nbsp;&nbsp;<span style="color:#8a8779;font-size:13px;">target lead: {k["target_lead_days"]:.0f} дн.</span>',
            unsafe_allow_html=True)
ui.kpi_row([
    ("Батчів", fmt_num(k["n_batches"])), ("Lead Time", fmt_days(k["avg_supply_lead_days"])),
    ("Std Lead Time", fmt_days(k["std_supply_lead_days"])), ("Delay Rate", fmt_pct(k["delay_rate_pct"])),
    ("Avg Delay", fmt_days(k["avg_delay_when_delayed"])), ("До 1-го продажу", fmt_days(k["avg_days_to_first_sale"])),
    ("Revenue", fmt_money(k["revenue"])), ("Net Contribution", fmt_money(k["net_contribution"])),
])
st.markdown(chain_html([("Supply Channel", k["channel_name"]), ("Delivery", "Delivery"), ("Batch", "Batch"),
                         ("Sale", "Sale / Customer")]), unsafe_allow_html=True)

tabs = st.tabs(["Lead Time Distribution", "Supplier → Channel → Delivery", "Постачальники каналу", "Партії"])
with tabs[0]:
    st.caption("Розподіл Lead Time за каналами (весь поточний зріз) — не лише середнє, а й варіативність.")
    st.plotly_chart(viz.lead_time_box(batch_full, "channel_name", "supply_lead_days"), use_container_width=True)
with tabs[1]:
    st.caption("Топ-8 постачальників за обсягом → канал → чи відбулась затримка.")
    st.plotly_chart(viz.sankey_supplier_channel_delay(batch_full), use_container_width=True)
with tabs[2]:
    ui.data_table(data["by_supplier"], key="ch_suppliers", search_cols=["supplier_name"], download_name=f"{sel}_suppliers")
with tabs[3]:
    ui.data_table(data["batches"], key="ch_batches", search_cols=["batch_id", "product_name", "supplier_name"],
                  download_name=f"{sel}_batches")

st.divider()
with st.expander("Показати всі канали (повна таблиця)"):
    ui.data_table(clist, key="ch_all", search_cols=["channel_name"], download_name="channels")
