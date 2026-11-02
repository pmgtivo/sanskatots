"""Amazon adapter — the Seller Central "Unified Transaction" report.

Download: Seller Central -> Payments -> Reports Repository -> Custom Unified
Transaction (one CSV per month, ``2026Oct1-2026Oct31CustomUnifiedTransaction.csv``).

Why this report
---------------
Unlike the All Orders report it carries the money itself, so nothing is modelled:

* ``Order``              the sale, with product sales, promotion rebates, selling
                         fees, other transaction fees and tax collected at source.
* ``Refund``             a return. The sale is reversed and Amazon bills a return
                         handling fee on top, which is the real cost of a return.
* ``Shipping Services``  the Easy Ship weight-handling fee, keyed to an order.
* ``Service Fee``        advertising (``Cost of Advertising``) and other charges.
* ``Transfer``           the payout that reached the bank.

Transaction Status says whether the money is ``Released`` (payable / paid) or
``Deferred`` (shipped but still inside the hold window).

How rows become orders
----------------------
The report is a ledger of postings, so rows are folded back into one line per
``Order Id`` + ``SKU``. The order is dated by its sale posting (the report has no
order-placed date). A refund is attached to its order even when it posts in a
later month, so a September sale returned in October is a September return.

* refund >= half the invoice  -> ``Return``; a smaller refund is a partial refund
* ``Deferred`` sale, no refund -> ``In Transit`` (return window still open)
* ``Released`` sale            -> ``Delivered``

Amazon does not post cancelled-before-shipping orders, so ``Cancelled`` is empty.
Postings are UTC in the file and converted to Indian time before a month is
decided.
"""

from __future__ import annotations

import os
from typing import List

import pandas as pd

from .base import (
    DELIVERED,
    FEE_ADJ,
    IN_TRANSIT,
    RETURN,
    PlatformAdapter,
    clean_state,
    empty_ads,
    empty_bank,
    finalise_ads,
    finalise_bank,
    finalise_orders,
)

HEADER_MARKERS = ("date/time", "settlement id", "order id", "selling fees", "transaction status")
#: A refund below this share of the sale is a partial refund, not a return.
PARTIAL_REFUND = 0.5
PREAMBLE_LINES = 40

ADS_DESCRIPTION = "cost of advertising"

MONEY_COLUMNS = [
    "product sales", "shipping credits", "gift wrap credits", "promotional rebates",
    "total sales tax liable(gst before adjusting tcs)", "tcs-cgst", "tcs-sgst", "tcs-igst",
    "tds (section 194-o)", "selling fees", "fba fees", "other transaction fees", "other", "total",
]


def _header_row(path: str) -> int:
    """Line number of the real header; the report opens with a block of definitions."""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
            for i, line in enumerate(fh):
                low = line.lower()
                if all(m in low for m in HEADER_MARKERS):
                    return i
                if i > PREAMBLE_LINES:
                    break
    except OSError:
        pass
    return -1


