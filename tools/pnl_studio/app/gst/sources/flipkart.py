"""Flipkart — monthly "Sales Report" workbook (transaction level).

This is the report a seller actually gets from the Flipkart seller panel. Per
Flipkart's own Help sheet it "contains each and every b2c invoice which was
created, returned, cancelled or voided in the duration of the month", so the
``Sales Report`` sheet alone covers every outward rupee for the period.

Sheets:

    Help              free text, ignored
    Sales Report      one row per order item event — the value-bearing sheet
    Cash Back Report  credit/debit notes raised BY FLIPKART TO THE SELLER to
                      reimburse bank-funded offers — deliberately NOT loaded

Why the Cash Back sheet is excluded from turnover
-------------------------------------------------
Flipkart documents it as "cash back credit/debit notes created from Flipkart to
Sellers ... where offer burn is by the bank". Those are *inward* documents: the
bank, through Flipkart, reimburses the seller for a discount already deducted
on the customer's invoice. The Sales Report taxable value is net of that
discount (``Price before discount`` less ``Seller Share`` and
``Bank Offer Share``), so adding the cash-back notes would both double-count the
offer and misreport a reimbursement as an outward supply. The adapter instead
attaches a note recording how many such documents exist and their net value.

Sign convention
---------------
Flipkart pre-signs the taxable value: sales are positive, returns and
cancellations negative, and a "Return Cancellation" (a revoked return) is
positive again. The document type is therefore taken from the sign of the
value, not from the event label — that is what actually moves turnover, and it
means a new event name Flipkart invents later still nets correctly.

Tax period
----------
``Buyer Invoice Date`` always falls inside the month the file is for, while
``Order Date`` routinely spills into the previous month. The period is pinned
to the modal invoice month of the file, matching the rule that a credit note is
declared in the period it is issued. Any row dated outside that month is
counted and reported in the notes rather than silently refiled.

Download: Seller Hub -> Reports -> GST Reports -> Sales Report, one per month.
"""

from __future__ import annotations

import re
from typing import List, Set

import pandas as pd

from .base import CANCELLED, CREDIT_NOTE, INVOICE, GstSource, finalise

SHEET_SALES = "sales report"
SHEET_CASHBACK = "cash back report"

#: Sheet names of the *other* Flipkart GST workbook (pre-aggregated GSTR-1 /
#: GSTR-8 sections). Loading both reports for one month would double the
#: turnover, so that file is rejected with an explanation instead.
_AGGREGATED_SIGNATURE = {
    "section 5b in gstr-1",
    "section 7(a)(2) in gstr-1",
    "section 7(b)(2) in gstr-1",
    "section 12 in gstr-1",
    "section 3 in gstr-8",
}


def _key(name: object) -> str:
    """Normalise a header — Flipkart embeds newlines and long parentheticals."""
    s = re.sub(r"\s+", " ", str(name).replace("\n", " ")).strip().lower()
    return re.sub(r"\s*/\s*", "/", s)


def _clean(series: pd.Series) -> pd.Series:
    """Strip Flipkart's triple-quote wrapping and its "NA" sentinels."""
    out = series.astype(str).str.strip().str.strip('"').str.strip()
    return out.replace({"nan": "", "None": "", "NaT": "", "NA": "", "na": ""})


