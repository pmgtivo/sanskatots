# Amazon Label Packer

Amazon downloads each order as **2 pages**: page 1 = shipping label (no product info),
page 2 = tax invoice (product title, SKU, qty). This tool:

1. Pairs every label page with the invoice page(s) that follow it (works for any number of orders per PDF).
2. Reads product title, SKU and quantity from the invoice (multi-item orders supported).
3. Writes `QTY n | Product name [SKU]` in a box on the label, in the largest blank area (auto-detected; if the label is full, a strip is added below instead of covering anything).
4. Drops the invoice pages and merges all labels from all inputs into **one PDF**.

## Usage

The tool is standalone (one script + PyMuPDF) and not tied to any folder; copy it anywhere.

```bash
pip install -r requirements.txt

# Asks for the input file/folder (drag & drop works)
python3 pack_labels.py

# Or pass them directly: PDF files and/or folders (folders are searched recursively)
python3 pack_labels.py ~/Downloads/amazon_labels
python3 pack_labels.py order1.pdf order2.pdf -o ~/Desktop
```

Output: `amazon_merged_<N>_orders_<timestamp>.pdf`, saved next to the input (inside the folder if you gave a folder).
Earlier `amazon_merged_*` files are ignored on later runs.

| Option | Description |
| --- | --- |
| `-o`, `--output` | Output folder, or a full `.pdf` path. |
| `--full-title` | Print the whole Amazon title instead of only the part before the first `\|`. |
| `--max-chars N` | Truncate each title to N characters (default 90, `0` = no limit). |

Warnings are printed for invoice pages with no label, labels with no invoice (kept unchanged), or a label/invoice order-ID mismatch.

Note: pairing is by page order (label, then its invoice), which is how Amazon generates the file.
