"""Platform-agnostic P&L engine.

Consumes the normalised frames from `platforms.base` and produces a single JSON
serialisable result: cohort stats, funnel, ad spend, book/SKU P&L, the P&L
statement, cash position, sensitivity, break-even and the conservative view.

Cohort rule: an order belongs to the month it was PLACED in, regardless of which
export file it arrived in or when it settled.
"""

from __future__ import annotations

import calendar
from typing import Any, Dict, List, Optional

import pandas as pd

from .platforms.base import (
    DELIVERED,
    EXCHANGE,
    FEE_ADJ,
    IN_TRANSIT,
    LOST_STATUSES,
    RETURN,
    RTO,
    SOLD_STATUSES,
)

UNMAPPED = "UNMAPPED"
SENSITIVITY_RATES = [0.04, 0.06, 0.08, 0.10, 0.12, 0.15]


def _f(value: Any, digits: int = 2) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    if value != value:  # NaN
        return 0.0
    return round(value, digits)


def _pct(num: float, den: float, digits: int = 2) -> float:
    return _f(num / den * 100, digits) if den else 0.0


def month_bounds(month: str):
    year, mon = int(month[:4]), int(month[5:7])
    start = pd.Timestamp(year=year, month=mon, day=1)
    end = start + pd.offsets.MonthBegin(1)
    return start, end


def month_label(month: str) -> str:
    year, mon = int(month[:4]), int(month[5:7])
    return "%s %d" % (calendar.month_name[mon], year)


def _group_pnl(g: pd.DataFrame, fg: pd.DataFrame, resell_rate: float) -> Dict[str, Any]:
    """P&L for one slice (a book or a single SKU). `fg` = its fee-adjustment lines."""
    st = g["status"]
    sold_mask = st.isin(SOLD_STATUSES)
    lost_mask = st.isin(LOST_STATUSES)

    units_sold = _f(g.loc[sold_mask, "quantity"].sum(), 0)
    o_del = int((st == DELIVERED).sum())
    o_transit = int((st == IN_TRANSIT).sum())
    o_ret = int((st == RETURN).sum())
    o_rto = int((st == RTO).sum())
    o_exc = int((st == EXCHANGE).sum())
    closed = len(g) - o_transit

    cogs_sold = _f((g.loc[sold_mask, "_cost"] * g.loc[sold_mask, "quantity"]).sum())
    cogs_writeoff = _f((g.loc[lost_mask, "_cost"] * g.loc[lost_mask, "quantity"]).sum() * (1 - resell_rate))
    settlement = _f(g["settlement"].sum() + fg["settlement"].sum())
    gross_profit = _f(settlement - cogs_sold - cogs_writeoff)
    gross_sale = _f(g["gross_sale"].sum())
    delivered = g[st == DELIVERED]

    return {
        "orders": int(len(g)),
        "units_sold": units_sold,
        "units_returned": _f(g.loc[st == RETURN, "quantity"].sum(), 0),
        "units_rto": _f(g.loc[st == RTO, "quantity"].sum(), 0),
        "delivered": o_del,
        "in_transit": o_transit,
        "returns": o_ret,
        "rto": o_rto,
        "exchange": o_exc,
        "return_pct": _pct(o_ret, closed),
        "rto_pct": _pct(o_rto, closed),
        "fail_pct": _pct(o_ret + o_rto, closed),
        "asp": _f(delivered["gross_sale"].mean()) if len(delivered) else 0.0,
        "gross_sale": gross_sale,
        "return_revenue": _f(g["return_revenue"].sum()),
        "fwd_shipping": _f(g["fwd_shipping"].sum()),
        "return_shipping": _f(g["return_shipping"].sum()),
        "affiliate": _f(g["affiliate"].sum() + fg["affiliate"].sum()),
        "claims": _f(g["claims"].sum() + fg["claims"].sum()),
        "settlement": settlement,
        "settle_per_unit": _f(delivered["settlement"].mean()) if len(delivered) else 0.0,
        "avg_cost": _f(cogs_sold / units_sold) if units_sold else 0.0,
        "cogs": -cogs_sold,
        "writeoff": -cogs_writeoff,
        "gross_profit": gross_profit,
        "gp_per_unit": _f(gross_profit / units_sold) if units_sold else 0.0,
        "gp_pct": _pct(gross_profit, gross_sale, 1),
    }


