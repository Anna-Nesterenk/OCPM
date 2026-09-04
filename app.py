"""
app.py
======
Entry point. Deliberately thin: it loads the dataset once, renders the
global sidebar (brand + filters, ТЗ §18), and hands off to whichever page
the user has selected via Streamlit's native multipage router. All actual
page content lives under pages/ -- see ТЗ §5 for the required file layout.

Run with:
    pip install -r requirements.txt
    streamlit run app.py
"""
import streamlit as st

import navigation
from data_loader import data_files_present, load_bundle

st.set_page_config(page_title="OCPM Lens", page_icon="🔗", layout="wide")

navigation.init_session()

missing = data_files_present()
if missing:
    st.error(
        "Не знайдено файли датасету у папці `data/`:\n\n"
        + "\n".join(f"- {m}" for m in missing)
        + "\n\nРозпакуйте OCPM_Supply_to_Customer_Dataset_v1 у папку `data/` поруч з `app.py` і перезапустіть застосунок."
    )
    st.stop()

bundle = load_bundle()
st.session_state["bundle"] = bundle

with st.sidebar:
    st.markdown("## 🔗 OCPM Lens")
    st.caption("Supply-to-Customer · Object-Centric Investigation")
    st.divider()
    filters = navigation.render_global_filters(bundle)

st.session_state["filtered_batch_full"] = navigation.apply_filters(bundle.batch_full, filters)
st.session_state["filtered_sales_full"] = navigation.apply_filters_to_sales(bundle.sales_full, filters)

pages = [
    st.Page("pages/01_Overview.py", title="Overview", icon="🏠", default=True),
    st.Page("pages/02_Explore.py", title="Explore by Object", icon="🧭"),
    st.Page("pages/03_Product.py", title="Product 360°", icon="📦"),
    st.Page("pages/04_Supplier.py", title="Supplier 360°", icon="🏭"),
    st.Page("pages/05_Batch.py", title="Batch 360°", icon="🧬"),
    st.Page("pages/06_Supply_Channel.py", title="Supply Channel", icon="🚚"),
    st.Page("pages/07_Customer.py", title="Customer 360°", icon="🧑‍🤝‍🧑"),
    st.Page("pages/08_Insights.py", title="Insights", icon="💡"),
    st.Page("pages/09_Methodology.py", title="Methodology", icon="📖"),
]
pg = st.navigation(pages)
pg.run()
