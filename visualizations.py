"""
visualizations.py
==================
Shared Plotly chart builders used across the 360 pages. Kept here (rather than
inline in each page) so the same chart looks and behaves the same everywhere
it appears, per the eight visualization types prioritised in the research
(ТЗ §17): Object Relationship Graph (see ocpm_graph.py), Supplier Performance
Matrix, Product Profitability Matrix, Product/Batch Journey, Lead Time
Comparison, Supplier -> Channel -> Delivery, Supplier -> Batch -> Product ->
Return, Inventory Aging.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_model import color_for

BG = dict(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
FONT = dict(family="IBM Plex Sans, sans-serif")


def _style(fig, height=420, **kw):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), font=FONT, **BG, **kw)
    return fig


# ---------------------------------------------------------------------------
# Product Profitability Matrix -- Margin x Turnover (ТЗ §10.4)
# ---------------------------------------------------------------------------
def profitability_matrix(df: pd.DataFrame, name_col="product_name", size_col="revenue") -> go.Figure:
    d = df.copy()
    d["margin_pct"] = np.where(d["revenue"] > 0, d["net_contribution"] / d["revenue"] * 100, 0)
    d["turnover_pct"] = d["turnover_ratio"] * 100
    med_margin, med_turn = d["margin_pct"].median(), d["turnover_pct"].median()

    fig = px.scatter(
        d, x="turnover_pct", y="margin_pct", size=size_col, color="margin_pct",
        color_continuous_scale=["#c23b3b", "#c9930b", "#1f9e6e"],
        hover_name=name_col,
        hover_data={size_col: ":$,.0f", "turnover_pct": ":.1f", "margin_pct": ":.1f"},
        labels={"turnover_pct": "Оборотність, %", "margin_pct": "Маржа (Net Contribution / Revenue), %"},
    )
    fig.add_hline(y=med_margin, line_dash="dot", line_color="rgba(120,120,120,0.5)")
    fig.add_vline(x=med_turn, line_dash="dot", line_color="rgba(120,120,120,0.5)")
    fig.update_traces(marker=dict(line=dict(width=1, color="rgba(0,0,0,0.25)")))
    fig.update_coloraxes(showscale=False)
    return _style(fig, height=480)


# ---------------------------------------------------------------------------
# Supplier Performance Matrix -- Price x Delay Rate x Return Rate (ТЗ §11)
# ---------------------------------------------------------------------------
def supplier_matrix(df: pd.DataFrame) -> go.Figure:
    d = df.copy()
    fig = px.scatter(
        d, x="avg_purchase_price", y="delay_rate_pct", size="return_rate_pct", color="supplier_name",
        hover_name="supplier_name",
        hover_data={"avg_purchase_price": ":$.2f", "delay_rate_pct": ":.1f", "return_rate_pct": ":.1f"},
        labels={"avg_purchase_price": "Середня закупівельна ціна", "delay_rate_pct": "Delay Rate, %"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(marker=dict(line=dict(width=1, color="rgba(0,0,0,0.25)"), sizemin=6))
    fig.update_layout(showlegend=False)
    fig.add_annotation(
        text="Розмір бульбашки = Return Rate", xref="paper", yref="paper", x=0.99, y=1.06,
        showarrow=False, font=dict(size=11, color="#8a8779"),
    )
    return _style(fig, height=480)


# ---------------------------------------------------------------------------
# Lead Time distribution -- box plot by group (ТЗ §12)
# ---------------------------------------------------------------------------
def lead_time_box(batch_full: pd.DataFrame, by="channel_name", value="supply_lead_days") -> go.Figure:
    d = batch_full.dropna(subset=[value])
    order = d.groupby(by)[value].median().sort_values().index.tolist()
    fig = px.box(
        d, x=by, y=value, color=by, category_orders={by: order},
        color_discrete_sequence=px.colors.qualitative.Set2,
        labels={value: "Lead Time, дн.", by: by},
    )
    fig.update_layout(showlegend=False)
    return _style(fig, height=440)


# ---------------------------------------------------------------------------
# Product / Batch Journey timeline (ТЗ §13)
# ---------------------------------------------------------------------------
def batch_journey(batch_row: pd.Series) -> go.Figure:
    events = [("PO Created", batch_row.get("order_date"))]
    if pd.notna(batch_row.get("dispatch_date")):
        events.append(("Delivery Dispatched", batch_row["dispatch_date"]))
    events.append(("Goods Received", batch_row.get("received_date")))
    if pd.notna(batch_row.get("first_sale_date")):
        events.append(("First Sale", batch_row["first_sale_date"]))
    if pd.notna(batch_row.get("last_sale_date")) and batch_row.get("last_sale_date") != batch_row.get("first_sale_date"):
        events.append(("Last Sale", batch_row["last_sale_date"]))
    events = [(label, d) for label, d in events if pd.notna(d)]
    events.sort(key=lambda t: t[1])

    labels = [e[0] for e in events]
    dates = [e[1] for e in events]
    colors = ["#d9791f", "#1f9e6e", "#1f9e6e", "#d1447e", "#d1447e"][: len(events)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=[0] * len(dates), mode="markers+lines",
        marker=dict(size=16, color=colors, line=dict(width=1, color="#14140f")),
        line=dict(color="rgba(120,120,120,0.4)", width=2),
        text=labels, hovertext=[f"{l}<br>{d.date()}" for l, d in zip(labels, dates)], hoverinfo="text",
    ))
    # Stagger annotation height when neighbouring events fall close together in time
    # (e.g. PO Created / Dispatched / Received are often only days apart), so their
    # labels don't render on top of each other.
    span_days = max((dates[-1] - dates[0]).days, 1) if len(dates) > 1 else 1
    close_threshold = span_days * 0.06
    levels = []
    for i, d in enumerate(dates):
        lvl = 0
        if i > 0 and abs((d - dates[i - 1]).days) < close_threshold:
            lvl = (levels[i - 1] + 1) % 3
        levels.append(lvl)
    y_offsets = [0.18, 0.36, 0.54]
    for label, d, lvl in zip(labels, dates, levels):
        fig.add_annotation(x=d, y=y_offsets[lvl], text=f"<b>{label}</b><br>{d.date()}",
                            showarrow=(lvl > 0), arrowhead=0, ax=0, ay=0, font=dict(size=11))
    fig.update_yaxes(visible=False, range=[-0.3, 0.78])
    fig.update_xaxes(title="")
    return _style(fig, height=230)


# ---------------------------------------------------------------------------
# Sankeys: Supplier -> Channel -> Delivery(on-time/delayed) and
#          Supplier -> Batch(bucket) -> Product -> Return
# ---------------------------------------------------------------------------
def sankey_supplier_channel_delay(batch_full: pd.DataFrame, top_n=8) -> go.Figure:
    d = batch_full.copy()
    top_suppliers = d["supplier_name"].value_counts().head(top_n).index.tolist()
    d = d[d["supplier_name"].isin(top_suppliers)]
    d["delay_bucket"] = np.where(d["delay_days"] > 0, "Затримано", "Вчасно")

    nodes = list(dict.fromkeys(
        list(d["supplier_name"].unique()) + list(d["channel_name"].dropna().unique()) + ["Вчасно", "Затримано"]
    ))
    idx = {n: i for i, n in enumerate(nodes)}

    l1 = d.groupby(["supplier_name", "channel_name"]).size().reset_index(name="value")
    l2 = d.groupby(["channel_name", "delay_bucket"]).size().reset_index(name="value")

    src = [idx[s] for s in l1["supplier_name"]] + [idx[c] for c in l2["channel_name"]]
    tgt = [idx[c] for c in l1["channel_name"]] + [idx[b] for b in l2["delay_bucket"]]
    val = list(l1["value"]) + list(l2["value"])
    node_colors = [color_for("Supplier")] * len(top_suppliers) + \
                  [color_for("Supply Channel")] * (len(nodes) - len(top_suppliers) - 2) + \
                  ["#1f9e6e", "#c23b3b"]

    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, color=node_colors, pad=14, thickness=16,
                   line=dict(color="rgba(0,0,0,0.3)", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color="rgba(150,150,150,0.35)"),
    ))
    return _style(fig, height=460)


def sankey_supplier_product_return(batch_full: pd.DataFrame, top_n=8) -> go.Figure:
    d = batch_full[batch_full["return_qty"] > 0].copy()
    if d.empty:
        return go.Figure()
    top_suppliers = d.groupby("supplier_name")["return_qty"].sum().sort_values(ascending=False).head(top_n).index
    d = d[d["supplier_name"].isin(top_suppliers)]
    top_products = d.groupby("product_name")["return_qty"].sum().sort_values(ascending=False).head(top_n).index
    d = d[d["product_name"].isin(top_products)]

    nodes = list(dict.fromkeys(
        list(d["supplier_name"].unique()) + list(d["product_name"].unique()) + ["Return"]
    ))
    idx = {n: i for i, n in enumerate(nodes)}
    l1 = d.groupby(["supplier_name", "product_name"])["return_qty"].sum().reset_index()
    l2 = d.groupby("product_name")["return_qty"].sum().reset_index()

    src = [idx[s] for s in l1["supplier_name"]] + [idx[p] for p in l2["product_name"]]
    tgt = [idx[p] for p in l1["product_name"]] + [idx["Return"]] * len(l2)
    val = list(l1["return_qty"]) + list(l2["return_qty"])
    node_colors = [color_for("Supplier")] * len(d["supplier_name"].unique()) + \
                  [color_for("Product")] * len(d["product_name"].unique()) + [color_for("Return")]

    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, color=node_colors, pad=14, thickness=16,
                   line=dict(color="rgba(0,0,0,0.3)", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color="rgba(194,59,59,0.30)"),
    ))
    return _style(fig, height=460)


# ---------------------------------------------------------------------------
# Inventory Aging (ТЗ §17)
# ---------------------------------------------------------------------------
def inventory_aging(batch_full: pd.DataFrame, as_of: pd.Timestamp | None = None) -> go.Figure:
    d = batch_full[batch_full["quantity_remaining"] > 0].copy()
    if d.empty:
        return go.Figure()
    as_of = as_of or pd.Timestamp.now()
    d["age_days"] = (as_of - d["received_date"]).dt.days
    bins = [0, 30, 60, 90, 180, 365, 10_000]
    labels = ["0-30", "31-60", "61-90", "91-180", "181-365", "365+"]
    d["bucket"] = pd.cut(d["age_days"], bins=bins, labels=labels)
    agg = d.groupby("bucket", observed=True)["inventory_value_unsold"].sum().reindex(labels).fillna(0).reset_index()

    fig = px.bar(
        agg, x="bucket", y="inventory_value_unsold",
        labels={"bucket": "Вік запасу, дн.", "inventory_value_unsold": "Заморожена вартість, $"},
        color_discrete_sequence=[color_for("Batch")],
    )
    return _style(fig, height=380)


def bar(df: pd.DataFrame, x: str, y: str, color=None, horizontal=False, height=380, **kw) -> go.Figure:
    if horizontal:
        fig = px.bar(df, x=y, y=x, orientation="h", color_discrete_sequence=[color or "#2a6fd6"], **kw)
    else:
        fig = px.bar(df, x=x, y=y, color_discrete_sequence=[color or "#2a6fd6"], **kw)
    return _style(fig, height=height)
