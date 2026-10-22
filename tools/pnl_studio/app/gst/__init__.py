"""GST return preparation for marketplace sellers.

``loader`` finds and parses the marketplace GST reports, ``engine`` turns them
into the exact boxes of GSTR-1 and GSTR-3B, and ``report`` renders the filing
pack. ``rules`` holds the statutory reference data, isolated so a law change is
a one-file edit.
"""

from __future__ import annotations

from . import config_store, engine, loader, report, rules, sources

__all__ = ["config_store", "engine", "loader", "report", "rules", "sources"]
