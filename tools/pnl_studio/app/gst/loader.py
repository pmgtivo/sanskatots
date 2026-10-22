"""Discovery, parsing and de-duplication of marketplace GST reports.

Scans the same roots as PnL Studio plus the dedicated GST folder, identifies
each file by content, and collapses duplicates. Duplication is a real hazard
here: the same monthly export is routinely saved into more than one folder, and
counting a month twice would overstate turnover.

Two de-duplication layers run:

1. **Byte-identical files** are collapsed by SHA-1 before parsing. The first
   path encountered wins; the rest are recorded as skipped so the audit trail
   still names them.
2. **Identical document lines** are collapsed on a natural key. For Amazon that
   is the shipment item id; for Meesho the sub-order number plus period plus
   document type. A sub-order legitimately appears twice when it sells in one
   month and is returned in another, so the period and document type are part
   of the key.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pandas as pd

from ..settings import REPO_ROOT, UPLOAD_DIR
from . import sources

#: Folders scanned for GST exports, most specific first.
GST_ROOTS = [
    os.path.join(REPO_ROOT, "Finance", "GST Fillings"),
    os.path.join(REPO_ROOT, "Finance"),
    UPLOAD_DIR,
]

SCAN_EXT = {".csv", ".xlsx", ".xls"}

#: Files that look like exports but are not GST reports.
SKIP_TOKENS = ("~$", ".ds_store")


def _candidate_files() -> List[str]:
    seen = set()
    out = []
    for root in GST_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in sorted(filenames):
                lower = name.lower()
                if any(token in lower for token in SKIP_TOKENS):
                    continue
                if os.path.splitext(lower)[1] not in SCAN_EXT:
                    continue
                path = os.path.join(dirpath, name)
                real = os.path.realpath(path)
                if real in seen:
                    continue
                seen.add(real)
                out.append(path)
    return out


def _dedupe_key(df: pd.DataFrame) -> pd.Series:
    """Natural key for a document line, used to drop repeated exports."""
    return (
        df["platform"].astype(str) + "|"
        + df["period"].astype(str) + "|"
        + df["doc_type"].astype(str) + "|"
        + df["order_id"].astype(str) + "|"
        + df["doc_no"].astype(str) + "|"
        + df["hsn"].astype(str) + "|"
        + df["taxable_value"].round(2).astype(str)
    )


def load_all() -> Dict[str, Any]:
    """Parse every recognised GST report found on disk.

    Returns a dict with the combined frame plus a full provenance record:
    which files were read, which were skipped as duplicates, and what failed.
    """
    frames: List[pd.DataFrame] = []
    doc_frames: List[pd.DataFrame] = []
    files: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    digests: Dict[str, str] = {}

    for path in _candidate_files():
        rel = os.path.relpath(path, REPO_ROOT)
        register = sources.detect_register(path)
        source = None if register else sources.detect(path)
        if source is None and register is None:
            continue
        platform = register.platform if register else source.key
        try:
            digest = sources.file_digest(path)
        except OSError as exc:
            errors.append({"file": rel, "error": "unreadable: %s" % exc})
            continue
        if digest in digests:
            files.append({
                "rel": rel, "platform": platform, "rows": 0,
                "skipped": "byte-identical copy of %s" % digests[digest],
            })
            continue
        digests[digest] = rel
        if register is not None:
            try:
                docs = register.load(path)
            except Exception as exc:
                errors.append({"file": rel, "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            doc_frames.append(docs)
            files.append({
                "rel": rel, "platform": platform, "rows": int(len(docs)),
                "skipped": "",
                "notes": ["document-number register: feeds Table 13 only, "
                          "carries no turnover"],
            })
            continue
        try:
            frame = source.load(path)
        except Exception as exc:  # a malformed export must not kill the run
            errors.append({"file": rel, "error": "%s: %s" % (type(exc).__name__, exc)})
            continue
        frame["source_rel"] = rel
        frames.append(frame)
        try:
            notes = source.notes(path)
        except Exception:
            notes = []
        files.append({
            "rel": rel, "platform": source.key, "rows": int(len(frame)),
            "skipped": "", "notes": notes,
        })

    if not frames:
        combined = sources.empty()
        combined["source_rel"] = []
        before = after = 0
        dropped = 0
    else:
        combined = pd.concat(frames, ignore_index=True, sort=False)
        before = int(len(combined))
        key = _dedupe_key(combined)
        # Keep repeated lines that are genuinely repeated within one file (two
        # identical units on one order); only drop cross-file repetition.
        combined["_key"] = key
        combined["_occurrence"] = combined.groupby(["_key", "source_rel"]).cumcount()
        combined = combined.drop_duplicates(subset=["_key", "_occurrence"], keep="first")
        combined = combined.drop(columns=["_key", "_occurrence"])
        after = int(len(combined))
        dropped = before - after

    if doc_frames:
        documents = pd.concat(doc_frames, ignore_index=True)
        documents = documents.drop_duplicates(subset=["platform", "kind", "doc_no"])
    else:
        documents = pd.DataFrame(columns=sources.REGISTER_COLUMNS)

    return {
        "lines": combined.reset_index(drop=True),
        "documents": documents.reset_index(drop=True),
        "files": files,
        "errors": errors,
        "rows_before_dedupe": before,
        "rows_after_dedupe": after,
        "rows_dropped": dropped,
    }


def available_periods(lines: pd.DataFrame) -> List[str]:
    if lines is None or len(lines) == 0:
        return []
    periods = sorted({p for p in lines["period"].astype(str) if len(p) == 7})
    return periods
