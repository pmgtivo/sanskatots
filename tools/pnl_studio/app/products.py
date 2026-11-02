"""Product-level view across platforms: what sold, what came back, what that cost.

Built from the per-platform results, so every figure here is the same number the
platform's own Returns tab shows, just summed per product. Nothing is recomputed
from raw orders.
"""

from __future__ import annotations

from typing import Any, Dict, List

SUMMED = (
    "orders", "closed", "in_transit", "returns", "rto", "failed", "units_sold", "units_returned",
    "units_closed", "gross_sale", "refunded", "return_shipping", "writeoff", "loss", "claims", "net_loss",
)


def _f(value: Any, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _pct(num: float, den: float, digits: int = 2) -> float:
    return _f(num / den * 100, digits) if den else 0.0


def _finish(row: Dict[str, Any]) -> Dict[str, Any]:
    row["return_pct"] = _pct(row["returns"], row["closed"])
    row["rto_pct"] = _pct(row["rto"], row["closed"])
    row["fail_pct"] = _pct(row["failed"], row["closed"])
    row["unit_fail_pct"] = _pct(row["units_returned"], row["units_closed"])
    row["loss_per_failed"] = _f(row["loss"] / row["failed"]) if row["failed"] else 0.0
    row["loss_pct_of_gross_profit"] = _pct(row["loss"], row["gross_profit"]) if row["gross_profit"] > 0 else 0.0
    return row


def _merge(results: List[Dict[str, Any]], table: str, profit_table: str, key: str) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for result in results:
        if not result.get("has_data"):
            continue
        profit = {p[key]: p for p in result.get(profit_table, [])}
        for r in result["returns"][table]:
            name = r["name"]
            row = merged.setdefault(name, {
                "name": name, "gross_profit": 0.0, "net_profit": 0.0, "platforms": [],
                **{k: 0.0 for k in SUMMED},
            })
            for k in SUMMED:
                row[k] += r.get(k, 0) or 0
            p = profit.get(name, {})
            row["gross_profit"] += p.get("gross_profit", 0.0)
            row["net_profit"] += p.get("net_profit", 0.0)
            row["platforms"].append(_finish({
                "platform": result["platform"], "label": _label(result),
                "gross_profit": p.get("gross_profit", 0.0), "net_profit": p.get("net_profit", 0.0),
                **{k: r.get(k, 0) or 0 for k in SUMMED},
            }))
    rows = [_finish(r) for r in merged.values()]
    for r in rows:
        for k in list(SUMMED) + ["gross_profit", "net_profit"]:
            r[k] = _f(r[k], 0 if k in ("orders", "closed", "in_transit", "returns", "rto", "failed",
                                        "units_sold", "units_returned", "units_closed") else 2)
    rows.sort(key=lambda r: (-r["units_returned"], -r["loss"], r["name"]))
    return rows


def _label(result: Dict[str, Any]) -> str:
    return result["platform"].title()


def build(month: str, month_label: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    books = _merge(results, "by_book", "books", "book")
    skus = _merge(results, "by_sku", "skus", "sku")
    totals = {k: _f(sum(b[k] for b in books)) for k in SUMMED}
    totals["fail_pct"] = _pct(totals["failed"], totals["closed"])
    totals["unit_fail_pct"] = _pct(totals["units_returned"], totals["units_closed"])
    worst = [b["name"] for b in books if b["closed"] >= 8 and b["failed"] > 0]
    return {
        "month": month,
        "month_label": month_label,
        "by_book": books,
        "by_sku": skus,
        "totals": totals,
        "most_returned": books[0]["name"] if books and books[0]["units_returned"] else None,
        "highest_rate": max(worst, key=lambda n: next(b["fail_pct"] for b in books if b["name"] == n)) if worst else None,
    }
