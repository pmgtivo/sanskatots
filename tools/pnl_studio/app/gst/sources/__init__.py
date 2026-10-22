"""Marketplace GST-report adapter registry.

Detection is by file *content*, never by path, so it does not matter how the
monthly folders are organised. Order matters: the two adapters with strict
signatures are tried before Flipkart's permissive alias matcher.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .amazon import AmazonGstSource
from .base import (CANCELLED, COLUMNS, CREDIT_NOTE, INVOICE, INTER, INTRA,
                   REPLACEMENT, VALUE_DOCS, GstSource, empty, file_digest,
                   finalise)
from .flipkart import FlipkartGstSource
from .meesho import MeeshoGstSource
from .registers import REGISTER_COLUMNS, detect_register

SOURCES: Dict[str, GstSource] = {
    s.key: s for s in (AmazonGstSource(), MeeshoGstSource(), FlipkartGstSource())
}

#: Every matcher keys off sheet or column names, so order only breaks ties.
_ORDER = ["amazon", "meesho", "flipkart"]


def ordered() -> List[GstSource]:
    return [SOURCES[k] for k in _ORDER]


def detect(path: str) -> Optional[GstSource]:
    for source in ordered():
        try:
            if source.matches(path):
                return source
        except Exception:
            continue
    return None


__all__ = [
    "SOURCES", "ordered", "detect", "detect_register", "REGISTER_COLUMNS",
    "GstSource", "COLUMNS", "empty", "finalise",
    "file_digest", "INVOICE", "CREDIT_NOTE", "CANCELLED", "REPLACEMENT",
    "VALUE_DOCS", "INTER", "INTRA",
]
