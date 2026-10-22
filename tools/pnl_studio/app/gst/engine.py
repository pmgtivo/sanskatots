"""GST return computation — every number the seller types into the portal.

Scope: outward supplies only, reconstructed from marketplace GST reports. The
engine is deliberately conservative — anything it cannot prove it raises as an
anomaly rather than silently absorbing into a total.

The arithmetic rules it applies:

* Only ``INVOICE`` and ``CREDIT_NOTE`` lines carry value. Cancelled orders never
  produced an invoice and free replacements carry no consideration, so both are
  counted for reconciliation but excluded from turnover.
* Credit notes are negative, so a month's figure is the *net* of supplies and
  returns. That is what GSTR-1 Table 8 and GSTR-3B 3.1(c) ask for.
* The tax period follows the **document date**, not the order date. An August
  order invoiced in September belongs to September.
* The exemption bucket follows the HSN, except where the marketplace actually
  charged tax — then the line is taxable, because that money changed hands and
  section 76 requires it to reach the Government.
* GSTR-3B Table 3.2 is scoped by the form itself to supplies shown in 3.1(a),
  3.1(b) and 3.1.1(i). Exempt supplies are therefore excluded from 3.2.
"""

from __future__ import annotations

import calendar
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from . import rules
from .sources import (CANCELLED, CREDIT_NOTE, INVOICE, REPLACEMENT, SOURCES,
                      VALUE_DOCS)

MONEY_TOLERANCE = 0.05
UQC = "NOS-NUMBERS"


def r2(value: Any) -> float:
    try:
        out = round(float(value) + 0.0, 2)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if out == 0 else out


def period_label(period: str) -> str:
    try:
        year, month = period.split("-")
        return "%s %s" % (calendar.month_name[int(month)], year)
    except Exception:
        return period


def periods_label(periods: Sequence[str]) -> str:
    if not periods:
        return "(no period)"
    if len(periods) == 1:
        return period_label(periods[0])
    return "%s to %s" % (period_label(periods[0]), period_label(periods[-1]))


