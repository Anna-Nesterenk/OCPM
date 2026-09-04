"""
pages/08_Insights.py
======================
The Insight Engine UI (ТЗ §16): insights are recomputed live from whatever
the current global filters leave in scope -- change the filters, and the
register below changes with them.
"""
import pandas as pd
import streamlit as st

import ui
from insights import generate_insights
from data_model import chain_html

bundle = st.session_state["bundle"]
batch_full = st.session_state["filtered_batch_full"]

ui.page_chrome("Insights", "Insight Engine",
                "Кожна картка нижче обчислюється наживо з поточного зрізу даних (з урахуванням глобальних "
                "фільтрів) — це не заздалегідь написаний текст.")

if batch_full.empty:
    st.warning("Поточна комбінація фільтрів не містить жодної партії.")
    st.stop()

cards = generate_insights(batch_full)

categories = ["Supplier Risk", "Slow Inventory", "Channel Inefficiency", "High Return Chain", "Financial Risk"]
picked = st.multiselect("Категорії інсайтів", categories, default=categories)
cards = [c for c in cards if c["category"] in picked]

if not cards:
    st.info(
        "На поточному зрізі даних жоден детектор не знайшов достатньо сильного сигналу "
        "(замалий обсяг вибірки або немає відхилень від фонових середніх). Спробуйте розширити фільтри."
    )
else:
    st.caption(f"Знайдено {len(cards)} інсайт(ів) на поточному зрізі даних.")
    for i, card in enumerate(cards, 1):
        ui.render_insight_card(card, i)

    st.divider()
    st.markdown("#### Insight Register")
    reg = pd.DataFrame([{
        "№": i + 1, "Insight": c["title"], "Category": c["category"],
        "Objects": " → ".join(t for t, _ in c["object_chain"]),
        "Evidence": " | ".join(c["evidence"]), "Potential Impact": c["impact"],
    } for i, c in enumerate(cards)])
    ui.data_table(reg, key="insight_register", download_name="insight_register", height=320)

with st.expander("Як формуються ці інсайти"):
    st.markdown(
        "- **Supplier Risk** — постачальники з поєднанням нижчої ціни й вищого Delay Rate, або аномально "
        "високим Return Rate відносно вибірки.\n"
        "- **Slow Inventory** — висока частка партій без продажів, або партії з екстремально довгим "
        "часом до першого продажу (90-й перцентиль).\n"
        "- **Channel Inefficiency** — канал з найшвидшим Lead Time, який попри це не дає найкращого "
        "сумарного часу до продажу.\n"
        "- **High Return Chain** — партія з найвищим Return Rate (мін. 5 проданих одиниць) і те, "
        "наскільки часто її постачальник трапляється серед найпроблемніших.\n"
        "- **Financial Risk** — категорія товарів, що концентрує непропорційно велику частку замороженої "
        "вартості запасів.\n\n"
        "Пороги (MIN_SAMPLE, перцентилі, стандартні відхилення) — у `insights.py`."
    )