def _money(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce").fillna(0.0)


def _posted(series: pd.Series) -> pd.Series:
    """'30 Sept 2026 7:46:47 pm UTC' -> naive Indian time."""
    text = series.astype(str).str.replace(" UTC", "", regex=False).str.replace("Sept", "Sep", regex=False).str.strip()
    parsed = pd.to_datetime(text, format="%d %b %Y %I:%M:%S %p", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed[missing] = pd.to_datetime(text[missing], errors="coerce", format="mixed")
    return parsed.dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)


def _read(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path, skiprows=_header_row(path), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    for col in MONEY_COLUMNS:
        raw[col] = _money(raw[col]) if col in raw.columns else 0.0
    raw["quantity"] = _money(raw["quantity"]) if "quantity" in raw.columns else 0.0
    raw["_when"] = _posted(raw["date/time"])
    raw["_type"] = raw["type"].str.strip().str.lower()
    raw["_desc"] = raw["description"].str.strip().str.lower()
    return raw


def _key(order_id: pd.Series, sku: pd.Series) -> pd.Series:
    return order_id.astype(str).str.strip() + "|" + sku.astype(str).str.strip()


class AmazonAdapter(PlatformAdapter):
    key = "amazon"
    label = "Amazon"
    implemented = True
    extensions = [".csv"]

    # -- detection -------------------------------------------------------

    def matches(self, path: str) -> bool:
        return path.lower().endswith(".csv") and _header_row(path) >= 0

    def kind(self, path: str) -> str:
        return "Unified Transaction report"

    # -- parsing ---------------------------------------------------------

    def load_orders(self, path: str) -> pd.DataFrame:
        raw = _read(path)
        source = os.path.basename(path)
        ad = (raw["_type"] == "service fee") & (raw["_desc"] == ADS_DESCRIPTION)
        keep = raw["_type"].isin({"order", "refund", "shipping services", "service fee", "adjustment"}) & ~ad
        raw = raw[keep]
        if raw.empty:
            return finalise_orders(pd.DataFrame(columns=["order_id"]))

        events = raw["_type"].map({
            "order": "ORDER", "refund": "REFUND", "shipping services": "SHIPPING",
            "service fee": "FEE", "adjustment": "FEE",
        })
        tax_at_source = (raw["tcs-cgst"] + raw["tcs-sgst"] + raw["tcs-igst"] + raw["tds (section 194-o)"])
        customer_value = (raw["product sales"] + raw["shipping credits"] + raw["gift wrap credits"]
                          + raw["promotional rebates"] + raw["total sales tax liable(gst before adjusting tcs)"])
        is_line = events.isin(["ORDER", "REFUND"])
        sku = raw["sku"].str.strip()
        order_id = _key(raw["order id"], sku).where(is_line, raw["order id"].str.strip() + "|")
        stamp = raw["date/time"].str.strip()
        out = pd.DataFrame({
            "order_id": order_id.values,
            "order_date": raw["_when"].values,
            "status": "",
            "sku": sku.values,
            "quantity": raw["quantity"].where(is_line, 0.0).values,
            "gross_sale": customer_value.where(is_line, 0.0).values,
            "commission": (raw["selling fees"] + raw["fba fees"]).where(is_line, 0.0).values,
            "fwd_shipping": raw["other transaction fees"].where(is_line, 0.0).values,
            "tds": tax_at_source.where(is_line, 0.0).values,
            "settlement": raw["total"].values,
            "paid": (raw["transaction status"].str.strip().str.lower() == "released").values,
            "event": events.values,
            "event_id": (stamp + "|" + raw["type"].str.strip() + "|" + raw["order id"].str.strip() + "|"
                         + sku + "|" + raw["total"].astype(str)).values,
            "event_date": raw["_when"].values,
            "state": raw["order state"].map(_state).values,
            "pay_mode": raw["account type"].map(_pay_mode).values,
            "reason": raw["description"].where(~is_line, "").str.strip().values,
            "source": source,
        })
        out["snapshot"] = out["event_date"].max()
        return finalise_orders(out)

    def load_ads(self, path: str) -> pd.DataFrame:
        raw = _read(path)
        raw = raw[(raw["_type"] == "service fee") & (raw["_desc"] == ADS_DESCRIPTION)]
        if raw.empty:
            return empty_ads()
        out = pd.DataFrame({
            "campaign": "Amazon Sponsored Ads",
            "run_date": raw["_when"].values,
            "ad_cost": -raw["total"].values,
            "gst": 0.0,
            "credits": 0.0,
            "total_cost": -raw["total"].values,
            "source": os.path.basename(path),
            "ref": (raw["date/time"].str.strip() + "|" + raw["settlement id"].str.strip()).values,
        })
        return finalise_ads(out)

    def load_bank(self, path: str) -> pd.DataFrame:
        raw = _read(path)
        raw = raw[raw["_type"] == "transfer"]
        if raw.empty:
            return empty_bank()
        return finalise_bank(pd.DataFrame({
            "date": raw["_when"].values,
            "amount": -raw["total"].values,
            "ref": raw["settlement id"].str.strip().values,
            "kind": "Transfer to bank",
            "source": os.path.basename(path),
        }))

    # -- ledger -> one row per order line ---------------------------------

    def consolidate(self, orders: pd.DataFrame) -> pd.DataFrame:
        if not len(orders) or not (orders["event"] != "").any():
            return orders
        plain = orders[orders["event"] == ""]
        # The same posting can appear Deferred in an early export and Released in a later
        # one; the Released copy wins.
        ev = (orders[orders["event"] != ""].sort_values("paid")
              .drop_duplicates(["event", "event_id"], keep="last"))
        as_of = ev["event_date"].max()

        sales = ev[ev["event"] == "ORDER"]
        refunds = ev[ev["event"] == "REFUND"]
        shipping = ev[ev["event"] == "SHIPPING"]
        fees = ev[ev["event"] == "FEE"]

        sale = sales.groupby("order_id").agg(
            order_date=("order_date", "min"), sku=("sku", "first"), quantity=("quantity", "sum"),
            gross_sale=("gross_sale", "sum"), commission=("commission", "sum"),
            fwd_shipping=("fwd_shipping", "sum"), tds=("tds", "sum"), settlement=("settlement", "sum"),
            paid=("paid", "all"), event_date=("event_date", "max"), state=("state", "first"),
            pay_mode=("pay_mode", "first"), source=("source", "first"),
        )
        ref = refunds.groupby("order_id").agg(
            r_date=("order_date", "min"), r_sku=("sku", "first"), r_qty=("quantity", "sum"),
            r_value=("gross_sale", "sum"), r_fee=("commission", "sum"), r_other_fee=("fwd_shipping", "sum"),
            r_tds=("tds", "sum"), r_settle=("settlement", "sum"), r_paid=("paid", "all"),
            r_event=("event_date", "max"), r_state=("state", "first"), r_mode=("pay_mode", "first"),
            r_source=("source", "first"),
        )
        lines = sale.join(ref, how="outer")

        # Easy Ship weight-handling fees are posted against the order id only: spread them
        # across that order's lines, and keep any whose order is not in the data as plain fees.
        ship_alloc = pd.DataFrame(columns=["order_id", "fee", "paid"])
        orphan_ship = shipping.iloc[0:0]
        if len(shipping):
            by_order = {}
            for key in lines.index:
                by_order.setdefault(key.split("|")[0], []).append(key)
            rows = []
            orphans = []
            for _, s in shipping.iterrows():
                targets = by_order.get(s["order_id"].split("|")[0])
                if not targets:
                    orphans.append(s.name)
                    continue
                weight = lines.loc[targets, "gross_sale"].fillna(0.0).clip(lower=0.0)
                weight = weight / weight.sum() if weight.sum() > 0 else pd.Series(1.0 / len(targets), index=targets)
                for key in targets:
                    rows.append({"order_id": key, "fee": s["settlement"] * float(weight[key]), "paid": bool(s["paid"])})
            ship_alloc = pd.DataFrame(rows, columns=["order_id", "fee", "paid"])
            orphan_ship = shipping.loc[orphans]
        ship = ship_alloc.groupby("order_id").agg(ship_fee=("fee", "sum"), ship_paid=("paid", "all"))
        lines = lines.join(ship)

        out: List[dict] = []
        for key, r in lines.iterrows():
            has_sale = pd.notna(r["order_date"])
            has_refund = pd.notna(r["r_value"])
            gross = float(r["gross_sale"]) if has_sale else 0.0
            refund_value = abs(float(r["r_value"])) if has_refund else 0.0
            r_fee = float(r["r_fee"]) + float(r["r_other_fee"]) if has_refund else 0.0
            ship_fee = float(r["ship_fee"]) if pd.notna(r["ship_fee"]) else 0.0

            full_return = has_refund and refund_value > 0 and (not has_sale or refund_value >= PARTIAL_REFUND * gross)
            if not has_sale:
                gross = refund_value  # sale predates the loaded data; assume it was fully paid
            placed = r["order_date"] if has_sale else r["r_date"]
            paid_flags = [bool(r["paid"])] if has_sale else []
            if has_refund:
                paid_flags.append(bool(r["r_paid"]))
            if pd.notna(r["ship_paid"]):
                paid_flags.append(bool(r["ship_paid"]))

            if full_return:
                status = RETURN
            elif has_sale and not bool(r["paid"]):
                status = IN_TRANSIT
            else:
                status = DELIVERED

            commission = float(r["commission"]) if has_sale else 0.0
            if r_fee > 0:   # a fee credited back on the refund
                commission += r_fee
                r_fee = 0.0
            settlement = ((float(r["settlement"]) if has_sale else 0.0)
                          + (float(r["r_settle"]) if has_refund else 0.0) + ship_fee)
            out.append({
                "order_id": key,
                "order_date": placed,
                "status": status,
                "sku": (r["sku"] if has_sale else r["r_sku"]),
                "quantity": float(r["quantity"]) if has_sale else float(r["r_qty"]),
                "gross_sale": gross,
                "return_revenue": -refund_value if has_refund else 0.0,
                "commission": commission,
                "fwd_shipping": (float(r["fwd_shipping"]) if has_sale else 0.0) + ship_fee,
                "return_shipping": r_fee,
                "tds": (float(r["tds"]) if has_sale else 0.0) + (float(r["r_tds"]) if has_refund else 0.0),
                "settlement": settlement,
                "paid": all(paid_flags) if paid_flags else False,
                "snapshot": as_of,
                "source": r["source"] if has_sale else r["r_source"],
                "event_date": max([d for d in (r["event_date"], r["r_event"]) if pd.notna(d)] or [placed]),
                "state": (r["state"] if has_sale else r["r_state"]) or "",
                "pay_mode": (r["pay_mode"] if has_sale else r["r_mode"]) or "",
                "reason": "" if has_sale else "Refund of an order placed before the loaded data",
            })

        # Charges not tied to a sale: subscription, cancellation charges, adjustments, stray fees.
        side = pd.concat([fees, orphan_ship])
        for _, s in side.iterrows():
            out.append({
                "order_id": "FEE|" + s["event_id"],
                "order_date": s["order_date"],
                "status": FEE_ADJ,
                "sku": "(unassigned)",
                "quantity": 0.0,
                "settlement": s["settlement"],
                "other": s["settlement"],
                "paid": bool(s["paid"]),
                "snapshot": as_of,
                "source": s["source"],
                "event_date": s["event_date"],
                "reason": s["reason"],
            })

        merged = finalise_orders(pd.DataFrame(out))
        return pd.concat([plain, merged], ignore_index=True) if len(plain) else merged


def _state(raw: object) -> str:
    return clean_state(str(raw)) if str(raw).strip() else ""


def _pay_mode(account_type: object) -> str:
    text = str(account_type).lower()
    if not text.strip():
        return ""
    return "COD" if "cash on delivery" in text else "Prepaid"
