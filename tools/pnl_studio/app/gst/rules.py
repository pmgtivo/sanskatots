"""Statutory reference data for Indian GST return preparation.

Everything in this module is *law*, not data: rates, exemption entries, state
codes, form table labels and due dates. It is kept separate from the engine so
that a rule change is a one-file edit and so the report can cite the source of
every classification decision it makes.

IMPORTANT — the serial numbers and notification references below were compiled
from the consolidated exemption notification. The CBIC portal cannot be scraped
programmatically (JavaScript-rendered, PDFs behind a session), so the report
prints `VERIFY_SOURCES` next to every citation. Confirm them once against the
official consolidated notification before your first filing; they do not change
often, and nothing in the *arithmetic* depends on them.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

# --------------------------------------------------------------------------
# Supply classification buckets
# --------------------------------------------------------------------------

TAXABLE = "TAXABLE"
EXEMPT = "EXEMPT"
NIL_RATED = "NIL_RATED"
NON_GST = "NON_GST"

#: How each bucket is presented in GSTR-1 Table 8 / GSTR-3B 3.1(c).
BUCKET_LABEL = {
    TAXABLE: "Taxable",
    EXEMPT: "Exempted (other than nil rated / non-GST)",
    NIL_RATED: "Nil Rated Supplies",
    NON_GST: "Non-GST supplies",
}

# --------------------------------------------------------------------------
# Exempt goods — Notification No. 2/2017-Central Tax (Rate) dated 28.06.2017
# (and the identical 2/2017-Integrated Tax (Rate) for inter-State supplies).
#
# These goods are EXEMPT, not "nil rated". Nil-rated means the goods appear in
# the *rate* notification (1/2017) at a 0% entry. Printed books do not appear
# in 1/2017 at all; they are exempted under section 11 via 2/2017. The practical
# consequence for the seller:
#   * GSTR-1 Table 8 -> the "Exempted" column, NOT the "Nil Rated" column.
#   * GSTR-3B 3.1(c) -> the combined "Nil rated, exempted" row (same box either
#     way, so the tax payable is identical).
#   * Section 17(2) -> input tax credit attributable to these supplies is NOT
#     available. This is the real-money consequence of the distinction.
# --------------------------------------------------------------------------

EXEMPT_HSN: Dict[str, Tuple[str, str]] = {
    "4901": (
        "Printed books, including Braille books",
        "Notfn. 2/2017-CT(R) Sch. Sl. No. 119",
    ),
    "4902": (
        "Newspapers, journals and periodicals, whether or not illustrated "
        "or containing advertising material",
        "Notfn. 2/2017-CT(R) Sch. Sl. No. 120",
    ),
    "4903": (
        "Children's picture, drawing or colouring books",
        "Notfn. 2/2017-CT(R) Sch. Sl. No. 121",
    ),
    "4905": (
        "Maps and hydrographic or similar charts of all kinds, including "
        "atlases, wall maps, topographical plans and globes, printed",
        "Notfn. 2/2017-CT(R) Sch. Sl. No. 123",
    ),
}

#: Goods frequently confused with exempt books by sellers. Printed here as a
#: warning when such an HSN shows up, because they are fully taxable.
TAXABLE_LOOKALIKE_HSN: Dict[str, Tuple[str, float]] = {
    "4820": ("Exercise books, note books, registers, diaries, letter pads", 0.18),
    "4817": ("Envelopes, letter cards, plain postcards", 0.18),
    "4911": ("Other printed matter, including printed pictures and photographs", 0.12),
    "9503": ("Tricycles, scooters, puzzles and other toys", 0.18),
    "9504": ("Video game consoles, board games, playing cards", 0.18),
}

#: Rates valid after the 22-Sep-2025 rationalisation (the 12% and 28% slabs were
#: merged away into 5% / 18% / 40%). Used only to sanity-check marketplace data.
VALID_GST_RATES = (0.0, 0.05, 0.18, 0.40)

#: Legacy slabs. A line carrying one of these after 22-Sep-2025 is suspicious
#: but not impossible (amendment of an older invoice), so it is warned, not
#: rejected.
LEGACY_GST_RATES = (0.03, 0.12, 0.28)

RATE_RATIONALISATION_DATE = "2025-09-22"


def classify_hsn(hsn: Optional[str]) -> Tuple[str, str, str]:
    """Return ``(bucket, description, citation)`` for an HSN code.

    Matching is done on the 4-digit heading, which is what the exemption
    notification itself specifies. ``490110`` therefore resolves via ``4901``.
    """
    code = (hsn or "").strip().replace(" ", "")
    if not code or code.lower() in ("nan", "none"):
        return (TAXABLE, "(HSN missing)", "unclassified — HSN absent from source row")
    heading = code[:4]
    if heading in EXEMPT_HSN:
        desc, cite = EXEMPT_HSN[heading]
        return (EXEMPT, desc, cite)
    if heading in TAXABLE_LOOKALIKE_HSN:
        desc, rate = TAXABLE_LOOKALIKE_HSN[heading]
        return (TAXABLE, desc, "taxable @ %.0f%% — Notfn. 1/2017-CT(R)" % (rate * 100))
    return (TAXABLE, "(HSN not in local rule table)", "unrecognised HSN — confirm manually")


# --------------------------------------------------------------------------
# TCS under section 52 of the CGST Act
#
# Section 52(1) obliges an electronic commerce operator to collect tax at source
# on the "net value of TAXABLE supplies" made through it. Exempt supplies are
# outside that charge, so a seller of exempt books should see ZERO TCS. Any
# non-zero TCS against an exempt line is therefore a marketplace error and the
# engine raises it as an anomaly.
#
# Rate: reduced from 1% to 0.5% (0.25% CGST + 0.25% SGST intra-State, or 0.5%
# IGST inter-State) with effect from 10-July-2024.
# --------------------------------------------------------------------------

TCS_RATE_CURRENT = 0.005
TCS_RATE_LEGACY = 0.010
TCS_RATE_CHANGE_DATE = "2024-07-10"
TCS_CITATION = (
    "s.52(1) CGST Act r/w Notfn. 15/2024-Central Tax (rate cut to 0.5% w.e.f. 10-Jul-2024)"
)

# --------------------------------------------------------------------------
# State / UT codes (first two digits of a GSTIN)
# --------------------------------------------------------------------------

STATE_CODES: Dict[str, str] = {
    "JAMMU AND KASHMIR": "01", "HIMACHAL PRADESH": "02", "PUNJAB": "03",
    "CHANDIGARH": "04", "UTTARAKHAND": "05", "HARYANA": "06", "DELHI": "07",
    "RAJASTHAN": "08", "UTTAR PRADESH": "09", "BIHAR": "10", "SIKKIM": "11",
    "ARUNACHAL PRADESH": "12", "NAGALAND": "13", "MANIPUR": "14",
    "MIZORAM": "15", "TRIPURA": "16", "MEGHALAYA": "17", "ASSAM": "18",
    "WEST BENGAL": "19", "JHARKHAND": "20", "ODISHA": "21",
    "CHHATTISGARH": "22", "MADHYA PRADESH": "23", "GUJARAT": "24",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "26", "MAHARASHTRA": "27",
    "KARNATAKA": "29", "GOA": "30", "LAKSHADWEEP": "31", "KERALA": "32",
    "TAMIL NADU": "33", "PUDUCHERRY": "34",
    "ANDAMAN AND NICOBAR ISLANDS": "35", "TELANGANA": "36",
    "ANDHRA PRADESH": "37", "LADAKH": "38", "OTHER TERRITORY": "97",
}

#: Spellings the marketplaces actually emit.
STATE_ALIASES: Dict[str, str] = {
    "ORISSA": "ODISHA",
    "PONDICHERRY": "PUDUCHERRY",
    "UTTARANCHAL": "UTTARAKHAND",
    "NEW DELHI": "DELHI",
    "DELHI (NCT)": "DELHI",
    "NCT OF DELHI": "DELHI",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "JAMMU AND KASHMIR (UT)": "JAMMU AND KASHMIR",
    "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN AND NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "ANDAMAN & NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
    "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU (UT)":
        "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    # Meesho emits the single-H spelling; Amazon emits the correct double-H one.
    "CHATTISGARH": "CHHATTISGARH",
    "CHHATISGARH": "CHHATTISGARH",
    # Flipkart emits the Malayalam endonym for Kerala on some addresses.
    "KERALAM": "KERALA",
    "TELENGANA": "TELANGANA",
    "PUNJAB(INDIA)": "PUNJAB",
    "TAMILNADU": "TAMIL NADU",
    "UTTARPRADESH": "UTTAR PRADESH",
    "WESTBENGAL": "WEST BENGAL",
    "HIMACHALPRADESH": "HIMACHAL PRADESH",
    "ANDHRAPRADESH": "ANDHRA PRADESH",
    "MADHYAPRADESH": "MADHYA PRADESH",
    "ARUNACHALPRADESH": "ARUNACHAL PRADESH",
}

CODE_TO_STATE = {code: name for name, code in STATE_CODES.items()}


def normalise_state(raw: Optional[str]) -> Tuple[str, str]:
    """Return ``(canonical_state_name, state_code)``; code is ``""`` if unknown."""
    name = (raw or "").strip().upper()
    name = " ".join(name.split())
    if not name or name in ("NAN", "NONE"):
        return ("(unknown)", "")
    name = STATE_ALIASES.get(name, name)
    return (name, STATE_CODES.get(name, ""))


def state_code_of_gstin(gstin: Optional[str]) -> str:
    g = (gstin or "").strip()
    return g[:2] if len(g) >= 2 and g[:2].isdigit() else ""


# --------------------------------------------------------------------------
# Return form table labels — reproduced so the report names boxes exactly as
# the GST portal does, which is what you will be typing into.
# --------------------------------------------------------------------------

GSTR1_TABLE_8_ROWS = [
    ("8A", "Inter-State supplies to registered persons"),
    ("8B", "Intra-State supplies to registered persons"),
    ("8C", "Inter-State supplies to unregistered persons"),
    ("8D", "Intra-State supplies to unregistered persons"),
]

GSTR1_TABLE_8_COLUMNS = ["Nil Rated Supplies", "Exempted", "Non-GST supplies"]

GSTR3B_ROWS = {
    "3.1(a)": "Outward taxable supplies (other than zero rated, nil rated and exempted)",
    "3.1(b)": "Outward taxable supplies (zero rated)",
    "3.1(c)": "Other outward supplies (Nil rated, exempted)",
    "3.1(d)": "Inward supplies (liable to reverse charge)",
    "3.1(e)": "Non-GST outward supplies",
    "3.1.1(i)": "Taxable supplies on which electronic commerce operator pays tax u/s 9(5)",
    "3.1.1(ii)": "Taxable supplies made by registered person through electronic commerce "
                 "operator, on which electronic commerce operator is required to pay tax u/s 9(5)",
    "3.2": "Of the supplies shown in 3.1(a), 3.1(b) and 3.1.1(i) above, details of "
           "inter-State supplies made to unregistered persons, composition taxable "
           "persons and UIN holders",
    "4": "Eligible ITC",
    "5": "Values of exempt, nil rated and non-GST inward supplies",
}

#: Table 3.2 is explicitly scoped to supplies "shown in 3.1(a), 3.1(b) and
#: 3.1.1(i)" — i.e. TAXABLE supplies only. Exempt book sales must NOT be
#: repeated there. This is the single most common error for exempt sellers.
GSTR3B_32_EXCLUDES_EXEMPT = True

# --------------------------------------------------------------------------
# HSN reporting (GSTR-1 Table 12) digit requirement by aggregate annual
# turnover of the preceding financial year.
# --------------------------------------------------------------------------

HSN_DIGITS_UPTO_5CR = 4
HSN_DIGITS_ABOVE_5CR = 6
AATO_THRESHOLD = 50_000_000.0


def hsn_digits_required(aato: float) -> int:
    return HSN_DIGITS_ABOVE_5CR if aato > AATO_THRESHOLD else HSN_DIGITS_UPTO_5CR


# --------------------------------------------------------------------------
# Due dates
# --------------------------------------------------------------------------

#: QRMP quarterly GSTR-3B is due on the 22nd for this group of States/UTs and
#: on the 24th for the rest. Karnataka is in the 22nd group.
QRMP_22ND_GROUP = {
    "CHHATTISGARH", "MADHYA PRADESH", "GUJARAT", "MAHARASHTRA", "KARNATAKA",
    "GOA", "KERALA", "TAMIL NADU", "TELANGANA", "ANDHRA PRADESH",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU", "PUDUCHERRY",
    "ANDAMAN AND NICOBAR ISLANDS", "LAKSHADWEEP",
}


def qrmp_3b_due_day(state: str) -> int:
    name, _ = normalise_state(state)
    return 22 if name in QRMP_22ND_GROUP else 24


DUE_DATES = {
    "monthly_gstr1": "11th of the following month",
    "monthly_gstr3b": "20th of the following month",
    "qrmp_iff": "13th of the following month (optional, months 1 and 2 of the quarter)",
    "qrmp_gstr1": "13th of the month following the quarter",
    "qrmp_gstr3b_22": "22nd of the month following the quarter",
    "qrmp_gstr3b_24": "24th of the month following the quarter",
}

#: Returns cannot be filed after three years from their original due date.
THREE_YEAR_BAR_NOTE = (
    "Returns are time-barred three years after the original due date "
    "(effective for tax periods from 01-Jul-2025)."
)

VERIFY_SOURCES = (
    "Rule references compiled offline — the CBIC portal cannot be scraped. "
    "Verify once at https://cbic-gst.gov.in and https://taxinformation.cbic.gov.in "
    "before your first filing."
)
