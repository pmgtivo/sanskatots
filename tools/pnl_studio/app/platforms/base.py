"""Normalised schema every marketplace adapter must produce.

Adding a marketplace = subclass `PlatformAdapter`, emit these two frames, and
register it in `platforms/__init__.py`. Nothing downstream is platform aware.
"""

from __future__ import annotations

import os
from typing import List

import pandas as pd

DELIVERED = "Delivered"
IN_TRANSIT = "In Transit"
RETURN = "Return"
RTO = "RTO"
EXCHANGE = "Exchange"
CANCELLED = "Cancelled"
FEE_ADJ = "Fee Adjustment"

SOLD_STATUSES = (DELIVERED, IN_TRANSIT, EXCHANGE)
LOST_STATUSES = (RETURN, RTO)

#: Event-ledger platforms only learn an order was delivered when it says so; an
#: order older than this many days with no return is treated as delivered, and
#: a younger one as still open (its return window has not closed).
OPEN_DAYS = 14

ORDER_COLUMNS = [
    "order_id",       # unique line id (sub-order / shipment item)
    "order_date",     # datetime64 — cohort is built on this, never the filename
    "status",         # one of the canonical statuses above
    "sku",            # seller SKU
    "quantity",
    "gross_sale",     # sale value incl. shipping & GST
    "return_revenue", # negative reversal on returns/RTO
    "fwd_shipping",
    "return_shipping",
    "affiliate",
    "claims",
    "tds",
    "commission",
    "settlement",     # what the marketplace actually pays out
    "paid",           # True = already settled, False = still receivable
    "snapshot",       # as-of date of the export, used to supersede stale estimates
    "source",         # source file name
    # -- optional, filled by adapters whose exports are event ledgers --------
    "offers",         # bank-offer cashback the platform reimburses to the seller
    "est",            # True = settlement is MODELLED from config fees, not reported
    "event",          # raw event on this row ("" once consolidated)
    "event_id",       # document id of the event, used to drop repeated exports
    "event_date",
    "state",          # customer's delivery state
    "pay_mode",       # Prepaid | COD
    "reason",         # claim / return reason text when the platform gives one
]

AD_COLUMNS = ["campaign", "run_date", "ad_cost", "gst", "credits", "total_cost", "source"]

ORDER_NUMERIC = [
    "quantity", "gross_sale", "return_revenue", "fwd_shipping", "return_shipping",
    "affiliate", "claims", "tds", "commission", "settlement", "offers",
]
ORDER_TEXT = ["event", "event_id", "state", "pay_mode", "reason"]


def clean_state(raw: str) -> str:
    """Customer state as a tidy title-case name, via the GST module's spelling table."""
    from ..gst import rules  # Keralam -> Kerala, Chattisgarh -> Chhattisgarh, ...
    name, _ = rules.normalise_state(raw)
    return (name or raw or "").title()


def empty_orders() -> pd.DataFrame:
    return pd.DataFrame(columns=ORDER_COLUMNS)


def empty_ads() -> pd.DataFrame:
    return pd.DataFrame(columns=AD_COLUMNS)


def finalise_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a partially-filled frame into the canonical order schema."""
    for col in ORDER_COLUMNS:
        if col not in df.columns:
            df[col] = 0 if col in ORDER_NUMERIC else ""
    for col in ORDER_NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["snapshot"] = pd.to_datetime(df["snapshot"], errors="coerce")
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    for col in ORDER_TEXT:
        df[col] = df[col].fillna("").astype(str).replace({"nan": "", "None": ""}).str.strip()
    df["est"] = df["est"].replace({"": False}).fillna(False).astype(bool)
    df["order_id"] = df["order_id"].astype(str)
    df["sku"] = df["sku"].astype(str).str.strip().replace({"": "(unassigned)", "nan": "(unassigned)"})
    df["status"] = df["status"].astype(str)
    df["paid"] = df["paid"].astype(bool)
    return df[ORDER_COLUMNS]


def finalise_ads(df: pd.DataFrame) -> pd.DataFrame:
    for col in AD_COLUMNS:
        if col not in df.columns:
            df[col] = 0 if col in ("ad_cost", "gst", "credits", "total_cost") else ""
    for col in ("ad_cost", "gst", "credits", "total_cost"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["run_date"] = pd.to_datetime(df["run_date"], errors="coerce")
    df["campaign"] = df["campaign"].astype(str)
    return df[AD_COLUMNS]


class PlatformAdapter:
    key = ""
    label = ""
    extensions: List[str] = [".xlsx"]
    implemented = True

    def matches(self, path: str) -> bool:
        """True if this adapter can parse the given file."""
        raise NotImplementedError

    def load_orders(self, path: str) -> pd.DataFrame:
        raise NotImplementedError

    def load_ads(self, path: str) -> pd.DataFrame:
        return empty_ads()

    def kind(self, path: str) -> str:
        """Short human label for a file, shown in the Data Sources tab."""
        return "Settled" if "PREVIOUS" in os.path.basename(path).upper() else "Outstanding"

    def consolidate(self, orders: pd.DataFrame) -> pd.DataFrame:
        """Collapse event rows into one row per order. Default: rows are already orders."""
        return orders
