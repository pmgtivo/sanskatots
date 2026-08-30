# Shipping Label Cropper

Crops the **shipping label** out of an A4 courier PDF and saves a clean,
print-ready **4x6 inch** label PDF.

Supported layouts (auto-detected, no flags needed):

| Layout | What it does |
|---|---|
| **Delhivery** A4 sheet | Crops the bordered label card out of the mostly-blank A4 page |
| **Flipkart / Meesho** "Invoice + Label" sheet | Keeps the label, discards the tax-invoice half below the cut line |
| Already-4x6 PDF | Passed through untouched, so re-running is safe |

Input can be a **single PDF**, a **multi-page PDF** (each page becomes one
label) or a **folder of PDFs**.

## Install

```bash
pip install -r requirements.txt
```

(The repo's `.venv` already has both packages, so you can just use
`../../.venv/bin/python`.)

## Quick start

Output is always named after the input with ` Crop` appended.

```bash
# one file  ->  "Shipping Label 1 Crop.pdf" next to it
python crop_labels.py "Shipping Label 1.pdf"

# multi-page file  ->  "Multi Labels Crop.pdf", one 4x6 page per label
python crop_labels.py "Multi Labels.pdf"

# a whole folder  ->  "Delhivery labels Crop/" with one cropped PDF per input
python crop_labels.py "../../Delhivery labels"

# a whole folder  ->  ONE combined "Delhivery labels Crop.pdf" (bulk printing)
python crop_labels.py "../../Delhivery labels" --merge

# explicit output location
python crop_labels.py "Shipping Label 1.pdf" -o "Output/Label.pdf"
```

Use `--suffix` to change the ` Crop` text, e.g. `--suffix "_4x6"`.

## Output quality

| Need | Command |
|---|---|
| Sharpest text, smallest file (**default**) | `--mode vector` |
| High-resolution image output | `--mode raster --dpi 600` |
| Maximum quality image | `--mode raster --dpi 1200 --sharpen` |
| Darker / bolder text | `--mode raster --dpi 600 --sharpen --contrast 1.4` |
| Thermal printer (pure black & white) | `--mode raster --dpi 600 --sharpen --mono` |

* **`vector` (default)** keeps the original text, barcodes and QR codes as
  vectors, so the label stays perfectly sharp at *any* print size or zoom level
  and the file stays tiny. This is the highest possible text quality.
* **`raster`** re-renders the label as an image at `--dpi`. Use it when your
  printer or courier portal needs a flattened image, or when you want the extra
  `--sharpen` / `--contrast` / `--mono` text-crispening options.
  `--dpi 300` = good, `600` = better (default), `1200` = maximum.

## Page geometry

| Option | Purpose |
|---|---|
| `--size 4x6` | Output page size (default). Also `6x4`, `a6`, `a5`, `auto`, or custom like `--size 100x150mm` |
| `--size auto` | Page is exactly the cropped label size — no whitespace, no scaling |
| `--fit contain` | Keeps the label's aspect ratio, centred (default) |
| `--fit stretch` | Stretches the label to fill the whole page edge to edge |
| `--margin 6` | Adds a white border, in points (72 pt = 1 inch) |
| `--pad 2` | Extra padding around the detected label, in points |
| `--region X0 Y0 X1 Y1` | Skip auto-detection and crop an exact rectangle |

## Other options

| Option | Purpose |
|---|---|
| `-o, --output` | Output PDF file, or output folder in batch mode |
| `--suffix` | Text appended to the input name (default: ` Crop`) |
| `-r, --recursive` | Also process PDFs in sub-folders |
| `--merge` | Batch mode: write every label into a single PDF |
| `-v, --verbose` | Print the detected crop box and method for each page |

## How label detection works

For every page the tool:

1. Looks for the dashed **"cut here"** line that separates the label from the
   tax invoice, and keeps everything above it.
2. If there is no dashed line, it falls back to the first **"Tax Invoice" /
   "Bill of Supply" / "Sold By"** heading and keeps everything above that.
3. Looks for the bordered **label card** rectangle (inside that limit, if one
   was found) and crops exactly to it. This is what handles Delhivery sheets,
   where the label sits in the middle of a blank A4 page and there is no
   invoice section at all.
4. If there is no card border either, it shrink-wraps the crop to the actual
   printed content (text, boxes, barcodes, QR codes) so there is no wasted
   whitespace.

Pages that are already label sized (≤ 380 x 700 pt) are passed through
unchanged, so re-running the tool on its own output is safe.

If a particular courier's layout is not detected correctly, run once with
`-v` to see the detected box, then pin it down with `--region X0 Y0 X1 Y1`.

## Examples

```bash
# The Delhivery labels in this repo -> one print-ready file
python crop_labels.py "../../Delhivery labels" --merge

# 200 orders -> one print-ready file for a thermal printer
python crop_labels.py ./orders_july -o ./labels/july_labels.pdf \
    --merge --mode raster --dpi 600 --sharpen --mono
```
