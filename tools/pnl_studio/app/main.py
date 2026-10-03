"""FastAPI app for PnL Studio — local-only marketplace P&L dashboard."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import engine, loader, platforms, report
from .config_store import load_config, platform_settings, resell_rate_for, save_config
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
    result = engine.compute(data["orders"], data["ads"], cfg, platform, month, rate, ship)
    result["sources"] = {
        "files": [{"name": f["name"], "rel": f["rel"], "settled": f["settled"],
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
        "files": [{"name": f["name"], "rel": f["rel"], "settled": f["settled"],
                   "order_rows": f.get("order_rows", 0), "ad_rows": f.get("ad_rows", 0),
                   "duplicates": f["duplicates"]} for f in data["files"]],
        "rows_before_dedupe": data["rows_before_dedupe"],
        "rows_after_dedupe": data["rows_after_dedupe"],
        "errors": data["errors"],
    }


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
    folder = "%s_Profit_Loss" % engine.month_label(month)[:3]
    return os.path.join(REPO_ROOT, "Finance", folder, _report_name(platform, month))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.exception_handler(ValueError)
def value_error_handler(request, exc: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=400)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
