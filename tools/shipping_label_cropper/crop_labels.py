#!/usr/bin/env python3
"""
Shipping Label Cropper
======================

Crops the shipping/courier label out of an A4 courier PDF and writes a clean,
print-ready label PDF (4x6 inch by default).

Supported layouts
-----------------
* Flipkart / Meesho style "Invoice + Label" sheets - the invoice half below the
  dashed cut line / "Tax Invoice" heading is discarded.
* Delhivery style A4 sheets - the bordered label card in the middle of an
  otherwise blank A4 page is cropped out.

Input may be a single PDF, a multi-page PDF or a folder of PDFs.  Output is
written as "<input name> Crop.pdf".

Usage
-----
    # single file -> "Shipping Label 1 Crop.pdf" next to it
    python crop_labels.py "Shipping Label 1.pdf"

    # whole folder -> "<folder> Crop/" with one cropped PDF per input
    python crop_labels.py "./Delhivery labels"

    # whole folder -> ONE combined PDF, best for bulk printing
    python crop_labels.py "./Delhivery labels" --merge

    # maximum text sharpness (vector, default) or high-DPI raster
    python crop_labels.py ./input_labels -o ./out --mode raster --dpi 600 --sharpen

Run `python crop_labels.py --help` for the full option list.
"""

from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required.  Install it with:  pip install pymupdf")

PT_PER_INCH = 72.0

# Named output page sizes, in points (width x height).
PAGE_SIZES = {
    "4x6": (4 * PT_PER_INCH, 6 * PT_PER_INCH),
    "a6": (297.6, 419.5),
    "a5": (419.5, 595.3),
    "6x4": (6 * PT_PER_INCH, 4 * PT_PER_INCH),
}

# Text that marks the start of the tax-invoice section (i.e. end of the label).
INVOICE_MARKERS = (
    "tax invoice",
    "bill of supply",
    "invoice no",
    "sold by",
    "declaration",
)

# Default suffix appended to the input name to build the output name.
DEFAULT_SUFFIX = " Crop"


# --------------------------------------------------------------------------
# Label detection
# --------------------------------------------------------------------------
@dataclass
class Detection:
    rect: fitz.Rect
    method: str


def _long_dashed_cut_lines(page: fitz.Page) -> List[float]:
    """Y positions of dashed horizontal 'cut here' separators."""
    width = page.rect.width
    ys: List[float] = []
    for drawing in page.get_drawings():
        dashes = drawing.get("dashes")
        if not dashes or dashes in ("[] 0", "[]0"):
            continue
        r = drawing["rect"]
        if r.height <= 3 and r.width >= 0.5 * width:
            ys.append((r.y0 + r.y1) / 2.0)
    return sorted(ys)


def _invoice_marker_y(page: fitz.Page) -> Optional[float]:
    """Top Y of the first tax-invoice heading found on the page."""
    best: Optional[float] = None
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        lowered = text.strip().lower()
        if any(lowered.startswith(m) for m in INVOICE_MARKERS):
            # ignore the 'Sold By' block that is printed *inside* the label
            if best is None or y0 < best:
                best = y0
    return best


def _content_bbox(page: fitz.Page, limit_y: float) -> Optional[fitz.Rect]:
    """Union bounding box of every drawing/text/image fully above ``limit_y``."""
    box: Optional[fitz.Rect] = None

    def add(r: Sequence[float]) -> None:
        nonlocal box
        rect = fitz.Rect(r)
        if rect.is_empty or rect.is_infinite:
            return
        if rect.y1 > limit_y or rect.y0 < -1:
            return
        box = rect if box is None else (box | rect)

    for drawing in page.get_drawings():
        add(drawing["rect"])
    for block in page.get_text("blocks"):
        if block[4].strip():
            add(block[:4])
    for image in page.get_image_info():
        add(image["bbox"])

    return box


def _label_frame(page: fitz.Page, limit_y: Optional[float]) -> Optional[fitz.Rect]:
    """Largest bordered 'label card' rectangle on the page (Delhivery style)."""
    pw, ph = page.rect.width, page.rect.height
    page_area = pw * ph
    best: Optional[fitz.Rect] = None

    for drawing in page.get_drawings():
        r = drawing["rect"]
        if not (0.20 * pw <= r.width <= 0.98 * pw):
            continue
        if not (0.20 * ph <= r.height <= 0.98 * ph):
            continue
        if r.width * r.height < 0.10 * page_area:
            continue
        if r.height < 0.6 * r.width:  # a label card is never that wide & flat
            continue
        if limit_y is not None and r.y1 > limit_y + 4:
            continue
        if best is None or r.get_area() > best.get_area():
            best = r

    if best is None:
        return None

    # A frame with no text inside is decoration, not a label.
    inside = [b for b in page.get_text("blocks")
              if b[4].strip() and fitz.Rect(b[:4]).intersects(best)]
    return best if len(inside) >= 3 else None


