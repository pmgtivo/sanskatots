"""Flipkart adapter — the monthly "Sales Report" workbook.

Download: Seller Hub -> Reports -> GST Reports -> Sales Report (one file per
month). It is the same workbook the GST module reads, so one download serves
both tools.

What it contains, and what it does not
--------------------------------------
* ``Sales Report``  one row per order-item EVENT: Sale, Return, Cancellation,
  Return Cancellation (a revoked return). Values are priced after discount.
* ``Cash Back Report``  credit / debit notes Flipkart raises TO the seller to
  refund bank-funded offers. Those are real money received, so they feed the
  ``offers`` column.
* It does NOT contain commission, shipping fees, collection fees, payouts or
  claims. Settlement is therefore modelled from the fee assumptions in the
  Config tab and every Flipkart order is marked ``est=True`` so the dashboard
  can say so.

Event handling
--------------
``Final Invoice Amount`` is unsigned on a return, ``Taxable Value`` is signed,
so the sign is taken from the latter. An order item can be returned, the return
revoked and returned again; only the net of all its events decides whether the
item ended up sold or returned.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

import pandas as pd

from .base import (
    CANCELLED,
    DELIVERED,
    IN_TRANSIT,
    OPEN_DAYS,
    RETURN,
    PlatformAdapter,
    clean_state,
    finalise_orders,
)

SHEET_SALES = "sales report"
SHEET_CASHBACK = "cash back report"

EVENT_MAP = {
    "sale": "SALE",
    "return": "RETURN",
    "cancellation": "CANCEL",
    "return cancellation": "RETURN_REVOKED",
}
MOVES = ("SALE", "RETURN", "CANCEL", "RETURN_REVOKED")


def _norm(name: object) -> str:
    return re.sub(r"\s+", " ", str(name).replace("\n", " ")).strip().lower()


def _col(df: pd.DataFrame, *prefixes: str) -> str:
    for want in prefixes:
        for have in df.columns:
            if have == want or have.startswith(want):
                return have
    return ""


def _num(df: pd.DataFrame, *prefixes: str) -> pd.Series:
    col = _col(df, *prefixes)
    if not col:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def _txt(df: pd.DataFrame, *prefixes: str) -> pd.Series:
    col = _col(df, *prefixes)
    if not col:
        return pd.Series("", index=df.index)
    out = df[col].astype(str).str.strip().str.strip('"').str.strip()
    return out.replace({"nan": "", "NaT": "", "NA": "", "None": ""})


class FlipkartAdapter(PlatformAdapter):
    key = "flipkart"
    label = "Flipkart"
    implemented = True
    extensions = [".xlsx"]

    # -- detection -------------------------------------------------------

    def matches(self, path: str) -> bool:
        if not path.lower().endswith((".xlsx", ".xls")):
            return False
        try:
            sheets = {_norm(s) for s in pd.ExcelFile(path).sheet_names}
        except Exception:
            return False
        return SHEET_SALES in sheets and SHEET_CASHBACK in sheets

    def kind(self, path: str) -> str:
        return "Sales report"

    # -- parsing ---------------------------------------------------------

    @staticmethod
    def _sheet(path: str, want: str) -> pd.DataFrame:
        xl = pd.ExcelFile(path)
        for name in xl.sheet_names:
            if _norm(name) == want:
                frame = xl.parse(name, dtype=str)
                frame.columns = [_norm(c) for c in frame.columns]
                return frame
        return pd.DataFrame()

    def load_orders(self, path: str) -> pd.DataFrame:
        source = os.path.basename(path)
        frames: List[pd.DataFrame] = []

        sales = self._sheet(path, SHEET_SALES)
        if len(sales):
            taxable = _num(sales, "taxable value")
            sign = taxable.apply(lambda v: -1.0 if v < 0 else 1.0)
            sku = _txt(sales, "sku").str.replace(r"(?i)^sku\s*:\s*", "", regex=True)
            events = _txt(sales, "event sub type").str.lower().map(
                lambda e: EVENT_MAP.get(e, re.sub(r"\W+", "_", e).upper()))
            order_type = _txt(sales, "order type").str.lower()
            frames.append(pd.DataFrame({
                "order_id": _txt(sales, "order item id"),
                "order_date": pd.to_datetime(_txt(sales, "order date"), errors="coerce"),
                "status": "",
                "sku": sku,
                "quantity": _num(sales, "item quantity"),
                "gross_sale": _num(sales, "final invoice amount") * sign,
                "tds": -_num(sales, "tds amount") * sign,
                "event": events,
                "event_id": _txt(sales, "buyer invoice id"),
                "event_date": pd.to_datetime(_txt(sales, "buyer invoice date"), errors="coerce"),
                "state": _txt(sales, "customer's delivery state").map(clean_state),
                "pay_mode": order_type.map(lambda t: "COD" if t == "postpaid" else "Prepaid" if t else ""),
                "est": True,
                "paid": False,
                "source": source,
            }))

        cash = self._sheet(path, SHEET_CASHBACK)
        if len(cash):
            frames.append(pd.DataFrame({
                "order_id": _txt(cash, "order item id"),
                "offers": _num(cash, "taxable value"),
                "event": "CASHBACK",
                "event_id": _txt(cash, "credit note id/ debit note id", "credit note id"),
                "event_date": pd.to_datetime(_txt(cash, "invoice date"), errors="coerce"),
                "est": True,
                "paid": False,
                "source": source,
            }))

        if not frames:
            return finalise_orders(pd.DataFrame(columns=["order_id"]))
        out = pd.concat(frames, ignore_index=True, sort=False)
        out["snapshot"] = out["event_date"].max()
        return finalise_orders(out)

    # -- event ledger -> one row per order item ---------------------------

    def consolidate(self, orders: pd.DataFrame) -> pd.DataFrame:
        if not len(orders) or not (orders["event"] != "").any():
            return orders
        plain = orders[orders["event"] == ""]
        ev = orders[orders["event"] != ""].drop_duplicates(["order_id", "event", "event_id"])
        as_of = ev["event_date"].max()

        cashback = ev[ev["event"] == "CASHBACK"].groupby("order_id")["offers"].sum()
        moves = ev[ev["event"].isin(MOVES)]

        rows: List[Dict] = []
        for order_id, g in moves.groupby("order_id", sort=False):
            sales = g[g["event"] == "SALE"]
            base = (sales if len(sales) else g).sort_values("event_date").iloc[0]
            sale_amount = float(sales["gross_sale"].max()) if len(sales) else abs(float(base["gross_sale"]))
            net = float(g["gross_sale"].sum())
            returned = net <= 0.005
            had_return = bool((g["event"] == "RETURN").any())
            first_sale = sales["event_date"].min() if len(sales) else base["event_date"]
            age = (as_of - first_sale).days if pd.notna(as_of) and pd.notna(first_sale) else 999

            if returned:
                status = RETURN if had_return else CANCELLED
            else:
                status = IN_TRANSIT if age < OPEN_DAYS else DELIVERED

            rows.append({
                "order_id": order_id,
                "order_date": base["order_date"],
                "status": status,
                "sku": base["sku"],
                "quantity": float(sales["quantity"].max()) if len(sales) else float(base["quantity"]),
                "gross_sale": sale_amount,
                "return_revenue": -sale_amount if returned else 0.0,
                "tds": float(g["tds"].sum()),
                "offers": float(cashback.get(order_id, 0.0)),
                "event_date": g["event_date"].max(),
                "state": base["state"],
                "pay_mode": base["pay_mode"],
                "est": True,
                "paid": False,
                "snapshot": as_of,
                "source": base["source"],
            })
        if not rows:
            return plain
        merged = finalise_orders(pd.DataFrame(rows))
        return pd.concat([plain, merged], ignore_index=True) if len(plain) else merged
