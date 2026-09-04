"""
ocpm_graph.py
=============
The Object Relationship Graph (ТЗ §9.3 / §17): a NetworkX graph of the 15
business object types and their direct relationships, rendered with Plotly.

The edge list mirrors the FK structure of the dataset (who references whom)
plus the one M:N relation (Supplier <-> Product). Edge weight = number of
linking records, which is what the "thickness" and the degree ranking are
based on.
"""
from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from data_model import color_for

EDGES: list[tuple[str, str, int, str]] = [
    ("Supplier", "Purchase Order", 500, "PO.supplier_id"),
    ("Purchase Order", "PO Item", 679, "POItem.po_id"),
    ("PO Item", "Product", 679, "POItem.product_id"),
    ("Product", "Product Category", 48, "Product.category_id"),
    ("Supplier", "Delivery", 1014, "Delivery.supplier_id"),
    ("Delivery", "Supply Channel", 1014, "Delivery.channel_id"),
    ("Delivery", "Delivery Item", 1366, "DeliveryItem.delivery_id"),
    ("PO Item", "Delivery Item", 1366, "DeliveryItem.po_item_id"),
    ("Delivery Item", "Batch", 1366, "Batch.delivery_item_id"),
    ("Batch", "Warehouse", 1366, "Batch.warehouse_id"),
    ("Batch", "Sale", 2714, "Sale.batch_id"),
    ("Sales Order", "Sales Order Item", 2796, "SOItem.sales_order_id"),
    ("Sales Order Item", "Product", 2796, "SOItem.product_id"),
    ("Sales Order Item", "Sale", 2714, "Sale.sales_order_item_id"),
    ("Customer", "Sales Order", 1400, "SalesOrder.customer_id"),
    ("Customer", "Sale", 2714, "Sale.customer_id"),
    ("Sale", "Return", 163, "Return.sale_id"),
    ("Batch", "Return", 163, "Return.batch_id"),
    ("Customer", "Return", 163, "Return.customer_id"),
    ("Supplier", "Product", 144, "SupplierProductRelation (M:N)"),
]

# Hand-placed layered layout (clean, reproducible -- avoids spring-layout jitter
# and node/edge collisions on a graph this structured).
POSITIONS: dict[str, tuple[float, float]] = {
    "Supplier": (0.0, 0.45), "Purchase Order": (1.3, 0.45), "PO Item": (2.6, 0.45),
    "Product": (2.0, 1.15), "Product Category": (2.0, -1.15),
    "Supply Channel": (3.9, 1.85), "Delivery": (3.9, 0.45),
    "Delivery Item": (5.2, 0.45), "Batch": (6.5, 0.45),
    "Warehouse": (6.5, -1.15),
    "Sales Order": (6.5, 1.85), "Sales Order Item": (7.8, 1.05),
    "Sale": (7.8, 0.45),
    "Customer": (7.8, -1.15), "Return": (7.8, -1.9),
}


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    for node in POSITIONS:
        G.add_node(node)
    for src, dst, count, via in EDGES:
        G.add_edge(src, dst, weight=count, via=via)
    return G


def degree_table(G: nx.DiGraph):
    import pandas as pd
    deg = dict(G.to_undirected().degree())
    df = pd.DataFrame({"object_type": list(deg.keys()), "degree": list(deg.values())})
    return df.sort_values("degree", ascending=False).reset_index(drop=True)


def plot_object_graph(G: nx.DiGraph, highlight: str | None = None) -> go.Figure:
    """Renders the object relationship graph. `highlight` optionally makes one
    node type (e.g. the object type currently being explored) pop visually."""
    pos = POSITIONS

    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        width = max(1.0, min(6.0, (data["weight"] ** 0.5) / 8))
        edge_traces.append(
            go.Scatter(
                x=[x0, x1], y=[y0, y1], mode="lines",
                line=dict(width=width, color="rgba(120,120,120,0.35)"),
                hoverinfo="text", text=f"{u} → {v}<br>{data['via']}<br>{data['weight']:,} записів",
                showlegend=False,
            )
        )

    deg = dict(G.to_undirected().degree())
    node_x, node_y, node_color, node_text, node_size, node_line = [], [], [], [], [], []
    for n in G.nodes():
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        node_color.append(color_for(n))
        node_text.append(f"<b>{n}</b><br>degree: {deg[n]}")
        node_size.append(26 + deg[n] * 5)
        node_line.append(4 if n == highlight else 1)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=list(G.nodes()), textposition="middle center",
        textfont=dict(size=10, color="white"),
        marker=dict(size=node_size, color=node_color, line=dict(width=node_line, color="#14140f")),
        hoverinfo="text", hovertext=node_text, showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        height=560, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False, range=[-0.8, 8.6]),
        yaxis=dict(visible=False, range=[-2.5, 2.5]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
    )
    return fig