def detect_label_rect(page: fitz.Page, pad: float = 0.0) -> Detection:
    """Locate the shipping-label block on a courier page."""
    page_rect = page.rect

    # A page that is already label sized needs no cropping.
    if page_rect.width <= 380 and page_rect.height <= 700:
        return Detection(page_rect, "passthrough")

    limit_y: Optional[float] = None
    method = ""

    cuts = [y for y in _long_dashed_cut_lines(page) if y > 0.15 * page_rect.height]
    if cuts:
        limit_y, method = cuts[0], "cut-line"

    if limit_y is None:
        marker = _invoice_marker_y(page)
        if marker and marker > 0.15 * page_rect.height:
            limit_y, method = marker - 2, "invoice-heading"

    frame = _label_frame(page, limit_y)
    if frame is not None:
        box = frame
        method = f"{method}+frame" if method else "frame"
    else:
        if limit_y is None:
            # No invoice section and no card border: the whole page is the label.
            limit_y, method = page_rect.height, "page-content"
        box = _content_bbox(page, limit_y)
        if box is None or box.width < 50 or box.height < 50:
            box = fitz.Rect(page_rect.x0, page_rect.y0, page_rect.x1, limit_y)
            method += "+fallback"

    box = fitz.Rect(box.x0 - pad, box.y0 - pad, box.x1 + pad, box.y1 + pad) & page_rect
    return Detection(box, method)


# --------------------------------------------------------------------------
# Output geometry
# --------------------------------------------------------------------------
def resolve_page_size(spec: str, crop: fitz.Rect) -> tuple:
    spec = spec.strip().lower()
    if spec == "auto":
        return crop.width, crop.height
    if spec in PAGE_SIZES:
        return PAGE_SIZES[spec]
    if "x" in spec:  # e.g. "4x6" in inches or "100x150mm"
        raw = spec.replace("in", "").replace("mm", "")
        try:
            w, h = (float(v) for v in raw.split("x"))
        except ValueError:
            raise argparse.ArgumentTypeError(f"Unrecognised --size value: {spec}")
        factor = 72.0 / 25.4 if spec.endswith("mm") else PT_PER_INCH
        return w * factor, h * factor
    raise argparse.ArgumentTypeError(f"Unrecognised --size value: {spec}")


def target_rect(page_w: float, page_h: float, crop: fitz.Rect, fit: str,
                margin: float) -> fitz.Rect:
    area = fitz.Rect(margin, margin, page_w - margin, page_h - margin)
    if fit == "stretch" or crop.width <= 0 or crop.height <= 0:
        return area
    scale = min(area.width / crop.width, area.height / crop.height)
    w, h = crop.width * scale, crop.height * scale
    x = area.x0 + (area.width - w) / 2
    y = area.y0 + (area.height - h) / 2
    return fitz.Rect(x, y, x + w, y + h)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def _enhance(pix: fitz.Pixmap, sharpen: bool, contrast: float,
             mono: bool) -> bytes:
    """Post-process a rendered label for crisper thermal-printer output."""
    png = pix.tobytes("png")
    if not (sharpen or contrast != 1.0 or mono):
        return png
    try:
        from PIL import Image, ImageEnhance, ImageFilter
    except ImportError:
        print("  ! Pillow not installed - skipping image enhancement",
              file=sys.stderr)
        return png

    img = Image.open(io.BytesIO(png)).convert("L")
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if sharpen:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=160,
                                                 threshold=2))
    if mono:
        img = img.point(lambda p: 255 if p > 176 else 0, mode="1")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_label(out_doc: fitz.Document, src: fitz.Document, pno: int,
                 crop: fitz.Rect, opts: argparse.Namespace) -> None:
    page_w, page_h = resolve_page_size(opts.size, crop)
    dest = target_rect(page_w, page_h, crop, opts.fit, opts.margin)
    new_page = out_doc.new_page(width=page_w, height=page_h)

    if opts.mode == "vector":
        # Keeps text/barcodes as vectors -> resolution independent, sharpest.
        new_page.show_pdf_page(dest, src, pno, clip=crop)
        return

    pix = src[pno].get_pixmap(dpi=opts.dpi, clip=crop, colorspace=fitz.csGRAY
                              if (opts.mono or opts.grayscale) else fitz.csRGB,
                              alpha=False)
    stream = _enhance(pix, opts.sharpen, opts.contrast, opts.mono)
    new_page.insert_image(dest, stream=stream)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
def process_pdf(path: Path, opts: argparse.Namespace,
                out_doc: Optional[fitz.Document] = None) -> Optional[fitz.Document]:
    src = fitz.open(path)
    doc = out_doc if out_doc is not None else fitz.open()
    try:
        for pno in range(len(src)):
            page = src[pno]
            if opts.region:
                crop = fitz.Rect(*opts.region)
                method = "manual"
            else:
                det = detect_label_rect(page, pad=opts.pad)
                crop, method = det.rect, det.method
            if crop.is_empty:
                print(f"  ! {path.name} page {pno + 1}: no label found - skipped",
                      file=sys.stderr)
                continue
            render_label(doc, src, pno, crop, opts)
            if opts.verbose:
                print(f"  page {pno + 1}: {method} crop "
                      f"({crop.x0:.1f}, {crop.y0:.1f}, {crop.x1:.1f}, {crop.y1:.1f})")
    finally:
        src.close()
    return doc


