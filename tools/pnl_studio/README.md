# PnL Studio

Browser-based profit & loss for marketplace sales. Replaces the per-month
`*_book_pnl.py` / `*_cohort_pnl.py` scripts with one tool that works for any
month, re-runs instantly when you change an assumption, and exports the same
markdown report format.

Meesho, Flipkart and Amazon are all implemented, and all three are read from
their **money** reports (Meesho payment workbooks, Flipkart Settlement Report,
Amazon Unified Transaction report), so fees, TDS, ads, refunds and payouts are
the platforms' own figures. Each platform also shows what actually reached the
bank, and Returns is broken down per product.

## Monthly close

```
Finance/Profit_Loss/<YYYY-MM>/
    Amazon/     Custom Unified Transaction report (.csv)
    Flipkart/   Settlement Report (.xlsx)
    Meesho/     payment workbooks (PREVIOUS / OUTSTANDING)
    Reports/    markdown P&L saved from the Report tab
Finance/Profit_Loss/_legacy_scripts/    the old per-month scripts
```

1. `tools/pnl_studio/new_month.sh 2026-10` creates the folders.
2. Drop the month's downloads in. Where a file sits does not matter to the maths
   (orders are cohorted by the date they were placed); the layout is for you.
3. Open the **All Platforms** tab for the month, then **Returns** per platform.
4. **Report → Save** writes the markdown into that month's `Reports/`.

The old Flipkart Sales Report, Amazon All Orders and GST MTR files are no longer
read by the P&L (they carry no fees or payouts). They stay in use by the GST
Filing tab.

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
- Return shipping cost per failed order (₹157 for Meesho). For Flipkart and Amazon
  the real return fees are in the reports, so this only feeds the what-if
  sensitivity on the Risk tab.

The header slider overrides the resell rate for the current view without saving,
so you can see the sensitivity immediately. Move it and press Recalculate: every
tab that shows write-off, return loss or net profit follows it, including **All
Platforms**, where a moved slider applies to all three platforms (untouched, each
platform keeps its own configured rate). Compare Months and the Returns trend
always use each month's configured rate.

## Reconciliation with the old scripts

September 2026 matches `september_cohort_pnl.py` exactly: net profit ₹31,038.54,
484 units, ₹64.13/unit, ACOS 16.07%, ROAS 6.22x, return 9.73%, RTO 4.35%.

August differs slightly — ₹23,916 here vs ₹24,231 in the published report. The
August script only read the August Meesho folder, so it never saw the
refund leg of an August order that settled in the September file. Scanning the
whole tree picks it up, which makes this figure the more complete one.

Saving a report refuses to overwrite an existing file unless you confirm.

## Flipkart and Amazon P&L

Both platforms are read from their **money** reports, so fees, TDS, ads, refunds
and payouts are the platform's own figures; nothing is modelled.

| Platform | File read | Where to get it | What it gives |
| --- | --- | --- | --- |
| Flipkart | Settlement Report `.xlsx` | Seller Hub → Payments → Settlement Report | per order item: sale, Flipkart-funded offer, refund, every marketplace fee, reverse-shipping fee, GST, TDS/TCS, Seller Protection Fund payout, bank settlement, return type; wallet ad top-ups; NEFT payouts |
| Amazon | Custom Unified Transaction `.csv` | Seller Central → Payments → Reports Repository | sale, promo rebates, selling and other fees, Easy Ship weight fees, return handling fee on refunds, advertising charges, bank transfers, Released/Deferred status |

* **Rows become orders.** Both reports are ledgers of postings. They are folded
  back into one line per Flipkart `Order item ID` / Amazon `Order Id` + `SKU`
  across every file found, so a sale in one month and its refund in a later
  one are one order.
* **Returns.** Flipkart `Customer Return` → Return (a reverse-shipping fee plus
  GST is billed), `Logistics Return` → RTO (no fee). Amazon: a refund of at least
  half the sale is a Return and the return handling fee on the refund is the
  return cost; a smaller refund is a partial refund and the order stays sold.
* **Open orders.** Amazon `Deferred` sales are open (still inside the hold
  window). Flipkart orders placed within 14 days of the last payout are labelled
  open because their return window has not closed. Open orders are left out of
  the return rate, whose denominator is closed orders only.
* **Claims.** Flipkart's Seller Protection Fund payouts are the claims.
* **Ads.** Flipkart ad spend is the wallet top-ups netted off the payout (what
  actually left your money); Amazon's is `Cost of Advertising`.
* **Cohort month.** Flipkart orders are dated by order date. Amazon's report
  has no order date, so an order is dated by its sale posting.
* **Cancellations** are not in either report (neither platform bills a
  cancel-before-ship), so Cancelled is 0 for them.
* **Amazon times** are UTC in the export and are converted to Indian time before
  the month is decided.
* **Partial months.** Flipkart only lists settled orders, so the newest orders
  are missing until the next settlement report arrives. The tool shows the date
  range it has seen and warns when the last days of the month are absent.

### Bank settled

Each platform's Cash section now shows what **reached the bank** in the
calendar month (Amazon `Transfer` rows, Flipkart NEFT payouts, Meesho payment
dates) next to what the month's order cohort has earned. The two differ by
payout timing and the tool says by how much. For Flipkart the payout total is
checked against the report's own `Net Bank Settlement`; any gap (fines,
recoveries) shows as a separate line.

### Returns per product

**All Platforms** has *Returns by product*, *Product × platform* and *Returns by
SKU*: units sold, units returned (returns + RTO), return/RTO %, refunded value,
return fees, stock write-off, return loss, claims and gross profit, summed across
Meesho, Flipkart and Amazon. The per-platform **Returns** tab has the same
columns by book and SKU.

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
   `load_ads()`, `load_bank()` (payouts), `kind()` and `consolidate()` (for
   ledgers), and register it in `app/platforms/__init__.py`.
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
  returns.py     return rates, return loss, claims, by book / SKU / state / COD
  products.py    sales, returns and return cost per product across platforms
  platforms/     base.py (canonical schema) + meesho.py, flipkart.py, amazon.py
  gst/           rules.py (statute), loader.py, engine.py, report.py, cli.py,
                 sources/ (amazon.py, meesho.py, flipkart.py)
static/          index.html, app.js, styles.css (no external dependencies)
config/catalog.json
config/gst.json
uploads/         drag-dropped files land here (git-ignored)
```
