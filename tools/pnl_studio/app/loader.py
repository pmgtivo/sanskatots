"""Discover marketplace export files on disk, parse them and de-duplicate.

Export files overlap heavily (the same workbook is copied into several month
folders, and each export repeats orders from adjacent months), so everything is
de-duplicated twice: identical files by content hash, then order lines by key.
"""

from __future__ import annotations

import hashlib
import os
import warnings
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import platforms
from .platforms.base import empty_ads, empty_orders
from .settings import DATA_ROOTS, REPO_ROOT

# Meesho exports carry no default cell style; openpyxl warns once per workbook.
warnings.filterwarnings("ignore", message="Workbook contains no default style")

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# path -> (mtime, size, orders, ads)
_PARSE_CACHE: Dict[str, Tuple[float, int, pd.DataFrame, pd.DataFrame]] = {}


def _walk(root: str) -> List[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.startswith("~$") or name.startswith("."):
                continue
            if os.path.splitext(name)[1].lower() in {".xlsx", ".xls", ".csv"}:
                found.append(os.path.join(dirpath, name))
    return found


def _sha1(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def discover(platform: Optional[str] = None) -> List[Dict]:
    """Return one record per distinct file (duplicate copies collapsed)."""
    seen: Dict[str, Dict] = {}
    for root in DATA_ROOTS:
        if not os.path.isdir(root):
            continue
        for path in sorted(_walk(root)):
            adapter = platforms.detect(path)
            if adapter is None or (platform and adapter.key != platform):
                continue
            digest = _sha1(path)
            rel = os.path.relpath(path, REPO_ROOT)
            if digest in seen:
                seen[digest]["duplicates"].append(rel)
                continue
            seen[digest] = {
                "path": path,
                "name": os.path.basename(path),
                "rel": rel,
                "platform": adapter.key,
                "settled": "PREVIOUS" in os.path.basename(path).upper(),
                "size": os.path.getsize(path),
                "duplicates": [],
            }
    return list(seen.values())


def _parse(path: str, adapter) -> Tuple[pd.DataFrame, pd.DataFrame]:
    stat = os.stat(path)
    cached = _PARSE_CACHE.get(path)
    if cached and cached[0] == stat.st_mtime and cached[1] == stat.st_size:
        return cached[2], cached[3]
    orders = adapter.load_orders(path)
    ads = adapter.load_ads(path)
    _PARSE_CACHE[path] = (stat.st_mtime, stat.st_size, orders, ads)
    return orders, ads


def load_platform(platform: str) -> Dict:
    """Parse every discovered file for a platform into two de-duplicated frames."""
    adapter = platforms.get(platform)
    files = discover(platform)
    order_frames, ad_frames = [], []
    errors = []
    for rec in files:
        try:
            orders, ads = _parse(rec["path"], adapter)
        except Exception as exc:  # a corrupt/unexpected workbook must not kill the dashboard
            errors.append({"file": rec["name"], "error": str(exc)})
            continue
        rec["order_rows"] = int(len(orders))
        rec["ad_rows"] = int(len(ads))
        order_frames.append(orders)
        if len(ads):
            ad_frames.append(ads)

    orders = pd.concat(order_frames, ignore_index=True) if order_frames else empty_orders()
    ads = pd.concat(ad_frames, ignore_index=True) if ad_frames else empty_ads()

    rows_before = int(len(orders))
    if rows_before:
        orders = _dedupe_orders(orders)
    if len(ads):
        ads = ads.drop_duplicates(
            subset=["campaign", "run_date", "ad_cost", "gst", "credits", "total_cost"]
        ).reset_index(drop=True)

    return {
        "orders": orders,
        "ads": ads,
        "files": files,
        "errors": errors,
        "rows_before_dedupe": rows_before,
        "rows_after_dedupe": int(len(orders)),
    }


def available_months(orders: pd.DataFrame) -> List[str]:
    if not len(orders):
        return []
    months = orders["order_date"].dropna().dt.strftime("%Y-%m")
    return sorted(months.unique().tolist())


def _dedupe_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Collapse the three ways the same order line shows up across exports.

    1. Byte-identical repeats of the same line in overlapping exports.
    2. An "outstanding" estimate that a later "previous payment" file settles for
       a different amount — the settled row wins, the estimate is dropped.
    3. Several outstanding snapshots of the same unsettled leg — newest wins.

    A sub-order legitimately appears more than once when its sale and its refund
    settle in different months, so identical (order_id, status) pairs are only
    collapsed when they also share the same gross sale value.
    """
    df = orders.sort_values(["snapshot", "paid"], na_position="first")
    df = df.drop_duplicates(
        subset=["order_id", "status", "gross_sale", "settlement", "quantity"], keep="last"
    )
    settled_exists = df.groupby(["order_id", "status"])["paid"].transform("max").astype(bool)
    df = df[df["paid"] | ~settled_exists]
    stale = (~df["paid"]) & df.duplicated(subset=["order_id", "status", "gross_sale"], keep="last")
    return df[~stale].reset_index(drop=True)