def collect_inputs(target: Path, recursive: bool) -> List[Path]:
    if target.is_file():
        return [target]
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(p for p in target.glob(pattern)
                  if p.is_file() and not p.name.startswith("."))


def save(doc: fitz.Document, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_path, garbage=4, deflate=True)
    doc.close()


def cropped_name(stem: str, suffix: str) -> str:
    return f"{stem}{suffix}.pdf"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Crop 4x6 shipping labels out of A4 courier PDFs "
                    "(Delhivery, Flipkart, Meesho).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input", type=Path,
                   help="Input PDF file (single or multi-page) or a directory "
                        "of PDFs")
    p.add_argument("-o", "--output", type=Path, default=None,
                   help="Output PDF file, or output directory for batch mode "
                        "(default: '<input> Crop')")
    p.add_argument("--suffix", default=DEFAULT_SUFFIX,
                   help="Text appended to the input name for the output name")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="Recurse into sub-directories in batch mode")
    p.add_argument("--merge", action="store_true",
                   help="Batch mode: write all labels into one combined PDF")

    q = p.add_argument_group("output quality")
    q.add_argument("--mode", choices=("vector", "raster"), default="vector",
                   help="vector = keep original text/barcodes (sharpest, "
                        "smallest); raster = re-render as an image")
    q.add_argument("--dpi", type=int, default=600,
                   help="Raster mode render resolution (300=good, 600=better, "
                        "1200=max)")
    q.add_argument("--sharpen", action="store_true",
                   help="Raster mode: unsharp-mask the text for crisper print")
    q.add_argument("--contrast", type=float, default=1.0,
                   help="Raster mode: contrast boost, e.g. 1.4")
    q.add_argument("--grayscale", action="store_true",
                   help="Raster mode: render grayscale (smaller files)")
    q.add_argument("--mono", action="store_true",
                   help="Raster mode: pure black & white, ideal for thermal "
                        "printers")

    g = p.add_argument_group("page geometry")
    g.add_argument("--size", default="4x6",
                   help="Output page size: 4x6, 6x4, a6, a5, auto, or WxH "
                        "(inches, or add 'mm')")
    g.add_argument("--fit", choices=("contain", "stretch"), default="contain",
                   help="contain = keep aspect ratio; stretch = fill the page")
    g.add_argument("--margin", type=float, default=0.0,
                   help="White margin around the label, in points")
    g.add_argument("--pad", type=float, default=2.0,
                   help="Extra padding around the detected label, in points")
    g.add_argument("--region", type=float, nargs=4,
                   metavar=("X0", "Y0", "X1", "Y1"),
                   help="Skip auto-detection and crop this rectangle (points)")

    p.add_argument("-v", "--verbose", action="store_true",
                   help="Print the detected crop box for every page")
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    opts = build_parser().parse_args(list(argv) if argv is not None else None)

    if not opts.input.exists():
        print(f"Input not found: {opts.input}", file=sys.stderr)
        return 1

    files = collect_inputs(opts.input, opts.recursive)
    if not files:
        print(f"No PDF files found in {opts.input}", file=sys.stderr)
        return 1

    single_file = opts.input.is_file()
    processed = failed = 0

    if single_file or opts.merge:
        default_name = cropped_name(
            opts.input.stem if single_file else opts.input.name, opts.suffix)
        if opts.output is None:
            out_path = opts.input.with_name(default_name)
        elif opts.output.suffix.lower() == ".pdf":
            out_path = opts.output
        else:
            out_path = opts.output / default_name

        merged = fitz.open()
        for pdf in files:
            print(f"-> {pdf.name}")
            try:
                process_pdf(pdf, opts, merged)
                processed += 1
            except Exception as exc:  # keep going through the batch
                failed += 1
                print(f"  ! failed: {exc}", file=sys.stderr)
        if len(merged) == 0:
            print("No labels produced.", file=sys.stderr)
            return 1
        save(merged, out_path)
        print(f"Saved {out_path}")
    else:
        out_dir = opts.output or opts.input.with_name(
            opts.input.name + opts.suffix)
        for pdf in files:
            print(f"-> {pdf.name}")
            try:
                doc = process_pdf(pdf, opts)
                if len(doc) == 0:
                    doc.close()
                    raise ValueError("no label detected")
                rel = pdf.relative_to(opts.input).with_name(
                    cropped_name(pdf.stem, opts.suffix))
                save(doc, out_dir / rel)
                processed += 1
            except Exception as exc:
                failed += 1
                print(f"  ! failed: {exc}", file=sys.stderr)
        print(f"Saved labels to {out_dir}")
    print(f"Done: {processed} file(s) processed, {failed} failed.")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