def compute(
    orders: pd.DataFrame,
    ads: pd.DataFrame,
    cfg: Dict[str, Any],
    platform: str,
    month: str,
    resell_rate: float,
    return_shipping_per_order: float,
) -> Dict[str, Any]:
    sku_cfg = cfg.get("skus", {})
    start, end = month_bounds(month)

    df = orders.copy()
    df["_book"] = df["sku"].map(lambda s: (sku_cfg.get(s) or {}).get("book", UNMAPPED))
    df["_cost"] = df["sku"].map(lambda s: float((sku_cfg.get(s) or {}).get("cost", 0.0)))

    in_month = (df["order_date"] >= start) & (df["order_date"] < end)
    cohort = df[in_month].copy()
    excluded = df[~in_month]

    fee = cohort[cohort["status"] == FEE_ADJ]
    real = cohort[cohort["status"] != FEE_ADJ].copy()

    ad_month = ads[(ads["run_date"] >= start) & (ads["run_date"] < end)] if len(ads) else ads
    ad_total = _f(abs(ad_month["total_cost"].sum())) if len(ad_month) else 0.0

    result: Dict[str, Any] = {
        "platform": platform,
        "month": month,
        "month_label": month_label(month),
        "resell_rate": resell_rate,
        "writeoff_pct": _f((1 - resell_rate) * 100, 0),
        "return_shipping_per_order": _f(return_shipping_per_order),
        "currency": cfg.get("currency", "Rs"),
        "has_data": bool(len(real)),
    }

    result["cohort"] = {
        "rows_in_scope": int(len(df)),
        "rows_excluded": int(len(excluded)),
        "rows_kept": int(len(cohort)),
        "order_lines": int(len(real)),
        "fee_lines": int(len(fee)),
        "unique_orders": int(cohort["order_id"].nunique()),
        "unmapped_skus": sorted(set(real.loc[real["_book"] == UNMAPPED, "sku"])),
        "zero_cost_skus": sorted(set(real.loc[real["_cost"] == 0, "sku"])),
    }

    if not len(real):
        return result

    # ------------------------------------------------------------------ funnel
    funnel = []
    for status, g in real.groupby("status"):
        funnel.append({
            "status": status,
            "orders": int(len(g)),
            "units": _f(g["quantity"].sum(), 0),
            "gross_sale": _f(g["gross_sale"].sum()),
            "settlement": _f(g["settlement"].sum()),
            "pct": _pct(len(g), len(real)),
        })
    funnel.sort(key=lambda r: -r["orders"])
    result["funnel"] = funnel

    total_orders = len(real)
    n_transit = int((real["status"] == IN_TRANSIT).sum())
    n_ret = int((real["status"] == RETURN).sum())
    n_rto = int((real["status"] == RTO).sum())
    closed = total_orders - n_transit
    result["funnel_summary"] = {
        "orders": total_orders,
        "delivered": int((real["status"] == DELIVERED).sum()),
        "in_transit": n_transit,
        "returns": n_ret,
        "rto": n_rto,
        "exchange": int((real["status"] == EXCHANGE).sum()),
        "closed": closed,
        "return_pct_all": _pct(n_ret, total_orders),
        "rto_pct_all": _pct(n_rto, total_orders),
        "return_pct_closed": _pct(n_ret, closed),
        "rto_pct_closed": _pct(n_rto, closed),
        "leakage_pct": _pct(n_ret + n_rto, total_orders),
    }

    # --------------------------------------------------------------- ad spend
    campaigns = []
    if len(ad_month):
        for campaign, g in ad_month.groupby("campaign"):
            campaigns.append({
                "campaign": str(campaign),
                "days": int(g["run_date"].nunique()),
                "spend": _f(abs(g["total_cost"].sum())),
            })
        campaigns.sort(key=lambda r: -r["spend"])
        for c in campaigns:
            c["share_pct"] = _pct(c["spend"], ad_total, 1)
    result["ads"] = {
        "total": ad_total,
        "base": _f(ad_month["ad_cost"].sum()) if len(ad_month) else 0.0,
        "gst": _f(abs(ad_month["gst"].sum())) if len(ad_month) else 0.0,
        "credits": _f(ad_month["credits"].sum()) if len(ad_month) else 0.0,
        "days_active": int(ad_month["run_date"].nunique()) if len(ad_month) else 0,
        "days_in_month": calendar.monthrange(start.year, start.month)[1],
        "campaigns": campaigns,
    }

    # ------------------------------------------------------- book & SKU P&L
    def build(level: str, key_col: str) -> List[Dict[str, Any]]:
        rows = []
        for key, g in real.groupby(key_col):
            row = {level: str(key)}
            row.update(_group_pnl(g, fee[fee[key_col] == key], resell_rate))
            if level == "sku":
                row["book"] = str(g["_book"].iloc[0])
                row["cost"] = _f(g["_cost"].iloc[0])
                row["contrib_per_unit"] = _f(row["settle_per_unit"] - row["cost"]) if row["settle_per_unit"] else 0.0
            rows.append(row)
        rows.sort(key=lambda r: -r["gross_profit"])
        return rows

    books = build("book", "_book")
    skus = build("sku", "sku")

    total_gross = sum(r["gross_sale"] for r in books)
    total_gp = sum(r["gross_profit"] for r in books)
    total_units = sum(r["units_sold"] for r in books)
    for r in books:
        r["ad_alloc"] = -_f(r["gross_sale"] / total_gross * ad_total) if total_gross else 0.0
        r["net_profit"] = _f(r["gross_profit"] + r["ad_alloc"])
        r["np_per_unit"] = _f(r["net_profit"] / r["units_sold"]) if r["units_sold"] else 0.0
        r["np_pct"] = _pct(r["net_profit"], r["gross_sale"], 1)
        r["rev_share_pct"] = _pct(r["gross_sale"], total_gross, 1)
        r["unit_share_pct"] = _pct(r["units_sold"], total_units, 1)
        r["profit_share_pct"] = _pct(r["gross_profit"], total_gp, 1)
    result["books"] = books
    result["skus"] = skus
    result["ad_allocation_note"] = (
        "Ad spend is reported by the marketplace at campaign level, not SKU level. "
        "It is allocated here pro-rata by gross sale, so per-book ACOS is a modelling "
        "assumption, not an observed figure."
    )

    # ----------------------------------------------------------- P&L statement
    gross = _f(real["gross_sale"].sum())
    rev_reversal = _f(real["return_revenue"].sum())
    fwd_ship = _f(real["fwd_shipping"].sum())
    ret_ship = _f(real["return_shipping"].sum())
    affiliate = _f(real["affiliate"].sum() + fee["affiliate"].sum())
    claims = _f(real["claims"].sum() + fee["claims"].sum())
    tds = _f(real["tds"].sum())
    commission = _f(real["commission"].sum())
    settlement = _f(real["settlement"].sum() + fee["settlement"].sum())
    cogs_sold = _f(-sum(r["cogs"] for r in books))
    cogs_writeoff = _f(-sum(r["writeoff"] for r in books))
    gross_profit = _f(settlement - cogs_sold - cogs_writeoff)
    net_profit = _f(gross_profit - ad_total)
    units_sold = _f(total_units, 0)

    result["statement"] = [
        {"label": "Gross sale value (incl. shipping & GST)", "value": gross},
        {"label": "Less: returns & RTO revenue reversal", "value": rev_reversal},
        {"label": "NET REVENUE", "value": _f(gross + rev_reversal), "emphasis": True},
        {"divider": True},
        {"label": "Marketplace commission", "value": commission},
        {"label": "Forward shipping charge", "value": fwd_ship},
        {"label": "Return shipping charge", "value": ret_ship},
        {"label": "Affiliate fee", "value": affiliate},
        {"label": "Claims recovered", "value": claims},
        {"label": "TDS", "value": tds},
        {"label": "TOTAL SETTLEMENT (marketplace pays you)", "value": settlement, "emphasis": True},
        {"divider": True},
        {"label": "Less: manufacturing cost of units sold", "value": -cogs_sold},
        {"label": "Less: write-off on returns (%d%% of returned stock)" % round((1 - resell_rate) * 100),
         "value": -cogs_writeoff},
        {"label": "GROSS PROFIT", "value": gross_profit, "emphasis": True},
        {"divider": True},
        {"label": "Less: marketplace ads (incl. GST)", "value": -ad_total},
        {"label": "NET PROFIT (%s order cohort)" % result["month_label"], "value": net_profit, "emphasis": True},
    ]
    for line in result["statement"]:
        if "value" in line:
            line["pct_of_gross"] = _pct(line["value"], gross)

    delivered_lines = real[real["status"] == DELIVERED]
    result["kpis"] = {
        "gross_sale": gross,
        "net_revenue": _f(gross + rev_reversal),
        "settlement": settlement,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "ad_spend": ad_total,
        "units_sold": units_sold,
        "orders": total_orders,
        "asp_per_order": _f(gross / total_orders) if total_orders else 0.0,
        "asp_per_unit": _f(gross / units_sold) if units_sold else 0.0,
        "asp_delivered": _f(delivered_lines["gross_sale"].mean()) if len(delivered_lines) else 0.0,
        "np_per_unit": _f(net_profit / units_sold) if units_sold else 0.0,
        "gp_per_unit": _f(gross_profit / units_sold) if units_sold else 0.0,
        "net_margin_on_gross": _pct(net_profit, gross),
        "net_margin_on_settlement": _pct(net_profit, settlement),
        "gross_margin": _pct(gross_profit, gross),
        "avg_cogs_per_unit": _f(cogs_sold / units_sold) if units_sold else 0.0,
        "blended_cogs_pct": _pct(cogs_sold + cogs_writeoff, gross),
        "acos": _pct(ad_total, gross),
        "tacos": _pct(ad_total, gross + rev_reversal),
        "roas": _f(gross / ad_total) if ad_total else 0.0,
        "return_pct_closed": _pct(n_ret, closed),
        "rto_pct_closed": _pct(n_rto, closed),
    }

    # ------------------------------------------------------------ cash position
    paid = _f(real[real["paid"]]["settlement"].sum() + fee[fee["paid"]]["settlement"].sum())
    result["cash"] = {
        "settled": paid,
        "receivable": _f(settlement - paid),
        "total": settlement,
        "settled_lines": int(real["paid"].sum()),
        "receivable_lines": int((~real["paid"]).sum()),
        "ads_deducted": ad_total,
        "manufacturing_outlay": cogs_sold,
    }

    # ----------------------------------------------------- return cost per book
    return_costs = []
    for r in books:
        total_cost = _f(r["return_shipping"] + r["writeoff"])
        failed = r["returns"] + r["rto"]
        return_costs.append({
            "book": r["book"],
            "returns": r["returns"],
            "rto": r["rto"],
            "return_shipping": r["return_shipping"],
            "writeoff": r["writeoff"],
            "total_cost": total_cost,
            "pct_of_book_gp": _pct(-total_cost, r["gross_profit"], 1) if r["gross_profit"] else 0.0,
            "cost_per_return": _f(total_cost / failed) if failed else 0.0,
        })
    total_return_cost = _f(abs(sum(r["total_cost"] for r in return_costs)))
    result["return_costs"] = return_costs
    result["return_cost_summary"] = {
        "total": total_return_cost,
        "pct_of_net_profit": _pct(total_return_cost, net_profit),
    }

    # -------------------------------------------- break-even & sensitivity
    avg_cost = cogs_sold / units_sold if units_sold else 0.0
    cost_per_failure = return_shipping_per_order + (1 - resell_rate) * avg_cost
    current_rate = n_ret / total_orders if total_orders else 0.0
    base_cost = total_orders * current_rate * cost_per_failure
    result["breakeven"] = {
        "ad_headroom": gross_profit,
        "ad_spent": ad_total,
        "ad_used_pct": _pct(ad_total, gross_profit, 1),
        "breakeven_cogs_per_unit": _f((settlement - ad_total) / units_sold) if units_sold else 0.0,
        "actual_cogs_per_unit": _f(avg_cost),
        "headroom_per_unit": _f(((settlement - ad_total) / units_sold - avg_cost)) if units_sold else 0.0,
    }
    rates = sorted(set(SENSITIVITY_RATES + [round(current_rate, 4)]))
    result["sensitivity"] = {
        "cost_per_failure": _f(cost_per_failure),
        "avg_cost_per_unit": _f(avg_cost),
        "current_return_rate": _pct(n_ret, total_orders),
        "rows": [{
            "return_rate": _f(rate * 100),
            "return_cost": _f(total_orders * rate * cost_per_failure),
            "net_profit": _f(net_profit + base_cost - total_orders * rate * cost_per_failure),
            "is_current": abs(rate - current_rate) < 1e-9,
        } for rate in rates],
    }

    # ------------------------------------------------- conservative / worst case
    transit = real[real["status"] == IN_TRANSIT]
    transit_settlement = _f(transit["settlement"].sum())
    transit_units = _f(transit["quantity"].sum(), 0)
    closed_ret_rate = n_ret / closed if closed else 0.0
    fail_rate = (n_ret + n_rto) / closed if closed else 0.0
    at_risk = _f(transit_settlement * fail_rate)
    recovered = _f((transit["_cost"] * transit["quantity"]).sum() * fail_rate * resell_rate)
    extra_ship = _f(transit_units * closed_ret_rate * return_shipping_per_order)
    conservative = _f(net_profit - at_risk + recovered - extra_ship)
    worst_recovered = _f((transit["_cost"] * transit["quantity"]).sum() * resell_rate)
    worst = _f(net_profit - transit_settlement + worst_recovered - transit_units * return_shipping_per_order)
    result["conservative"] = {
        "transit_orders": int(len(transit)),
        "transit_units": transit_units,
        "transit_settlement": transit_settlement,
        "fail_rate": _f(fail_rate * 100),
        "settlement_at_risk": at_risk,
        "stock_recovered": recovered,
        "extra_return_shipping": extra_ship,
        "reported_net_profit": net_profit,
        "conservative_net_profit": conservative,
        "downside": _f(net_profit - conservative),
        "downside_pct": _pct(net_profit - conservative, net_profit),
        "worst_case_net_profit": worst,
    }
    return result


