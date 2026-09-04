"""
insights.py
===========
The Insight Engine (ТЗ §16): every card is *computed* from whatever slice of
`batch_full` / `sales_full` is currently in scope (i.e. it respects the
global filters) -- nothing here is a pre-written conclusion. Re-running this
module against a different filter selection can surface different insights,
weaker evidence, or none at all, which is the point.

Each insight is a dict with the five required fields (ТЗ §16 "Insight Card"):
observation, evidence (list[str]), object_chain (list[(object_type,label)]),
impact, investigation, plus `category` (one of the five ТЗ §16 minimal
categories) and `severity` used only to sort the register.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.batch import high_return_batches

MIN_SAMPLE = 3  # below this many batches/deliveries a group is too thin to call out


def _card(category, title, observation, evidence, chain, impact, investigation, severity=1):
    return dict(category=category, title=title, observation=observation, evidence=evidence,
                object_chain=chain, impact=impact, investigation=investigation, severity=severity)


# ---------------------------------------------------------------------------
# 1. Supplier Risk: low price + high delay, or high return rate
# ---------------------------------------------------------------------------
def detect_supplier_risk(batch_full: pd.DataFrame) -> list[dict]:
    cards = []
    g = batch_full.groupby(["supplier_id", "supplier_name"]).agg(
        n_batches=("batch_id", "nunique"), avg_price=("purchase_unit_price", "mean"),
        qty_sold=("quantity_sold", "sum"), return_qty=("return_qty", "sum"),
    )
    delay = batch_full.groupby(["supplier_id", "supplier_name"]).apply(
        lambda x: (x["delay_days"] > 0).mean() * 100, include_groups=False
    ).rename("delay_rate_pct")
    g = g.join(delay).reset_index()
    g = g[g["n_batches"] >= MIN_SAMPLE]
    if g.empty or len(g) < 2:
        return cards

    g["return_rate_pct"] = np.where(g["qty_sold"] > 0, g["return_qty"] / g["qty_sold"] * 100, 0)
    fleet_delay_rate = (batch_full["delay_days"] > 0).mean() * 100
    price_rank = g["avg_price"].rank(pct=True)
    delay_rank = g["delay_rate_pct"].rank(pct=True)

    # cheap-but-risky: bottom-tercile price, top-tercile delay
    risky = g[(price_rank <= 0.4) & (delay_rank >= 0.6) & (g["delay_rate_pct"] > fleet_delay_rate)]
    for _, r in risky.sort_values("delay_rate_pct", ascending=False).head(3).iterrows():
        peers = g[g["supplier_id"] != r["supplier_id"]]
        price_gap = (r["avg_price"] - peers["avg_price"].mean()) / peers["avg_price"].mean() * 100 if len(peers) else 0
        cards.append(_card(
            "Supplier Risk",
            f"{r['supplier_name']}: нижча ціна поєднана з підвищеним Delay Rate",
            f"{r['supplier_name']} — серед постачальників з нижчою закупівельною ціною (percentile "
            f"{price_rank[r.name]*100:.0f}), але його Delay Rate суттєво вищий за середній по вибірці.",
            [
                f"Середня ціна: {r['avg_price']:.2f} ({price_gap:+.1f}% відносно інших постачальників у вибірці)",
                f"Delay Rate: {r['delay_rate_pct']:.1f}% проти {fleet_delay_rate:.1f}% у середньому по вибірці",
                f"Return Rate: {r['return_rate_pct']:.1f}%",
                f"Батчів у вибірці: {int(r['n_batches'])}",
            ],
            [("Supplier", r["supplier_name"]), ("Delivery", "Delivery"), ("Batch", "Batch"),
             ("Product", "Product"), ("Return", "Return")],
            "Позірна економія на закупівельній ціні може нівелюватись ризиком дефіциту та вартістю повернень.",
            "Порахувати total cost of ownership для цього постачальника і порівняти з альтернативами по тих самих товарах.",
            severity=3,
        ))

    high_return = g[g["return_rate_pct"] > g["return_rate_pct"].mean() + g["return_rate_pct"].std()] \
        if g["return_rate_pct"].std() > 0 else g.iloc[0:0]
    for _, r in high_return.sort_values("return_rate_pct", ascending=False).head(2).iterrows():
        cards.append(_card(
            "Supplier Risk",
            f"{r['supplier_name']}: аномально високий Return Rate",
            f"Return Rate постачальника {r['supplier_name']} помітно вищий за середнє + 1 стандартне відхилення по вибірці постачальників.",
            [f"Return Rate: {r['return_rate_pct']:.1f}%", f"Продано одиниць у вибірці: {r['qty_sold']:.0f}",
             f"Повернено одиниць: {r['return_qty']:.0f}"],
            [("Supplier", r["supplier_name"]), ("Batch", "Batch"), ("Product", "Product"), ("Return", "Return")],
            "Прямий негативний вплив на маржинальність товарів цього постачальника.",
            "Перевірити причини повернень (`returns.reason`) саме для партій цього постачальника.",
            severity=2,
        ))
    return cards


# ---------------------------------------------------------------------------
# 2. Slow Inventory: batches that sit unsold for a long time / never sell
# ---------------------------------------------------------------------------
def detect_slow_inventory(batch_full: pd.DataFrame) -> list[dict]:
    cards = []
    n = len(batch_full)
    if n < MIN_SAMPLE:
        return cards
    untouched = batch_full[batch_full["is_untouched"]]
    pct_untouched = len(untouched) / n * 100
    unsold_value = batch_full["inventory_value_unsold"].sum()
    realized_nc = batch_full["net_contribution"].sum()

    if pct_untouched >= 40:
        ratio = unsold_value / realized_nc if realized_nc > 0 else np.nan
        cards.append(_card(
            "Slow Inventory",
            "Суттєва частка партій у поточному зрізі жодного разу не продавалась",
            f"{pct_untouched:.1f}% партій у поточному зрізі даних мають quantity_remaining = quantity_received "
            "(жодного зафіксованого продажу).",
            [
                f"{len(untouched):,} з {n:,} партій без продажу ({pct_untouched:.1f}%)",
                f"Оцінна заморожена вартість: ${unsold_value:,.0f}",
                (f"Це у {ratio:.1f}x більше за реалізований Net Contribution поточного зрізу (${realized_nc:,.0f})"
                 if not np.isnan(ratio) and ratio > 0 else f"Реалізований Net Contribution поточного зрізу: ${realized_nc:,.0f}"),
            ],
            [("Purchase Order", "Purchase Order"), ("Delivery", "Delivery"), ("Batch", "Batch"), ("Warehouse", "Warehouse")],
            "Великий обсяг обігового капіталу заморожений у запасах, що не генерують доходу.",
            "Розділити партії на 'молоді' (щойно отримані) і 'застарілі' (давно отримані, досі не продані) і сфокусуватись на другій групі.",
            severity=3,
        ))

    sold = batch_full[batch_full["quantity_sold"] > 0]
    if len(sold) >= MIN_SAMPLE:
        thresh = sold["days_to_first_sale"].quantile(0.9)
        slow = sold[sold["days_to_first_sale"] >= thresh].sort_values("days_to_first_sale", ascending=False)
        if len(slow) >= 1 and thresh > sold["days_to_first_sale"].median() * 1.5:
            top = slow.iloc[0]
            cards.append(_card(
                "Slow Inventory",
                "Партії з екстремально довгим часом до першого продажу",
                f"10% найповільніших партій чекають до першого продажу щонайменше {thresh:.0f} днів — "
                f"проти медіани {sold['days_to_first_sale'].median():.0f} днів по вибірці.",
                [f"Найповільніша партія: {top['batch_id']} ({top['product_name']}, {top['supplier_name']}) — "
                 f"{top['days_to_first_sale']:.0f} дн. до першого продажу",
                 f"90-й перцентиль Days to First Sale: {thresh:.0f} дн.", f"Медіана: {sold['days_to_first_sale'].median():.0f} дн."],
                [("Batch", top["batch_id"]), ("Warehouse", top["warehouse_name"]), ("Sale", "Sale")],
                "Довге зберігання підвищує вартість капіталу і ризик знецінення/списання товару.",
                "Перевірити, чи це системна проблема складу/категорії, чи ізольований випадок.",
                severity=2,
            ))
    return cards


# ---------------------------------------------------------------------------
# 3. Channel Inefficiency: fast transit that doesn't translate into fast Time to Sale
# ---------------------------------------------------------------------------
def detect_channel_inefficiency(batch_full: pd.DataFrame) -> list[dict]:
    cards = []
    g = batch_full.groupby(["channel_id", "channel_name"]).agg(
        n=("batch_id", "nunique"), avg_lead=("supply_lead_days", "mean"),
        avg_days_to_sale=("days_to_first_sale", "mean"),
    ).reset_index()
    g = g[g["n"] >= MIN_SAMPLE].dropna(subset=["avg_lead", "avg_days_to_sale"])
    if len(g) < 2:
        return cards
    g["e2e_proxy"] = g["avg_lead"] + g["avg_days_to_sale"]
    fastest_transit = g.sort_values("avg_lead").iloc[0]
    best_e2e = g.sort_values("e2e_proxy").iloc[0]
    if fastest_transit["channel_id"] != best_e2e["channel_id"]:
        rank_e2e = g.sort_values("e2e_proxy").reset_index(drop=True)
        pos = rank_e2e.index[rank_e2e["channel_id"] == fastest_transit["channel_id"]][0] + 1
        cards.append(_card(
            "Channel Inefficiency",
            f"{fastest_transit['channel_name']}: найшвидший транзит, але не найшвидший вихід на ринок",
            f"{fastest_transit['channel_name']} має найкоротший середній Supply Lead Time у поточній вибірці, "
            f"але за сумарним часом Lead Time + Days to First Sale посідає {pos}-е місце з {len(g)}.",
            [f"Supply Lead Time: {fastest_transit['avg_lead']:.1f} дн. (найкоротший)",
             f"Days to First Sale: {fastest_transit['avg_days_to_sale']:.1f} дн.",
             f"Найкращий сумарний час: {best_e2e['channel_name']} ({best_e2e['e2e_proxy']:.1f} дн. проти "
             f"{fastest_transit['e2e_proxy']:.1f} дн. у {fastest_transit['channel_name']})"],
            [("Supply Channel", fastest_transit["channel_name"]), ("Delivery", "Delivery"),
             ("Batch", "Batch"), ("Warehouse", "Warehouse"), ("Sale", "Sale")],
            "Логістична премія за швидкість каналу може не окупатись, якщо товар потім довго простоює на складі.",
            "Перевірити процес поповнення полиць/запуску продажів саме для партій цього каналу.",
            severity=2,
        ))
    return cards


# ---------------------------------------------------------------------------
# 4. High Return Chain: Supplier -> Batch -> Product -> Return
# ---------------------------------------------------------------------------
def detect_high_return_chain(batch_full: pd.DataFrame, min_sold=5) -> list[dict]:
    cards = []
    hot = high_return_batches(batch_full, min_sold=min_sold, n=5)
    hot = hot[hot["return_rate_qty"] > 0]
    if hot.empty:
        return cards
    top = hot.iloc[0]
    supplier_share = (hot["supplier_name"] == top["supplier_name"]).sum()
    cards.append(_card(
        "High Return Chain",
        f"Партія {top['batch_id']} ({top['product_name']}) — Return Rate {top['return_rate_qty']:.0f}%",
        f"Серед партій з щонайменше {min_sold} проданими одиницями, {top['batch_id']} має найвищу частку "
        f"повернень у поточній вибірці; постачальник {top['supplier_name']} трапляється {supplier_share} раз(и) "
        f"у топ-5 найпроблемніших партій за Return Rate.",
        [f"Return Rate: {top['return_rate_qty']:.1f}%", f"Постачальник: {top['supplier_name']}",
         f"Категорія: {top['category_name']}",
         f"{top['supplier_name']} у топ-5 найвищих Return Rate: {supplier_share} з 5"],
        [("Supplier", top["supplier_name"]), ("Batch", top["batch_id"]), ("Product", top["product_name"]),
         ("Return", "Return")],
        "Проблема може бути локалізована на рівні конкретної партії/постачальника, а не всієї категорії товару.",
        "Порівняти return reason для цієї партії з іншими партіями того самого товару від інших постачальників.",
        severity=3,
    ))
    return cards


# ---------------------------------------------------------------------------
# 5. Financial Risk: large unsold value concentrated in one place
# ---------------------------------------------------------------------------
def detect_financial_risk(batch_full: pd.DataFrame) -> list[dict]:
    cards = []
    d = batch_full[batch_full["inventory_value_unsold"] > 0]
    if len(d) < MIN_SAMPLE:
        return cards
    by_cat = d.groupby("category_name")["inventory_value_unsold"].sum().sort_values(ascending=False)
    total = by_cat.sum()
    if total <= 0:
        return cards
    top_cat, top_val = by_cat.index[0], by_cat.iloc[0]
    share = top_val / total * 100
    if share >= 25:
        cards.append(_card(
            "Financial Risk",
            f"Категорія «{top_cat}» концентрує {share:.0f}% замороженої вартості запасів",
            f"У поточному зрізі непроданий запас категорії «{top_cat}» становить непропорційно велику частку "
            "загальної замороженої вартості запасів.",
            [f"Заморожена вартість «{top_cat}»: ${top_val:,.0f}", f"Загалом по всіх категоріях: ${total:,.0f}",
             f"Частка: {share:.1f}%"],
            [("Product Category", top_cat), ("Product", "Product"), ("Batch", "Batch"), ("Warehouse", "Warehouse")],
            "Концентрація заморожених коштів в одній категорії підвищує ризик списань і тиск на cash flow.",
            "Перевірити, чи закупівельні обсяги цієї категорії відповідають реальному темпу продажів.",
            severity=2,
        ))
    return cards


ALL_DETECTORS = [
    detect_supplier_risk, detect_slow_inventory, detect_channel_inefficiency,
    detect_high_return_chain, detect_financial_risk,
]


def generate_insights(batch_full: pd.DataFrame) -> list[dict]:
    """Run every detector against the current (filtered) batch_full and return
    a severity-sorted list of insight cards. Returns [] gracefully if the
    filtered slice is too thin to say anything meaningful."""
    cards: list[dict] = []
    if batch_full is None or batch_full.empty:
        return cards
    for det in ALL_DETECTORS:
        try:
            cards.extend(det(batch_full))
        except Exception:
            # A detector should never crash the page -- skip it if a filter
            # combination produces a degenerate slice (e.g. one supplier only).
            continue
    cards.sort(key=lambda c: -c["severity"])
    return cards
