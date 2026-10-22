"""Modelled settlement for platforms whose exports carry no fee data.

Flipkart's Sales Report and Amazon's All Orders / MTR reports say what the
customer paid and what came back, but not what the marketplace kept. For those
orders (``est=True``) the fee lines are computed here from the per-platform
``fee_model`` in the catalog config, so the P&L is a *model*, not a statement.
Replace the placeholders with real figures from the platform's own settlement
report and the model becomes exact.

Rules, per order:

* dispatched and kept (delivered / in transit / exchange)
    commission  = pct x customer-paid value, plus a fixed fee per priced order
    shipping    = forward shipping fee per order
* dispatched and lost (return / RTO)
    commission refunded, forward shipping fee still charged,
    plus the return shipping cost per failed order
* fees carry GST at ``fee_gst_pct`` and, because books are exempt, that GST is a
  real cost (no input credit under s.17(2)).
* TDS comes from the export when it has it, otherwise ``tds_pct`` of the sale.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .platforms.base import LOST_STATUSES, SOLD_STATUSES

DEFAULT_FEE_MODEL: Dict[str, Any] = {
    "commission_pct": 0.0,    # fraction of the customer-paid value
    "fixed_fee": 0.0,         # per priced order: closing / fixed / collection fee
    "fwd_shipping": 0.0,      # per dispatched order, charged even if later returned
    "fee_gst_pct": 0.18,      # GST on marketplace fees
    "tds_pct": 0.0,           # only used where the export carries no TDS
    "note": "",
}


def model_for(cfg: Dict[str, Any], platform: str) -> Dict[str, Any]:
    stored = ((cfg.get("platforms") or {}).get(platform) or {}).get("fee_model") or {}
    return dict(DEFAULT_FEE_MODEL, **stored)


def apply(orders: pd.DataFrame, model: Dict[str, Any], return_shipping: float) -> pd.DataFrame:
    """Return ``orders`` with fee columns and settlement filled in for est rows."""
    if not len(orders) or not orders["est"].any():
        return orders
    df = orders.copy()
    est = df["est"]
    sold = est & df["status"].isin(SOLD_STATUSES)
    lost = est & df["status"].isin(LOST_STATUSES)
    gst = 1.0 + float(model["fee_gst_pct"])

    priced = sold & (df["gross_sale"] > 0.005)
    commission = -(float(model["commission_pct"]) * df["gross_sale"] + float(model["fixed_fee"])) * gst
    df.loc[priced, "commission"] = commission[priced]
    df.loc[sold | lost, "fwd_shipping"] = -float(model["fwd_shipping"]) * gst
    df.loc[lost, "return_shipping"] = -float(return_shipping)

    no_tds = sold & (df["tds"].abs() < 1e-9)
    df.loc[no_tds, "tds"] = -float(model["tds_pct"]) * df.loc[no_tds, "gross_sale"]

    parts = ["gross_sale", "return_revenue", "commission", "fwd_shipping",
             "return_shipping", "affiliate", "claims", "tds", "offers"]
    df.loc[est, "settlement"] = df.loc[est, parts].sum(axis=1)
    return df