def _agg(frame: pd.DataFrame) -> Dict[str, float]:
    if frame is None or len(frame) == 0:
        return {k: 0.0 for k in
                ("taxable", "igst", "cgst", "sgst", "cess", "tax", "invoice",
                 "quantity", "shipping", "lines")}
    tax = float(frame["igst"].sum() + frame["cgst"].sum() + frame["sgst"].sum() + frame["cess"].sum())
    taxable = float(frame["taxable_value"].sum())
    return {
        "taxable": r2(taxable),
        "igst": r2(frame["igst"].sum()),
        "cgst": r2(frame["cgst"].sum()),
        "sgst": r2(frame["sgst"].sum()),
        "cess": r2(frame["cess"].sum()),
        "tax": r2(tax),
        "invoice": r2(taxable + tax),
        "quantity": r2(frame["quantity"].sum()),
        "shipping": r2(frame["shipping_value"].sum()),
        "lines": int(len(frame)),
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute(lines: pd.DataFrame, periods: Sequence[str], cfg: Dict[str, Any],
            documents: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Build every GST table for the given tax period(s)."""
    periods = [p for p in sorted(set(periods)) if p]
    seller = cfg.get("seller", {})
    filing = cfg.get("filing", {})
    report_wrong_tax = bool(filing.get("report_wrongly_charged_tax", True))
    aato = float(filing.get("aato_previous_fy", 0) or 0)

    all_lines = lines if lines is not None else pd.DataFrame()
    scope = all_lines[all_lines["period"].isin(periods)].copy() if len(all_lines) else all_lines

    value_rows = scope[scope["doc_type"].isin(VALUE_DOCS)].copy() if len(scope) else scope
    zero_rows = scope[~scope["doc_type"].isin(VALUE_DOCS)].copy() if len(scope) else scope

    anomalies = _validate(scope, seller)

    taxable_rows = value_rows[value_rows["bucket"] == rules.TAXABLE] if len(value_rows) else value_rows
    exempt_rows = value_rows[value_rows["bucket"] == rules.EXEMPT] if len(value_rows) else value_rows
    nil_rows = value_rows[value_rows["bucket"] == rules.NIL_RATED] if len(value_rows) else value_rows
    nongst_rows = value_rows[value_rows["bucket"] == rules.NON_GST] if len(value_rows) else value_rows

    if not report_wrong_tax:
        # Caller chose to park the wrongly-taxed lines pending a credit note.
        taxable_rows = taxable_rows.iloc[0:0]

    result: Dict[str, Any] = {
        "periods": periods,
        "label": periods_label(periods),
        "seller": seller,
        "filing": _filing_calendar(periods, filing, seller),
        "totals": {
            "all": _agg(value_rows),
            "taxable": _agg(taxable_rows),
            "exempt": _agg(exempt_rows),
            "nil_rated": _agg(nil_rows),
            "non_gst": _agg(nongst_rows),
            "invoices": _agg(value_rows[value_rows["doc_type"] == INVOICE]) if len(value_rows) else _agg(None),
            "credit_notes": _agg(value_rows[value_rows["doc_type"] == CREDIT_NOTE]) if len(value_rows) else _agg(None),
        },
        "by_period": _by_period(value_rows, periods),
        "by_platform": _by_platform(value_rows, zero_rows),
        "by_state": _by_state(value_rows),
        "tables": {
            "gstr1_table_5": _table_5(taxable_rows),
            "gstr1_table_7": _table_7(taxable_rows),
            "gstr1_table_8": _table_8(value_rows),
            "gstr1_table_12": _table_12(value_rows, aato),
            "gstr1_table_13": _table_13(scope, documents),
            "gstr1_table_14": _table_14(value_rows, cfg),
            "gstr3b": _gstr3b(taxable_rows, exempt_rows, nil_rows, nongst_rows),
            "gstr3b_3_2": _gstr3b_32(taxable_rows),
            "tcs": _tcs(value_rows, taxable_rows, cfg),
            "itc": _itc_guidance(value_rows, exempt_rows, nil_rows),
        },
        "anomalies": anomalies,
        "hsn_digits": rules.hsn_digits_required(aato),
        "report_wrongly_charged_tax": report_wrong_tax,
    }
    return result


# ---------------------------------------------------------------------------
# Breakdowns
# ---------------------------------------------------------------------------

def _by_period(rows: pd.DataFrame, periods: Sequence[str]) -> List[Dict[str, Any]]:
    out = []
    for period in periods:
        chunk = rows[rows["period"] == period] if len(rows) else rows
        entry = {"period": period, "label": period_label(period), "total": _agg(chunk)}
        for bucket, name in ((rules.TAXABLE, "taxable"), (rules.EXEMPT, "exempt"),
                             (rules.NIL_RATED, "nil_rated"), (rules.NON_GST, "non_gst")):
            entry[name] = _agg(chunk[chunk["bucket"] == bucket] if len(chunk) else chunk)
        out.append(entry)
    return out


def _by_platform(rows: pd.DataFrame, zero_rows: pd.DataFrame) -> List[Dict[str, Any]]:
    keys = sorted(set(list(rows["platform"]) if len(rows) else [])
                  | set(list(zero_rows["platform"]) if len(zero_rows) else []))
    out = []
    for key in keys:
        chunk = rows[rows["platform"] == key] if len(rows) else rows
        zeros = zero_rows[zero_rows["platform"] == key] if len(zero_rows) else zero_rows
        out.append({
            "platform": key,
            "total": _agg(chunk),
            "invoices": _agg(chunk[chunk["doc_type"] == INVOICE] if len(chunk) else chunk),
            "credit_notes": _agg(chunk[chunk["doc_type"] == CREDIT_NOTE] if len(chunk) else chunk),
            "exempt": _agg(chunk[chunk["bucket"] == rules.EXEMPT] if len(chunk) else chunk),
            "taxable": _agg(chunk[chunk["bucket"] == rules.TAXABLE] if len(chunk) else chunk),
            "cancelled": int((zeros["doc_type"] == CANCELLED).sum()) if len(zeros) else 0,
            "replacements": int((zeros["doc_type"] == REPLACEMENT).sum()) if len(zeros) else 0,
            "tcs_collected": r2(chunk[["tcs_igst", "tcs_cgst", "tcs_sgst"]].sum().sum()) if len(chunk) else 0.0,
        })
    return out


def _by_state(rows: pd.DataFrame) -> List[Dict[str, Any]]:
    if rows is None or len(rows) == 0:
        return []
    out = []
    for (code, state, supply), chunk in rows.groupby(["pos_code", "pos_state", "supply_type"]):
        agg = _agg(chunk)
        agg.update({"pos_code": code, "pos_state": state, "supply_type": supply})
        out.append(agg)
    out.sort(key=lambda r: -abs(r["taxable"]))
    return out


# ---------------------------------------------------------------------------
# GSTR-1 tables
# ---------------------------------------------------------------------------

def _is_b2c(frame: pd.DataFrame) -> pd.Series:
    return frame["buyer_gstin"].astype(str).str.len() < 15


def _table_5(taxable: pd.DataFrame) -> Dict[str, Any]:
    """Table 5 — B2C Large: inter-State, invoice value above Rs 2.5 lakh."""
    rows: List[Dict[str, Any]] = []
    if len(taxable):
        sel = taxable[_is_b2c(taxable) & (taxable["supply_type"] == "INTER")]
        if len(sel):
            grouped = sel.groupby(["doc_no", "pos_code", "pos_state", "rate"], dropna=False)
            for (doc_no, code, state, rate), chunk in grouped:
                agg = _agg(chunk)
                if abs(agg["invoice"]) <= 250000:
                    continue
                rows.append({
                    "invoice_no": doc_no, "pos_code": code, "pos_state": state,
                    "rate_pct": r2(float(rate) * 100), "taxable": agg["taxable"],
                    "igst": agg["igst"], "cess": agg["cess"],
                })
    return {
        "title": "Table 5 — B2C (Large): inter-State supplies to unregistered "
                 "persons where invoice value exceeds Rs 2,50,000",
        "rows": rows,
        "note": "Empty is the expected result for this business — no single "
                "consumer invoice comes close to Rs 2.5 lakh.",
    }


def _table_7(taxable: pd.DataFrame) -> Dict[str, Any]:
    """Table 7 — B2C Others, consolidated rate-wise (and State-wise if inter-State)."""
    intra: List[Dict[str, Any]] = []
    inter: List[Dict[str, Any]] = []
    if len(taxable):
        sel = taxable[_is_b2c(taxable)]
        large = sel.groupby(["doc_no"])["taxable_value"].transform("sum").abs() > 250000
        sel = sel[~(large & (sel["supply_type"] == "INTER"))]
        for (rate,), chunk in sel[sel["supply_type"] == "INTRA"].groupby(["rate"]):
            agg = _agg(chunk)
            intra.append({
                "rate_pct": r2(float(rate) * 100), "taxable": agg["taxable"],
                "cgst": agg["cgst"], "sgst": agg["sgst"], "cess": agg["cess"],
            })
        grouped = sel[sel["supply_type"] == "INTER"].groupby(["pos_code", "pos_state", "rate"])
        for (code, state, rate), chunk in grouped:
            agg = _agg(chunk)
            inter.append({
                "pos_code": code, "pos_state": state,
                "rate_pct": r2(float(rate) * 100), "taxable": agg["taxable"],
                "igst": agg["igst"], "cess": agg["cess"],
            })
    return {
        "title": "Table 7 — B2C (Others): consolidated taxable supplies to unregistered persons",
        "intra_state": intra,
        "inter_state": inter,
        "note": "Exempt book sales do NOT belong here. Table 7 carries taxable "
                "supplies only; the exempt turnover goes to Table 8.",
    }


def _table_8(rows: pd.DataFrame) -> Dict[str, Any]:
    """Table 8 — Nil rated, exempted and non-GST outward supplies."""
    bucket_col = {rules.NIL_RATED: "nil_rated", rules.EXEMPT: "exempted", rules.NON_GST: "non_gst"}
    out = []
    for code, label in rules.GSTR1_TABLE_8_ROWS:
        inter = code in ("8A", "8C")
        registered = code in ("8A", "8B")
        entry = {"row": code, "description": label,
                 "nil_rated": 0.0, "exempted": 0.0, "non_gst": 0.0, "lines": 0}
        if len(rows):
            b2c = _is_b2c(rows)
            sel = rows[
                (rows["supply_type"] == ("INTER" if inter else "INTRA"))
                & ((~b2c) if registered else b2c)
            ]
            for bucket, field in bucket_col.items():
                chunk = sel[sel["bucket"] == bucket]
                entry[field] = _agg(chunk)["taxable"]
                entry["lines"] += int(len(chunk))
        entry["total"] = r2(entry["nil_rated"] + entry["exempted"] + entry["non_gst"])
        out.append(entry)
    grand = r2(sum(r["total"] for r in out))
    return {
        "title": "Table 8 — Nil rated, exempted and non-GST outward supplies",
        "columns": rules.GSTR1_TABLE_8_COLUMNS,
        "rows": out,
        "total": grand,
        "note": "Printed books are exempted under Notfn. 2/2017-CT(R), not "
                "nil-rated, so the value sits in the 'Exempted' column. The box "
                "total is identical either way; the distinction matters for ITC "
                "under section 17(2).",
    }


def _table_12(rows: pd.DataFrame, aato: float) -> Dict[str, Any]:
    digits = rules.hsn_digits_required(aato)
    b2b: List[Dict[str, Any]] = []
    b2c: List[Dict[str, Any]] = []
    if len(rows):
        work = rows.copy()
        work["hsn_report"] = work["hsn"].astype(str).str.replace(r"\D", "", regex=True).str[:digits]
        b2c_mask = _is_b2c(work)
        for target, sel in (("b2b", work[~b2c_mask]), ("b2c", work[b2c_mask])):
            for (hsn, rate), chunk in sel.groupby(["hsn_report", "rate"]):
                agg = _agg(chunk)
                _, desc, cite = rules.classify_hsn(hsn)
                entry = {
                    "hsn": hsn or "(missing)", "description": desc, "uqc": UQC,
                    "rate_pct": r2(float(rate) * 100),
                    "quantity": agg["quantity"], "total_value": agg["invoice"],
                    "taxable": agg["taxable"], "igst": agg["igst"],
                    "cgst": agg["cgst"], "sgst": agg["sgst"], "cess": agg["cess"],
                    "citation": cite,
                }
                (b2b if target == "b2b" else b2c).append(entry)
    b2b.sort(key=lambda r: r["hsn"])
    b2c.sort(key=lambda r: r["hsn"])
    return {
        "title": "Table 12 — HSN-wise summary of outward supplies",
        "digits": digits,
        "b2b": b2b,
        "b2c": b2c,
        "note": "Aggregate annual turnover up to Rs 5 crore permits %d-digit HSN. "
                "Table 12 is split into B2B and B2C tabs on the portal and the "
                "HSN must be picked from the dropdown, not typed." % digits,
    }


def _split_serial(platform: str, number: str) -> Tuple[str, int]:
    """Split a document number into (series, running sequence).

    Flipkart numbers are always 16 characters: a 9-character series code
    followed by a 7-digit sequence. Splitting at the first digit would merge
    unrelated series (NUAHL49... and NUAHL52...), so it is done positionally.
    """
    if platform == "flipkart" and len(number) == 16 and number[-7:].isdigit():
        return number[:-7], int(number[-7:])
    m = re.match(r"^(.*?)(\d+)$", number)
    return (m.group(1), int(m.group(2))) if m else (number, 0)


def _compose_serial(platform: str, series: str, seq: int) -> str:
    return "%s%07d" % (series, seq) if platform == "flipkart" else "%s%d" % (series, seq)


def _register_rows(platform: str, chunk: pd.DataFrame,
                   docs: pd.DataFrame) -> List[Dict[str, Any]]:
    """Table 13 rows for a platform whose numbers come from a separate register.

    The register can hold numbers outside the period (a document generated
    after the period closed) and can omit numbers that the turnover proves were
    issued. Both are resolved against the turnover lines:

    * the series is bounded by the first and last number that match a turnover
      line, so later numbers are left for the next period;
    * a number missing inside that span is counted as issued when there is a
      turnover line with no register entry to account for it, and as cancelled
      only once those are used up.
    """
    labels = {"INVOICE": "Invoices for outward supply",
              "CREDIT_NOTE": "Credit Note", "CREDIT_DISCOUNT": "Credit Note"}
    value = chunk[chunk["doc_type"].isin(VALUE_DOCS)]
    kinds = SOURCES[platform].doc_kinds(value)
    rows: List[Dict[str, Any]] = []
    for kind in ("INVOICE", "CREDIT_NOTE", "CREDIT_DISCOUNT"):
        wanted = set(value[kinds == kind]["order_id"])
        if not wanted:
            continue
        pool = docs[(docs["platform"] == platform) & (docs["kind"] == kind)]
        matched = pool[pool["order_id"].isin(wanted)]
        if not len(matched):
            rows.append({
                "platform": platform, "document": labels[kind], "series": "",
                "from": "", "to": "", "total": len(wanted), "cancelled": 0,
                "count": len(wanted), "missing": [], "missing_unexplained": [],
                "inferred_issued": 0, "after_period": 0, "numbered": False,
                "issued": True, "reference_only": False, "notes": [],
            })
            continue
        without_number = len(wanted - set(pool["order_id"]))
        series_list = sorted(matched["series"].unique())
        for series in series_list:
            ours = pool[pool["series"] == series]
            hit = matched[matched["series"] == series]
            lo, hi = int(hit["seq"].min()), int(hit["seq"].max())
            present = set(ours[(ours["seq"] >= lo) & (ours["seq"] <= hi)]["seq"])
            gaps = [i for i in range(lo, hi + 1) if i not in present]
            inferred = min(len(gaps), without_number) if len(series_list) == 1 else 0
            cancelled = len(gaps) - inferred
            later = int((ours["seq"] > hi).sum())
            notes = []
            if inferred:
                notes.append("%d missing number(s) match turnover lines that have no "
                             "register entry, so they are counted as issued" % inferred)
            if cancelled:
                notes.append("CHECK: %d missing number(s) match no turnover line and are "
                             "counted as cancelled - confirm they were never issued" % cancelled)
            if later:
                notes.append("%d later number(s) after %s fall in the next period"
                             % (later, _doc_label(hit, hi)))
            rows.append({
                "platform": platform, "document": labels[kind], "series": series,
                "from": _doc_label(hit, lo), "to": _doc_label(hit, hi),
                "total": hi - lo + 1, "cancelled": cancelled,
                "count": hi - lo + 1 - cancelled,
                "missing": ["%s%d" % (series, i) for i in gaps],
                "missing_unexplained": [],
                "inferred_issued": inferred, "after_period": later,
                "numbered": True, "issued": True, "reference_only": False,
                "notes": notes,
            })
    return rows


def _doc_label(matched: pd.DataFrame, seq: int) -> str:
    return str(matched[matched["seq"] == seq]["doc_no"].iloc[0])


def _table_13(scope: pd.DataFrame,
              documents: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Table 13 — documents issued, one row per document SERIES.

    The portal wants, for each series: first number, last number, total
    numbers in that span, how many were cancelled and the net issued. A
    marketplace can run several series at once (Flipkart runs twelve this
    quarter), and quoting one from-to across them would be wrong.

    Bill of supply has no line of its own in the portal's dropdown; it is part
    of 'Invoices for outward supply'. A number missing from a series is
    reported as cancelled; those that match a cancelled or replacement order
    in the marketplace report are marked as explained.
    """
    out: List[Dict[str, Any]] = []
    registered = (set(documents["platform"]) if documents is not None and len(documents)
                  else set())
    if len(scope):
        for platform, chunk in scope.groupby("platform"):
            if platform in registered:
                out += _register_rows(platform, chunk, documents)
                continue
            numbered = chunk[chunk["doc_no"] != ""]
            side = set(numbered[numbered["doc_type"].isin(
                (CANCELLED, REPLACEMENT))]["doc_no"])
            for doc_type, label in ((INVOICE, "Invoices for outward supply"),
                                    (CREDIT_NOTE, "Credit Note")):
                group = chunk[chunk["doc_type"] == doc_type]
                if not len(group):
                    continue
                nums = group[group["doc_no"] != ""]["doc_no"].astype(str)
                if not len(nums):
                    # Meesho's report carries no document numbers at all.
                    out.append({
                        "platform": platform, "document": label, "series": "",
                        "from": "", "to": "", "total": int(len(group)),
                        "cancelled": 0, "count": int(len(group)),
                        "missing": [], "missing_unexplained": [],
                        "numbered": False, "issued": True,
                        "reference_only": False,
                    })
                    continue
                by_series: Dict[str, set] = {}
                for n in set(nums):
                    series, seq = _split_serial(platform, n)
                    by_series.setdefault(series, set()).add(seq)
                for series in sorted(by_series):
                    seqs = sorted(by_series[series])
                    lo, hi = seqs[0], seqs[-1]
                    gaps = [_compose_serial(platform, series, i)
                            for i in range(lo, hi + 1) if i not in by_series[series]]
                    out.append({
                        "platform": platform, "document": label, "series": series,
                        "from": _compose_serial(platform, series, lo),
                        "to": _compose_serial(platform, series, hi),
                        "total": hi - lo + 1, "cancelled": len(gaps),
                        "count": len(seqs), "missing": gaps,
                        "missing_unexplained": [g for g in gaps if g not in side],
                        "numbered": True, "issued": True, "reference_only": False,
                    })
    out.sort(key=lambda r: (r["platform"], r["document"], r["series"]))
    return {
        "title": "Table 13 — Documents issued during the tax period",
        "rows": out,
        "note": "Enter one portal row per line above. 'Invoices for outward "
                "supply' covers tax invoices AND bills of supply together; "
                "'Credit Note' covers credit notes. 'Total number' is the span "
                "first-to-last and 'Cancelled' the numbers inside it with no "
                "document in the marketplace report. Meesho's report carries "
                "no document numbers, so only counts are available; take the "
                "serial range from Meesho's invoice download.",
    }


def _table_14(rows: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, Any]:
    ecos = cfg.get("ecommerce_operators", {})
    out = []
    if len(rows):
        for platform, chunk in rows.groupby("platform"):
            eco = ecos.get(platform, {})
            agg = _agg(chunk)
            taxable_only = _agg(chunk[chunk["bucket"] == rules.TAXABLE])
            tcs = float((chunk["tcs_igst"] + chunk["tcs_cgst"] + chunk["tcs_sgst"]).sum())
            out.append({
                "platform": platform,
                "eco_gstin": eco.get("gstin", ""),
                "eco_name": eco.get("label", ""),
                "net_value_all": agg["taxable"],
                "net_value_taxable": taxable_only["taxable"],
                "igst": taxable_only["igst"], "cgst": taxable_only["cgst"],
                "sgst": taxable_only["sgst"], "cess": taxable_only["cess"],
                "tcs": r2(tcs),
                "enter": taxable_only["taxable"] > 0.005,
            })
    out.sort(key=lambda r: r["platform"])
    return {
        "title": "Table 14 — Supplies made through an e-commerce operator",
        "rows": out,
        "note": "Table 14 lists supplies on which the operator collected TCS "
                "under section 52. That TCS attaches only to the net value of "
                "TAXABLE supplies, so exempt book sales are not entered here "
                "and an operator with a nil taxable column needs no row. "
                "The portal matches Table 14 against the operator's GSTR-8, "
                "so the value should agree with the TCS statement.",
    }


# ---------------------------------------------------------------------------
# GSTR-3B
# ---------------------------------------------------------------------------

def _gstr3b(taxable: pd.DataFrame, exempt: pd.DataFrame,
            nil: pd.DataFrame, nongst: pd.DataFrame) -> Dict[str, Any]:
    t = _agg(taxable)
    e = _agg(exempt)
    n = _agg(nil)
    g = _agg(nongst)
    rows = [
        {"row": "3.1(a)", "description": rules.GSTR3B_ROWS["3.1(a)"],
         "taxable": t["taxable"], "igst": t["igst"], "cgst": t["cgst"],
         "sgst": t["sgst"], "cess": t["cess"]},
        {"row": "3.1(b)", "description": rules.GSTR3B_ROWS["3.1(b)"],
         "taxable": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
        {"row": "3.1(c)", "description": rules.GSTR3B_ROWS["3.1(c)"],
         "taxable": r2(e["taxable"] + n["taxable"]), "igst": 0.0, "cgst": 0.0,
         "sgst": 0.0, "cess": 0.0},
        {"row": "3.1(d)", "description": rules.GSTR3B_ROWS["3.1(d)"],
         "taxable": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
        {"row": "3.1(e)", "description": rules.GSTR3B_ROWS["3.1(e)"],
         "taxable": g["taxable"], "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0},
    ]
    return {
        "title": "GSTR-3B Table 3.1 — Details of outward supplies and inward supplies liable to reverse charge",
        "rows": rows,
        "tax_payable": {
            "igst": t["igst"], "cgst": t["cgst"], "sgst": t["sgst"], "cess": t["cess"],
            "total": r2(t["igst"] + t["cgst"] + t["sgst"] + t["cess"]),
        },
        "note": "3.1(c) is a value-only box — no tax is entered against it. "
                "The exempt turnover is reported here and nowhere else in 3.1.",
    }


def _gstr3b_32(taxable: pd.DataFrame) -> Dict[str, Any]:
    rows = []
    if len(taxable):
        sel = taxable[_is_b2c(taxable) & (taxable["supply_type"] == "INTER")]
        for (code, state), chunk in sel.groupby(["pos_code", "pos_state"]):
            agg = _agg(chunk)
            rows.append({"pos_code": code, "pos_state": state,
                         "taxable": agg["taxable"], "igst": agg["igst"]})
    rows.sort(key=lambda r: r["pos_code"])
    return {
        "title": "GSTR-3B Table 3.2 — " + rules.GSTR3B_ROWS["3.2"],
        "rows": rows,
        "note": "CRITICAL: 3.2 is scoped by the form to supplies shown in "
                "3.1(a), 3.1(b) and 3.1.1(i) — TAXABLE supplies only. Exempt "
                "book sales must NOT be repeated here even though they are "
                "inter-State sales to unregistered persons. This is the single "
                "most common filing error for exempt e-commerce sellers. "
                "Note also that 3.2 is auto-populated from GSTR-1 and is "
                "hard-locked on the portal, so it must agree with Table 7.",
    }


# ---------------------------------------------------------------------------
# TCS and ITC
# ---------------------------------------------------------------------------

def _tcs(rows: pd.DataFrame, taxable: pd.DataFrame, cfg: Dict[str, Any]) -> Dict[str, Any]:
    ecos = cfg.get("ecommerce_operators", {})
    out = []
    if len(rows):
        for platform, chunk in rows.groupby("platform"):
            tax_chunk = taxable[taxable["platform"] == platform] if len(taxable) else taxable
            net_taxable = _agg(tax_chunk)["taxable"]
            collected = r2(chunk[["tcs_igst", "tcs_cgst", "tcs_sgst"]].sum().sum())
            expected = r2(net_taxable * rules.TCS_RATE_CURRENT)
            out.append({
                "platform": platform,
                "eco_gstin": ecos.get(platform, {}).get("gstin", ""),
                "net_taxable_supplies": net_taxable,
                "net_exempt_supplies": _agg(chunk[chunk["bucket"] != rules.TAXABLE])["taxable"],
                "tcs_collected": collected,
                "tcs_expected": expected,
                "variance": r2(collected - expected),
                "tcs_igst": r2(chunk["tcs_igst"].sum()),
                "tcs_cgst": r2(chunk["tcs_cgst"].sum()),
                "tcs_sgst": r2(chunk["tcs_sgst"].sum()),
            })
    out.sort(key=lambda r: r["platform"])
    total = r2(sum(r["tcs_collected"] for r in out))
    return {
        "title": "TCS under section 52 — reconciliation against the operators' GSTR-8",
        "rows": out,
        "total_collected": total,
        "rate": rules.TCS_RATE_CURRENT,
        "citation": rules.TCS_CITATION,
        "note": "TCS is charged on the net value of TAXABLE supplies only, so an "
                "exempt-only month should show zero. Whatever is collected "
                "appears under 'TDS and TCS Credit received' on the portal; "
                "accept it there and it lands in your electronic CASH ledger "
                "(not the credit ledger). File that acceptance every period even "
                "when the amount is nil, otherwise the credit never moves.",
    }


def _itc_guidance(rows: pd.DataFrame, exempt: pd.DataFrame, nil: pd.DataFrame) -> Dict[str, Any]:
    total = _agg(rows)["taxable"]
    exempt_value = r2(_agg(exempt)["taxable"] + _agg(nil)["taxable"])
    share = r2((exempt_value / total * 100) if total else 0.0)
    return {
        "title": "GSTR-3B Table 4 — Input Tax Credit",
        "exempt_turnover": exempt_value,
        "total_turnover": total,
        "exempt_share_pct": share,
        "rows": [
            {"row": "4(A)(5)", "description": "All other ITC", "amount": None},
            {"row": "4(B)(1)", "description": "ITC reversed — rule 42 & 43", "amount": None},
            {"row": "4(B)(2)", "description": "ITC reversed — others", "amount": None},
        ],
        "guidance": [
            "Section 17(2) blocks input tax credit to the extent it is "
            "attributable to exempt supplies. With %.2f%% of turnover exempt, "
            "effectively none of your input GST is creditable." % share,
            "Marketplace commission, shipping, closing and advertising "
            "invoices all carry 18% GST. That GST is a COST for you, not a "
            "credit — book it to expenses in the P&L rather than to a tax "
            "asset. This is why the exempt-vs-nil-rated distinction matters.",
            "If you claim nothing, rule 42 apportionment does not arise and "
            "4(B)(1) stays blank. If you ever do claim common-credit ITC, it "
            "must be apportioned monthly under rule 42 and trued up by "
            "September of the following financial year.",
            "Table 5 of GSTR-3B (values of exempt, nil rated and non-GST "
            "INWARD supplies) is about purchases, not sales — do not put your "
            "book turnover there.",
        ],
        "note": "Supply your purchase register and this table can be computed "
                "instead of merely explained.",
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _add(out: List[Dict[str, Any]], severity: str, code: str, message: str,
         detail: Optional[Any] = None) -> None:
    out.append({"severity": severity, "code": code, "message": message,
                "detail": detail if detail is not None else ""})


def _validate(scope: pd.DataFrame, seller: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if scope is None or len(scope) == 0:
        _add(out, "error", "no-data", "No GST report rows were found for this period.")
        return out

    value_rows = scope[scope["doc_type"].isin(VALUE_DOCS)]

    # 1. Invoice value identity: taxable + tax must equal the source's own total.
    if "_invoice_amount" in scope.columns:
        tax = scope["igst"] + scope["cgst"] + scope["sgst"] + scope["cess"]
        diff = (scope["_invoice_amount"] - (scope["taxable_value"] + tax)).abs()
        bad = scope[diff > MONEY_TOLERANCE]
        if len(bad):
            _add(out, "error", "invoice-identity",
                 "%d line(s) where invoice value != taxable value + tax. The "
                 "source file is internally inconsistent; do not file until "
                 "resolved." % len(bad),
                 bad[["platform", "source_file", "doc_no", "order_id",
                      "taxable_value", "_invoice_amount"]].head(20).to_dict("records"))

    # 2. Tax charged on a line whose HSN is exempt — money collected from the
    #    customer that must still reach the Government (section 76).
    if len(value_rows):
        charged = value_rows[(value_rows["igst"].abs() + value_rows["cgst"].abs()
                              + value_rows["sgst"].abs()) > 0.005]
        wrong = []
        for _, row in charged.iterrows():
            bucket, _desc, _cite = rules.classify_hsn(row["hsn"])
            if bucket == rules.EXEMPT:
                wrong.append({
                    "platform": row["platform"], "doc_no": row["doc_no"],
                    "order_id": row["order_id"], "sku": row["sku"],
                    "hsn": row["hsn"], "pos_state": row["pos_state"],
                    "taxable": r2(row["taxable_value"]),
                    "tax": r2(row["igst"] + row["cgst"] + row["sgst"]),
                    "rate_pct": r2(row["rate"] * 100),
                })
        if wrong:
            _add(out, "error", "tax-on-exempt",
                 "%d line(s) carry GST on an HSN that is exempt under Notfn. "
                 "2/2017-CT(R). The marketplace's tax code is misconfigured. "
                 "The tax WAS collected from the customer, so section 76 "
                 "requires it to be paid to the Government — report these as "
                 "taxable B2C supplies, pay the tax, and separately ask the "
                 "operator to fix the product tax code." % len(wrong), wrong)

    # 3. TCS collected against exempt supplies.
    if len(value_rows):
        tcs_total = value_rows[["tcs_igst", "tcs_cgst", "tcs_sgst"]].sum(axis=1)
        bad = value_rows[(tcs_total.abs() > 0.005) & (value_rows["bucket"] != rules.TAXABLE)]
        if len(bad):
            _add(out, "warning", "tcs-on-exempt",
                 "%d exempt line(s) show TCS. Section 52(1) charges TCS on the "
                 "net value of taxable supplies only — query the operator."
                 % len(bad),
                 bad[["platform", "doc_no", "order_id", "tcs_igst", "tcs_cgst",
                      "tcs_sgst"]].head(20).to_dict("records"))

    # 4. Rate sanity.
    if len(value_rows):
        valid = set(rules.VALID_GST_RATES)
        legacy = set(rules.LEGACY_GST_RATES)
        seen = {round(float(r), 4) for r in value_rows["rate"]}
        unknown = sorted(r for r in seen if r not in valid and r not in legacy)
        if unknown:
            _add(out, "error", "unknown-rate",
                 "Rate(s) outside the statutory slabs: %s"
                 % ", ".join("%.2f%%" % (r * 100) for r in unknown))
        used_legacy = sorted(r for r in seen if r in legacy)
        if used_legacy:
            _add(out, "warning", "legacy-rate",
                 "Pre-rationalisation slab(s) present: %s. The 12%% and 28%% "
                 "slabs were withdrawn on %s — confirm these are amendments to "
                 "older invoices."
                 % (", ".join("%.0f%%" % (r * 100) for r in used_legacy),
                    rules.RATE_RATIONALISATION_DATE))

    # 5. Declared rate vs tax actually charged.
    if len(value_rows):
        tax = value_rows["igst"] + value_rows["cgst"] + value_rows["sgst"]
        expected = value_rows["taxable_value"] * value_rows["rate"]
        bad = value_rows[(tax - expected).abs() > 1.0]
        if len(bad):
            _add(out, "warning", "rate-tax-mismatch",
                 "%d line(s) where the tax charged does not match rate x taxable "
                 "value (tolerance Re 1 for rounding)." % len(bad),
                 bad[["platform", "doc_no", "order_id", "rate", "taxable_value"]]
                 .head(20).to_dict("records"))

    # 6. Intra-State line carrying IGST, or inter-State carrying CGST/SGST.
    if len(value_rows):
        wrong_head = value_rows[
            ((value_rows["supply_type"] == "INTRA") & (value_rows["igst"].abs() > 0.005))
            | ((value_rows["supply_type"] == "INTER")
               & ((value_rows["cgst"].abs() + value_rows["sgst"].abs()) > 0.005))
        ]
        if len(wrong_head):
            _add(out, "error", "wrong-tax-head",
                 "%d line(s) use the wrong tax head for the place of supply "
                 "(IGST on an intra-State supply or CGST/SGST on an "
                 "inter-State supply)." % len(wrong_head),
                 wrong_head[["platform", "doc_no", "pos_state", "supply_type",
                             "igst", "cgst", "sgst"]].head(20).to_dict("records"))

    # 7. Missing HSN on a line that carries value.
    if len(value_rows):
        missing = value_rows[value_rows["hsn"].astype(str).str.replace(r"\D", "", regex=True) == ""]
        missing = missing[missing["taxable_value"].abs() > 0.005]
        if len(missing):
            _add(out, "error", "hsn-missing",
                 "%d value-carrying line(s) have no HSN, so they cannot be "
                 "classified or placed in Table 12." % len(missing),
                 missing[["platform", "source_file", "doc_no", "order_id",
                          "taxable_value"]].head(20).to_dict("records"))

    # 8. Unmappable place of supply.
    unknown_pos = scope[(scope["pos_code"] == "") & (scope["taxable_value"].abs() > 0.005)]
    if len(unknown_pos):
        names = sorted({s for s in unknown_pos["pos_state"]})
        _add(out, "error", "pos-unmapped",
             "Place of supply could not be mapped to a State code for %d line(s): %s. "
             "Add the spelling to rules.STATE_ALIASES." % (len(unknown_pos), ", ".join(names)))

    # 9. Same SKU treated inconsistently — the signature of a marketplace tax
    #    code misconfiguration.
    if len(value_rows):
        skued = value_rows[value_rows["sku"].astype(str).str.len() > 0]
        for sku, chunk in skued.groupby("sku"):
            buckets = sorted(set(chunk["bucket"]))
            if len(buckets) > 1:
                _add(out, "error", "sku-inconsistent-bucket",
                     "SKU %s is treated as %s across different lines in the same "
                     "period. One of them is wrong." % (sku, " and ".join(buckets)),
                     chunk[chunk["bucket"] == rules.TAXABLE][
                         ["platform", "doc_no", "order_id", "hsn", "rate",
                          "taxable_value"]].head(10).to_dict("records"))
            hsns = sorted({h[:4] for h in chunk["hsn"].astype(str) if h})
            if len(hsns) > 1:
                _add(out, "warning", "sku-inconsistent-hsn",
                     "SKU %s is reported under more than one HSN heading: %s."
                     % (sku, ", ".join(hsns)))

    # 10. Seller GSTIN consistency.
    declared = str(seller.get("gstin", "") or "").strip().upper()
    found = sorted({g for g in scope["seller_gstin"].astype(str) if g})
    if declared and found and [g.upper() for g in found] != [declared]:
        _add(out, "error", "gstin-mismatch",
             "Report rows carry seller GSTIN %s but the configured GSTIN is %s."
             % (", ".join(found), declared))
    if len(found) > 1:
        _add(out, "error", "gstin-multiple",
             "More than one seller GSTIN appears: %s. Each registration files "
             "its own return." % ", ".join(found))

    # 11. Document date outside the claimed period.
    stray = scope[scope["doc_date"].notna()]
    if len(stray):
        drift = stray[stray["doc_date"].dt.strftime("%Y-%m") != stray["period"]]
        if len(drift):
            _add(out, "warning", "period-drift",
                 "%d line(s) have a document date outside the tax period they "
                 "are reported in. Expected for Meesho, whose GST report is "
                 "keyed to its own filing month; investigate for other sources."
                 % len(drift),
                 drift.groupby("platform").size().to_dict())

    # 12. A cancelled order whose document still carries POSITIVE net value
    #     means the sale was counted and never reversed. A negative net is the
    #     credit note doing its job, so only a positive residue is a problem.
    cancelled = scope[(scope["doc_type"] == CANCELLED) & (scope["doc_no"] != "")]
    if len(cancelled) and len(value_rows):
        valued = value_rows[value_rows["taxable_value"].abs() > 0.005]
        net_by_doc = valued.groupby(["platform", "doc_no"])["taxable_value"].sum()
        stranded = []
        for platform, doc_no in sorted(set(zip(cancelled["platform"], cancelled["doc_no"]))):
            net = float(net_by_doc.get((platform, doc_no), 0.0))
            if net > 0.005:
                stranded.append({"platform": platform, "doc_no": doc_no,
                                 "net_value_still_counted": r2(net)})
        if stranded:
            _add(out, "error", "cancelled-but-counted",
                 "%d cancelled document(s) still carry a positive net value in "
                 "the turnover tables. The sale was counted but never reversed, "
                 "so turnover is overstated by that amount." % len(stranded),
                 stranded)

    return out


# ---------------------------------------------------------------------------
# Filing calendar
# ---------------------------------------------------------------------------

def _filing_calendar(periods: Sequence[str], filing: Dict[str, Any],
                     seller: Dict[str, Any]) -> Dict[str, Any]:
    frequency = str(filing.get("frequency", "monthly")).lower()
    state = str(seller.get("state", "") or "")
    day = rules.qrmp_3b_due_day(state)
    if not periods:
        return {"frequency": frequency, "due": []}
    last = periods[-1]
    year, month = (int(x) for x in last.split("-"))
    nxt_month = 1 if month == 12 else month + 1
    nxt_year = year + 1 if month == 12 else year
    due = []
    if frequency == "qrmp":
        due.append({"form": "GSTR-1 (quarterly)",
                    "due": "%04d-%02d-13" % (nxt_year, nxt_month),
                    "rule": rules.DUE_DATES["qrmp_gstr1"]})
        due.append({"form": "GSTR-3B (quarterly)",
                    "due": "%04d-%02d-%02d" % (nxt_year, nxt_month, day),
                    "rule": rules.DUE_DATES["qrmp_gstr3b_22" if day == 22 else "qrmp_gstr3b_24"]})
        due.append({"form": "IFF (optional, months 1-2 of the quarter)",
                    "due": "13th of the following month",
                    "rule": rules.DUE_DATES["qrmp_iff"]})
    else:
        due.append({"form": "GSTR-1", "due": "%04d-%02d-11" % (nxt_year, nxt_month),
                    "rule": rules.DUE_DATES["monthly_gstr1"]})
        due.append({"form": "GSTR-3B", "due": "%04d-%02d-20" % (nxt_year, nxt_month),
                    "rule": rules.DUE_DATES["monthly_gstr3b"]})
    return {
        "frequency": frequency,
        "state": state,
        "qrmp_group_day": day,
        "due": due,
        "time_bar": rules.THREE_YEAR_BAR_NOTE,
    }
