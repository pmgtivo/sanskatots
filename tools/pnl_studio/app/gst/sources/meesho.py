"""Meesho — GST / TCS reports.

Download: Supplier Panel -> Payments -> GST Report. Each month arrives as a
folder ``gst_<supplier_id>_<month>_<year>/`` holding two workbooks:

* ``tcs_sales.xlsx``        — supplies made in the month
* ``tcs_sales_return.xlsx`` — returns and cancellations in the month

Two quirks of this export drive the code below:

1. ``tcs_sales.xlsx`` also contains zero-quantity rows with a *negative* value.
   They are post-sale discount adjustments for which Meesho issues a credit
   note (series ``...CM<n>``, type CREDIT_DISCOUNT), so they are loaded as
   credit notes. The month nets the same either way; the classification
   matters for the document counts in Table 13.
2. The return workbook states values as **positive**. They are supplies being
   reversed, so the adapter negates them to match the canonical sign rule.

Meesho gives no invoice number and no invoice date, only ``month_number`` /
``financial_year`` — which is precisely the tax period Meesho itself reports in
its GSTR-8. The period is therefore taken from those fields rather than from a
date, so the figures reconcile against the operator's filing.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .. import rules
from .base import CREDIT_NOTE, INVOICE, GstSource, finalise

_SALES_MARKERS = ("sub_order_num", "total_taxable_sale_value", "hsn_code")
_RETURN_MARKER = "cancel_return_date"


def _period(month_number: pd.Series, reference: pd.Series) -> pd.Series:
    """Combine Meesho's filing month with the year implied by a row date.

    ``month_number`` is authoritative but carries no year, and Meesho's
    ``financial_year`` column is ambiguous across the January boundary. The year
    is therefore taken from a date on the same row and nudged by a year when the
    two are more than six months apart, which resolves the Dec/Jan rollover.
    """
    out = []
    for month, ref in zip(month_number, reference):
        try:
            month = int(month)
        except (TypeError, ValueError):
            month = 0
        if not 1 <= month <= 12 or pd.isna(ref):
            out.append("")
            continue
        year = int(ref.year)
        if month - int(ref.month) > 6:
            year -= 1
        elif int(ref.month) - month > 6:
            year += 1
        out.append("%04d-%02d" % (year, month))
    return pd.Series(out, index=month_number.index)


class MeeshoGstSource(GstSource):
    key = "meesho"
    label = "Meesho"
    implemented = True
    export_hint = (
        "Supplier Panel -> Payments -> GST Report. Keep both tcs_sales.xlsx and "
        "tcs_sales_return.xlsx from each monthly folder."
    )

    def matches(self, path: str) -> bool:
        if not path.lower().endswith((".xlsx", ".xls")):
            return False
        cols = self._columns_of_excel(path)
        return all(marker in cols for marker in _SALES_MARKERS)

    def doc_kinds(self, frame: pd.DataFrame) -> pd.Series:
        kinds = frame["doc_type"].copy()
        discount = (frame["doc_type"] == CREDIT_NOTE) & (frame["quantity"].abs() < 0.005)
        return kinds.where(~discount, "CREDIT_DISCOUNT")

    def load(self, path: str) -> pd.DataFrame:
        raw = pd.read_excel(path)
        if raw.empty:
            return finalise(raw)
        raw.columns = [str(c).strip().lower() for c in raw.columns]

        is_return = _RETURN_MARKER in raw.columns
        sign = -1.0 if is_return else 1.0

        taxable = self._num(raw["total_taxable_sale_value"]) * sign
        tax_total = self._num(raw.get("tax_amount", 0)) * sign
        shipping = self._num(raw.get("taxable_shipping", 0)) * sign
        qty = self._num(raw.get("quantity", 0)) * sign

        # Meesho reports the rate as a percentage; normalise to a fraction.
        rate = self._num(raw.get("gst_rate", 0))
        rate = rate.where(rate <= 1.0, rate / 100.0)

        seller_gstin = raw.get("gstin", pd.Series([""] * len(raw))).astype(str)
        seller_code = seller_gstin.map(rules.state_code_of_gstin)
        pos_code = raw.get(
            "end_customer_state_new", pd.Series([""] * len(raw))
        ).astype(str).map(lambda s: rules.normalise_state(s)[1])

        # Meesho gives one combined tax figure. Split it the way the law
        # requires: CGST+SGST within the seller's State, IGST outside it.
        intra = [bool(p) and bool(s) and p == s for p, s in zip(pos_code, seller_code)]
        intra = pd.Series(intra, index=raw.index)
        half = tax_total / 2.0
        cgst = half.where(intra, 0.0)
        sgst = half.where(intra, 0.0)
        igst = tax_total.where(~intra, 0.0)

        reference = pd.to_datetime(
            raw.get(_RETURN_MARKER) if is_return else raw.get("manifest_date"),
            errors="coerce",
        )
        order_date = pd.to_datetime(raw.get("order_date"), errors="coerce")
        reference = reference.fillna(order_date)
        month_number = raw.get("month_number", pd.Series([0] * len(raw)))

        adjustment = (~is_return) & (qty.abs() < 0.005) & (taxable < -0.005)
        doc_type = pd.Series(CREDIT_NOTE if is_return else INVOICE, index=raw.index)
        doc_type = doc_type.where(~adjustment, CREDIT_NOTE)

        out = pd.DataFrame({
            "platform": self.key,
            "source_file": self._name(path),
            "doc_type": doc_type,
            "doc_no": "",
            "doc_date": reference,
            "period": _period(month_number, reference),
            "order_id": raw.get("sub_order_num", "").astype(str),
            "order_date": order_date,
            "sku": "",
            "hsn": raw.get("hsn_code", "").astype(str),
            "description": "",
            "quantity": qty,
            "taxable_value": taxable,
            "igst": igst, "cgst": cgst, "sgst": sgst, "cess": 0.0,
            "rate": rate,
            "pos_state": raw.get("end_customer_state_new", "").astype(str),
            "seller_gstin": seller_gstin,
            "buyer_gstin": "",
            "shipping_value": shipping,
        })

        out["_invoice_amount"] = self._num(raw.get("total_invoice_value", 0)) * sign
        out["_total_tax"] = tax_total

        result = finalise(out)
        result["_invoice_amount"] = out["_invoice_amount"].values
        result["_total_tax"] = out["_total_tax"].values
        return result
