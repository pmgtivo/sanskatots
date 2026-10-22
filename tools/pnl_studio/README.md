# PnL Studio

Browser-based profit & loss for marketplace sales. Replaces the per-month
`*_book_pnl.py` / `*_cohort_pnl.py` scripts with one tool that works for any
month, re-runs instantly when you change an assumption, and exports the same
markdown report format.

Meesho, Flipkart and Amazon are all implemented. Meesho's payment files carry
real fees and payouts. Flipkart's and Amazon's order reports do not, so their
fees are **modelled** from rates in the Config tab and flagged *estimated*
everywhere they appear.

## Monthly close

```
Finance/Profit_Loss/<YYYY-MM>/
    Amazon/     All Orders report (.txt)  +  GST MTR B2C (.csv, supplies refunds)
    Flipkart/   monthly Sales Report (.xlsx)
    Meesho/     payment workbooks (PREVIOUS / OUTSTANDING)
    Reports/    markdown P&L saved from the Report tab
Finance/Profit_Loss/_legacy_scripts/    the old per-month scripts
```

1. `tools/pnl_studio/new_month.sh 2026-10` creates the folders.
2. Drop the month's downloads in. Where a file sits does not matter to the maths
   (orders are cohorted by the date they were placed); the layout is for you.
3. Open the **All Platforms** tab for the month, then **Returns** per platform.
4. **Report → Save** writes the markdown into that month's `Reports/`.

Amazon refunds only exist in the GST MTR, so keep the MTR in the same month
folder (or leave it under `GST Fillings/`; identical copies are collapsed).

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
is scanned recursively. Files are matched to a platform by content, not by path.

**De-duplication** happens in three layers, because the same order line shows up
repeatedly across exports:

1. Byte-identical file copies are collapsed by SHA-1 (e.g. the September
   workbook that also sits in `Profit_Loss/2026-08/Meesho/`).
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
August script only read the August Meesho folder, so it never saw the
refund leg of an August order that settled in the September file. Scanning the
whole tree picks it up, which makes this figure the more complete one.

Saving a report refuses to overwrite an existing file unless you confirm.

## Flipkart and Amazon P&L

| Platform | Files read | What they give | What they do not |
| --- | --- | --- | --- |
| Flipkart | monthly Sales Report `.xlsx` | sales, returns, cancellations, state, COD/prepaid, bank-offer cashback, TDS | commission, shipping, payouts, claims, return reasons |
| Amazon | All Orders `.txt` + GST MTR `.csv` | orders, cancellations, price, promo discount, state, refunds (from the MTR) | fees, payouts, claims, return reasons |

* **Events become orders.** Flipkart's report is an event ledger. An order item
  can be sold, returned, the return revoked and returned again, so only the net
  of its events decides the outcome (`Taxable Value` carries the sign; `Final
  Invoice Amount` does not).
* **Open orders.** Neither report says an order was delivered. Anything placed
  within 14 days of the data's last date counts as still open and is left out of
  the return rate, whose denominator is closed orders only.
* **Cancellations** never shipped. They are reported separately and excluded from
  orders, revenue and the return rate.
* **Flipkart cashback** (the Cash Back Report) is money the platform pays the
  seller for bank-funded offers, so it is added to settlement.
* **Amazon times** are UTC in the export and are converted to Indian time before
  the month is decided.
* **Estimated fees.** Config → each platform holds commission %, fixed fee per
  order, forward shipping per order, GST on fees and a TDS fallback; the
  per-failed-order return shipping sits beside them. Commission and the fixed fee
  are refunded on a return, forward shipping is not. The Amazon figures come from
  the SanskaTots plan (0% referral on books, Rs 17 closing fee, ~Rs 45 Easy
  Ship). **The Flipkart figures are placeholders.** Replace both with the rates
  in your platform settlement report, then profit is exact.

## Returns tab

For the selected platform and month:

* return %, RTO %, failed % (return + RTO), all on **closed** orders
* value refunded to customers, return shipping, written-off stock, total loss
* **claims** received, recovery % of return loss and, where entered, claimed vs
  received vs outstanding
* return rate by book, SKU, prepaid vs COD and delivery state, each flagged
  `HIGH` (1.4x the platform rate), `clean` or `low volume` (under 8 closed
  orders, too few to trust)
* plain-language notes on what stands out, and a month-by-month trend

Meesho's claims come straight from its payment file, with the reason text
(wrong product, damaged or used, missing items). Flipkart and Amazon exports
carry none, so type the month's claims filed and received into Config → the
platform's month row and they flow into the tab and the report.

## GST filing pack

The **GST Filing** tab (and `app/gst/`) turns the marketplace GST reports into
the exact box values for **GSTR-1** and **GSTR-3B**. It is deliberately separate
from the P&L engine: P&L works on *payment* data, GST works on *invoice* data,
and the two will never tie out.

Drop the exports anywhere under `Finance/GST Fillings/`. Detection is by file
*content*, not path, so the folder layout is up to you.

| Marketplace | File | Status |
| --- | --- | --- |
| Amazon | MTR B2C / B2B `.csv` | verified |
| Meesho | `tcs_sales.xlsx`, `tcs_sales_return.xlsx` | verified |
| Flipkart | monthly "Sales Report" `.xlsx` | verified |

### Flipkart: use the Sales Report, not the GSTR report

Flipkart's monthly **Sales Report** is transaction level — one row per order
item event — and by Flipkart's own description it "contains each and every b2c
invoice which was created, returned, cancelled or voided in the duration of the
month". The `Sales Report` sheet alone therefore covers every outward rupee.

