"""Flipkart adapter — the monthly Settlement Report workbook.

Download: Seller Hub -> Payments -> Settlement Report (one workbook per payout
period, ``<uuid>_<timestamp>.xlsx``).

What it contains
----------------
* ``Orders``    one row per order item *per payout*: sale amount, Flipkart-funded
                offer amount, refund, every marketplace fee, GST, TDS/TCS, the
                Seller Protection Fund payout and the bank settlement value, plus
                the order date, SKU and return type. All of it is real money.
* ``Ads``       wallet top-ups for Flipkart Ads. Top-ups are what leaves the
                settlement, so they are the ad spend.
* ``Summary of report`` the period's totals, ending in ``Net Bank Settlement``,
                which this adapter uses to prove its own arithmetic.

Because the file is organised by *payout date*, an order's rows can sit in
several workbooks (the sale in one month, its refund and reverse-shipping fee in
a later one). Rows are folded back into one line per ``Order item ID`` over every
workbook found, and the order is dated by when it was placed.

Return handling
---------------
* ``Customer Return``  the buyer sent it back: ``Return``. Flipkart bills a
                       reverse-shipping fee (plus GST) on top of the refund.
* ``Logistics Return`` the courier brought it back undelivered: ``RTO``. No fee.
* A refund without a return type is treated as an RTO.

Flipkart only settles shipped orders, so there are no cancellations here, and an
order placed in the last ``OPEN_DAYS`` days of the data is labelled open because
its return window has not closed even though it has been paid.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

import pandas as pd

from .base import (
    DELIVERED,
    IN_TRANSIT,
    OPEN_DAYS,
    RETURN,
    RTO,
    PlatformAdapter,
    empty_ads,
    empty_bank,
    finalise_ads,
    finalise_bank,
    finalise_orders,
)

SHEET_ORDERS = "orders"
SHEET_SUMMARY = "summary of report"
SHEET_ADS = "ads"
CUSTOMER_RETURN = "customer return"


def _norm(name: object) -> str:
    return re.sub(r"\s+", " ", str(name).replace("\n", " ")).strip().lower()


def _sheet_names(path: str) -> Dict[str, str]:
    return {_norm(s): s for s in pd.ExcelFile(path).sheet_names}


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _orders_frame(path: str) -> pd.DataFrame:
    """The Orders sheet with its three stacked header rows flattened into one label per column."""
    raw = pd.read_excel(path, sheet_name=_sheet_names(path)[SHEET_ORDERS], header=None, dtype=object)
    group = raw.iloc[0].ffill()
    labels = []
    for i in range(raw.shape[1]):
        parts = [group.iloc[i], raw.iloc[1, i], raw.iloc[2, i]]
        labels.append(" | ".join(_norm(p) for p in parts if pd.notna(p) and _norm(p)))
    body = raw.iloc[3:].copy()
    body.columns = labels
    return body


def _col(frame: pd.DataFrame, *fragments: str) -> pd.Series:
    """First column whose flattened label contains every fragment; zeros if absent."""
    for label in frame.columns:
        if all(f in label for f in fragments):
            return frame[label]
    return pd.Series(0.0, index=frame.index)


def _summary(path: str) -> Dict[str, object]:
    """Period totals from the Summary sheet, used to reconcile the order rows."""
    out: Dict[str, object] = {"net_bank": None, "period_end": pd.NaT, "ads_fees": 0.0, "ads_gst": 0.0}
    try:
        raw = pd.read_excel(path, sheet_name=_sheet_names(path)[SHEET_SUMMARY], header=None, dtype=object)
    except Exception:
        return out
    for _, row in raw.iterrows():
        cells = [_norm(c) if pd.notna(c) else "" for c in row.tolist()]
        values = [pd.to_numeric(c, errors="coerce") for c in row.tolist()]
        if any(c == "payment duration" for c in cells):
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", " ".join(str(c) for c in row.tolist() if pd.notna(c)))
            if dates:
                out["period_end"] = pd.Timestamp(max(dates))
        elif "net bank settlement" in cells[1]:
            out["net_bank"] = next((float(v) for v in values[2:] if pd.notna(v)), None)
        elif cells[1] == "ads fees":
            out["ads_fees"] = next((float(v) for v in values[2:] if pd.notna(v)), 0.0)
        elif cells[2] == "gst on ads fees":
            out["ads_gst"] = next((float(v) for v in values[3:] if pd.notna(v)), 0.0)
    return out


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
            sheets = set(_sheet_names(path))
        except Exception:
            return False
        return {SHEET_ORDERS, SHEET_SUMMARY, SHEET_ADS} <= sheets

    def kind(self, path: str) -> str:
        return "Settlement report"

    # -- parsing ---------------------------------------------------------

    def load_orders(self, path: str) -> pd.DataFrame:
        rows = _orders_frame(path)
        rows = rows[_col(rows, "transaction summary", "order item id").notna()]
        if rows.empty:
            return finalise_orders(pd.DataFrame(columns=["order_id"]))

        item = _col(rows, "transaction summary", "order item id").astype(str).str.strip()
        paid_on = pd.to_datetime(_col(rows, "payment date").astype(str), errors="coerce")
        bank = _num(_col(rows, "bank settlement value"))
        sale = _num(_col(rows, "transaction summary", "sale amount"))
        offer = _num(_col(rows, "transaction summary", "total offer")) + _num(_col(rows, "transaction summary", "offer adjustments"))
        refund = _num(_col(rows, "transaction summary", "refund"))

        forward_fee = _num(_col(rows, "marketplace fees", "| shipping fee"))
        reverse_fee = _num(_col(rows, "marketplace fees", "reverse shipping"))
        fee_total = _num(_col(rows, "transaction summary", "marketplace fee"))
        other_fee = fee_total - forward_fee - reverse_fee
        # GST on marketplace fees follows the fee it was charged on; with no fee it is a plain cost.
        gst = _num(_col(rows, "taxes", "gst on mp fees"))
        has_fee = fee_total.abs() > 1e-9
        forward_share = (forward_fee / fee_total).where(has_fee, 0.0)
        reverse_share = (reverse_fee / fee_total).where(has_fee, 0.0)
        other_share = (other_fee / fee_total).where(has_fee, 1.0)

        return_type = _col(rows, "order details", "return type").astype(str).str.strip().str.lower()
        return_type = return_type.replace({"nan": "", "none": ""})
        payer = _col(rows, "neft type").astype(str).str.strip().str.lower()
        neft = _col(rows, "neft id").astype(str).str.strip()

        out = pd.DataFrame({
            "order_id": item.values,
            "order_date": pd.to_datetime(_col(rows, "order details", "order date").astype(str), errors="coerce").values,
            "status": "",
            "sku": _col(rows, "seller sku").astype(str).str.strip().str.replace(r"(?i)^sku\s*:\s*", "", regex=True).values,
            "quantity": _num(_col(rows, "order details", "quantity")).values,
            "gross_sale": sale.clip(lower=0.0).values,
            "return_revenue": refund.values,
            "offers": offer.values,
            "commission": (other_fee + gst * other_share).values,
            "fwd_shipping": (forward_fee + gst * forward_share).values,
            "return_shipping": (reverse_fee + gst * reverse_share).values,
            "claims": _num(_col(rows, "protection fund")).values,
            "tds": (_num(_col(rows, "taxes", "tcs")) + _num(_col(rows, "taxes", "tds"))).values,
            "settlement": bank.values,
            "paid": True,
            "event": "SETTLEMENT",
            "event_id": (neft + "|" + paid_on.astype(str) + "|" + item + "|" + bank.round(3).astype(str)
                         + "|" + sale.astype(str) + "|" + offer.astype(str) + "|" + refund.astype(str)).values,
            "event_date": paid_on.values,
            "pay_mode": payer.map(lambda t: "COD" if t == "postpaid" else "Prepaid" if t else "").values,
            "reason": return_type.values,
            "source": os.path.basename(path),
        })
        out["snapshot"] = out["event_date"].max()
        return finalise_orders(out)

    def load_ads(self, path: str) -> pd.DataFrame:
        ads = self._ads_rows(path)
        if ads.empty:
            return empty_ads()
        info = _summary(path)
        total_fees = abs(float(info["ads_fees"])) + abs(float(info["ads_gst"]))
        gst_share = abs(float(info["ads_gst"])) / total_fees if total_fees else 0.0
        spend = -ads["settlement"]
        spend = spend[spend.abs() > 1e-9]
        ads = ads.loc[spend.index]
        out = pd.DataFrame({
            "campaign": "Flipkart Ads (wallet top-ups)",
            "run_date": ads["paid_on"].values,
            "ad_cost": (spend * (1 - gst_share)).values,
            "gst": (spend * gst_share).values,
            "credits": 0.0,
            "total_cost": spend.values,
            "source": os.path.basename(path),
            "ref": (ads["neft"] + "|" + ads["txn"]).values,
        })
        return finalise_ads(out)

    def load_bank(self, path: str) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []
        rows = _orders_frame(path)
        rows = rows[_col(rows, "transaction summary", "order item id").notna()]
        if len(rows):
            frames.append(pd.DataFrame({
                "ref": _col(rows, "neft id").astype(str).str.strip().values,
                "date": pd.to_datetime(_col(rows, "payment date").astype(str), errors="coerce").values,
                "amount": _num(_col(rows, "bank settlement value")).values,
            }))
        ads = self._ads_rows(path)
        if len(ads):
            frames.append(pd.DataFrame({
                "ref": ads["neft"].values, "date": ads["paid_on"].values, "amount": ads["settlement"].values,
            }))
        if not frames:
            return empty_bank()
        payouts = pd.concat(frames).groupby(["ref", "date"], as_index=False)["amount"].sum()
        payouts["kind"] = "NEFT payout"
        payouts["source"] = os.path.basename(path)

        # The Summary's Net Bank Settlement is Flipkart's own total. Anything the sheets above
        # did not account for (fines, TCS recovery, ...) is shown as one reconciling line.
        net = _summary(path)["net_bank"]
        gap = (float(net) - float(payouts["amount"].sum())) if net is not None else 0.0
        if abs(gap) > 0.5:
            end = _summary(path)["period_end"]
            payouts = pd.concat([payouts, pd.DataFrame([{
                "ref": "other-settlement-lines", "date": end if pd.notna(end) else payouts["date"].max(),
                "amount": gap, "kind": "Other settlement lines (fines, recoveries)",
                "source": os.path.basename(path),
            }])], ignore_index=True)
        return finalise_bank(payouts)

    @staticmethod
    def _ads_rows(path: str) -> pd.DataFrame:
        names = _sheet_names(path)
        if SHEET_ADS not in names:
            return pd.DataFrame()
        raw = pd.read_excel(path, sheet_name=names[SHEET_ADS], header=None, dtype=object)
        body = raw.iloc[2:]
        body = body[body.iloc[:, 0].notna()]
        if body.empty:
            return pd.DataFrame()
        return pd.DataFrame({
            "neft": body.iloc[:, 0].astype(str).str.strip().values,
            "paid_on": pd.to_datetime(body.iloc[:, 1].astype(str), errors="coerce").values,
            "settlement": pd.to_numeric(body.iloc[:, 2], errors="coerce").fillna(0.0).values,
            "txn": body.iloc[:, 5].astype(str).str.strip().values,
        })

    # -- settlement rows -> one row per order item -------------------------

    def consolidate(self, orders: pd.DataFrame) -> pd.DataFrame:
        if not len(orders) or not (orders["event"] != "").any():
            return orders
        plain = orders[orders["event"] == ""]
        ev = orders[orders["event"] != ""].drop_duplicates(["order_id", "event", "event_id"])
        as_of = ev["event_date"].max()

        rows: List[Dict] = []
        for order_id, g in ev.groupby("order_id", sort=False):
            base = g.sort_values("event_date").iloc[0]
            kinds = {r for r in g["reason"] if r}
            returned = bool(kinds) or (g["return_revenue"] < -0.005).any()
            positive = g.loc[g["gross_sale"] > 0.005, "gross_sale"]
            if returned:
                gross = float(positive.min()) if len(positive) else abs(float(g["return_revenue"].min()))
                status = RETURN if CUSTOMER_RETURN in kinds else RTO
            else:
                gross = float(g["gross_sale"].sum())
                age = (as_of - base["order_date"]).days if pd.notna(as_of) and pd.notna(base["order_date"]) else 999
                status = IN_TRANSIT if age < OPEN_DAYS else DELIVERED
            claims = float(g["claims"].sum())
            rows.append({
                "order_id": order_id,
                "order_date": base["order_date"],
                "status": status,
                "sku": base["sku"],
                "quantity": float(g["quantity"].max()),
                "gross_sale": gross,
                "return_revenue": -gross if returned else 0.0,
                "offers": float(g["offers"].sum()),
                "commission": float(g["commission"].sum()),
                "fwd_shipping": float(g["fwd_shipping"].sum()),
                "return_shipping": float(g["return_shipping"].sum()),
                "claims": claims,
                "tds": float(g["tds"].sum()),
                "settlement": float(g["settlement"].sum()),
                "paid": True,
                "snapshot": as_of,
                "source": base["source"],
                "event_date": g["event_date"].max(),
                "pay_mode": base["pay_mode"],
                "reason": "Seller Protection Fund payout" if abs(claims) > 0.005
                          else ", ".join(sorted(k.title() for k in kinds)),
            })
        merged = finalise_orders(pd.DataFrame(rows))
        return pd.concat([plain, merged], ignore_index=True) if len(plain) else merged
