"""Amazon adapter — not implemented yet.

To enable: map Amazon's Settlement / FBA reimbursement reports onto the canonical
columns in `base.ORDER_COLUMNS`, set `implemented = True`, and register nothing
else — the engine, report and comparison layers are platform agnostic.
"""

from __future__ import annotations

import os

import pandas as pd

from .base import PlatformAdapter


class AmazonAdapter(PlatformAdapter):
    key = "amazon"
    label = "Amazon"
    implemented = False
    extensions = [".xlsx", ".csv", ".txt"]

    def matches(self, path: str) -> bool:
        return False

    def load_orders(self, path: str) -> pd.DataFrame:
        raise NotImplementedError("Amazon export mapping not defined yet (%s)" % os.path.basename(path))
