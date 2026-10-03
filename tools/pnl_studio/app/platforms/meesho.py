"""Meesho Seller-Panel `SP_ORDER_ADS_REFERRAL_PAYMENT` workbook adapter."""

from __future__ import annotations

import os
import re

import pandas as pd

from .base import (
    CANCELLED,
    DELIVERED,
    EXCHANGE,
    FEE_ADJ,
    IN_TRANSIT,
    RETURN,
    RTO,
    PlatformAdapter,
    empty_ads,
    finalise_ads,
    finalise_orders,
)

ORDER_SHEET = "Order Payments"
ADS_SHEET = "Ads Cost"
HEADER_ROW = 1  # row 0 is a banner, real header is the second row

COLUMN_MAP = {
    "Sub Order No": "order_id",
    "Order Date": "order_date",
    "Supplier SKU": "sku",
    "Quantity": "quantity",
    "Total Sale Amount (Incl. Shipping & GST)": "gross_sale",
    "Total Sale Return Amount (Incl. Shipping & GST)": "return_revenue",
    "Shipping Charge (Incl. GST)": "fwd_shipping",
    "Return Shipping Charge (Incl. GST)": "return_shipping",
    "Recovery": "affiliate",
    "Claims": "claims",
    "TDS": "tds",
    "Meesho Commission (Incl. GST)": "commission",
    "Final Settlement Amount": "settlement",
}

STATUS_MAP = {
    "delivered": DELIVERED,
    "shipped": IN_TRANSIT,
    "return": RETURN,
    "rto": RTO,
    "exchange": EXCHANGE,
    "cancelled": CANCELLED,
    "canceled": CANCELLED,
}

_DATE_IN_NAME = re.compile(r"\d{4}-\d{2}-\d{2}")


def _snapshot_date(path: str):
    """Latest date in the filename = how current this export is."""
    dates = _DATE_IN_NAME.findall(os.path.basename(path))
    if dates:
        return pd.Timestamp(max(dates))
    return pd.Timestamp(os.path.getmtime(path), unit="s")


class MeeshoAdapter(PlatformAdapter):
    key = "meesho"
    label = "Meesho"

    def matches(self, path: str) -> bool:
        name = os.path.basename(path).upper()
        if not name.endswith(".XLSX"):
            return False
        if "ORDER_ADS_REFERRAL_PAYMENT" in name:
            return True
        try:
            return ORDER_SHEET in pd.ExcelFile(path).sheet_names
        except Exception:
            return False

    def load_orders(self, path: str) -> pd.DataFrame:
        raw = pd.read_excel(path, sheet_name=ORDER_SHEET, header=HEADER_ROW)
        # Legend/summary rows have no sub-order id; real lines always look like "1_abcd".
        raw = raw[raw["Sub Order No"].astype(str).str.contains("_", na=False)].copy()

        out = pd.DataFrame(index=raw.index)
        for src, dst in COLUMN_MAP.items():
            out[dst] = raw[src] if src in raw.columns else 0
        out["status"] = (
            raw["Live Order Status"].fillna(FEE_ADJ).astype(str).str.strip()
            .map(lambda s: STATUS_MAP.get(s.lower(), s))
        )
        # Settlement-only lines (affiliate fees, claims) carry no order status.
        out.loc[raw["Live Order Status"].isna(), "status"] = FEE_ADJ
        out["paid"] = "PREVIOUS" in os.path.basename(path).upper()
        out["snapshot"] = _snapshot_date(path)
        out["source"] = os.path.basename(path)
        return finalise_orders(out)

    def load_ads(self, path: str) -> pd.DataFrame:
        try:
            raw = pd.read_excel(path, sheet_name=ADS_SHEET, header=HEADER_ROW)
        except ValueError:
            return empty_ads()
        raw = raw[pd.to_numeric(raw["Ad Cost"], errors="coerce").notna()].copy()
        if raw.empty:
            return empty_ads()
        out = pd.DataFrame(index=raw.index)
        out["campaign"] = raw.get("Campaign ID", "")
        out["run_date"] = raw["Deduction Duration"]  # date ads actually ran, not deduction date
        out["ad_cost"] = raw["Ad Cost"]
        out["gst"] = raw.get("GST", 0)
        out["credits"] = raw.get("Credits / Waivers / Discounts", 0)
        out["total_cost"] = raw["Total Ads Cost"]
        out["source"] = os.path.basename(path)
        return finalise_ads(out)
