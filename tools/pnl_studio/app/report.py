"""Render an engine result as a markdown P&L report."""

from __future__ import annotations

from typing import Any, Dict, List

from . import platforms


def _money(value: float, cur: str = "Rs") -> str:
    return "%s %s%s" % (cur, "-" if value < 0 else "", format(abs(value), ",.2f"))


def _num(value: float) -> str:
    return format(value, ",.0f") if float(value).is_integer() else format(value, ",.2f")


def _table(headers: List[str], rows: List[List[str]], align_right_from: int = 1) -> str:
    sep = ["---" if i < align_right_from else "---:" for i in range(len(headers))]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(sep) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render(result: Dict[str, Any]) -> str:
    cur = result.get("currency", "Rs")
    label = result["month_label"]
    platform_label = platforms.get(result["platform"]).label
    out: List[str] = []
    add = out.append

    add("# SanskaTots %s P&L — %s" % (platform_label, label))
    add("")
    add("> Order cohort: every order **placed** in %s, regardless of which payment "
        "file it arrived in or when it settled." % label)
    add("")

    if not result.get("has_data"):
        add("_No order lines found for this month._")
        return "\n".join(out) + "\n"

    k = result["kpis"]
    cohort = result["cohort"]
    fs = result["funnel_summary"]
    ads = result["ads"]

    add("## 1. Headline")
    add("")
    add(_table(["Metric", "Value"], [
        ["Net profit", _money(k["net_profit"], cur)],
        ["Gross profit (before ads)", _money(k["gross_profit"], cur)],
        ["Gross sale value", _money(k["gross_sale"], cur)],
        ["Settlement received/receivable", _money(k["settlement"], cur)],
        ["Ad spend (incl. GST)", _money(k["ad_spend"], cur)],
        ["Units sold", _num(k["units_sold"])],
        ["Orders", _num(k["orders"])],
        ["ASP per order", _money(k["asp_per_order"], cur)],
        ["ASP per unit", _money(k["asp_per_unit"], cur)],
        ["Net profit per unit", _money(k["np_per_unit"], cur)],
        ["Net margin on gross sale", "%.2f%%" % k["net_margin_on_gross"]],
        ["Gross margin", "%.2f%%" % k["gross_margin"]],
        ["Avg COGS per unit", _money(k["avg_cogs_per_unit"], cur)],
        ["ACOS", "%.2f%%" % k["acos"]],
        ["TACOS", "%.2f%%" % k["tacos"]],
        ["ROAS", "%.2fx" % k["roas"]],
        ["Return % (closed orders)", "%.2f%%" % k["return_pct_closed"]],
        ["RTO % (closed orders)", "%.2f%%" % k["rto_pct_closed"]],
    ]))
    add("")

    add("## 2. Cohort build")
    add("")
    add(_table(["Step", "Rows"], [
        ["Rows across all de-duplicated payment files", _num(cohort["rows_in_scope"])],
        ["Excluded (order placed outside %s)" % label, _num(cohort["rows_excluded"])],
        ["Kept (order placed in %s)" % label, _num(cohort["rows_kept"])],
        ["— real order lines", _num(cohort["order_lines"])],
        ["— fee-adjustment lines", _num(cohort["fee_lines"])],
        ["Unique orders", _num(cohort["unique_orders"])],
    ]))
    if cohort["unmapped_skus"]:
        add("")
        add("> **Unmapped SKUs (no book/cost configured):** %s" % ", ".join(cohort["unmapped_skus"]))
    add("")

    add("## 3. Order funnel")
    add("")
    add(_table(["Status", "Orders", "Units", "Gross sale", "Settlement", "% of orders"],
               [[r["status"], _num(r["orders"]), _num(r["units"]), _money(r["gross_sale"], cur),
                 _money(r["settlement"], cur), "%.2f%%" % r["pct"]] for r in result["funnel"]]))
    add("")
    add("- Return rate on closed orders: **%.2f%%** (excludes %s still in transit)"
        % (fs["return_pct_closed"], _num(fs["in_transit"])))
    add("- RTO rate on closed orders: **%.2f%%**" % fs["rto_pct_closed"])
    add("- Combined return + RTO leakage on all orders: **%.2f%%**" % fs["leakage_pct"])
    add("")

    add("## 4. Ad spend")
    add("")
    add("Base %s · GST %s · credits %s · **total %s** across %d of %d days."
        % (_money(ads["base"], cur), _money(ads["gst"], cur), _money(ads["credits"], cur),
           _money(ads["total"], cur), ads["days_active"], ads["days_in_month"]))
    if ads["campaigns"]:
        add("")
        add(_table(["Campaign", "Days", "Spend", "Share"],
                   [[c["campaign"], _num(c["days"]), _money(c["spend"], cur), "%.1f%%" % c["share_pct"]]
                    for c in ads["campaigns"]]))
    add("")

    add("## 5. Book-level P&L")
    add("")
    add(_table(["Book", "Units", "ASP", "Gross sale", "Settlement", "COGS", "Write-off",
                "Gross profit", "Ad alloc.", "Net profit", "NP/unit", "NP %"],
               [[b["book"], _num(b["units_sold"]), _money(b["asp"], cur), _money(b["gross_sale"], cur),
                 _money(b["settlement"], cur), _money(b["cogs"], cur), _money(b["writeoff"], cur),
                 _money(b["gross_profit"], cur), _money(b["ad_alloc"], cur), _money(b["net_profit"], cur),
                 _money(b["np_per_unit"], cur), "%.1f%%" % b["np_pct"]] for b in result["books"]]))
    add("")
    add("> %s" % result["ad_allocation_note"])
    add("")

    add("## 6. Returns by book")
    add("")
    add(_table(["Book", "Returns", "RTO", "Return %", "Return shipping", "Stock write-off",
                "Total return cost", "Cost per failure"],
               [[r["book"], _num(r["returns"]), _num(r["rto"]),
                 "%.2f%%" % next(b["return_pct"] for b in result["books"] if b["book"] == r["book"]),
                 _money(r["return_shipping"], cur), _money(r["writeoff"], cur),
                 _money(r["total_cost"], cur), _money(r["cost_per_return"], cur)]
                for r in result["return_costs"]]))
    add("")
    add("Total return cost **%s** = %.1f%% of net profit."
        % (_money(result["return_cost_summary"]["total"], cur),
           result["return_cost_summary"]["pct_of_net_profit"]))
    add("")

    add("## 7. SKU detail")
    add("")
    add(_table(["SKU", "Book", "Cost/unit", "Orders", "Units", "Returns", "RTO", "ASP",
                "Settle/unit", "Contribution/unit", "Gross profit"],
               [[s["sku"], s["book"], _money(s["cost"], cur), _num(s["orders"]), _num(s["units_sold"]),
                 _num(s["returns"]), _num(s["rto"]), _money(s["asp"], cur),
                 _money(s["settle_per_unit"], cur), _money(s["contrib_per_unit"], cur),
                 _money(s["gross_profit"], cur)] for s in result["skus"]]))
    add("")

    add("## 8. P&L statement")
    add("")
    rows = []
    for line in result["statement"]:
        if line.get("divider"):
            continue
        name = "**%s**" % line["label"] if line.get("emphasis") else line["label"]
        rows.append([name, _money(line["value"], cur), "%.2f%%" % line["pct_of_gross"]])
    add(_table(["Line", "Amount", "% of gross sale"], rows))
    add("")

    cash = result["cash"]
    add("## 9. Cash position")
    add("")
    add(_table(["Item", "Amount"], [
        ["Settlement already banked", _money(cash["settled"], cur)],
        ["Settlement still receivable", _money(cash["receivable"], cur)],
        ["Total earned on %s orders" % label, _money(cash["total"], cur)],
        ["Cash deducted for ads", _money(cash["ads_deducted"], cur)],
        ["Manufacturing outlay on units sold", _money(cash["manufacturing_outlay"], cur)],
    ]))
    if cash["receivable"] > 0:
        add("")
        add("> %s of this month's settlement is still receivable — it is earned, not yet cash in hand."
            % _money(cash["receivable"], cur))
    add("")

    be = result["breakeven"]
    sens = result["sensitivity"]
    add("## 10. Break-even & sensitivity")
    add("")
    add("- Break-even ad spend (gross profit before ads): **%s** — you spent %s (%.1f%% of it)."
        % (_money(be["ad_headroom"], cur), _money(be["ad_spent"], cur), be["ad_used_pct"]))
    add("- Break-even blended COGS per unit: **%s** vs actual %s (headroom %s)."
        % (_money(be["breakeven_cogs_per_unit"], cur), _money(be["actual_cogs_per_unit"], cur),
           _money(be["headroom_per_unit"], cur)))
    add("")
    add("Each failed order costs %s (return shipping %s + %d%% stock write-off on a %s average unit):"
        % (_money(sens["cost_per_failure"], cur), _money(result["return_shipping_per_order"], cur),
           result["writeoff_pct"], _money(sens["avg_cost_per_unit"], cur)))
    add("")
    add(_table(["Return rate", "Return cost", "Net profit"],
               [["%.2f%%%s" % (r["return_rate"], " (current)" if r["is_current"] else ""),
                 _money(r["return_cost"], cur), _money(r["net_profit"], cur)] for r in sens["rows"]]))
    add("")

    cons = result["conservative"]
    add("## 11. Conservative view")
    add("")
    add("Applying the observed %.2f%% failure rate to the %s orders still in transit:"
        % (cons["fail_rate"], _num(cons["transit_orders"])))
    add("")
    add(_table(["Item", "Amount"], [
        ["Settlement at risk", _money(cons["settlement_at_risk"], cur)],
        ["Stock recovered (%d%% resellable)" % round(result["resell_rate"] * 100),
         _money(cons["stock_recovered"], cur)],
        ["Extra return shipping", _money(cons["extra_return_shipping"], cur)],
        ["**Reported net profit**", _money(cons["reported_net_profit"], cur)],
        ["**Conservative net profit**", _money(cons["conservative_net_profit"], cur)],
        ["Downside risk", "%s (%.1f%%)" % (_money(cons["downside"], cur), cons["downside_pct"])],
        ["Worst case (every in-transit order fails)", _money(cons["worst_case_net_profit"], cur)],
    ]))
    add("")

    add("---")
    add("")
    add("_Assumptions: %d%% of returned/RTO stock is resellable (%d%% written off); "
        "return shipping %s per failed order; units sold = delivered + in transit + exchange._"
        % (round(result["resell_rate"] * 100), result["writeoff_pct"],
           _money(result["return_shipping_per_order"], cur)))
    return "\n".join(out) + "\n"
