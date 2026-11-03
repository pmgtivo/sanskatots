#!/usr/bin/env python3
"""Amazon label packer.

Amazon order PDFs come as pairs of pages: a shipping label (barcode + address,
no product info) followed by the tax invoice (product title + quantity).

For every pair this tool reads the product title(s), SKU and quantity from the
invoice page, stamps them into the blank space of the shipping label page and
drops the invoice page. All labels from all given PDFs are merged into ONE pdf,
so the packer knows what goes into the box without printing the invoice.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

OUTPUT_PREFIX = "amazon_merged_"

ASIN_SKU_RE = re.compile(r"\|?\s*([A-Z0-9]{10})\s*\(\s*([^)]*?)\s*\)\s*$")
HSN_RE = re.compile(r"\s*HSN\s*:\s*\d+\s*$", re.I)
ORDER_NO_RE = re.compile(r"Order\s*Number\s*:?\s*(\d{3}-\d{7}-\d{7})", re.I)
LABEL_ORDER_RE = re.compile(r"Order\s*Id\s*:?\s*(\d{3}\s*[-–]\s*\d{7}\s*[-–]\s*\d{7})", re.I)


@dataclass
class Item:
    title: str
    sku: str
    qty: int


@dataclass
class Invoice:
    order_no: str
    items: list[Item] = field(default_factory=list)


def is_invoice_page(page: fitz.Page) -> bool:
    text = page.get_text()
    return bool(re.search(r"Tax\s*Invoice|Bill\s*of\s*Supply|Cash\s*Memo", text, re.I)) or bool(
        ORDER_NO_RE.search(text) and "Description" in text
    )


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_invoice_page(page: fitz.Page) -> Invoice:
    """Extract order number and (title, sku, qty) rows from an Amazon tax invoice page."""
    text = page.get_text()
    m = ORDER_NO_RE.search(text)
    invoice = Invoice(order_no=m.group(1) if m else "")

    words = page.get_text("words")
    desc = next((w for w in sorted(words, key=lambda w: (w[1], w[0])) if w[4] == "Description"), None)
    if not desc:
        return invoice
    # Header cells sit on the same row as "Description".
    header = [w for w in words if abs(w[1] - desc[1]) < 14 or abs(w[3] - desc[3]) < 14]
    unit = next((w for w in header if w[4] == "Unit"), None)
    qty_h = next((w for w in header if w[4] == "Qty"), None)
    if not (unit and qty_h):
        return invoice
    total = next((w for w in words if w[4].startswith("TOTAL") and w[1] > desc[3]), None)

    top = max(w[3] for w in header) + 1
    bottom = total[1] if total else page.rect.height
    desc_x0, desc_x1 = desc[0] - 3, unit[0] - 3
    qty_x0, qty_x1 = qty_h[0] - 8, qty_h[2] + 8

    # Each item row starts with its serial number in the first column.
    serials = sorted(
        (w for w in words if w[0] < desc_x0 and w[4].isdigit() and top <= w[1] < bottom),
        key=lambda w: w[1],
    )
    for i, s in enumerate(serials):
        y0 = s[1] - 4
        y1 = serials[i + 1][1] - 4 if i + 1 < len(serials) else bottom
        in_row = [w for w in words if y0 <= w[1] < y1]

        desc_words = sorted(
            (w for w in in_row if desc_x0 <= w[0] < desc_x1), key=lambda w: (w[5], w[6], w[7])
        )
        desc_text = HSN_RE.sub("", _clean(" ".join(w[4] for w in desc_words)))
        sku = ""
        am = ASIN_SKU_RE.search(desc_text)
        if am:
            sku = am.group(2).strip()
            desc_text = desc_text[: am.start()].rstrip(" |")

        qty_words = [w for w in in_row if w[0] >= qty_x0 and w[2] <= qty_x1 and w[4].isdigit()]
        qty = int(min(qty_words, key=lambda w: w[1])[4]) if qty_words else 1
        invoice.items.append(Item(title=desc_text, sku=sku, qty=qty))
    return invoice


def short_title(title: str, full: bool, max_chars: int) -> str:
    if not full:
        title = title.split("|")[0]
    title = _clean(title)
    if max_chars and len(title) > max_chars:
        title = title[: max_chars - 3].rstrip() + "..."
    return title


def latin(text: str) -> str:
    """Base-14 PDF fonts only cover Latin-1; transliterate anything else."""
    text = text.replace("₹", "Rs.")
    return unicodedata.normalize("NFKD", text).encode("latin-1", "ignore").decode("latin-1")


def build_lines(items: list[Item], full: bool, max_chars: int) -> list[str]:
    lines = []
    for it in items:
        sku = f"  [{it.sku}]" if it.sku else ""
        lines.append(latin(f"QTY {it.qty}  |  {short_title(it.title, full, max_chars)}{sku}"))
    if len(items) > 1:
        units = sum(i.qty for i in items)
        lines.insert(0, f"MULTI-ITEM ORDER: {len(items)} items, {units} units")
    return lines


def find_blank_bands(page: fitz.Page, min_height: float = 20.0):
    """Return white horizontal bands (y0, y1, x0, x1) in the lower 2/3 of the label, tallest first."""
    zoom = 2
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY)
    w, h, samples = pix.width, pix.height, pix.samples
    # Ink columns define the label's content extent (the page itself may have a white margin).
    ink_cols = [x for x in range(w) if any(samples[y * w + x] < 200 for y in range(0, h, 2))]
    if not ink_cols:
        return []
    x0, x1 = min(ink_cols), max(ink_cols)

    bands, start = [], None
    for y in range(int(h * 0.35), h):
        blank = min(samples[y * w + x0 : y * w + x1 + 1]) >= 200
        if blank and start is None:
            start = y
        elif not blank and start is not None:
            bands.append((start, y))
            start = None
    if start is not None:
        bands.append((start, h))
    result = [
        (a / zoom, b / zoom, x0 / zoom, x1 / zoom) for a, b in bands if (b - a) / zoom >= min_height
    ]
    return sorted(result, key=lambda b: b[1] - b[0], reverse=True)


FONT = "hebo"  # Helvetica-Bold
MAX_FONT, MIN_FONT, PAD = 13.0, 7.5, 4.0


def wrap(line: str, width: float, size: float) -> list[str]:
    out, cur = [], ""
    for word in line.split(" "):
        trial = f"{cur} {word}" if cur else word
        if not cur or fitz.get_text_length(trial, fontname=FONT, fontsize=size) <= width:
            cur = trial
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def fit_font_size(lines: list[str], width: float, height: float):
    """Largest font size at which the wrapped lines fit; None if even MIN_FONT does not."""
    size = MAX_FONT
    while size >= MIN_FONT:
        rows = sum(len(wrap(line, width, size)) for line in lines)
        if rows * size * 1.2 <= height:
            return size
        size -= 0.5
    return None


def draw_box(page: fitz.Page, box: fitz.Rect, lines: list[str], size: float) -> None:
    page.draw_rect(box, color=(0, 0, 0), width=1.5)
    y = box.y0 + PAD + size
    for line in lines:
        for row in wrap(line, box.width - 2 * PAD, size):
            page.insert_text((box.x0 + PAD, y), row, fontname=FONT, fontsize=size, color=(0, 0, 0))
            y += size * 1.2


def stamp_label(page: fitz.Page, lines: list[str]) -> str:
    """Write lines into the biggest blank area of the label. Returns where it was placed."""
    bands = find_blank_bands(page)
    for y0, y1, x0, x1 in bands:
        box = fitz.Rect(x0 + 6, y0 + 4, x1 - 6, y1 - 4)
        size = fit_font_size(lines, box.width - 2 * PAD, box.height - 2 * PAD)
        if size:
            rows = sum(len(wrap(line, box.width - 2 * PAD, size)) for line in lines)
            box.y1 = box.y0 + rows * size * 1.2 + 2 * PAD + 2  # hug the text, keep the rest white
            draw_box(page, box, lines, size)
            return "blank area"

    # No band is big enough: grow the page downwards so nothing on the label is covered.
    x0, x1 = (bands[0][2], bands[0][3]) if bands else (10, page.rect.width - 10)
    size = MIN_FONT + 1.5
    rows = sum(len(wrap(line, x1 - x0 - 12 - 2 * PAD, size)) for line in lines)
    needed = rows * size * 1.2 + 2 * PAD
    rect = page.rect
    page.set_mediabox(fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 + needed + 10))
    box = fitz.Rect(x0 + 6, rect.y1 + 4, x1 - 6, rect.y1 + needed + 6)
    draw_box(page, box, lines, size)
    return "extra strip"


def collect_pdfs(inputs: list[Path]) -> list[Path]:
    """Expand files/folders into PDFs, skipping merged outputs of earlier runs."""
    pdfs: list[Path] = []
    for p in inputs:
        if p.is_dir():
            pdfs += sorted(f for f in p.rglob("*.pdf") if f.is_file())
        elif p.is_file() and p.suffix.lower() == ".pdf":
            pdfs.append(p)
        else:
            print(f"! Skipping (not a PDF or folder): {p}", file=sys.stderr)
    return [f for f in pdfs if not f.name.startswith(OUTPUT_PREFIX)]


def ask_inputs() -> list[Path]:
    """Prompt for input paths (supports drag-and-drop / quoted paths, several separated by spaces)."""
    print("Enter the path of an Amazon label PDF or a folder containing PDFs.")
    print("(You can drag & drop it into this window; separate several paths with spaces.)")
    while True:
        try:
            raw = input("Input file/folder: ").strip()
        except EOFError:
            return []
        if not raw:
            continue
        paths = [Path(t).expanduser() for t in shlex.split(raw)]
        missing = [p for p in paths if not p.exists()]
        if missing:
            print("Not found: " + ", ".join(str(m) for m in missing))
            continue
        return paths


def default_output_dir(inputs: list[Path]) -> Path:
    first = inputs[0].resolve()
    return first if first.is_dir() else first.parent


def process_pdf(path: Path, out: fitz.Document, args) -> tuple[int, int]:
    """Append packed labels from one PDF to `out`. Returns (orders_stamped, warnings)."""
    done = warnings = 0
    src = fitz.open(path)
    i = 0
    while i < len(src):
        if is_invoice_page(src[i]):
            print(f"  ! {path.name} p{i + 1}: invoice page without a label before it - skipped")
            warnings += 1
            i += 1
            continue

        # Label page; gather the invoice page(s) that follow until the next label.
        j = i + 1
        invoices = []
        while j < len(src) and is_invoice_page(src[j]):
            invoices.append(parse_invoice_page(src[j]))
            j += 1
        items = [it for inv in invoices for it in inv.items]

        out.insert_pdf(src, from_page=i, to_page=i)
        if not items:
            print(f"  ! {path.name} p{i + 1}: no invoice/items found - label kept unchanged")
            warnings += 1
        else:
            order_no = next((inv.order_no for inv in invoices if inv.order_no), "?")
            label_order = LABEL_ORDER_RE.search(src[i].get_text())
            if label_order and re.sub(r"\s", "", label_order.group(1)).replace("–", "-") != order_no:
                print(f"  ! {path.name} p{i + 1}: label order id differs from invoice order {order_no}")
                warnings += 1
            where = stamp_label(out[-1], build_lines(items, args.full_title, args.max_chars))
            summary = "; ".join(f"{it.qty} x {short_title(it.title, False, 40)}" for it in items)
            print(f"  ✓ {path.name} p{i + 1} (order {order_no}): {summary}  [{where}]")
            done += 1
        i = j
    src.close()
    return done, warnings


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Write product name + quantity from the Amazon invoice page onto the shipping "
        "label page, drop the invoice page and merge everything into one PDF."
    )
    ap.add_argument("inputs", nargs="*", type=Path, help="PDF files and/or folders; asked interactively if omitted")
    ap.add_argument(
        "-o", "--output", type=Path,
        help=f"Output PDF file or folder (default: next to the input, named {OUTPUT_PREFIX}<N>_orders_<timestamp>.pdf)",
    )
    ap.add_argument("--full-title", action="store_true", help="Print the full Amazon title instead of only the part before the first '|'")
    ap.add_argument("--max-chars", type=int, default=90, help="Truncate each title to N characters, 0 = no limit (default 90)")
    args = ap.parse_args()

    inputs = [p.expanduser() for p in args.inputs] or ask_inputs()
    if not inputs:
        print("No input given.", file=sys.stderr)
        return 1
    pdfs = collect_pdfs(inputs)
    if not pdfs:
        print("No PDF files found.", file=sys.stderr)
        return 1

    out = fitz.open()
    total = warnings = 0
    for pdf in pdfs:
        print(pdf)
        try:
            d, w = process_pdf(pdf, out, args)
        except Exception as exc:  # a corrupt file must not stop the whole batch
            print(f"  ! Failed to process {pdf.name}: {exc}", file=sys.stderr)
            warnings += 1
            continue
        total += d
        warnings += w

    if len(out) == 0:
        print("Nothing to write.", file=sys.stderr)
        return 1

    name = f"{OUTPUT_PREFIX}{len(out)}_orders_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    if args.output is None:
        output = default_output_dir(inputs) / name
    elif args.output.suffix.lower() == ".pdf":
        output = args.output.expanduser()
    else:
        output = args.output.expanduser() / name
    output.parent.mkdir(parents=True, exist_ok=True)
    out.save(output, garbage=3, deflate=True)
    print(f"\nDone: {len(out)} order(s) from {len(pdfs)} file(s), {total} stamped, {warnings} warning(s).")
    print(f"Output: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
