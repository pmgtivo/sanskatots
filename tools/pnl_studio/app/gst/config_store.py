"""Seller identity and filing preferences for the GST module."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from ..settings import TOOL_DIR

CONFIG_PATH = os.path.join(TOOL_DIR, "config", "gst.json")

DEFAULTS: Dict[str, Any] = {
    "seller": {
        "legal_name": "Sanska Tots",
        "trade_name": "SanskaTots",
        "gstin": "29CEMPR5502N1ZS",
        "state": "KARNATAKA",
        "state_code": "29",
    },
    "filing": {
        "frequency": "qrmp",
        "aato_previous_fy": 0,
        "report_wrongly_charged_tax": True,
    },
    "ecommerce_operators": {
        "amazon": {"label": "Amazon Seller Services Pvt Ltd", "gstin": ""},
        "meesho": {"label": "Fashnear Technologies Pvt Ltd (Meesho)", "gstin": "29AARCM9332R1CK"},
        "flipkart": {"label": "Flipkart Internet Pvt Ltd", "gstin": ""},
    },
}


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULTS)
        return json.loads(json.dumps(DEFAULTS))
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        stored = json.load(fh)
    return _merge(DEFAULTS, stored)


def save_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    merged = _merge(DEFAULTS, cfg or {})
    gstin = str(merged["seller"].get("gstin", "")).strip().upper()
    if gstin and len(gstin) != 15:
        raise ValueError("GSTIN must be 15 characters, got %d" % len(gstin))
    merged["seller"]["gstin"] = gstin
    if gstin:
        merged["seller"]["state_code"] = gstin[:2]
    if str(merged["filing"].get("frequency", "")).lower() not in ("monthly", "qrmp"):
        raise ValueError("filing.frequency must be 'monthly' or 'qrmp'")
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return merged
