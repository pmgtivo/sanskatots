"""
SanskaTots Book Validator — Pronunciation (Transliteration) Validation
======================================================================

Purpose
-------
Regional-language books (Kannada / Hindi / Telugu / Tamil / Malayalam / Sanskrit)
usually print an Indic word together with a Roman "pronunciation guide", e.g.

    ಆನೆ (aane)          आम (aam)          గణేశ - Ganesha

This module checks that the Roman guide actually matches how the Indic word is
pronounced. It does so entirely offline:

    Indic word  --(indic-transliteration)-->  ISO-15919  --> canonical form
    Roman guide -------------------------------------------> canonical form
                            compare (exact / fuzzy)

The canonical form deliberately folds the distinctions that Indian romanisation
is inconsistent about (vowel length, aspiration, retroflex vs dental, sh/s,
doubled consonants, schwa deletion) so that legitimate spelling styles such as
"aane" / "ane" / "aanay" are accepted, while genuinely wrong guides such as
"anne" for ಆನೆ or "kamal" for कमला are flagged.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate
    TRANSLITERATION_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    TRANSLITERATION_AVAILABLE = False


# ─── Supported scripts ───────────────────────────────────────────────────────

# (unicode block start, unicode block end, sanscript scheme name, human label)
SCRIPT_BLOCKS: List[Tuple[int, int, str, str]] = [
    (0x0900, 0x097F, "devanagari", "Hindi/Sanskrit/Marathi"),
    (0x0980, 0x09FF, "bengali", "Bengali"),
    (0x0A00, 0x0A7F, "gurmukhi", "Punjabi"),
    (0x0A80, 0x0AFF, "gujarati", "Gujarati"),
    (0x0B00, 0x0B7F, "oriya", "Odia"),
    (0x0B80, 0x0BFF, "tamil", "Tamil"),
    (0x0C00, 0x0C7F, "telugu", "Telugu"),
    (0x0C80, 0x0CFF, "kannada", "Kannada"),
    (0x0D00, 0x0D7F, "malayalam", "Malayalam"),
]

SCRIPT_LABELS: Dict[str, str] = {s: label for _, _, s, label in SCRIPT_BLOCKS}

# Scripts where the inherent final "a" (schwa) is normally dropped when spoken,
# e.g. कमल is read "kamal", not "kamala".
SCHWA_DELETING_SCRIPTS = {"devanagari", "bengali", "gurmukhi", "gujarati", "oriya"}


def detect_script(text: str) -> Optional[str]:
    """Return the sanscript scheme name of the dominant Indic script in `text`."""
    counts: Dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for start, end, scheme, _ in SCRIPT_BLOCKS:
            if start <= cp <= end:
                counts[scheme] = counts.get(scheme, 0) + 1
                break
    if not counts:
        return None
    return max(counts, key=counts.get)


def is_indic_char(ch: str) -> bool:
    cp = ord(ch)
    return any(start <= cp <= end for start, end, _, _ in SCRIPT_BLOCKS)


# ─── Canonicalisation ────────────────────────────────────────────────────────

# ISO-15919 / IAST diacritics → plain ASCII skeleton
_DIACRITIC_MAP = {
    "ā": "a", "â": "a", "ǎ": "a",
    "ī": "i", "î": "i",
    "ū": "u", "û": "u",
    "ē": "e", "ê": "e", "è": "e", "é": "e",
    "ō": "o", "ô": "o", "ò": "o", "ó": "o",
    "ṛ": "ri", "ṝ": "ri", "ŕ": "ri", "r̥": "ri", "r̥̄": "ri",
    "ḷ": "l", "ḹ": "l", "l̥": "li", "l̥̄": "li",
    "ṁ": "m", "ṃ": "m", "m̐": "m", "ṉ": "n", "ṅ": "n", "ñ": "n", "ṇ": "n",
    "ḥ": "h",
    "ś": "s", "ṣ": "s",
    "ṭ": "t", "ḍ": "d", "ḻ": "l", "ṟ": "r", "ḽ": "l",
    "ĕ": "e", "ŏ": "o",
    "'": "", "’": "", "ʼ": "",
}

# Multi-character romanisation habits, applied longest-first.
_DIGRAPH_RULES: List[Tuple[str, str]] = [
    ("ksh", "ks"), ("kSh", "ks"),
    ("chh", "c"), ("shh", "s"),
    ("sh", "s"), ("ch", "c"),
    ("zh", "l"),          # Tamil ழ is often written "zh"
    ("jn", "gn"), ("gy", "gn"),
]

_ASPIRATE_RE = re.compile(r"([kgcjtdpb])h")


def _fold_vowels(s: str) -> str:
    s = s.replace("aa", "a").replace("ii", "i").replace("ee", "i")
    s = s.replace("oo", "u").replace("uu", "u").replace("ou", "au")
    s = s.replace("ay", "e").replace("ai", "e")   # "aanay" ≈ "aane"
    s = s.replace("ow", "au")
    return s


def canonical(text: str) -> str:
    """
    Reduce a Roman string (either an ISO transliteration or a hand-written
    pronunciation guide) to a comparison skeleton.

    Folds: case, diacritics, vowel length, aspiration, retroflex/dental,
    sh/s, w/v, z/j, q/k, x/ks and doubled consonants.
    """
    if not text:
        return ""

    s = unicodedata.normalize("NFC", text).lower()

    # Diacritics → ASCII (handle multi-codepoint sequences first)
    for src, dst in sorted(_DIACRITIC_MAP.items(), key=lambda kv: -len(kv[0])):
        if src in s:
            s = s.replace(src, dst)
    # Strip any leftover combining marks (e.g. decomposed r̥)
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if not unicodedata.combining(c))

    for src, dst in _DIGRAPH_RULES:
        s = s.replace(src, dst)

    # Indian romanisation is unreliable about aspiration: kh→k, bh→b, th→t …
    s = _ASPIRATE_RE.sub(r"\1", s)

    s = _fold_vowels(s)

    s = s.replace("w", "v").replace("z", "j").replace("q", "k").replace("x", "ks")
    s = s.replace("f", "p")

    s = re.sub(r"[^a-z]", "", s)
    return s


def _schwa_variants(skeleton: str) -> List[str]:
    """Accept the word with and without a trailing inherent 'a'."""
    out = [skeleton]
    if len(skeleton) > 2 and skeleton.endswith("a"):
        out.append(skeleton[:-1])
    return out


# ─── Human-readable suggestion ───────────────────────────────────────────────

_SUGGEST_MAP = [
    # Vocalic r/l are multi-codepoint in ISO (r + combining ring) — do these first
    ("r̥̄", "ree"), ("r̥", "ri"), ("l̥̄", "lee"), ("l̥", "li"),
    ("ṛ", "ri"), ("ṝ", "ri"), ("ḷ", "l"), ("ḹ", "l"),
    ("ā", "aa"), ("ī", "ee"), ("ū", "oo"), ("ē", "e"), ("ō", "o"),
    ("ĕ", "e"), ("ŏ", "o"), ("è", "e"), ("ò", "o"),
    ("ś", "sh"), ("ṣ", "sh"), ("ñ", "ny"), ("ṅ", "ng"),
    ("ṭ", "t"), ("ḍ", "d"), ("ṇ", "n"), ("ḻ", "zh"), ("ṟ", "r"),
    ("ṁ", "m"), ("ṃ", "m"), ("ḥ", "h"), ("ṉ", "n"),
    ("c", "ch"),
]


def suggest_roman(iso: str, script: str) -> str:
    """Turn an ISO-15919 string into a friendly, diacritic-free suggestion."""
    s = unicodedata.normalize("NFC", iso)
    # 'ch' before the bare 'c' → 'ch' rule so 'ch' doesn't become 'chh'
    s = s.replace("ch", "\x00")
    for src, dst in _SUGGEST_MAP:
        s = s.replace(src, dst)
    s = s.replace("\x00", "chh")
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if not unicodedata.combining(c))
    if script in SCHWA_DELETING_SCRIPTS and len(s) > 3 and s.endswith("a"):
        s = s[:-1]
    return s


# ─── Transliteration ─────────────────────────────────────────────────────────

def to_iso(word: str, script: str) -> Optional[str]:
    """Transliterate an Indic word to ISO-15919. Returns None if unavailable."""
    if not TRANSLITERATION_AVAILABLE:
        return None
    try:
        scheme = getattr(sanscript, script.upper(), script)
        return transliterate(word, scheme, sanscript.ISO)
    except Exception:
        return None


def compare(indic_word: str, roman_word: str, script: str) -> Optional[dict]:
    """
    Compare an Indic word with its Roman pronunciation guide.

    Returns a dict with keys: score (0..1), expected_iso, suggestion,
    expected_skeleton, actual_skeleton — or None if transliteration failed.
    """
    iso = to_iso(indic_word, script)
    if not iso:
        return None

    expected_variants = _schwa_variants(canonical(iso))
    actual = canonical(roman_word)

    best = 0.0
    for e in expected_variants:
        if not e or not actual:
            continue
        if e == actual:
            best = 1.0
            break
        best = max(best, SequenceMatcher(None, e, actual).ratio())

    return {
        "score": best,
        "expected_iso": iso,
        "suggestion": suggest_roman(iso, script),
        "expected_skeleton": expected_variants[0],
        "actual_skeleton": actual,
    }


# ─── Page text extraction & pairing ──────────────────────────────────────────

@dataclass
class Token:
    text: str
    script: Optional[str]        # sanscript scheme name, or None for Roman
    bbox: Tuple[float, float, float, float]
    bracketed: bool = False

    @property
    def is_indic(self) -> bool:
        return self.script is not None


@dataclass
class LineRec:
    text: str
    bbox: Tuple[float, float, float, float]
    tokens: List[Token]

    @property
    def indic_tokens(self) -> List[Token]:
        return [t for t in self.tokens if t.is_indic]

    @property
    def roman_tokens(self) -> List[Token]:
        return [t for t in self.tokens if not t.is_indic]


_ROMAN_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")


def _tokenize_line(text: str, spans: List[Tuple[int, int, Tuple]]) -> List[Token]:
    """Split a line into Indic and Roman tokens, mapping each back to a bbox."""

    def bbox_for(start: int, end: int) -> Tuple[float, float, float, float]:
        hits = [b for (s, e, b) in spans if s < end and e > start]
        if not hits:
            return (0.0, 0.0, 0.0, 0.0)
        return (
            min(h[0] for h in hits), min(h[1] for h in hits),
            max(h[2] for h in hits), max(h[3] for h in hits),
        )

    tokens: List[Token] = []

    # Indic runs (letters plus their combining marks / virama / ZWJ)
    i = 0
    n = len(text)
    while i < n:
        if is_indic_char(text[i]):
            j = i
            while j < n and (is_indic_char(text[j]) or text[j] in "\u200c\u200d"):
                j += 1
            chunk = text[i:j].strip()
            if chunk:
                scheme = detect_script(chunk)
                if scheme:
                    tokens.append(Token(chunk, scheme, bbox_for(i, j),
                                        _is_bracketed(text, i, j)))
            i = j
        else:
            i += 1

    for m in _ROMAN_RE.finditer(text):
        word = m.group()
        if len(word) < 2:
            continue
        tokens.append(Token(word, None, bbox_for(m.start(), m.end()),
                            _is_bracketed(text, m.start(), m.end())))

    tokens.sort(key=lambda t: (t.bbox[0], t.bbox[1]))
    return tokens


def _is_bracketed(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 2):start]
    after = text[end:end + 2]
    return any(c in before for c in "([{<") and any(c in after for c in ")]}>")


def extract_lines(page) -> List[LineRec]:
    """Build line records (text + per-token bboxes) from a PyMuPDF page."""
    lines: List[LineRec] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = ""
            spans: List[Tuple[int, int, Tuple]] = []
            for span in line.get("spans", []):
                stext = span.get("text", "")
                if not stext:
                    continue
                start = len(text)
                text += stext
                spans.append((start, len(text), tuple(span["bbox"])))
            if not text.strip():
                continue
            tokens = _tokenize_line(text, spans)
            if tokens:
                lines.append(LineRec(text, tuple(line["bbox"]), tokens))
    return lines


def _neighbour_roman_tokens(idx: int, lines: List[LineRec]) -> List[Token]:
    """
    Roman tokens on the nearest Roman-only line, covering the two layouts that
    books actually use:

        ಆನೆ            (stacked flashcard)      ಆನೆ  (aane)   (side by side,
        aane                                                   separate blocks)
    """
    src = lines[idx]
    x0, y0, x1, y1 = src.bbox
    height = max(y1 - y0, 1.0)
    width = max(x1 - x0, 1.0)
    candidates: List[Tuple[float, LineRec]] = []

    for other_idx, other in enumerate(lines):
        if other_idx == idx or other.indic_tokens or not other.roman_tokens:
            continue
        ox0, oy0, ox1, oy1 = other.bbox
        h_overlap = min(x1, ox1) - max(x0, ox0)
        v_overlap = min(y1, oy1) - max(y0, oy0)

        if h_overlap > 0 and v_overlap <= 0:
            # Stacked: same column, line above or below
            gap = (oy0 - y1) if oy0 >= y1 else (y0 - oy1) + height * 0.5
            limit = height * 2.2
        elif v_overlap > 0 and h_overlap <= 0:
            # Side by side: same row, to the right (preferred) or left
            gap = (ox0 - x1) if ox0 >= x1 else (x0 - ox1) + width * 0.5
            limit = max(width * 1.5, height * 6)
        elif h_overlap > 0 and v_overlap > 0:
            gap = 0.0
            limit = height * 2.2
        else:
            continue

        if 0 <= gap <= limit:
            candidates.append((gap, other))

    if not candidates:
        return []
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1].roman_tokens


# ─── Main entry point ────────────────────────────────────────────────────────

# Similarity thresholds
MATCH_OK = 0.86          # ≥ this → treated as correct
MATCH_WARN = 0.60        # ≥ this → warning (close but off), below → error
TRANSLATION_CUTOFF = 0.45  # below this AND a real English word → it's a translation


@dataclass
class PronunciationFinding:
    severity: str          # error | warning | info
    description: str
    bbox: Optional[Tuple[float, float, float, float]] = None


class PronunciationChecker:
    """
    Validates Roman pronunciation guides printed alongside Indic-script words.

    Parameters
    ----------
    languages : optional set of sanscript scheme names to restrict checking to
                (e.g. {"kannada"}). None = auto-detect any supported script.
    flag_missing : also report Indic words that have no pronunciation guide.
    english_words : callable(word) -> bool used to recognise plain English
                    translations (so "ಆನೆ Elephant" is not flagged as a bad
                    pronunciation). Optional.
    exceptions : mapping of Indic word -> accepted Roman spelling(s), for brand
                 names and deliberate stylings.
    """

    def __init__(
        self,
        languages: Optional[Sequence[str]] = None,
        flag_missing: bool = False,
        english_words=None,
        exceptions: Optional[Dict[str, Sequence[str]]] = None,
    ):
        self.languages = set(languages) if languages else None
        self.flag_missing = flag_missing
        self.english_words = english_words
        self.exceptions = {k: [canonical(v) for v in vals]
                           for k, vals in (exceptions or {}).items()}

    @property
    def available(self) -> bool:
        return TRANSLITERATION_AVAILABLE

    # ── helpers ──────────────────────────────────────────────────────────

    def _is_english(self, word: str) -> bool:
        if not self.english_words:
            return False
        try:
            return bool(self.english_words(word.lower()))
        except Exception:
            return False

    def _best_candidate(self, indic: Token, romans: List[Token]):
        """
        Pick the Roman token that best matches the Indic word.

        A bracketed token — "ಆನೆ (aane)" — is preferred when scores are close,
        since brackets almost always mark the pronunciation guide. The bonus
        only affects *selection*; the true score is what gets reported.
        """
        best = None
        for r in romans:
            result = compare(indic.text, r.text, indic.script)
            if not result:
                continue
            rank = result["score"] + (0.05 if r.bracketed else 0.0)
            if best is None or rank > best[0]:
                best = (rank, r, result)
        if best is None:
            return None
        _, roman, result = best
        return (result["score"], roman, result)

    # ── main check ───────────────────────────────────────────────────────

    def analyze_page(self, page, page_num: int) -> Tuple[List[PronunciationFinding], set]:
        """
        Analyse one page.

        Returns (findings, guide_words) where `guide_words` is the set of
        lower-cased Roman words identified as pronunciation guides for an Indic
        word. Callers use it to stop the English spell checker from flagging
        legitimate transliterations such as "aane" or "pusthaka".
        """
        if not TRANSLITERATION_AVAILABLE:
            return [], set()

        findings: List[PronunciationFinding] = []
        guide_words: set = set()
        lines = extract_lines(page)

        for idx, line in enumerate(lines):
            indics = line.indic_tokens
            if not indics:
                continue

            romans = line.roman_tokens
            if romans:
                # A bracketed Roman word next to Indic text is always a guide
                guide_words.update(r.text.lower() for r in romans if r.bracketed)
            else:
                romans = _neighbour_roman_tokens(idx, lines)

            for indic in indics:
                if self.languages and indic.script not in self.languages:
                    continue
                best = self._best_candidate(indic, romans)
                if best and best[0] >= TRANSLATION_CUTOFF:
                    guide_words.add(best[1].text.lower())
                findings.extend(self._check_word(indic, romans, best))

        return findings, guide_words

    def check_page(self, page, page_num: int) -> List[PronunciationFinding]:
        return self.analyze_page(page, page_num)[0]

    def _check_word(self, indic: Token, romans: List[Token],
                    best) -> List[PronunciationFinding]:
        label = SCRIPT_LABELS.get(indic.script, indic.script.title())

        if not romans or best is None:
            if self.flag_missing:
                iso = to_iso(indic.text, indic.script)
                hint = f' — suggested: "{suggest_roman(iso, indic.script)}"' if iso else ""
                return [PronunciationFinding(
                    severity="info",
                    description=(f'No pronunciation guide found for {label} word '
                                 f'"{indic.text}"{hint}'),
                    bbox=indic.bbox,
                )]
            return []

        score, roman, result = best
        suggestion = result["suggestion"]

        # Explicit exception list (brand names, deliberate spellings)
        allowed = self.exceptions.get(indic.text)
        if allowed and canonical(roman.text) in allowed:
            return []

        if score >= MATCH_OK:
            return []

        # Probably an English translation sitting next to the word, not a guide
        if score < TRANSLATION_CUTOFF and self._is_english(roman.text):
            if self.flag_missing:
                return [PronunciationFinding(
                    severity="info",
                    description=(f'{label} word "{indic.text}" has no Roman '
                                 f'pronunciation guide (only the English word '
                                 f'"{roman.text}") — suggested: "{suggestion}"'),
                    bbox=indic.bbox,
                )]
            return []

        if score >= MATCH_WARN:
            severity = "warning"
            verb = "may not match"
        else:
            severity = "error"
            verb = "does not match"

        return [PronunciationFinding(
            severity=severity,
            description=(
                f'Pronunciation {verb}: {label} "{indic.text}" is read as '
                f'"{suggestion}" (ISO: {result["expected_iso"]}), '
                f'but the book prints "{roman.text}" '
                f'[similarity {score:.0%}]'
            ),
            bbox=roman.bbox or indic.bbox,
        )]
