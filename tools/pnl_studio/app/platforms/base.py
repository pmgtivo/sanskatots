"""Normalised schema every marketplace adapter must produce.

Adding a marketplace = subclass `PlatformAdapter`, emit these two frames, and
register it in `platforms/__init__.py`. Nothing downstream is platform aware.
"""

from __future__ import annotations

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
]

AD_COLUMNS = ["campaign", "run_date", "ad_cost", "gst", "credits", "total_cost", "source"]

ORDER_NUMERIC = [
    "quantity", "gross_sale", "return_revenue", "fwd_shipping", "return_shipping",
    "affiliate", "claims", "tds", "commission", "settlement",
]


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
