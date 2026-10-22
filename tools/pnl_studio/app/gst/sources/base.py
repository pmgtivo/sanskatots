"""Canonical GST line schema that every marketplace adapter must produce.

One row = one document line (an invoice line, or a credit-note line). Signs are
carried on the values themselves: an invoice line is positive, a credit note is
negative. Downstream code therefore never needs to know which marketplace a row
came from, and netting a return against a sale is a plain ``sum()``.

Adding a marketplace means: subclass :class:`GstSource`, emit these columns, and
register the class in ``sources/__init__.py``. Nothing else changes.
"""

from __future__ import annotations

import hashlib
import os
from typing import List, Optional

import pandas as pd

from .. import rules

# Document types.
INVOICE = "INVOICE"            # a supply was made — counts towards turnover
CREDIT_NOTE = "CREDIT_NOTE"    # return / refund — reduces turnover (negative)
CANCELLED = "CANCELLED"        # order killed before invoicing — zero value
REPLACEMENT = "REPLACEMENT"    # free replacement — zero consideration

#: Only these document types move money for GST purposes.
VALUE_DOCS = (INVOICE, CREDIT_NOTE)

INTER = "INTER"
INTRA = "INTRA"

COLUMNS = [
    "platform",        # amazon | flipkart | meesho
    "source_file",     # file the row came from, for audit trail
    "doc_type",        # one of the constants above
    "doc_no",          # invoice / credit-note number ("" when not supplied)
    "doc_date",        # datetime64 — the date that decides the tax period
    "period",          # YYYY-MM, derived from doc_date (or from the file for Meesho)
    "order_id",
    "order_date",
    "sku",
    "hsn",
    "description",
    "quantity",        # signed
    "taxable_value",   # signed, excludes tax
    "igst", "cgst", "sgst", "cess",   # signed
    "rate",            # fraction, e.g. 0.18
    "pos_state",       # canonical place-of-supply state name
    "pos_code",        # two-digit state code
    "supply_type",     # INTER | INTRA
    "seller_gstin",
    "seller_state",
    "buyer_gstin",     # "" for B2C — all rows here are B2C unless a GSTIN appears
    "tcs_igst", "tcs_cgst", "tcs_sgst",
    "shipping_value",  # informational; already inside taxable_value
    "bucket",          # TAXABLE | EXEMPT | NIL_RATED | NON_GST
]

NUMERIC = [
    "quantity", "taxable_value", "igst", "cgst", "sgst", "cess", "rate",
    "tcs_igst", "tcs_cgst", "tcs_sgst", "shipping_value",
]

TEXT = [
    "platform", "source_file", "doc_type", "doc_no", "period", "order_id",
    "sku", "hsn", "description", "pos_state", "pos_code", "supply_type",
    "seller_gstin", "seller_state", "buyer_gstin", "bucket",
]


def empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def finalise(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a partially-filled frame into the canonical schema.

    Also derives anything the adapter chose not to compute itself: the supply
    type, the state code, the exemption bucket and the period.
    """
    if df is None or len(df) == 0:
        return empty()
    df = df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if col in NUMERIC else ""
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    for col in TEXT:
        df[col] = df[col].astype(str).replace({"nan": "", "None": "", "NaT": ""}).str.strip()
    df["doc_date"] = pd.to_datetime(df["doc_date"], errors="coerce")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # Period: trust an adapter that set it explicitly (Meesho reports by the
    # month it files for), otherwise derive from the document date.
    derived = df["doc_date"].dt.strftime("%Y-%m").fillna("")
    df["period"] = df["period"].where(df["period"].str.len() == 7, derived)

    # Place of supply.
    normalised = df["pos_state"].map(rules.normalise_state)
    df["pos_state"] = [n for n, _ in normalised]
    df["pos_code"] = [c for _, c in normalised]

    seller_code = df["seller_gstin"].map(rules.state_code_of_gstin)
    df["seller_state"] = [rules.CODE_TO_STATE.get(c, "") for c in seller_code]
    df["supply_type"] = [
        INTRA if (pc and sc and pc == sc) else INTER
        for pc, sc in zip(df["pos_code"], seller_code)
    ]

    # Exemption bucket: derived from HSN, then cross-checked against the tax the
    # marketplace actually charged. Tax actually charged wins, because that is
    # the money that changed hands and that is what must be reported.
    buckets = []
    for hsn, taxable, tax in zip(
        df["hsn"], df["taxable_value"],
        df["igst"] + df["cgst"] + df["sgst"] + df["cess"],
    ):
        bucket, _, _ = rules.classify_hsn(hsn)
        if abs(tax) > 0.005:
            bucket = rules.TAXABLE
        buckets.append(bucket)
    df["bucket"] = buckets

    return df[COLUMNS]


def file_digest(path: str) -> str:
    """SHA-1 of the file contents, used to collapse byte-identical copies."""
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class GstSource:
    """Base class for a marketplace GST-report adapter."""

    key = ""
    label = ""
    implemented = False
    #: Human description of which export to download from the seller panel.
    export_hint = ""

    def matches(self, path: str) -> bool:
        """True when this adapter recognises the file (by content, not path)."""
        raise NotImplementedError

    def load(self, path: str) -> pd.DataFrame:
        """Parse the file into the canonical schema."""
        raise NotImplementedError

    def notes(self, path: str) -> List[str]:
        """Caveats about this particular file, surfaced in the filing pack."""
        return []

    def doc_kinds(self, frame: pd.DataFrame) -> pd.Series:
        """Class of each line when matching against a document-number register."""
        return frame["doc_type"]

    # -- helpers shared by adapters -------------------------------------

    @staticmethod
    def _name(path: str) -> str:
        return os.path.basename(path)

    @staticmethod
    def _read_csv_head(path: str, n: int = 2048) -> str:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                return fh.read(n)
        except OSError:
            return ""

    @staticmethod
    def _columns_of_excel(path: str) -> List[str]:
        try:
            frame = pd.read_excel(path, nrows=0)
        except Exception:
            return []
        return [str(c).strip().lower() for c in frame.columns]

    @staticmethod
    def _num(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce").fillna(0.0)

    @staticmethod
    def _first_present(df: pd.DataFrame, *names: str) -> Optional[pd.Series]:
        for name in names:
            if name in df.columns:
                return df[name]
        return None