class FlipkartGstSource(GstSource):
    key = "flipkart"
    label = "Flipkart"
    implemented = True
    export_hint = (
        "Seller Hub -> Reports -> GST Reports -> Sales Report (one file per "
        "month). Save it anywhere under Finance/GST Fillings/Flipkart GST "
        "Report/ — the tax period is read from the invoice dates inside."
    )

    # -- workbook plumbing -----------------------------------------------

    @staticmethod
    def _sheets(path: str) -> Set[str]:
        try:
            return {str(s).strip().lower() for s in pd.ExcelFile(path).sheet_names}
        except Exception:
            return set()

    @staticmethod
    def _sheet(path: str, want: str) -> pd.DataFrame:
        xl = pd.ExcelFile(path)
        for name in xl.sheet_names:
            if str(name).strip().lower() == want:
                frame = xl.parse(name)
                frame.columns = [_key(c) for c in frame.columns]
                return frame
        return pd.DataFrame()

    @staticmethod
    def _col(df: pd.DataFrame, *candidates: str) -> str:
        """Resolve a column by exact name, then by prefix."""
        for want in candidates:
            if want in df.columns:
                return want
        for want in candidates:
            for have in df.columns:
                if have.startswith(want):
                    return have
        return ""

    def _num(self, df: pd.DataFrame, *candidates: str) -> pd.Series:
        col = self._col(df, *candidates)
        if not col:
            return pd.Series([0.0] * len(df), index=df.index)
        return pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    def _txt(self, df: pd.DataFrame, *candidates: str) -> pd.Series:
        col = self._col(df, *candidates)
        if not col:
            return pd.Series([""] * len(df), index=df.index)
        return _clean(df[col])

    # -- adapter API -----------------------------------------------------

    def matches(self, path: str) -> bool:
        if not path.lower().endswith((".xlsx", ".xls")):
            return False
        sheets = self._sheets(path)
        if SHEET_SALES in sheets and SHEET_CASHBACK in sheets:
            return True
        return len(_AGGREGATED_SIGNATURE & sheets) >= 3

    def notes(self, path: str) -> List[str]:
        out: List[str] = []
        try:
            sales = self._sheet(path, SHEET_SALES)
            cash = self._sheet(path, SHEET_CASHBACK)
        except Exception:
            return out
        if not len(sales):
            return ["no sales rows — Flipkart reported nil turnover for this file"]

        months = pd.to_datetime(
            self._txt(sales, "buyer invoice date"), errors="coerce"
        ).dt.strftime("%Y-%m").dropna()
        if len(months):
            period = months.mode().iloc[0]
            drift = int((months != period).sum())
            if drift:
                out.append(
                    "%d row(s) carry a buyer-invoice date outside %s; they are "
                    "still declared in %s, the month this report covers."
                    % (drift, period, period))

        if len(cash):
            net = float(self._num(cash, "taxable value").sum())
            out.append(
                "%d cash-back credit/debit note(s) worth Rs %.2f net were NOT "
                "added to turnover — Flipkart raises those to the seller to "
                "refund bank-funded offers already deducted on the customer "
                "invoice, so they are inward reimbursements, not outward "
                "supplies." % (len(cash), net))
        return out

    def load(self, path: str) -> pd.DataFrame:
        sheets = self._sheets(path)
        if SHEET_SALES not in sheets and len(_AGGREGATED_SIGNATURE & sheets) >= 3:
            raise ValueError(
                "this is Flipkart's aggregated 'GSTR-1 and GSTR-8' workbook, "
                "not the monthly Sales Report. The tool reads the Sales "
                "Report; keeping both for the same month would count the "
                "turnover twice. Remove this file.")

        sales = self._sheet(path, SHEET_SALES)
        if not len(sales):
            return finalise(pd.DataFrame())

        taxable = self._num(sales, "taxable value")
        igst = self._num(sales, "igst amount")
        cgst = self._num(sales, "cgst amount")
        sgst = self._num(sales, "sgst amount")
        tax = igst + cgst + sgst

        # Quantity is reported unsigned even on returns; mirror the value sign
        # so the HSN summary nets the same way the turnover does.
        quantity = self._num(sales, "item quantity").abs()
        quantity = quantity.where(taxable >= 0, -quantity)

        doc_type = [
            INVOICE if v > 0.005 else CREDIT_NOTE if v < -0.005 else CANCELLED
            for v in taxable
        ]

        # Derive the rate from the money itself rather than the reported rate
        # column, whose unit (18 vs 0.18) is unknowable while every line is 0%.
        rate = (tax / taxable.where(taxable.abs() > 0.005)).fillna(0.0).round(4)

        pos = self._txt(sales, "customer's delivery state")
        billing = self._txt(sales, "customer's billing state")
        pos = pos.where(pos.str.len() > 0, billing)

        doc_date = pd.to_datetime(
            self._txt(sales, "buyer invoice date"), errors="coerce")
        months = doc_date.dt.strftime("%Y-%m").dropna()
        period = months.mode().iloc[0] if len(months) else ""

        sku = self._txt(sales, "sku").str.replace(
            r"(?i)^sku\s*:\s*", "", regex=True)

        out = pd.DataFrame({
            "platform": self.key,
            "source_file": self._name(path),
            "doc_type": doc_type,
            "doc_no": self._txt(sales, "buyer invoice id"),
            "doc_date": doc_date,
            "period": period,
            "order_id": self._txt(sales, "order id"),
            "order_date": pd.to_datetime(
                self._txt(sales, "order date"), errors="coerce"),
            "sku": sku,
            "hsn": self._txt(sales, "hsn code"),
            "description": self._txt(sales, "product title/description"),
            "quantity": quantity,
            "taxable_value": taxable,
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "cess": self._num(sales, "luxury cess amount"),
            "rate": rate,
            "pos_state": pos,
            "seller_gstin": self._txt(sales, "seller gstin"),
            "buyer_gstin": self._txt(sales, "business gst number"),
            "tcs_igst": self._num(sales, "tcs igst amount"),
            "tcs_cgst": self._num(sales, "tcs cgst amount"),
            "tcs_sgst": self._num(sales, "tcs sgst amount"),
            "shipping_value": self._num(sales, "shipping charges"),
        })
        return finalise(out)
