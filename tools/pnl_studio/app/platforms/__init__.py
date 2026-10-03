"""Marketplace adapter registry."""

from __future__ import annotations

from typing import Dict, List, Optional

from .amazon import AmazonAdapter
from .base import PlatformAdapter
from .flipkart import FlipkartAdapter
from .meesho import MeeshoAdapter

ADAPTERS: Dict[str, PlatformAdapter] = {
    a.key: a for a in (MeeshoAdapter(), FlipkartAdapter(), AmazonAdapter())
}


def get(key: str) -> PlatformAdapter:
    if key not in ADAPTERS:
        raise KeyError("unknown platform %r" % key)
    return ADAPTERS[key]


def active() -> List[PlatformAdapter]:
    return [a for a in ADAPTERS.values() if a.implemented]


def detect(path: str) -> Optional[PlatformAdapter]:
    for adapter in active():
        try:
            if adapter.matches(path):
                return adapter
        except Exception:
            continue
    return None
