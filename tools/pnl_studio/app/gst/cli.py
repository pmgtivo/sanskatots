"""Command line entry point for the GST module.

    python -m app.gst.cli --periods 2026-07,2026-08,2026-09
    python -m app.gst.cli --quarter 2026-Q2 --save

Run from ``tools/pnl_studio``. With no period argument every period found on
disk is reported, one pack per period plus a combined pack.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

from ..settings import REPO_ROOT
from . import config_store, engine, loader, report

#: Indian financial-year quarters: Q1 = Apr-Jun, Q2 = Jul-Sep, and so on.
QUARTER_MONTHS = {"Q1": (4, 5, 6), "Q2": (7, 8, 9), "Q3": (10, 11, 12), "Q4": (1, 2, 3)}


def _quarter_periods(spec: str) -> List[str]:
    year_part, _, quarter = spec.upper().partition("-")
    if quarter not in QUARTER_MONTHS:
        raise SystemExit("quarter must look like 2026-Q2")
    year = int(year_part)
    months = QUARTER_MONTHS[quarter]
    # Q4 of FY 2026-27 falls in calendar 2027.
    offset = 1 if quarter == "Q4" else 0
    return ["%04d-%02d" % (year + offset, m) for m in months]


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="gst", description="Prepare GST return figures")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--periods", help="comma separated YYYY-MM list")
    group.add_argument("--quarter", help="financial-year quarter, e.g. 2026-Q2")
    parser.add_argument("--save", action="store_true",
                        help="write the pack under Finance/GST Fillings/")
    parser.add_argument("--out", help="explicit output path (.md)")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    parser.add_argument("--per-month", action="store_true",
                        help="also write one pack per month in the range")
    args = parser.parse_args(argv)

    cfg = config_store.load_config()
    data = loader.load_all()
    lines = data["lines"]
    found = loader.available_periods(lines)

    if args.quarter:
        periods = _quarter_periods(args.quarter)
    elif args.periods:
        periods = [p.strip() for p in args.periods.split(",") if p.strip()]
    else:
        periods = found

    if not periods:
        print("No GST report data found. Checked:", file=sys.stderr)
        for root in loader.GST_ROOTS:
            print("  " + root, file=sys.stderr)
        return 1

    unknown = [p for p in periods if p not in found]
    if unknown:
        print("warning: no rows for %s (available: %s)"
              % (", ".join(unknown), ", ".join(found) or "none"), file=sys.stderr)

    targets = [periods]
    if args.per_month and len(periods) > 1:
        targets = [[p] for p in periods] + [periods]

    exit_code = 0
    for group_periods in targets:
        result = engine.compute(lines, group_periods, cfg, data.get("documents"))
        if args.json:
            print(json.dumps({"result": result, "provenance": {
                k: data[k] for k in ("files", "errors", "rows_before_dedupe",
                                     "rows_after_dedupe", "rows_dropped")}},
                default=str, indent=2))
            continue
        markdown = report.render(result, data)
        if args.save or args.out:
            path = args.out if (args.out and len(targets) == 1) else _default_path(group_periods)
            path = os.path.abspath(os.path.join(REPO_ROOT, path))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(markdown)
            print("saved %s" % os.path.relpath(path, REPO_ROOT))
        else:
            print(markdown)
        if any(a["severity"] == "error" for a in result["anomalies"]):
            exit_code = 2
    return exit_code


def _default_path(periods: List[str]) -> str:
    name = periods[0] if len(periods) == 1 else "%s_to_%s" % (periods[0], periods[-1])
    return os.path.join("Finance", "GST Fillings", "GST_Filing_Pack_%s.md" % name)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
