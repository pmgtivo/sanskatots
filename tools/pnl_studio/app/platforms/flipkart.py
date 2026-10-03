"""Flipkart adapter — not implemented yet.

To enable: map Flipkart's settlement/orders export onto the canonical columns in
`base.ORDER_COLUMNS`, set `implemented = True`, and the whole dashboard, report
and month-comparison pipeline works unchanged.
"""

from __future__ import annotations

import os

import pandas as pd

from .base import PlatformAdapter, empty_orders


class FlipkartAdapter(PlatformAdapter):
    key = "flipkart"
    label = "Flipkart"
    implemented = False
    extensions = [".xlsx", ".csv"]

    def matches(self, path: str) -> bool:
        return False

    def load_orders(self, path: str) -> pd.DataFrame:
        raise NotImplementedError("Flipkart export mapping not defined yet (%s)" % os.path.basename(path))
