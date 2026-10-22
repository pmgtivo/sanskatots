"""Returns analysis: how often products come back, what it costs, and what the
marketplace gave back through claims.

Works on the same normalised order frame as the P&L engine, so it behaves the
same for every platform. Sections that need data a platform does not export
(delivery state, payment mode, claim reasons) are simply empty for it.

Definitions
-----------
* return %  = returned orders / closed orders        (customer returns)
* RTO %     = RTO orders / closed orders             (courier returned undelivered)
* failed %  = (returns + RTO) / closed orders
  Closed = every order except those still in transit, whose outcome is unknown.
  Cancelled orders never shipped and are reported separately.
* return loss = return shipping + the write-off on stock that cannot be resold
* claim recovery % = claims received / return loss
  Claims are what the platform pays back for a wrong, damaged or missing item
  in a returned parcel. Where the export carries no claims, the month's figures
  can be typed into Config and are used instead.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from .platforms.base import DELIVERED, IN_TRANSIT, LOST_STATUSES, RETURN, RTO

MIN_CLOSED_FOR_FLAG = 8        # a rate on fewer closed orders than this is noise
FLAG_MULTIPLE = 1.4            # "high" = this many times the platform average

CLAIM_REASONS = (
    ("wrong product", "Wrong product returned"),
    ("damaged", "Damaged / used product returned"),
    ("used", "Damaged / used product returned"),
    ("missing", "Missing items in returned parcel"),
)


def _f(value: Any, digits: int = 2) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if value != value else round(value, digits)


def _pct(num: float, den: float, digits: int = 2) -> float:
    return _f(num / den * 100, digits) if den else 0.0


def _slice(g: pd.DataFrame, fee: pd.DataFrame, resell_rate: float) -> Dict[str, Any]:
    st = g["status"]
    lost = g[st.isin(LOST_STATUSES)]
    orders = int(len(g))
    in_transit = int((st == IN_TRANSIT).sum())
    closed = orders - in_transit
    n_ret, n_rto = int((st == RETURN).sum()), int((st == RTO).sum())
    ship_cost = _f(-lost["return_shipping"].sum())
    writeoff = _f((lost["_cost"] * lost["quantity"]).sum() * (1 - resell_rate))
    claims = _f(g["claims"].sum() + (fee["claims"].sum() if len(fee) else 0.0))
    loss = _f(ship_cost + writeoff)
    gross = _f(g["gross_sale"].sum())
    refunded = _f(-lost["return_revenue"].sum())
    return {
        "orders": orders,
        "closed": closed,
        "in_transit": in_transit,
        "returns": n_ret,
        "rto": n_rto,
        "failed": n_ret + n_rto,
        "return_pct": _pct(n_ret, closed),
        "rto_pct": _pct(n_rto, closed),
        "fail_pct": _pct(n_ret + n_rto, closed),
        "units_returned": _f(lost["quantity"].sum(), 0),
        "gross_sale": gross,
        "refunded": refunded,
        "refund_pct_of_gross": _pct(refunded, gross),
        "return_shipping": ship_cost,
        "writeoff": writeoff,
        "loss": loss,
        "claims": claims,
        "net_loss": _f(loss - claims),
        "cost_per_failure": _f(loss / (n_ret + n_rto)) if (n_ret + n_rto) else 0.0,
    }


def _flag(row: Dict[str, Any], baseline: float) -> str:
    if row["closed"] < MIN_CLOSED_FOR_FLAG:
        return "low volume"
    if baseline and row["fail_pct"] >= baseline * FLAG_MULTIPLE and row["failed"] >= 2:
        return "HIGH"
    if row["failed"] == 0:
        return "clean"
    return ""


def _table(real: pd.DataFrame, fee: pd.DataFrame, key: str, resell_rate: float,
           baseline: float, fee_key: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = []
    for name, g in real.groupby(key):
        f = fee[fee[fee_key or key] == name] if len(fee) else fee
        row = {"name": str(name)}
        row.update(_slice(g, f, resell_rate))
        row["flag"] = _flag(row, baseline)
        rows.append(row)
    rows.sort(key=lambda r: (-r["fail_pct"] if r["closed"] >= MIN_CLOSED_FOR_FLAG else 1, -r["failed"], r["name"]))
    return rows


def _claim_reason(text: str) -> str:
    low = str(text).lower()
    for needle, label in CLAIM_REASONS:
        if needle in low:
            return label
    return "Other"


def _claims(real: pd.DataFrame, fee: pd.DataFrame, summary: Dict[str, Any],
            manual: Dict[str, Any]) -> Dict[str, Any]:
    both = pd.concat([real, fee]) if len(fee) else real
    claimed = both[both["claims"].abs() > 0.005]
    data_amount = _f(claimed["claims"].sum())
    reasons: Dict[str, Dict[str, float]] = {}
    for _, r in claimed.iterrows():
        label = _claim_reason(r["reason"]) if r["reason"] else "Reason not given"
        slot = reasons.setdefault(label, {"count": 0, "amount": 0.0})
        slot["count"] += 1
        slot["amount"] += float(r["claims"])

    m_received = _f(manual.get("claims_received_amount", 0))
    m_filed_amt = _f(manual.get("claims_filed_amount", 0))
    m_filed_n = int(_f(manual.get("claims_filed_count", 0), 0))
    if data_amount:
        basis, received, count = "platform report", data_amount, int(len(claimed))
    elif m_received or m_filed_amt or m_filed_n:
        basis, received, count = "entered manually", m_received, 0
    else:
        basis, received, count = "none", 0.0, 0

    loss = summary["loss"]
    failed = summary["failed"]
    return {
        "basis": basis,
        "received": _f(received),
        "claim_lines": count,
        "filed_count": m_filed_n,
        "filed_amount": m_filed_amt,
        "recovery_pct_of_loss": _pct(received, loss),
        "recovery_pct_of_filed": _pct(received, m_filed_amt) if m_filed_amt else None,
        "returns_without_claim": max(failed - count, 0) if basis == "platform report" else None,
        "claim_rate_pct": _pct(count, failed) if basis == "platform report" else None,
        "outstanding": _f(m_filed_amt - received) if m_filed_amt else None,
        "reasons": sorted(({"reason": k, "count": int(v["count"]), "amount": _f(v["amount"])}
                           for k, v in reasons.items()), key=lambda r: -r["amount"]),
    }


def build(real: pd.DataFrame, fee: pd.DataFrame, cancelled: pd.DataFrame,
          cfg_month: Dict[str, Any], resell_rate: float, gross_profit: float,
          est: bool) -> Dict[str, Any]:
    summary = _slice(real, fee, resell_rate)
    base = summary["fail_pct"]
    claims = _claims(real, fee, summary, cfg_month or {})

    total_orders = int(len(real)) + int(len(cancelled))
    summary["cancelled"] = int(len(cancelled))
    summary["cancel_pct"] = _pct(len(cancelled), total_orders)
    summary["loss_pct_of_gross_profit"] = _pct(summary["loss"], gross_profit) if gross_profit > 0 else 0.0
    summary["delivered"] = int((real["status"] == DELIVERED).sum())

    with_state = real[real["state"] != ""]
    states = _table(with_state, fee, "state", resell_rate, base) if len(with_state) else []
    with_mode = real[real["pay_mode"] != ""]
    modes = _table(with_mode, fee, "pay_mode", resell_rate, base) if len(with_mode) else []

    books = _table(real, fee, "_book", resell_rate, base)
    skus = _table(real, fee, "sku", resell_rate, base)

    out = {
        "summary": summary,
        "claims": claims,
        "by_book": books,
        "by_sku": skus,
        "by_state": states[:15],
        "by_pay_mode": modes,
        "has_state": bool(states),
        "has_pay_mode": bool(modes),
        "estimated": est,
    }
    out["insights"] = _insights(out)
    return out


def _insights(r: Dict[str, Any]) -> List[Dict[str, str]]:
    s, c = r["summary"], r["claims"]
    notes: List[Dict[str, str]] = []

    def add(level: str, text: str) -> None:
        notes.append({"level": level, "text": text})

    if s["in_transit"]:
        add("info", "%d order(s) are still open, so their returns are not in these figures yet. "
                    "The rate is measured on the %d closed orders." % (s["in_transit"], s["closed"]))
    if s["closed"] and s["failed"] == 0:
        add("good", "No returns on %d closed orders." % s["closed"])

    ranked = [b for b in r["by_book"] if b["closed"] >= MIN_CLOSED_FOR_FLAG and b["failed"] > 0]
    if ranked:
        worst = ranked[0]
        add("warn" if worst["flag"] == "HIGH" else "info",
            "Highest failure rate: %s at %.1f%% (%d of %d closed), against %.1f%% overall."
            % (worst["name"], worst["fail_pct"], worst["failed"], worst["closed"], s["fail_pct"]))
    costly = sorted((b for b in r["by_book"] if b["loss"] > 0), key=lambda b: -b["loss"])
    if costly:
        add("info", "Costliest returns: %s, %.2f lost to return shipping and unsellable stock."
            % (costly[0]["name"], costly[0]["loss"]))

    modes = {m["name"]: m for m in r["by_pay_mode"] if m["closed"] >= MIN_CLOSED_FOR_FLAG}
    if len(modes) == 2:
        hi, lo = sorted(modes.values(), key=lambda m: -m["fail_pct"])
        if hi["fail_pct"] > lo["fail_pct"] * 1.3 and hi["failed"] >= 2:
            add("warn", "%s orders fail %.1f%% of the time against %.1f%% for %s."
                % (hi["name"], hi["fail_pct"], lo["fail_pct"], lo["name"]))

    hot = [x for x in r["by_state"] if x["closed"] >= MIN_CLOSED_FOR_FLAG and x["flag"] == "HIGH"]
    if hot:
        add("warn", "Return-prone states: " + ", ".join("%s (%.0f%%)" % (x["name"], x["fail_pct"]) for x in hot[:4]) + ".")

    if s["loss"] > 0:
        if c["basis"] == "none":
            add("warn", "Return loss of %.2f has no claims recorded. If any returned parcel arrived wrong, "
                        "damaged or short, raise the claim in the seller panel and enter the totals in Config." % s["loss"])
        elif c["received"] > 0:
            add("good", "Claims recovered %.2f, which is %.1f%% of the %.2f return loss."
                % (c["received"], c["recovery_pct_of_loss"], s["loss"]))
        if c["returns_without_claim"]:
            add("info", "%d of %d failed orders have no claim against them. Check whether any came back "
                        "wrong, damaged or incomplete." % (c["returns_without_claim"], s["failed"]))
    if s["cancelled"]:
        add("info", "%d order(s) (%.1f%%) were cancelled before shipping and are excluded from the return rate."
            % (s["cancelled"], s["cancel_pct"]))
    return notes
