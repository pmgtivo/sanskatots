"""Amazon adapter — All Orders report plus the GST MTR for refunds.

Two exports feed it, and they complement each other:

* **All Orders report** (tab-separated ``.txt``): every order line with its
  status, price and promotion discount. This is the base of each order. It has
  NO returns, fees or payouts.
  Seller Central -> Reports -> Fulfilment -> All Orders.
* **GST MTR report** (``MTR_B2C-*.csv``, the same file the GST module reads):
  one row per Shipment / Refund / Cancel, with the exact tax-inclusive invoice
  amount. A Refund row is how a return shows up, so the MTR is what makes the
  return rate real. Without it every order looks sold.

Both are keyed on ``Order Id`` + ``SKU``. The MTR invoice amount wins over
``item-price - item-promotion-discount`` whenever it exists, because it is the
figure the customer was actually invoiced.

Amazon's purchase dates are UTC; orders are cohorted by Indian time, as Seller
Central and the MTR do, so a late-evening order is not put in the wrong month.
Fees and payouts are not in either file, so settlement is modelled from the
Config tab (``est=True``).
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

import pandas as pd

from .base import (
    CANCELLED,
    DELIVERED,
    EXCHANGE,
    IN_TRANSIT,
    OPEN_DAYS,
    RETURN,
    PlatformAdapter,
    clean_state,
    finalise_orders,
)

ORDERS_MARKERS = ("amazon-order-id", "order-item-id", "item-price")
MTR_MARKERS = ("transaction type", "order id", "shipment item id", "invoice amount")

MTR_EVENTS = {"shipment": "SHIPMENT", "refund": "REFUND", "freereplacement": "REPLACEMENT"}
#: A refund below this share of the invoice is a partial refund, not a return.
PARTIAL_REFUND = 0.5


def _head(path: str, size: int = 4096) -> str:
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            return fh.readline(size).lower()
    except OSError:
        return ""


def _is_orders(path: str) -> bool:
    head = _head(path)
    return "\t" in head and all(m in head for m in ORDERS_MARKERS)


def _is_mtr(path: str) -> bool:
    head = _head(path)
    return "," in head and all(m in head for m in MTR_MARKERS)


def _num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _key(order_id: pd.Series, sku: pd.Series) -> pd.Series:
    return order_id.astype(str).str.strip() + "|" + sku.astype(str).str.strip()


class AmazonAdapter(PlatformAdapter):
    key = "amazon"
    label = "Amazon"
    implemented = True
    extensions = [".txt", ".tsv", ".csv"]

    # -- detection -------------------------------------------------------

    def matches(self, path: str) -> bool:
        lower = path.lower()
        if lower.endswith((".txt", ".tsv", ".csv")):
            return _is_orders(path) or (lower.endswith(".csv") and _is_mtr(path))
        return False

    def kind(self, path: str) -> str:
        return "All Orders report" if _is_orders(path) else "GST MTR (refunds)"

    # -- parsing ---------------------------------------------------------

    def load_orders(self, path: str) -> pd.DataFrame:
        source = os.path.basename(path)
        if _is_orders(path):
            return self._load_all_orders(path, source)
        return self._load_mtr(path, source)

    def _load_all_orders(self, path: str, source: str) -> pd.DataFrame:
        raw = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, encoding="utf-8-sig")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        raw = raw[raw["amazon-order-id"].str.strip() != ""]
        purchased = (pd.to_datetime(raw["purchase-date"], utc=True, errors="coerce")
                     .dt.tz_convert("Asia/Kolkata").dt.tz_localize(None))
        updated = (pd.to_datetime(raw.get("last-updated-date", ""), utc=True, errors="coerce")
                   .dt.tz_convert("Asia/Kolkata").dt.tz_localize(None))
        gross = (_num(raw["item-price"]) - _num(raw["item-promotion-discount"])
                 + _num(raw.get("shipping-price", pd.Series("", index=raw.index)))
                 - _num(raw.get("ship-promotion-discount", pd.Series("", index=raw.index)))
                 + _num(raw.get("gift-wrap-price", pd.Series("", index=raw.index))))
        out = pd.DataFrame({
            "order_id": _key(raw["amazon-order-id"], raw["sku"]),
            "order_date": purchased,
            "status": raw["order-status"].str.strip(),
            "sku": raw["sku"].str.strip(),
            "quantity": _num(raw["quantity"]),
            "gross_sale": gross,
            "event": "ORDER",
            "event_id": raw["order-item-id"].str.strip(),
            "event_date": updated.fillna(purchased),
            "state": raw["ship-state"].map(clean_state),
            "est": True,
            "paid": False,
            "source": source,
        })
        out["snapshot"] = out["event_date"].max()
        return finalise_orders(out)

    def _load_mtr(self, path: str, source: str) -> pd.DataFrame:
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        events = raw["transaction type"].str.strip().str.lower().map(MTR_EVENTS)
        keep = events.notna()
        raw, events = raw[keep], events[keep]
        if raw.empty:
            return finalise_orders(pd.DataFrame(columns=["order_id"]))
        out = pd.DataFrame({
            "order_id": _key(raw["order id"], raw["sku"]),
            "order_date": pd.to_datetime(raw["order date"], errors="coerce"),
            "status": "",
            "sku": raw["sku"].str.strip(),
            "quantity": _num(raw["quantity"]),
            "gross_sale": _num(raw["invoice amount"]),
            "event": events.values,
            "event_id": (raw["invoice number"].str.strip() + "|" + raw["shipment item id"].str.strip()).values,
            "event_date": pd.to_datetime(raw["invoice date"], errors="coerce"),
            "state": raw["ship to state"].map(clean_state),
            "est": True,
            "paid": False,
            "source": source,
        })
        out["snapshot"] = out["event_date"].max()
        return finalise_orders(out)

    # -- event ledger -> one row per order line ---------------------------

    def consolidate(self, orders: pd.DataFrame) -> pd.DataFrame:
        if not len(orders) or not (orders["event"] != "").any():
            return orders
        plain = orders[orders["event"] == ""]
        ev = orders[orders["event"] != ""].drop_duplicates(["order_id", "event", "event_id"])
        as_of = pd.concat([ev["event_date"], ev["order_date"]]).max()

        rows: List[Dict] = []
        for order_id, g in ev.groupby("order_id", sort=False):
            listed = g[g["event"] == "ORDER"]
            shipped = g[g["event"] == "SHIPMENT"]
            refunds = g[g["event"] == "REFUND"]
            replaced = g[g["event"] == "REPLACEMENT"]
            base = (listed if len(listed) else g).sort_values("order_date").iloc[0]

            if len(shipped):
                gross = float(shipped["gross_sale"].sum())
            elif len(listed):
                gross = float(listed["gross_sale"].sum())
            else:
                gross = 0.0
            qty = float((listed if len(listed) else shipped if len(shipped) else g)["quantity"].sum())
            refund = abs(float(refunds["gross_sale"].sum())) if len(refunds) else 0.0
            raw_status = str(listed["status"].iloc[0]).lower() if len(listed) else ""
            placed = base["order_date"]
            age = (as_of - placed).days if pd.notna(as_of) and pd.notna(placed) else 999

            if raw_status == "cancelled" and not len(shipped):
                status = CANCELLED
            elif refund > 0 and gross > 0 and refund >= PARTIAL_REFUND * gross:
                status = RETURN
            elif gross <= 0.005 and (len(replaced) or raw_status.startswith("shipped")):
                status = EXCHANGE
            elif "delivered" in raw_status:
                status = DELIVERED
            else:
                status = IN_TRANSIT if age < OPEN_DAYS else DELIVERED

            rows.append({
                "order_id": order_id,
                "order_date": placed,
                "status": status,
                "sku": base["sku"],
                "quantity": qty,
                "gross_sale": gross,
                "return_revenue": -refund if refund else 0.0,
                "event_date": g["event_date"].max(),
                "state": base["state"],
                "est": True,
                "paid": False,
                "snapshot": as_of,
                "source": base["source"],
            })
        merged = finalise_orders(pd.DataFrame(rows))
        return pd.concat([plain, merged], ignore_index=True) if len(plain) else merged
