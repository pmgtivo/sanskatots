"""Read/write the catalog config (SKU -> book/cost map, per-platform assumptions)."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict

from .settings import CONFIG_PATH

_DEFAULT_PLATFORM = {"default_resell_rate": 0.7, "return_shipping_per_order": 0, "months": {}}


def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    cfg = validate_config(cfg)
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CONFIG_PATH), suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, CONFIG_PATH)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return cfg


def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(cfg, dict):
        raise ValueError("config must be an object")
    skus = cfg.get("skus")
    if not isinstance(skus, dict):
        raise ValueError("config.skus must be an object")
    clean_skus = {}
    for sku, meta in skus.items():
        sku = str(sku).strip()
        if not sku:
            continue
        if not isinstance(meta, dict):
            raise ValueError("config.skus['%s'] must be an object" % sku)
        book = str(meta.get("book", "")).strip()
        if not book:
            raise ValueError("SKU '%s' has no book" % sku)
        try:
            cost = float(meta.get("cost", 0))
        except (TypeError, ValueError):
            raise ValueError("SKU '%s' has a non-numeric cost" % sku)
        if cost < 0:
            raise ValueError("SKU '%s' has a negative cost" % sku)
        entry = {"book": book, "cost": cost}
        note = str(meta.get("note", "")).strip()
        if note:
            entry["note"] = note
        clean_skus[sku] = entry
    cfg["skus"] = clean_skus

    platforms = cfg.get("platforms")
    if not isinstance(platforms, dict):
        raise ValueError("config.platforms must be an object")
    for key, pf in platforms.items():
        if not isinstance(pf, dict):
            raise ValueError("config.platforms['%s'] must be an object" % key)
        pf["default_resell_rate"] = _rate(pf.get("default_resell_rate", 0.7))
        pf["return_shipping_per_order"] = max(0.0, float(pf.get("return_shipping_per_order", 0) or 0))
        months = pf.get("months") or {}
        if not isinstance(months, dict):
            raise ValueError("config.platforms['%s'].months must be an object" % key)
        for m, mo in months.items():
            if not isinstance(mo, dict):
                raise ValueError("month override '%s' must be an object" % m)
            if "resell_rate" in mo:
                mo["resell_rate"] = _rate(mo["resell_rate"])
            for field in CLAIM_FIELDS:
                if field in mo:
                    mo[field] = _money(mo[field], "%s.%s" % (m, field))
        pf["months"] = months
        if "fee_model" in pf:
            pf["fee_model"] = _fee_model(pf["fee_model"], key)
    return cfg


CLAIM_FIELDS = ("claims_filed_count", "claims_filed_amount", "claims_received_amount")


def _money(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if number < 0:
        raise ValueError("%s must not be negative" % label)
    return number


def _fee_model(model: Any, platform: str) -> Dict[str, Any]:
    if not isinstance(model, dict):
        raise ValueError("config.platforms['%s'].fee_model must be an object" % platform)
    clean: Dict[str, Any] = {}
    for field in ("commission_pct", "fee_gst_pct", "tds_pct"):
        clean[field] = _rate(model.get(field, 0))
    for field in ("fixed_fee", "fwd_shipping"):
        clean[field] = _money(model.get(field, 0), "%s.fee_model.%s" % (platform, field))
    note = str(model.get("note", "")).strip()
    if note:
        clean["note"] = note
    return clean


def _rate(value: Any) -> float:
    rate = float(value)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("resell rate must be between 0 and 1, got %r" % value)
    return rate


def platform_settings(cfg: Dict[str, Any], platform: str) -> Dict[str, Any]:
    return dict(_DEFAULT_PLATFORM, **(cfg.get("platforms", {}).get(platform) or {}))


def resell_rate_for(cfg: Dict[str, Any], platform: str, month: str) -> float:
    pf = platform_settings(cfg, platform)
    override = (pf.get("months") or {}).get(month) or {}
    return float(override.get("resell_rate", pf.get("default_resell_rate", 0.7)))
