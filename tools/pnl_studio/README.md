# PnL Studio

Browser-based profit & loss for marketplace sales. Replaces the per-month
`*_book_pnl.py` / `*_cohort_pnl.py` scripts with one tool that works for any
month, re-runs instantly when you change an assumption, and exports the same
markdown report format.

Meesho is implemented today. Flipkart and Amazon are stubbed behind the same
adapter interface.

## Start it

```sh
tools/pnl_studio/run.sh
```

That creates `.venv` if missing, installs dependencies on first run, starts the
server on <http://127.0.0.1:8777> and opens your browser. `Ctrl-C` stops it.

### Alias

Add to `~/.zshrc`, then `source ~/.zshrc`:

```sh
alias pnl='~/sourcecode/Deethya/sanskatots/tools/pnl_studio/run.sh'
```

Now just run `pnl`.

Environment overrides: `PNL_PORT=9000`, `PNL_NO_BROWSER=1`, `PNL_RELOAD=1`.

## How it works

**Cohort rule.** An order belongs to the month it was *placed* in — never the
month of the file it arrived in. Export files always contain spillover rows from
adjacent months.

**File discovery.** Everything under `Finance/` and `tools/pnl_studio/uploads/`
is scanned recursively, so it does not matter whether a month's workbooks sit in
the month folder or in a `Meesho_platform/` subfolder. Files are matched to a
platform by content, not by path.

**De-duplication** happens in three layers, because the same order line shows up
repeatedly across exports:

1. Byte-identical file copies are collapsed by SHA-1 (e.g. the September
   workbook that also sits in `Aug_Profit_Loss/Meesho_platform/`).
2. An `OUTSTANDING` estimate is dropped once a later `PREVIOUS PAYMENT` file
   settles that same line for a different amount.
3. Multiple outstanding snapshots of the same unsettled leg collapse to the
   newest.

A sub-order legitimately appears twice when its sale and its refund settle in
different months, so those legs are preserved.

**P&L definitions.**

| Term | Definition |
| --- | --- |
| Units sold | delivered + in transit + exchange |
| COGS | per-SKU manufacturing cost × units sold |
| Write-off | per-SKU cost × returned/RTO units × (1 − resell rate) |
| Settlement | what the marketplace pays, including fee-adjustment lines |
| Gross profit | settlement − COGS − write-off |
| Net profit | gross profit − ad spend |
| Return % | on *closed* orders only, excluding in-transit |
| ASP / order | gross sale ÷ orders |
| ASP / unit | gross sale ÷ units sold |

**Ad allocation.** Marketplaces report ad spend per campaign, not per SKU. Ads
are allocated pro-rata by gross sale, so per-book ACOS is identical across books
by construction. It is a modelling assumption, not an observed figure — the UI
and report both say so.

## Assumptions you control

In the **Config** tab (persisted to `config/catalog.json`):

- SKU → book mapping and per-unit manufacturing cost
- Default resell rate per platform, plus a per-month override
  (July 70%, August 50%, September 70% are pre-loaded)
- Return shipping cost per failed order (₹157 for Meesho)

The header slider overrides the resell rate for the current view without saving,
so you can see the sensitivity immediately.

## Reconciliation with the old scripts

September 2026 matches `september_cohort_pnl.py` exactly: net profit ₹31,038.54,
484 units, ₹64.13/unit, ACOS 16.07%, ROAS 6.22x, return 9.73%, RTO 4.35%.

August differs slightly — ₹23,916 here vs ₹24,231 in the published report. The
August script only read `Aug_Profit_Loss/Meesho_platform/`, so it never saw the
refund leg of an August order that settled in the September file. Scanning the
whole tree picks it up, which makes this figure the more complete one.

Saving a report refuses to overwrite an existing file unless you confirm.

## Adding Flipkart or Amazon

1. Map that marketplace's export onto the canonical columns in
   `app/platforms/base.py` (`ORDER_COLUMNS`, `AD_COLUMNS`).
2. Implement `matches()`, `load_orders()` and `load_ads()` in
   `app/platforms/flipkart.py` or `amazon.py`, and set `implemented = True`.
3. Add a `platforms` entry in `config/catalog.json`.

The engine, dashboard, report and month comparison are platform agnostic and
need no changes.

## Layout

```
app/
  main.py        FastAPI routes
  loader.py      file discovery, parsing cache, de-duplication
  engine.py      all P&L maths (platform agnostic)
  report.py      markdown report renderer
  config_store.py
  platforms/     base.py (canonical schema) + meesho.py, flipkart.py, amazon.py
static/          index.html, app.js, styles.css (no external dependencies)
config/catalog.json
uploads/         drag-dropped files land here (git-ignored)
```