def compare(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Month-over-month KPI table with deltas vs the previous month."""
    metrics = [
        ("orders", "Orders", "int"),
        ("units_sold", "Units sold", "int"),
        ("gross_sale", "Gross sale", "money"),
        ("settlement", "Settlement", "money"),
        ("ad_spend", "Ad spend", "money"),
        ("gross_profit", "Gross profit", "money"),
        ("net_profit", "Net profit", "money"),
        ("np_per_unit", "Net profit / unit", "money"),
        ("asp_per_order", "ASP / order", "money"),
        ("asp_per_unit", "ASP / unit", "money"),
        ("avg_cogs_per_unit", "Avg COGS / unit", "money"),
        ("net_margin_on_gross", "Net margin %", "pct"),
        ("gross_margin", "Gross margin %", "pct"),
        ("acos", "ACOS %", "pct"),
        ("roas", "ROAS", "x"),
        ("return_pct_closed", "Return % (closed)", "pct"),
        ("rto_pct_closed", "RTO % (closed)", "pct"),
    ]
    usable = [r for r in results if r.get("kpis")]
    rows = []
    for key, label, kind in metrics:
        values = [r["kpis"].get(key, 0.0) for r in usable]
        deltas: List[Optional[float]] = [None]
        for prev, cur in zip(values, values[1:]):
            deltas.append(_pct(cur - prev, abs(prev), 1) if prev else None)
        rows.append({"key": key, "label": label, "kind": kind, "values": values, "deltas": deltas})
    return {
        "months": [{"month": r["month"], "label": r["month_label"]} for r in usable],
        "rows": rows,
        "books": _compare_books(usable),
    }


def _compare_books(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    names: List[str] = []
    for r in results:
        for b in r.get("books", []):
            if b["book"] not in names:
                names.append(b["book"])
    rows = []
    for name in names:
        units, profit = [], []
        for r in results:
            match = next((b for b in r.get("books", []) if b["book"] == name), None)
            units.append(match["units_sold"] if match else 0.0)
            profit.append(match["net_profit"] if match else 0.0)
        rows.append({"book": name, "units": units, "net_profit": profit})
    rows.sort(key=lambda r: -sum(r["net_profit"]))
    return {"rows": rows}
