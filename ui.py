"""
ui.py
=====
Small shared UI building blocks (page chrome, KPI tiles, insight cards,
sortable/searchable/downloadable tables) so every page in pages/ looks like
part of the same product instead of nine independently-styled scripts.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from data_model import badge_html, chain_html
from metrics import fmt_money, fmt_num, fmt_pct, fmt_days

CSS = """
<style>
:root{
  --ocpm-bg:#f7f6f1; --ocpm-surface:#ffffff; --ocpm-ink:#14140f; --ocpm-ink2:#54524a;
  --ocpm-muted:#8a8779; --ocpm-hair:#e4e2d7; --ocpm-accent:#2a5fb4;
}
.block-container{padding-top:2rem; max-width:1200px;}
h1,h2,h3{letter-spacing:-0.01em;}
.ocpm-kpi-row{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:6px 0 18px;}
.ocpm-kpi{background:var(--ocpm-surface); border:1px solid var(--ocpm-hair); border-radius:11px; padding:12px 15px;
  box-shadow:0 1px 2px rgba(20,20,15,.05), 0 6px 16px -10px rgba(20,20,15,.15);}
.ocpm-kpi .v{font-size:21px; font-weight:700; letter-spacing:-.01em;}
.ocpm-kpi .l{color:var(--ocpm-muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; margin-top:2px;}
.ocpm-card{background:var(--ocpm-surface); border:1px solid var(--ocpm-hair); border-radius:12px; padding:18px 20px; margin-bottom:16px;}
.ocpm-insight{border:1px solid var(--ocpm-hair); border-radius:12px; background:var(--ocpm-surface); margin-bottom:14px; overflow:hidden;}
.ocpm-insight-head{padding:12px 18px; border-bottom:1px solid var(--ocpm-hair); display:flex; justify-content:space-between; align-items:center; gap:10px;}
.ocpm-insight-head b{font-size:14.5px;}
.ocpm-cat-pill{font-size:10.5px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--ocpm-muted);
  border:1px solid var(--ocpm-hair); border-radius:999px; padding:2px 9px;}
.ocpm-insight-body{padding:14px 18px; font-size:13.3px; color:var(--ocpm-ink2);}
.ocpm-insight-body .lbl{font-size:10.3px; text-transform:uppercase; letter-spacing:.06em; color:var(--ocpm-muted); font-weight:700; margin:10px 0 4px;}
.ocpm-insight-body .lbl:first-child{margin-top:0;}
.ocpm-evidence{margin:0; padding-left:18px;}
.ocpm-evidence li{margin:2px 0; font-family:ui-monospace, "IBM Plex Mono", monospace; font-size:12.3px;}
.ocpm-eyebrow{color:var(--ocpm-accent); font-size:11.5px; font-weight:700; text-transform:uppercase; letter-spacing:.07em; margin-bottom:2px;}
</style>
"""


def page_chrome(eyebrow: str, title: str, lede: str = ""):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="ocpm-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    if lede:
        st.caption(lede)


def kpi_row(items: list[tuple[str, str]]):
    """items: list of (label, formatted_value)."""
    html = '<div class="ocpm-kpi-row">' + "".join(
        f'<div class="ocpm-kpi"><div class="v">{val}</div><div class="l">{label}</div></div>'
        for label, val in items
    ) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def object_link_button(label: str, object_type: str, object_id: str, key: str):
    """A button styled like a badge that drills down into another object's 360 page."""
    from navigation import select_and_go
    if st.button(label, key=key, use_container_width=False):
        select_and_go(object_type, object_id)


def render_insight_card(card: dict, idx: int):
    ev = "".join(f"<li>{e}</li>" for e in card["evidence"])
    chain = chain_html(card["object_chain"])
    html = f"""
    <div class="ocpm-insight">
      <div class="ocpm-insight-head">
        <b>{idx}. {card['title']}</b>
        <span class="ocpm-cat-pill">{card['category']}</span>
      </div>
      <div class="ocpm-insight-body">
        <div class="lbl">1 · Observation</div><div>{card['observation']}</div>
        <div class="lbl">2 · Evidence</div><ul class="ocpm-evidence">{ev}</ul>
        <div class="lbl">3 · Object Chain</div>{chain}
        <div class="lbl">4 · Potential Business Impact</div><div>{card['impact']}</div>
        <div class="lbl">5 · Recommended Investigation</div><div>{card['investigation']}</div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def data_table(df: pd.DataFrame, key: str, search_cols: list[str] | None = None,
               height: int = 420, download_name: str | None = None):
    """A searchable, sortable, paginated, CSV-downloadable table (ТЗ §20)."""
    if df is None or df.empty:
        st.info("Немає даних для поточного вибору фільтрів.")
        return
    d = df.copy()
    top = st.columns([3, 1])
    if search_cols:
        q = top[0].text_input("Пошук", key=f"{key}_q", placeholder="Пошук…", label_visibility="collapsed")
        if q:
            mask = False
            for c in search_cols:
                if c in d.columns:
                    mask = mask | d[c].astype(str).str.contains(q, case=False, na=False)
            d = d[mask]
    top[1].caption(f"{len(d):,} з {len(df):,} рядків")
    st.dataframe(d, use_container_width=True, height=height, hide_index=True)
    st.download_button(
        "⬇ Завантажити CSV", d.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{download_name or key}.csv", mime="text/csv", key=f"{key}_dl",
    )
