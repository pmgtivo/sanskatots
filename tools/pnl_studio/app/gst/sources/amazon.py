"""Amazon — Merchant Tax Report (MTR), B2C and B2B variants.

Download: Seller Central -> Reports -> Tax Document Library -> Merchant Tax
Report (B2C). One CSV per month. The B2B variant carries the same columns plus
the customer's GSTIN, so both load through this adapter.

Sign convention in the source: ``Refund`` rows already carry a negative
``Tax Exclusive Gross`` / ``Invoice Amount``, so the sign is preserved rather
than re-derived. ``Cancel`` rows are all-zero (no invoice was ever raised) and
``FreeReplacement`` rows are zero-consideration; both are kept as
non-value documents so they can be counted in the reconciliation section but
never reach the turnover tables.
"""

from __future__ import annotations

import pandas as pd

from .base import CANCELLED, CREDIT_NOTE, INVOICE, REPLACEMENT, GstSource, finalise

#: Amazon transaction type -> canonical document type.
DOC_TYPE_MAP = {
    "shipment": INVOICE,
    "shipment item": INVOICE,
    "refund": CREDIT_NOTE,
    "return": CREDIT_NOTE,
    "cancel": CANCELLED,
    "freereplacement": REPLACEMENT,
    "free replacement": REPLACEMENT,
    "replacement": REPLACEMENT,
}

_REQUIRED = ("seller gstin", "transaction type", "tax exclusive gross")


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Case-insensitive column fetch; zeros/blanks when Amazon omits a column."""
    lowered = {str(c).strip().lower(): c for c in df.columns}
    key = lowered.get(name.strip().lower())
    if key is None:
        return pd.Series([""] * len(df), index=df.index)
    return df[key]


def _n(df: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(_col(df, name), errors="coerce").fillna(0.0)


class AmazonGstSource(GstSource):
    key = "amazon"
    label = "Amazon"
    implemented = True
    export_hint = (
        "Seller Central -> Reports -> Tax Document Library -> "
        "Merchant Tax Report B2C (and B2B if you have GSTIN buyers), monthly CSV."
    )

    def matches(self, path: str) -> bool:
        if not path.lower().endswith(".csv"):
            return False
        head = self._read_csv_head(path).lower()
        return all(token in head for token in _REQUIRED)

    def load(self, path: str) -> pd.DataFrame:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
        if raw.empty:
            return finalise(raw)

        txn = _col(raw, "transaction type").astype(str).str.strip().str.lower()
        doc_type = txn.map(DOC_TYPE_MAP).fillna(INVOICE)

        is_credit = doc_type == CREDIT_NOTE

        # Tax components: principal + shipping + gift wrap, each of which Amazon
        # splits across its own columns.
        igst = (_n(raw, "igst tax") + _n(raw, "shipping igst tax")
                + _n(raw, "gift wrap igst tax"))
        cgst = (_n(raw, "cgst tax") + _n(raw, "shipping cgst tax")
                + _n(raw, "gift wrap cgst tax"))
        sgst = (_n(raw, "sgst tax") + _n(raw, "utgst tax")
                + _n(raw, "shipping sgst tax") + _n(raw, "shipping utgst tax")
                + _n(raw, "gift wrap sgst tax") + _n(raw, "gift wrap utgst tax"))
        cess = (_n(raw, "compensatory cess tax") + _n(raw, "shipping cess tax amount")
                + _n(raw, "gift wrap compensatory cess tax"))

        # `Tax Exclusive Gross` is Amazon's own net-of-promotions, net-of-tax
        # figure and already carries the right sign on refunds.
        taxable = _n(raw, "tax exclusive gross")

        rate = _n(raw, "igst rate") + _n(raw, "cgst rate") + _n(raw, "sgst rate") + _n(raw, "utgst rate")

        qty = _n(raw, "quantity").abs()
        qty = qty.where(~is_credit, -qty)

        invoice_date = pd.to_datetime(_col(raw, "invoice date"), errors="coerce")
        credit_date = pd.to_datetime(_col(raw, "credit note date"), errors="coerce")
        doc_date = invoice_date.where(~is_credit, credit_date.fillna(invoice_date))

        invoice_no = _col(raw, "invoice number").astype(str)
        credit_no = _col(raw, "credit note no").astype(str)
        doc_no = invoice_no.where(~is_credit, credit_no)

        out = pd.DataFrame({
            "platform": self.key,
            "source_file": self._name(path),
            "doc_type": doc_type,
            "doc_no": doc_no,
            "doc_date": doc_date,
            "order_id": _col(raw, "order id").astype(str),
            "order_date": pd.to_datetime(_col(raw, "order date"), errors="coerce"),
            "sku": _col(raw, "sku").astype(str),
            "hsn": _col(raw, "hsn/sac").astype(str),
            "description": _col(raw, "item description").astype(str),
            "quantity": qty,
            "taxable_value": taxable,
            "igst": igst, "cgst": cgst, "sgst": sgst, "cess": cess,
            "rate": rate,
            "pos_state": _col(raw, "ship to state").astype(str),
            "seller_gstin": _col(raw, "seller gstin").astype(str),
            "buyer_gstin": _col(raw, "customer bill to gstid").astype(str),
            "tcs_igst": _n(raw, "tcs igst amount"),
            "tcs_cgst": _n(raw, "tcs cgst amount"),
            "tcs_sgst": _n(raw, "tcs sgst amount") + _n(raw, "tcs utgst amount"),
            "shipping_value": _n(raw, "shipping amount"),
        })

        # Amazon's own control total, carried through so the engine can prove
        # that invoice value == taxable + tax on every single line.
        out["_invoice_amount"] = _n(raw, "invoice amount")
        out["_total_tax"] = _n(raw, "total tax amount")

        result = finalise(out)
        result["_invoice_amount"] = out["_invoice_amount"].values
        result["_total_tax"] = out["_total_tax"].values
        return result
