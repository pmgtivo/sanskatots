#!/usr/bin/env python3
"""Group Meesho sub-order IDs from downloaded shipping labels by delivery partner.

Reads one or more Meesho "Sub Order Labels" PDFs, extracts every sub-order ID
together with its courier (Delhivery / Xpress Bees / Shadowfax / Valmo / ...),
and by default prints the comma-separated sub-order IDs per partner to the
console. With --excel it also writes one `My-orders-are-not-picked-up-yet-
<Partner>.xlsx` per partner in the single-column ("Sub Order Num") format
Meesho expects.

Usage:
    python3 meesho_not_picked_up.py                       # all PDFs in this folder
    python3 meesho_not_picked_up.py labels/ a.pdf b.pdf   # explicit files/folders
    python3 meesho_not_picked_up.py --excel -o out/       # also write xlsx files
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import OrderedDict, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required. Install it with: python3 -m pip install pymupdf")

HEADER = "Sub Order Num"
OUTPUT_PREFIX = "My-orders-are-not-picked-up-yet"

# Meesho sub-order id: 18-digit order number + "_" + item index, e.g. 327738730993537539_1
SUB_ORDER_RE = re.compile(r"\b(\d{14,22}_\d{1,3})\b")

# On a Meesho label the courier name sits on the line directly above "Pickup".
COURIER_BEFORE_PICKUP_RE = re.compile(r"([^\n]+)\n\s*Pickup\b")

# Fallback: scan the page for a known courier name. Keys are matched case-insensitively
# against the page text with all whitespace removed.
KNOWN_COURIERS = OrderedDict(
    [
        ("xpressbees", "Xpress Bees"),
        ("delhivery", "Delhivery"),
        ("shadowfax", "Shadowfax"),
        ("valmo", "Valmo"),
        ("ecomexpress", "Ecom Express"),
        ("bluedart", "Blue Dart"),
        ("shiprocket", "Shiprocket"),
    ]
)

UNKNOWN_PARTNER = "Unknown"


def normalise_courier(raw: str) -> str:
    """Map a raw label string to a canonical partner name."""
    squashed = re.sub(r"[^a-z]", "", raw.lower())
    for key, name in KNOWN_COURIERS.items():
        if key in squashed:
            return name
    cleaned = " ".join(raw.split())
    return cleaned or UNKNOWN_PARTNER


def detect_courier(page_text: str) -> str:
    match = COURIER_BEFORE_PICKUP_RE.search(page_text)
    if match:
        candidate = normalise_courier(match.group(1))
        if candidate != UNKNOWN_PARTNER:
            return candidate
    squashed = re.sub(r"[^a-z]", "", page_text.lower())
    for key, name in KNOWN_COURIERS.items():
        if key in squashed:
            return name
    return UNKNOWN_PARTNER


def collect_pdfs(inputs: list[Path]) -> list[Path]:
    pdfs: list[Path] = []
    for item in inputs:
        if item.is_dir():
            pdfs.extend(sorted(p for p in item.rglob("*.pdf") if p.is_file()))
        elif item.is_file() and item.suffix.lower() == ".pdf":
            pdfs.append(item)
        else:
            print(f"  ! skipping (not a PDF or folder): {item}", file=sys.stderr)
    # de-duplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in pdfs:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(p)
    return unique


def extract_orders(pdf_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return {partner: [sub_order_id, ...]} and a list of warnings for this PDF."""
    grouped: dict[str, list[str]] = defaultdict(list)
    warnings: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page_no, page in enumerate(doc, start=1):
            text = page.get_text()
            ids = list(OrderedDict.fromkeys(SUB_ORDER_RE.findall(text)))
            if not ids:
                warnings.append(f"{pdf_path.name} p{page_no}: no sub-order id found")
                continue
            partner = detect_courier(text)
            if partner == UNKNOWN_PARTNER:
                warnings.append(
                    f"{pdf_path.name} p{page_no}: courier not recognised for {', '.join(ids)}"
                )
            grouped[partner].extend(ids)
    return grouped, warnings


def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return slug or "Unknown"


CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "</Types>"
)

ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)

WORKBOOK = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
)

WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    "</Relationships>"
)

STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
    "</styleSheet>"
)


def write_xlsx(path: Path, column_values: list[str]) -> None:
    """Write a single-column sheet: header in A1, one value per row below."""
    strings = [HEADER, *column_values]
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(strings)}" uniqueCount="{len(strings)}">'
        + "".join(f"<si><t>{escape(s)}</t></si>" for s in strings)
        + "</sst>"
    )
    rows = [f'<row r="1"><c r="A1" s="1" t="s"><v>0</v></c></row>']
    rows.extend(
        f'<row r="{i}"><c r="A{i}" t="s"><v>{i - 1}</v></c></row>'
        for i in range(2, len(strings) + 1)
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:A{len(strings)}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="24" customWidth="1"/></cols>'
        "<sheetData>" + "".join(rows) + "</sheetData></worksheet>"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("xl/workbook.xml", WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        z.writestr("xl/styles.xml", STYLES)
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/worksheets/sheet1.xml", sheet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Group Meesho sub-order IDs from shipping labels by delivery partner."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Label PDF files and/or folders to scan (default: the script's folder).",
    )
    parser.add_argument(
        "-x",
        "--excel",
        action="store_true",
        help="Also write one .xlsx per delivery partner.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Where to write the xlsx/csv files (default: <script folder>/output).",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Also write one .csv per delivery partner.",
    )
    args = parser.parse_args(argv)

    script_dir = Path(__file__).resolve().parent
    inputs = args.inputs or [script_dir]
    output_dir = args.output_dir or (script_dir / "output")

    pdfs = collect_pdfs(inputs)
    if not pdfs:
        print("No PDF labels found.", file=sys.stderr)
        return 1

    print(f"Scanning {len(pdfs)} label PDF(s)...", file=sys.stderr)
    grouped: dict[str, list[str]] = defaultdict(list)
    warnings: list[str] = []
    for pdf in pdfs:
        try:
            partial, pdf_warnings = extract_orders(pdf)
        except Exception as exc:  # unreadable/encrypted/corrupt PDF
            warnings.append(f"{pdf.name}: could not read ({exc})")
            continue
        for partner, ids in partial.items():
            grouped[partner].extend(ids)
        warnings.extend(pdf_warnings)

    if not grouped:
        print("No Meesho sub-order IDs found in the given labels.", file=sys.stderr)
        return 1

    seen_globally: set[str] = set()
    duplicates = 0
    total = 0
    per_partner: OrderedDict[str, list[str]] = OrderedDict()
    for partner in sorted(grouped):
        unique_ids: list[str] = []
        for sub_order in grouped[partner]:
            if sub_order in seen_globally:
                duplicates += 1
                continue
            seen_globally.add(sub_order)
            unique_ids.append(sub_order)
        if unique_ids:
            per_partner[partner] = unique_ids
            total += len(unique_ids)

    for partner, ids in per_partner.items():
        print(f"\n{partner} ({len(ids)})")
        print(",".join(ids))

    if args.excel or args.csv:
        print(f"\nWriting to {output_dir}", file=sys.stderr)
        for partner, ids in per_partner.items():
            stem = output_dir / f"{OUTPUT_PREFIX}-{slugify(partner)}"
            if args.excel:
                write_xlsx(stem.with_suffix(".xlsx"), ids)
            if args.csv:
                stem.with_suffix(".csv").write_text(
                    "\n".join([HEADER, *ids]) + "\n", encoding="utf-8"
                )
            written = " + ".join(
                ext for ext, on in (("xlsx", args.excel), ("csv", args.csv)) if on
            )
            print(f"  {partner:<14} {len(ids):>4} orders -> {stem.name}.{written}", file=sys.stderr)

    print(f"\nTotal: {total} sub-orders across {len(per_partner)} partner(s).", file=sys.stderr)
    if duplicates:
        print(f"Skipped {duplicates} duplicate sub-order id(s).", file=sys.stderr)
    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for warning in warnings:
            print(f"  ! {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
