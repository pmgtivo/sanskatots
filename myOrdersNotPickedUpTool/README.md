# Meesho "Orders Not Picked Up" Tool

Extracts Meesho **sub-order IDs** from downloaded shipping label PDFs and groups them by
**delivery partner** (Delhivery / Xpress Bees / Shadowfax / ...).

Use it when the delivery boy misses a pickup and you need to raise the issue on Meesho
per courier partner.

## What it does

1. Reads every page of the label PDFs you point it at.
2. Picks up the sub-order ID from the `Order No.` field under *Product Details*
   (format `327738730993537539_1`). A label with multiple items yields multiple IDs.
3. Detects the courier from the line directly above `Pickup` on the label, with a
   whole-page keyword fallback.
4. De-duplicates IDs and prints them **comma-separated, grouped by partner**.
5. Optionally writes one `.xlsx` (and/or `.csv`) per partner in the Meesho template
   format: `Sub Order Num` in `A1`, one ID per row below.

Non-Meesho PDFs in the same folder (Amazon / Flipkart / raw courier labels) are skipped
with a warning instead of breaking the run.

## Requirements

- Python 3.9+
- [PyMuPDF](https://pymupdf.readthedocs.io/) — `python3 -m pip install pymupdf`

No Excel library is needed; the `.xlsx` is written with the standard library.

## Usage

```bash
cd myOrdersNotPickedUpTool

# Default: scan every PDF in this folder, print IDs grouped by partner
python3 meesho_not_picked_up.py

# Scan a specific folder (recursive) or specific files
python3 meesho_not_picked_up.py ../labels_sample_files
python3 meesho_not_picked_up.py Sub_Order_Labels_1b4472de.pdf other.pdf

# Also write one Excel file per delivery partner
python3 meesho_not_picked_up.py --excel

# Excel + CSV into a custom folder
python3 meesho_not_picked_up.py --excel --csv -o ~/Desktop/not-picked-up
```

### Options

| Option | Description |
| --- | --- |
| `inputs` | PDF files and/or folders to scan. Folders are searched recursively. Defaults to the script's own folder. |
| `-x`, `--excel` | Also write one `.xlsx` per delivery partner. |
| `--csv` | Also write one `.csv` per delivery partner. |
| `-o`, `--output-dir` | Where to write the `.xlsx` / `.csv` files. Default: `./output`. |
| `-h`, `--help` | Show help. |

Output files are named `My-orders-are-not-picked-up-yet-<Partner>.xlsx`.

## Example output

```
$ python3 meesho_not_picked_up.py

Delhivery (8)
327844096943182339_1,327889506964685953_1,327889506964685953_2,...

Shadowfax (8)
327738730993537539_1,327740045934366272_1,327796276907332352_1,...

Xpress Bees (13)
327740824764928768_1,327783070805643904_1,327871210199306881_1,...

Total: 29 sub-orders across 3 partner(s).
```

The sub-order lists go to **stdout**; progress, totals and warnings go to **stderr**, so
you can pipe just the IDs:

```bash
python3 meesho_not_picked_up.py 2>/dev/null | pbcopy
```

## Typical workflow

1. In Meesho Supplier Panel, download the labels of the orders that were not picked up.
2. Drop the PDFs into this folder (or keep them in a dated folder and pass its path).
3. Run the tool.
4. Copy the comma-separated IDs for a partner into the Meesho complaint form, or upload
   the generated `.xlsx` for that partner.

## Adding a new courier

If Meesho onboards another partner, add it to `KNOWN_COURIERS` in
[meesho_not_picked_up.py](meesho_not_picked_up.py) — the key is the courier name in
lowercase with all non-letters removed (e.g. `"xpressbees"`), the value is the display
name used in the output and filename.
