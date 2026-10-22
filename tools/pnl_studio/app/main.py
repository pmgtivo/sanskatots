"""FastAPI app for PnL Studio — local-only marketplace P&L dashboard."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import engine, fees, loader, platforms, report
from .config_store import load_config, platform_settings, resell_rate_for, save_config
from .gst import config_store as gst_config
from .gst import engine as gst_engine
from .gst import loader as gst_loader
from .gst import report as gst_report
from .settings import ALLOWED_UPLOAD_EXT, REPO_ROOT, STATIC_DIR, UPLOAD_DIR

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

app = FastAPI(title="SanskaTots PnL Studio", docs_url=None, redoc_url=None)


def _check_month(month: str) -> str:
    if not MONTH_RE.match(month or ""):
        raise HTTPException(400, "month must be YYYY-MM")
    return month


def _check_platform(key: str) -> str:
    adapter = platforms.ADAPTERS.get(key)
    if adapter is None:
        raise HTTPException(404, "unknown platform %r" % key)
    if not adapter.implemented:
        raise HTTPException(400, "%s support is not implemented yet" % adapter.label)
    return key


def _run(platform: str, month: str, resell_rate: Optional[float], return_ship: Optional[float]) -> Dict[str, Any]:
    cfg = load_config()
    data = loader.load_platform(platform)
    pf = platform_settings(cfg, platform)
    rate = resell_rate if resell_rate is not None else resell_rate_for(cfg, platform, month)
    if not 0.0 <= rate <= 1.0:
        raise HTTPException(400, "resell_rate must be between 0 and 1")
    ship = return_ship if return_ship is not None else float(pf.get("return_shipping_per_order", 0))
    model = fees.model_for(cfg, platform)
    orders = fees.apply(data["orders"], model, ship)
    result = engine.compute(orders, data["ads"], cfg, platform, month, rate, ship)
    result["fee_model"] = model if result.get("settlement_estimated") else None
    result["sources"] = {
        "files": [{"name": f["name"], "rel": f["rel"], "settled": f["settled"], "kind": f.get("kind", ""),
                   "order_rows": f.get("order_rows", 0), "ad_rows": f.get("ad_rows", 0),
                   "duplicates": f["duplicates"]} for f in data["files"]],
        "rows_before_dedupe": data["rows_before_dedupe"],
        "rows_after_dedupe": data["rows_after_dedupe"],
        "errors": data["errors"],
    }
    return result


@app.get("/api/platforms")
def api_platforms() -> Dict[str, Any]:
    return {"platforms": [
        {"key": a.key, "label": a.label, "implemented": a.implemented}
        for a in platforms.ADAPTERS.values()
    ]}


@app.get("/api/datasets")
def api_datasets(platform: str = Query("meesho")) -> Dict[str, Any]:
    _check_platform(platform)
    data = loader.load_platform(platform)
    months = loader.available_months(data["orders"])
    cfg = load_config()
    return {
        "platform": platform,
        "months": [{"month": m, "label": engine.month_label(m),
                    "resell_rate": resell_rate_for(cfg, platform, m)} for m in months],
        "files": [{"name": f["name"], "rel": f["rel"], "settled": f["settled"], "kind": f.get("kind", ""),
                   "order_rows": f.get("order_rows", 0), "ad_rows": f.get("ad_rows", 0),
                   "duplicates": f["duplicates"]} for f in data["files"]],
        "rows_before_dedupe": data["rows_before_dedupe"],
        "rows_after_dedupe": data["rows_after_dedupe"],
        "errors": data["errors"],
    }


@app.get("/api/summary")
def api_summary(month: str = Query(...)) -> Dict[str, Any]:
    """One month across every platform that has data: the monthly close view."""
    month = _check_month(month)
    sums = ("orders", "units_sold", "gross_sale", "settlement", "gross_profit", "ad_spend",
            "net_profit", "return_loss", "claims_received", "failed", "closed", "cancelled")
    totals: Dict[str, Any] = {k: 0 for k in sums}
    rows: List[Dict[str, Any]] = []
    for adapter in platforms.active():
        result = _run(adapter.key, month, None, None)
        if not result.get("has_data"):
            rows.append({"platform": adapter.key, "label": adapter.label, "has_data": False})
            continue
        k, ret = result["kpis"], result["returns"]["summary"]
        row = {
            "platform": adapter.key, "label": adapter.label, "has_data": True,
            "estimated": result["settlement_estimated"],
            "orders": k["orders"], "units_sold": k["units_sold"], "gross_sale": k["gross_sale"],
            "settlement": k["settlement"], "gross_profit": k["gross_profit"],
            "ad_spend": k["ad_spend"], "net_profit": k["net_profit"], "np_per_unit": k["np_per_unit"],
            "net_margin": k["net_margin_on_gross"],
            "return_pct": ret["return_pct"], "rto_pct": ret["rto_pct"], "fail_pct": ret["fail_pct"],
            "failed": ret["failed"], "closed": ret["closed"], "in_transit": ret["in_transit"],
            "return_loss": ret["loss"], "claims_received": result["returns"]["claims"]["received"],
            "cancelled": ret["cancelled"],
        }
        rows.append(row)
        for key in sums:
            totals[key] += row[key]
    totals = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in totals.items()}
    totals["fail_pct"] = round(totals["failed"] / totals["closed"] * 100, 2) if totals["closed"] else 0.0
    totals["estimated"] = any(r.get("estimated") for r in rows)
    return {"month": month, "month_label": engine.month_label(month), "platforms": rows, "totals": totals}


@app.get("/api/pnl")
def api_pnl(
    platform: str = Query("meesho"),
    month: str = Query(...),
    resell_rate: Optional[float] = Query(None),
    return_shipping: Optional[float] = Query(None),
) -> Dict[str, Any]:
    _check_platform(platform)
    return _run(platform, _check_month(month), resell_rate, return_shipping)


@app.get("/api/compare")
def api_compare(
    platform: str = Query("meesho"),
    months: str = Query(...),
) -> Dict[str, Any]:
    _check_platform(platform)
    wanted = [_check_month(m.strip()) for m in months.split(",") if m.strip()]
    if not wanted:
        raise HTTPException(400, "no months given")
    results = [_run(platform, m, None, None) for m in sorted(set(wanted))]
    return engine.compare(results)


@app.get("/api/report")
def api_report(
    platform: str = Query("meesho"),
    month: str = Query(...),
    resell_rate: Optional[float] = Query(None),
    return_shipping: Optional[float] = Query(None),
) -> Dict[str, Any]:
    _check_platform(platform)
    result = _run(platform, _check_month(month), resell_rate, return_shipping)
    return {"markdown": report.render(result), "filename": _report_name(platform, month)}


@app.post("/api/report/save")
def api_report_save(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    platform = _check_platform(payload.get("platform", "meesho"))
    month = _check_month(payload.get("month", ""))
    target = _resolve_report_path(payload.get("path"), platform, month)
    rel = os.path.relpath(target, REPO_ROOT)
    if os.path.exists(target) and not payload.get("overwrite"):
        raise HTTPException(409, "%s already exists — confirm to overwrite it" % rel)
    result = _run(platform, month, payload.get("resell_rate"), payload.get("return_shipping"))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(report.render(result))
    return {"saved": rel}


@app.get("/api/config")
def api_config() -> Dict[str, Any]:
    return load_config()


@app.put("/api/config")
def api_config_save(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        return save_config(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/upload")
async def api_upload(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    saved, rejected = [], []
    for upload in files:
        name = os.path.basename(upload.filename or "")
        if not name or os.path.splitext(name)[1].lower() not in ALLOWED_UPLOAD_EXT:
            rejected.append({"name": upload.filename, "reason": "unsupported file type"})
            continue
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        target = os.path.join(UPLOAD_DIR, name)
        size = 0
        too_big = False
        with open(target, "wb") as fh:
            while True:
                chunk = await upload.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    too_big = True
                    break
                fh.write(chunk)
        if too_big:
            os.unlink(target)
            rejected.append({"name": name, "reason": "file larger than 50 MB"})
            continue
        detected = platforms.detect(target)
        if detected is None:
            os.unlink(target)
            rejected.append({"name": name, "reason": "no marketplace adapter recognised this file"})
        else:
            saved.append({"name": name, "platform": detected.key})
    return {"saved": saved, "rejected": rejected}


def _report_name(platform: str, month: str) -> str:
    label = engine.month_label(month).replace(" ", "")
    return "SanskaTots_%s_PnL_%s.md" % (platforms.get(platform).label, label)


def _resolve_report_path(raw: Optional[str], platform: str, month: str) -> str:
    if raw:
        candidate = os.path.abspath(os.path.join(REPO_ROOT, raw))
        if os.path.commonpath([candidate, REPO_ROOT]) != REPO_ROOT:
            raise HTTPException(400, "report path must stay inside the repository")
        if not candidate.endswith(".md"):
            raise HTTPException(400, "report path must end with .md")
        return candidate
    folder = os.path.join(REPO_ROOT, "Finance", "Profit_Loss", month, "Reports")
    return os.path.join(folder, _report_name(platform, month))


# ---------------------------------------------------------------------------
# GST module
# ---------------------------------------------------------------------------

def _gst_run(periods: List[str]) -> Dict[str, Any]:
    cfg = gst_config.load_config()
    data = gst_loader.load_all()
    wanted = [_check_month(p.strip()) for p in periods if p.strip()]
    if not wanted:
        raise HTTPException(400, "no tax period given")
    result = gst_engine.compute(data["lines"], wanted, cfg, data.get("documents"))
    provenance = {k: data[k] for k in ("files", "errors", "rows_before_dedupe",
                                       "rows_after_dedupe", "rows_dropped")}
    return {"result": result, "provenance": provenance}


@app.get("/api/gst/periods")
def api_gst_periods() -> Dict[str, Any]:
    data = gst_loader.load_all()
    periods = gst_loader.available_periods(data["lines"])
    return {
        "periods": [{"period": p, "label": gst_engine.period_label(p)} for p in periods],
        "files": data["files"],
        "errors": data["errors"],
        "rows_before_dedupe": data["rows_before_dedupe"],
        "rows_after_dedupe": data["rows_after_dedupe"],
        "rows_dropped": data["rows_dropped"],
    }


@app.get("/api/gst")
def api_gst(periods: str = Query(...)) -> Dict[str, Any]:
    return _gst_run(periods.split(","))


@app.get("/api/gst/report")
def api_gst_report(periods: str = Query(...)) -> Dict[str, Any]:
    payload = _gst_run(periods.split(","))
    wanted = payload["result"]["periods"]
    name = wanted[0] if len(wanted) == 1 else "%s_to_%s" % (wanted[0], wanted[-1])
    return {
        "markdown": gst_report.render(payload["result"], payload["provenance"]),
        "filename": "GST_Filing_Pack_%s.md" % name,
    }


@app.post("/api/gst/report/save")
def api_gst_report_save(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    periods = payload.get("periods") or []
    if isinstance(periods, str):
        periods = periods.split(",")
    run = _gst_run(periods)
    wanted = run["result"]["periods"]
    name = wanted[0] if len(wanted) == 1 else "%s_to_%s" % (wanted[0], wanted[-1])
    default = os.path.join("Finance", "GST Fillings", "GST_Filing_Pack_%s.md" % name)
    target = _resolve_gst_path(payload.get("path"), default)
    rel = os.path.relpath(target, REPO_ROOT)
    if os.path.exists(target) and not payload.get("overwrite"):
        raise HTTPException(409, "%s already exists — confirm to overwrite it" % rel)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(gst_report.render(run["result"], run["provenance"]))
    return {"saved": rel}


@app.get("/api/gst/config")
def api_gst_config() -> Dict[str, Any]:
    return gst_config.load_config()


@app.put("/api/gst/config")
def api_gst_config_save(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        return gst_config.save_config(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _resolve_gst_path(raw: Optional[str], default: str) -> str:
    candidate = os.path.abspath(os.path.join(REPO_ROOT, raw or default))
    if os.path.commonpath([candidate, REPO_ROOT]) != REPO_ROOT:
        raise HTTPException(400, "report path must stay inside the repository")
    if not candidate.endswith(".md"):
        raise HTTPException(400, "report path must end with .md")
    return candidate


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.exception_handler(ValueError)
def value_error_handler(request, exc: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
