"""
pages/09_Methodology.py
=========================
Traditional Process Mining vs Object-Centric Process Mining (ТЗ §21):
explains the Event Log, the Object Model, Event↔Object Relations, why Batch
is central, and gives concrete examples of insights that only exist in the
cross-object view.
"""
import pandas as pd
import streamlit as st

import ui
from ocpm_graph import build_graph, degree_table

bundle = st.session_state["bundle"]

ui.page_chrome("Methodology", "Traditional Process Mining vs Object-Centric Process Mining",
                "Чому цей застосунок побудований навколо об'єктів, а не навколо єдиного Case ID.")

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
    st.markdown("#### Traditional Process Mining")
    st.markdown("**One Process + One Case ID**")
    st.markdown(
        "Кожна подія прив'язується рівно до одного кейсу (наприклад, Purchase Order). "
        "Аналіз бачить лише те, що відбувається *всередині* цього кейсу — від його початку до кінця."
    )
    po_status_variance = bundle.purchase_orders["status"].nunique()
    st.warning(
        f"У цьому датасеті поле `purchase_orders.status` має лише **{po_status_variance}** унікальне значення "
        f"на всі {len(bundle.purchase_orders)} записів ('Approved'). Process mining на кейсі Purchase Order "
        "буквально не знаходить жодної варіативності процесу — і зупиняється тут."
    )
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
    st.markdown("#### Object-Centric Process Mining (OCPM)")
    st.markdown("**One Business Reality + Multiple Connected Objects**")
    st.markdown(
        "Подія може одночасно стосуватися кількох об'єктів (Product, Batch, Delivery, Sale, Customer...). "
        "Аналіз може почати з будь-якого об'єкта і перейти до пов'язаних, простежуючи наскрізний контекст."
    )
    avg_types = bundle.event_object_relations.groupby("event_id")["object_type"].nunique().mean()
    st.success(
        f"У цьому датасеті одна подія пов'язана в середньому з **{avg_types:.2f}** різними типами об'єктів "
        f"(з {len(bundle.event_object_relations):,} записів у `event_object_relations.csv`)."
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
st.markdown("#### Структура Event Log")
st.dataframe(bundle.events.head(8), use_container_width=True, hide_index=True)
st.caption(f"{len(bundle.events):,} подій, {bundle.events['activity'].nunique()} унікальних типів активностей.")
act_counts = bundle.events["activity"].value_counts().rename_axis("activity").reset_index(name="count")
st.dataframe(act_counts, use_container_width=True, hide_index=True, height=260)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
st.markdown("#### Object Model & Event → Object Relations")
st.dataframe(bundle.objects.groupby("object_type").size().rename("count").reset_index(), use_container_width=True, hide_index=True)
G = build_graph()
deg = degree_table(G)
st.markdown("**Ступінь зв'язності об'єктів (degree)** — скільки типів об'єктів напряму пов'язані з даним:")
st.dataframe(deg, use_container_width=True, hide_index=True, height=220)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
st.markdown("#### Ключова роль Batch")
st.markdown(
    "**Batch** — об'єкт із найвищим degree разом з Product і Sale. Це єдина сутність моделі, що одночасно "
    "«пам'ятає» походження товару (Supplier → Purchase Order → Delivery) і його призначення "
    "(Warehouse → Sale → Customer → Return). Саме тому сторінка **Batch 360°** — головний наскрізний "
    "маршрут дослідження в цьому застосунку (ТЗ §8.5)."
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="ocpm-card">', unsafe_allow_html=True)
st.markdown("#### Приклади: де традиційний аналіз втрачає контекст")
st.markdown(
    "**1. Case = Purchase Order.** `status` завжди 'Approved' — жодної варіативності. Об'єктний аналіз через "
    "PO Item → Delivery → Batch → Sale → Return розкриває Delay Rate від одиниць до майже половини поставок "
    "залежно від постачальника і каналу — варіативність, яка на рівні PO просто не існує як атрибут.\n\n"
    "**2. Case = Return.** Традиційний аналіз повернень зупиняється на рівні товару/категорії "
    "('Electronics має підвищений Return Rate'). Зв'язок Return → Batch → Supplier дозволяє показати, "
    "що в межах тієї самої категорії конкретні партії від конкретних постачальників дають істотно вищий "
    "Return Rate, ніж категорія в середньому — дивіться сторінку **Insights → High Return Chain**.\n\n"
    "**3. Case = Delivery.** Delivery-центричний аналіз логістики закінчується на подіях 'Receive Goods' / "
    "'Put Away' — до того, як товар почне продаватись. Канал з найкоротшим Lead Time може виглядати "
    "найкращим, поки його не продовжити через Batch до Sale і не побачити реальний Time to First Sale "
    "(дивіться сторінку **Supply Channel** і **Insights → Channel Inefficiency**)."
)
st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    "OCPM Lens · Object-Centric Process Investigation Environment · "
    "Побудовано на результатах дослідження OCPM Supply-to-Customer Dataset v1."
)
