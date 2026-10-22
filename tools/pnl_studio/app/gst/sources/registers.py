"""Document-number registers — files that carry invoice / credit-note NUMBERS
but no money, used only to build GSTR-1 Table 13.

Meesho's GST report has values but no document numbers. Its separate
"Tax_invoice_details.xlsx" download has the numbers but no values. This module
reads the second kind; the engine then reconciles it against the first.

Meesho runs three independent series, told apart by the letters before the
running number:

    <base><n>      INVOICE          e.g. qism927211
    <base>C<n>     CREDIT NOTE      e.g. qism927C13      (returns)
    <base>CM<n>    CREDIT_DISCOUNT  e.g. qism927CM5      (post-sale discount)

The invoice series has no separator, so its base is learnt from the credit-note
numbers in the same file rather than assumed.
"""

from __future__ import annotations

import re
from typing import List, Optional

import pandas as pd

REGISTER_COLUMNS = ["platform", "kind", "series", "seq", "doc_no", "order_id", "source_file"]

_KINDS = {
    "INVOICE": "INVOICE",
    "CREDIT NOTE": "CREDIT_NOTE",
    "CREDIT_DISCOUNT": "CREDIT_DISCOUNT",
}


class MeeshoInvoiceRegister:
    platform = "meesho"
    label = "Meesho invoice register"

    def matches(self, path: str) -> bool:
        if not path.lower().endswith((".xlsx", ".xls")):
            return False
        try:
            cols = {str(c).strip().lower() for c in pd.read_excel(path, nrows=0).columns}
        except Exception:
            return False
        return {"type", "suborder no.", "invoice no."} <= cols

    def load(self, path: str) -> pd.DataFrame:
        raw = pd.read_excel(path, dtype=str)
        raw.columns = [str(c).strip().lower() for c in raw.columns]
        numbers = raw["invoice no."].astype(str).str.strip()
        types = raw["type"].astype(str).str.strip().str.upper()

        unknown = sorted(set(types) - set(_KINDS))
        if unknown:
            raise ValueError("unrecognised document type(s) %s in Meesho register" % unknown)

        bases = self._bases(numbers[types != "INVOICE"])
        rows: List[dict] = []
        for number, kind_raw, order in zip(numbers, types, raw["suborder no."].astype(str).str.strip()):
            kind = _KINDS[kind_raw]
            series, seq = self._split(number, kind, bases)
            if series is None:
                raise ValueError("cannot read document number %r (%s)" % (number, kind))
            rows.append({
                "platform": self.platform, "kind": kind, "series": series,
                "seq": seq, "doc_no": number, "order_id": order,
                "source_file": path.rsplit("/", 1)[-1],
            })
        return pd.DataFrame(rows, columns=REGISTER_COLUMNS)

    @staticmethod
    def _bases(credit_numbers: pd.Series) -> List[str]:
        found = set()
        for number in credit_numbers:
            m = re.match(r"^(.+?)(?:CM|C)\d+$", number)
            if m:
                found.add(m.group(1))
        return sorted(found, key=len, reverse=True)

    @staticmethod
    def _split(number: str, kind: str, bases: List[str]):
        if kind == "INVOICE":
            for base in bases:
                rest = number[len(base):]
                if number.startswith(base) and rest.isdigit():
                    return base, int(rest)
            m = re.match(r"^([A-Za-z]+\d{3})(\d+)$", number)
            return (m.group(1), int(m.group(2))) if m else (None, None)
        m = re.match(r"^(.+?(?:CM|C))(\d+)$", number)
        return (m.group(1), int(m.group(2))) if m else (None, None)


REGISTERS = [MeeshoInvoiceRegister()]


def detect_register(path: str) -> Optional[MeeshoInvoiceRegister]:
    for register in REGISTERS:
        try:
            if register.matches(path):
                return register
        except Exception:
            continue
    return None