The `Cash Back Report` sheet is **not** loaded into turnover. Flipkart raises
those credit/debit notes *to the seller* to reimburse bank-funded offers that
were already deducted on the customer's invoice, so they are inward
reimbursements, not outward supplies — adding them would double-count the
discount. The pack prints a note recording their count and net value.

Three things the adapter derives rather than trusts:

* **Document type comes from the sign of the value**, not the event label.
  Flipkart pre-signs returns and cancellations negative and "Return
  Cancellation" (a revoked return) positive, so netting works even if Flipkart
  invents a new event name later.
* **The tax period is the modal `Buyer Invoice Date` month.** `Order Date`
  routinely spills into the previous month and must not be used. A row dated
  outside that month is still declared in it — that is the rule for a credit
  note — and the count is reported in the notes.
* **The rate is computed from tax ÷ taxable value**, because the reported rate
  column's unit (`18` vs `0.18`) is unknowable while every line is 0%.

Flipkart's *other* GST download — the pre-aggregated "GSTR-1 and GSTR-8"
workbook — is recognised and **rejected**, because keeping both reports for the
same month would count the turnover twice.

### Meesho: Table 13 needs the invoice register too

Meesho's GST report has values but no document numbers. Download the monthly
`Tax_invoice_details.xlsx` (the `..._TAX_INVOICE` folders) as well and drop it
under `Finance/GST Fillings/Meesho GST Report/Invoices/`. It is recognised by
its columns, carries no turnover, and is used only for Table 13.

Meesho runs three series: invoices (`<base><n>`), return credit notes
(`<base>C<n>`) and discount credit notes (`<base>CM<n>`). Numbers are issued
when the parcel is manifested, so the register can hold numbers that belong to
the next period. The engine bounds each series by the first and last number
that matches a turnover line, and counts a missing number as issued when a
turnover line has no register entry to account for it. Anything left over is
reported as cancelled with a CHECK note. Month-by-month Table 13 is therefore
only reliable for the whole quarter, not at month boundaries.

### From the command line

```sh
cd tools/pnl_studio
python -m app.gst.cli --quarter 2026-Q2            # print to stdout
python -m app.gst.cli --quarter 2026-Q2 --save    # write into Finance/GST Fillings/
python -m app.gst.cli --periods 2026-09 --json    # machine readable
```

Add `--per-month` to also emit one pack per month inside the quarter. The exit
code is `2` when any blocker-severity anomaly is found, so it is safe to use in
a pre-filing check.

### Printed books are EXEMPT, not nil-rated

This distinction drives most of the module:

- **Exempt** = listed in Notification 2/2017-Central Tax (Rate). Headings 4901,
  4902, 4903 and 4905 sit here (Sl. Nos. 119, 120, 121 and 123).
- **Nil rated** = a 0% entry in the *rate* notification 1/2017. Books are not.

Consequences the tool applies automatically:

1. Turnover goes in the **Exempted** column of GSTR-1 Table 8, never Nil Rated.
2. It goes in **GSTR-3B 3.1(c)**, a value-only box with no tax against it.
3. An exempt supply travels under a **bill of supply** (s.31(3)(c) r/w rule 49),
   not a tax invoice. Table 13 has no separate bill-of-supply line, so both
   go under "Invoices for outward supply", one row per document series.
4. **ITC is blocked** by s.17(2). The pack prints the reversal position rather
   than offering credit.

If a marketplace charges GST on a book anyway, the tool does *not* silently
zero it: s.76 requires tax actually collected to be paid over. It is reported
as a taxable supply and raised as a blocker so you can get the operator's
product tax code fixed.

### Validation before you file

Every run ends in 13 checks — invoice-value identity, tax charged on exempt
HSN, TCS on exempt supplies, invalid or legacy rates, wrong tax head for the
place of supply, missing HSN, unmapped states, the same SKU classified two
ways, GSTIN mismatch, period drift, and cancelled documents still carrying
value. Blockers change the numbers you file; checks are informational.

### Configuration

`config/gst.json` holds the GSTIN, home state, filing frequency (`qrmp` or
`monthly`), previous-year AATO (which decides 4- vs 6-digit HSN) and the
e-commerce operator GSTINs. Due dates follow the QRMP state group
(Karnataka is in the 22nd group).

> Statutory references carry a `VERIFY_SOURCES` note in `app/gst/rules.py`.
> The CBIC site could not be scraped, so confirm the citations against the
> notification text before relying on them. All rule data lives in that one
> file, so a law change is a single-file edit.

## Adding another marketplace

1. Map its export onto the canonical columns in `app/platforms/base.py`
   (`ORDER_COLUMNS`, `AD_COLUMNS`).
2. Subclass `PlatformAdapter`: `matches()`, `load_orders()`, optionally
   `load_ads()`, `kind()` and `consolidate()` (for event ledgers), and register
   it in `app/platforms/__init__.py`.
3. Add a `platforms` entry, with a `fee_model` if the export has no fees, in
   `config/catalog.json`.

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
  fees.py        modelled settlement for platforms whose exports carry no fees
  returns.py     return rates, return loss, claims, by book / SKU / state / COD
  platforms/     base.py (canonical schema) + meesho.py, flipkart.py, amazon.py
  gst/           rules.py (statute), loader.py, engine.py, report.py, cli.py,
                 sources/ (amazon.py, meesho.py, flipkart.py)
static/          index.html, app.js, styles.css (no external dependencies)
config/catalog.json
config/gst.json
uploads/         drag-dropped files land here (git-ignored)
```
