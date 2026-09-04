"""
data_model.py
=============
The object-centric vocabulary of the app: the canonical list of business
object types, the color each one carries everywhere in the UI, and small
structures used to pass filter/navigation state between pages.

Keeping this in one module is what guarantees "one type of object -> one
color, everywhere" (ТЗ §23) instead of every page inventing its own palette.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import date
from typing import Optional

# ---------------------------------------------------------------------------
# Object types & colors
# ---------------------------------------------------------------------------
# Concept from the spec: Supplier=orange, Product=blue, Batch=green,
# Supply Channel=purple, Customer=pink/red, Return=red. Extended consistently
# for the remaining object types so every node in the OCPM graph has a home.
OBJECT_COLORS: dict[str, str] = {
    "Product": "#2a6fd6",
    "Product Category": "#c9930b",
    "Supplier": "#d9791f",
    "Purchase Order": "#d9791f",
    "PO Item": "#2a6fd6",
    "Supply Channel": "#7a4fd1",
    "Delivery": "#1f9e6e",
    "Delivery Item": "#1f9e6e",
    "Batch": "#1f9e6e",
    "Warehouse": "#5b6ee1",
    "Sales Order": "#d1447e",
    "Sales Order Item": "#d1447e",
    "Sale": "#d1447e",
    "Customer": "#d1447e",
    "Return": "#c9382f",
}

# The six entry-point object types the "Explore by Object" screen offers (ТЗ §7.1)
ENTRY_OBJECT_TYPES = ["Supplier", "Product", "Batch", "Customer", "Product Category", "Supply Channel"]

# Full object model (ТЗ §6)
ALL_OBJECT_TYPES = [
    "Product Category", "Product", "Supplier", "Purchase Order", "PO Item",
    "Supply Channel", "Delivery", "Delivery Item", "Batch", "Warehouse",
    "Sales Order", "Sales Order Item", "Sale", "Customer", "Return",
]


def color_for(object_type: str) -> str:
    return OBJECT_COLORS.get(object_type, "#6b7280")


def badge_html(object_type: str, label: Optional[str] = None) -> str:
    """A small inline colored pill, consistent everywhere an object is named."""
    c = color_for(object_type)
    text = label if label is not None else object_type
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'font-size:12px;font-weight:600;padding:2px 9px 2px 7px;border-radius:999px;'
        f'background:{c}22;color:{c};white-space:nowrap;">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{c};"></span>{text}</span>'
    )


def chain_html(steps: list[tuple[str, str]]) -> str:
    """Render an Object Chain like Supplier -> Delivery -> Batch -> Product -> Return."""
    parts = []
    for i, (otype, label) in enumerate(steps):
        parts.append(badge_html(otype, label))
        if i < len(steps) - 1:
            parts.append('<span style="color:#9a9890;margin:0 2px;">&rarr;</span>')
    return '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:2px;">' + "".join(parts) + "</div>"


# ---------------------------------------------------------------------------
# Cross-page navigation / selection context
# ---------------------------------------------------------------------------
SESSION_DEFAULTS = {
    "selected_supplier": None,
    "selected_product": None,
    "selected_batch": None,
    "selected_customer": None,
    "selected_category": None,
    "selected_channel": None,
    "explore_object_type": "Supplier",
    "nav_request": None,   # (page_path, context_dict) set by navigation.go_to(), consumed on next render
}


@dataclass
class Filters:
    """Global filter state (ТЗ §18). An empty/None field means 'no restriction'."""
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    categories: list[str] = field(default_factory=list)
    suppliers: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    warehouses: list[str] = field(default_factory=list)
    segments: list[str] = field(default_factory=list)
    customers: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(
            getattr(self, f.name) for f in fields(self) if f.name not in ("date_from", "date_to")
        ) and self.date_from is None and self.date_to is None
