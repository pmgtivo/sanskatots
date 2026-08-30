# Order Command Center

One Chrome extension to run Amazon, Flipkart and Meesho orders from a single screen:
pack-and-ship pipeline, scan-to-pack, returns/RTO tracking, and weekly/monthly profit reports.

**All data stays on your computer.** Nothing is uploaded anywhere. There is no account,
no server and no internet call. The trade-off: you must take a backup yourself (one click, Settings tab).

---

## Install (2 minutes, one time)

1. Open Chrome and go to `chrome://extensions`
2. Turn on **Developer mode** (toggle, top-right)
3. Click **Load unpacked**
4. Select this folder: `tools/order_command_center`
5. The dashboard opens automatically. Pin the extension for quick access.

To open it later: click the extension icon → **Open dashboard**.

> Keep this folder where it is. If you move or delete it, Chrome unloads the extension.
> Your data survives (it lives in the browser profile), but take a backup before moving things.

---

## First-time setup (10 minutes, one time)

1. **Import one order file** from each platform (see below) so the SKUs are known.
2. Go to **SKUs & Costs** → click **Pull SKUs from my orders**.
3. Fill the **cost price** for each SKU — what one unit actually costs you to make/buy.
   Without this, profit numbers are meaningless.
4. Go to **Settings** → **Platform fees** and put in your real numbers from the
   settlement reports. Defaults are reasonable India values, not your actual contract:

   | Platform | Default assumption |
   |---|---|
   | Amazon | 12% commission + ₹25 fixed + ₹65 shipping + 18% GST on those fees |
   | Flipkart | 12% commission + ₹20 fixed + ₹60 shipping + 18% GST on those fees |
   | Meesho | "price already net of fees" — the supplier price you import is treated as take-home |

   If a platform pays you a final settled amount, tick **price already net of fees** and
   leave commission/shipping at 0, otherwise fees get double-counted.

---

## Getting orders in

### Way 1 — CSV import (dependable, use this daily)

| Platform | Where to download |
|---|---|
| Amazon | Seller Central → Orders → **Order Reports** → request "Unshipped" or "All orders" → download the `.txt` |
| Flipkart | Seller Hub → Orders → **Download** → all orders CSV |
| Meesho | Supplier Panel → Orders → **Download** order CSV (use the Payments CSV when you want settled prices) |

Drop the file(s) on the **Import** tab. Columns are auto-detected; correct any that look wrong
and hit Import. You can drop several files at once — they are processed one after another.

**Re-importing the same file is safe.** Existing lines are updated, and your manual packing
progress is never rewound (a stale file that says "New" will not undo a "Packed" you already did).

### Way 2 — Grab from the panel page (helper)

When you are on a seller panel with the order list on screen, a black bar appears bottom-right:
**Grab orders from this page**. It reads the visible table. Handy for a quick top-up, but
platforms change their pages often, so treat CSV as the source of truth.

### Way 3 — Add one order by hand

Bottom of the **Import** tab. For a manual/WhatsApp/exhibition order.

---

## Daily routine

**Pack & Ship** tab is a 3-lane conveyor belt. Work left to right:

1. **Print label** — print label + invoice in the seller panel, then click *Label done*
2. **Pick & pack** — click *Print pick list* for a SKU-wise picking sheet, pack, click *Packed*
3. **Hand over to courier** — when pickup happens, click *Handed over*

**Scan-to-pack:** the black box at the top is always focused. Scan the barcode on the label
with a USB scanner (or type the AWB and press Enter) and the order jumps to its next step
automatically. Scan once → label printed. Scan again while packing → packed. Scan at pickup
→ handed over. Green box + high beep = found; red box + low beep = not found, stop and check.

You can also set the dropdown to a fixed step (e.g. always "Handed over") when doing a
manifest run, then scan every parcel in the pile.

**No scanner?** Every order card has the same buttons. Click instead of scan.

### Statuses

| Status | Meaning |
|---|---|
| New order | Downloaded, label not printed |
| Label printed | Label + invoice printed |
| Packed & label pasted | Item checked, packed, label stuck |
| Handed over to courier | Pickup done / manifest closed |
| In transit | On the way |
| Delivered | Money will settle |
| RTO — coming back | Customer never took it |
| RTO received back | Parcel is back with you |
| Return requested / received | Customer return |
| Exchange requested | Replacement to be shipped |
| Lost / damaged by courier | Raise a claim |
| Cancelled | Cancelled before dispatch — no money, no cost |

Anything returned lands in **Needs attention** and stays there until you open the parcel and
click **Stock back on shelf** or **Damaged — write off**, and pick a reason. That reason is
what the "Why orders come back" report groups by — the single most useful table for fixing RTO.

---

## Reports

**Reports** tab, switch between weekly (Mon–Sun) and monthly:

- Revenue booked vs **delivered revenue** (money that is actually yours)
- Platform fees, cost of goods, real profit and margin %
- RTO % and return % — watch these per platform and per SKU
- Money lost to RTO/returns
- Profit per SKU — kill the SKUs that lose money, push the ones that don't

**Export this report** gives a CSV for your CA or your own Excel. **Print** gives a clean printout.

### How profit is worked out per order line

```
delivered:  price − commission − fixed fee − shipping − GST on fees − (cost price + packaging)
RTO/return: 0 revenue, and you still pay RTO/return charge + shipping + GST + packaging
            (stock cost is only counted as lost if you mark the item damaged)
cancelled:  nothing at all
lost:       you lose the cost of goods
```

---

## Backup — do this every Friday

**Settings → Download full backup (.json)**. Keep it in Google Drive/iCloud.
If Chrome data is ever cleared or you move to a new laptop, **Restore from backup** brings
everything back. The popup nags you if the last backup is over 7 days old.

`Export all orders (.csv)` gives the same data in a spreadsheet-friendly form.

---

## Try it before using real data

The `samples/` folder has one small file per platform. Import them, set a cost price,
play with the pipeline, then **Settings → Delete all data** before starting for real.

## Checking the tool still works

Open `tests/self_test.html` through a local web server (browsers block modules on `file://`):

```bash
cd tools/order_command_center
python3 -m http.server 8781
# then open http://127.0.0.1:8781/tests/self_test.html
```

All lines should be green with **ALL TESTS PASSED** at the bottom. Run this after any code change.

---

## Limits, honestly

- Labels are generated by Amazon/Flipkart/Meesho, not here. This tool tracks them; it does not
  create courier labels or book pickups.
- Delivery status is not live-tracked. It updates when you import a fresh order file or set it
  yourself. For under 20 orders/day that is a 2-minute daily import.
- Fees are your configured estimates, not the exact settlement. Reconcile against the payment
  report monthly and adjust the numbers in Settings.
- Data lives in one Chrome profile on one computer. No multi-device sync by design.

## Folder map

```
manifest.json            extension definition
src/background.js        service worker: page-grab handling, opens dashboard
src/lib/db.js            IndexedDB storage
src/lib/model.js         statuses, status machine, profit engine
src/lib/csv.js           CSV parsing + per-platform column mapping
src/dashboard/           the main app (Pack & Ship, Orders, Import, SKUs, Reports, Settings)
src/content/grab.js      "Grab orders from this page" bar on seller panels
src/popup/               toolbar popup with today's counts
tests/self_test.html     self test
samples/                 example order files
```
