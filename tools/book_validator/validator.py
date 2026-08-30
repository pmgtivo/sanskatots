"""
SanskaTots Book Validator — Core Logic
Checks PDF book designs for: spelling errors, alignment issues,
pronunciation (transliteration) accuracy, AI visual review.
"""

import fitz  # PyMuPDF
import re
import json
import base64
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from pronunciation import (
    PronunciationChecker,
    SCRIPT_LABELS,
    TRANSLITERATION_AVAILABLE,
)

try:
    from spellchecker import SpellChecker
    SPELLCHECK_AVAILABLE = True
except ImportError:
    SPELLCHECK_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ─── Words to never flag as misspellings ────────────────────────────────────

CUSTOM_WORDS = {
    # Brand / company
    "sanskatots", "sanskar", "tots", "deethya",
    # Indian languages
    "kannada", "hindi", "telugu", "tamil", "malayalam", "sanskrit",
    # Hindu mythology & religion
    "shloka", "shlokas", "krishna", "arjuna", "ganesha", "lakshmi",
    "saraswati", "ramayana", "mahabharata", "bhagavad", "gita", "rama",
    "laxman", "sita", "hanuman", "vishnu", "shiva", "brahma", "durga",
    "vedic", "vedas", "dharma", "karma", "ahimsa", "yoga", "mantra",
    "namah", "namaskar", "namaste", "puja", "diwali", "navratri",
    # Product / education terms
    "velcro", "montessori", "preschool", "tracing", "busybook", "cutout",
    "workbook", "flashcard", "flashcards",
}


# ─── Data classes ────────────────────────────────────────────────────────────

@dataclass
class Issue:
    page: int           # 1-indexed page number
    category: str       # spelling | alignment | design | content | print_risk | pronunciation
    severity: str       # error | warning | info
    description: str
    bbox: Optional[Tuple] = None  # (x0, y0, x1, y1) in PDF pts for annotation


@dataclass
class ValidationReport:
    filename: str
    total_pages: int
    issues: List[Issue] = field(default_factory=list)

    def issues_for_page(self, page_num: int) -> List[Issue]:
        return [i for i in self.issues if i.page == page_num]

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    @property
    def pages_with_issues(self) -> List[int]:
        return sorted(set(i.page for i in self.issues))

    def summary(self) -> str:
        total = len(self.issues)
        if total == 0:
            return "✅ No issues found — design looks clean!"
        parts = []
        if self.error_count:
            parts.append(f"{self.error_count} error(s)")
        if self.warning_count:
            parts.append(f"{self.warning_count} warning(s)")
        if self.info_count:
            parts.append(f"{self.info_count} info")
        return f"{total} issue(s) found: {', '.join(parts)}"


# ─── Main Validator Class ────────────────────────────────────────────────────

class BookValidator:
    """
    Validates a PDF book design for:
      1. Spelling mistakes (pyspellchecker)
      2. Alignment / layout issues (PyMuPDF bounding box analysis)
      3. Pronunciation / transliteration accuracy (indic-transliteration)
      4. Visual design & fundamental issues (GPT-4o Vision)
    """

    def __init__(
        self,
        openai_api_key: str = None,
        pronunciation_languages: Optional[Sequence[str]] = None,
        flag_missing_pronunciation: bool = False,
        pronunciation_exceptions: Optional[Dict[str, Sequence[str]]] = None,
    ):
        # Spell checker
        if SPELLCHECK_AVAILABLE:
            self.spell = SpellChecker()
            self.spell.word_frequency.load_words(list(CUSTOM_WORDS))
        else:
            self.spell = None

        # Pronunciation / transliteration checker.
        # The spell checker doubles as an "is this a plain English word?" oracle
        # so English translations printed next to an Indic word are not mistaken
        # for wrong pronunciation guides.
        english_oracle = None
        if self.spell:
            english_oracle = lambda w: w in self.spell  # noqa: E731

        self.pronunciation = PronunciationChecker(
            languages=pronunciation_languages,
            flag_missing=flag_missing_pronunciation,
            english_words=english_oracle,
            exceptions=pronunciation_exceptions,
        )
        # page number -> set of Roman words that are pronunciation guides.
        # Shared between the pronunciation and spelling checks so the same page
        # is only analysed once, whichever check runs first.
        self._guide_cache: Dict[int, set] = {}
        self._pron_cache: Dict[int, list] = {}

        # OpenAI client for AI visual review
        self.openai_client = None
        if openai_api_key and OPENAI_AVAILABLE:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)

    def validate(
        self,
        pdf_path: str,
        run_spell: bool = True,
        run_alignment: bool = True,
        run_pronunciation: bool = True,
        run_ai: bool = True,
    ) -> ValidationReport:
        """
        Run all enabled checks on every page of the PDF.
        Returns a ValidationReport with all found issues.
        """
        doc = fitz.open(pdf_path)
        report = ValidationReport(filename=pdf_path, total_pages=len(doc))
        self._guide_cache.clear()
        self._pron_cache.clear()

        for idx in range(len(doc)):
            page = doc[idx]
            p = idx + 1  # 1-based page number for display

            if run_spell and self.spell:
                report.issues.extend(self._check_spelling(page, p))

            if run_alignment:
                report.issues.extend(self._check_alignment(page, p))

            if run_pronunciation:
                report.issues.extend(self._check_pronunciation(page, p))

            if run_ai and self.openai_client:
                report.issues.extend(self._ai_visual_review(page, p))

        doc.close()
        return report

    # ─── 1. Spell Check ──────────────────────────────────────────────────────

    def _analyze_pronunciation(self, page: fitz.Page, page_num: int):
        """Run (and memoise) the pronunciation pass for a page."""
        if page_num not in self._pron_cache:
            findings, guides = self.pronunciation.analyze_page(page, page_num)
            self._pron_cache[page_num] = findings
            self._guide_cache[page_num] = guides
        return self._pron_cache[page_num], self._guide_cache[page_num]

    def _check_spelling(self, page: fitz.Page, page_num: int) -> List[Issue]:
        issues = []
        blocks = page.get_text("dict")["blocks"]

        # Roman pronunciation guides ("aane", "pusthaka") are not English words
        # and must not be reported as misspellings.
        guide_words = set()
        if self.pronunciation.available:
            guide_words = self._analyze_pronunciation(page, page_num)[1]

        for block in blocks:
            if block.get("type") != 0:  # 0 = text
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    # Extract only plain English words (3+ chars, no digits)
                    words = re.findall(r"[a-zA-Z]{3,}", text)

                    # Filter out: ALL CAPS (acronyms), known custom words,
                    # proper nouns, and Indic pronunciation guides
                    words_to_check = [
                        w for w in words
                        if not w.isupper()                         # skip ALL_CAPS
                        and w.lower() not in CUSTOM_WORDS          # skip custom dict
                        and w.lower() not in guide_words           # skip transliterations
                        and not w[0].isupper()                     # skip capitalised (proper nouns)
                    ]

                    if not words_to_check:
                        continue

                    misspelled = self.spell.unknown(words_to_check)

                    for word in misspelled:
                        candidates = self.spell.candidates(word) or set()
                        suggestions = [c for c in list(candidates)[:3] if c != word.lower()]
                        desc = f'Possible misspelling: "{word}"'
                        if suggestions:
                            desc += f' — did you mean: {", ".join(suggestions)}?'

                        issues.append(Issue(
                            page=page_num,
                            category="spelling",
                            severity="error",
                            description=desc,
                            bbox=tuple(span["bbox"]),
                        ))

        return issues

    # ─── 2. Alignment / Layout Check ─────────────────────────────────────────

    def _check_alignment(self, page: fitz.Page, page_num: int) -> List[Issue]:
        issues = []
        w = page.rect.width
        h = page.rect.height

        # 8% safe zone margin — standard for offset printing
        mx = w * 0.08
        my = h * 0.08
        safe_zone = fitz.Rect(mx, my, w - mx, h - my)

        blocks = page.get_text("dict")["blocks"]
        text_blocks: List[Tuple[fitz.Rect, str]] = []

        for block in blocks:
            brect = fitz.Rect(block["bbox"])
            if brect.get_area() < 1:
                continue

            # ── Text block checks ─────────────────────────────────────────
            if block["type"] == 0:
                snippet = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        snippet += span.get("text", " ")
                snippet = snippet.strip()[:50]

                # Outside safe zone?
                if not safe_zone.contains(brect):
                    edges = []
                    if brect.x0 < mx:       edges.append("left margin")
                    if brect.x1 > w - mx:   edges.append("right margin")
                    if brect.y0 < my:       edges.append("top margin")
                    if brect.y1 > h - my:   edges.append("bottom margin")

                    if edges:
                        issues.append(Issue(
                            page=page_num,
                            category="alignment",
                            severity="warning",
                            description=(
                                f'Text outside safe zone ({", ".join(edges)}): '
                                f'"{snippet[:30]}..." — risk of being cut during print trimming'
                            ),
                            bbox=tuple(block["bbox"]),
                        ))

                text_blocks.append((brect, snippet))

            # ── Image block checks ────────────────────────────────────────
            elif block["type"] == 1:
                bleed_tolerance = 3  # pts
                if (brect.x0 < -bleed_tolerance or brect.x1 > w + bleed_tolerance
                        or brect.y0 < -bleed_tolerance or brect.y1 > h + bleed_tolerance):
                    issues.append(Issue(
                        page=page_num,
                        category="alignment",
                        severity="error",
                        description="Image extends beyond page boundary — will be clipped when printed",
                        bbox=tuple(block["bbox"]),
                    ))

        # ── Overlapping text blocks ───────────────────────────────────────
        for i in range(len(text_blocks)):
            for j in range(i + 1, len(text_blocks)):
                r1, s1 = text_blocks[i]
                r2, s2 = text_blocks[j]
                overlap = r1 & r2
                if not overlap.is_empty and overlap.get_area() > 40:
                    issues.append(Issue(
                        page=page_num,
                        category="alignment",
                        severity="error",
                        description=(
                            f'Text blocks overlap: "{s1[:25]}" and "{s2[:25]}" '
                            f'(overlap: {overlap.get_area():.0f} pt²)'
                        ),
                        bbox=tuple(overlap),
                    ))

        # ── Tiny text check (children need legible fonts) ─────────────────
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_size = span.get("size", 99)
                    text = span.get("text", "").strip()
                    if font_size < 7 and len(text) > 2:
                        issues.append(Issue(
                            page=page_num,
                            category="design",
                            severity="warning",
                            description=(
                                f'Very small text ({font_size:.1f}pt): "{text[:30]}" '
                                f'— minimum 8pt recommended for children\'s books'
                            ),
                            bbox=tuple(span["bbox"]),
                        ))

        return issues

    # ─── 3. Pronunciation / Transliteration Check ────────────────────────────

    def _check_pronunciation(self, page: fitz.Page, page_num: int) -> List[Issue]:
        """
        Verify that the Roman pronunciation guide printed next to each Indic
        word actually matches how that word is read.
        """
        if not self.pronunciation.available:
            return []

        findings = self._analyze_pronunciation(page, page_num)[0]

        issues: List[Issue] = []
        for finding in findings:
            issues.append(Issue(
                page=page_num,
                category="pronunciation",
                severity=finding.severity,
                description=finding.description,
                bbox=finding.bbox,
            ))
        return issues

    # ─── 4. AI Visual Review (GPT-4o Vision) ─────────────────────────────────

    def _ai_visual_review(self, page: fitz.Page, page_num: int) -> List[Issue]:
        issues = []
        try:
            # Render at 150 DPI (good quality without huge payload)
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()

            prompt = (
                "You are a professional book QA reviewer for SanskaTots, "
                "an Indian children's educational book brand. "
                "Target readers: Indian children aged 1.5–5 years. "
                "Books include: Velcro activity books, mythology story books, tracing workbooks, regional language books.\n\n"
                "Carefully review this page image and identify ONLY real, specific issues. "
                "Ignore Sanskrit/Kannada/Hindi/regional language words — those are correct.\n\n"
                "Check for:\n"
                "- spelling: Visible English text spelling mistakes\n"
                "- design: Text too small for children, poor contrast (light text on light bg), "
                "font inconsistency on same page, cluttered or hard-to-follow layout\n"
                "- alignment: Visually obvious misalignment — skewed text, uneven element spacing, "
                "elements clearly off-grid or uncentered when they should be centered\n"
                "- content: Grammatically wrong English, confusing activity instructions, "
                "factually incorrect content (e.g., wrong mythology facts)\n"
                "- pronunciation: The Roman pronunciation guide printed next to an Indic "
                "(Kannada/Hindi/Telugu/Tamil/Malayalam/Sanskrit) word does not match how that "
                "word is actually read; also broken/garbled Indic glyphs, missing matras or "
                "vowel signs, tofu boxes, or clipped conjunct characters\n"
                "- print_risk: Text or key elements very close to the page edge "
                "(within ~5mm) that will likely be cut during print trimming\n\n"
                "Rules:\n"
                "1. Output ONLY a JSON array — no explanation, no markdown, just [...]\n"
                "2. Each item: {\"category\": \"...\", \"severity\": \"error|warning|info\", "
                "\"description\": \"specific and actionable description\"}\n"
                "3. If no issues found: return []\n"
                "4. Maximum 8 items per page\n"
                "5. Do NOT flag style preferences — only genuine usability or print problems"
            )

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }],
                max_tokens=900,
                temperature=0.1,
            )

            raw = response.choices[0].message.content.strip()
            # Extract JSON array even if model adds surrounding text
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                for item in json.loads(json_match.group()):
                    if isinstance(item, dict):
                        issues.append(Issue(
                            page=page_num,
                            category=item.get("category", "design"),
                            severity=item.get("severity", "warning"),
                            description=f"[AI] {item.get('description', '').strip()}",
                        ))

        except Exception as e:
            issues.append(Issue(
                page=page_num,
                category="design",
                severity="info",
                description=f"AI review unavailable for this page: {e}",
            ))

        return issues


# ─── Rendering Helper ────────────────────────────────────────────────────────

def render_page_annotated(pdf_path: str, page_num: int, issues: List[Issue]) -> bytes:
    """
    Render a PDF page as PNG (2× zoom) with colored bounding box annotations
    drawn around all issues that have a bbox.

    Severity colors:
      error   → red
      warning → orange
      info    → blue
    """
    COLORS = {
        "error":   (1.0, 0.15, 0.15),
        "warning": (1.0, 0.65, 0.0),
        "info":    (0.1, 0.5,  1.0),
    }

    doc = fitz.open(pdf_path)
    page = doc[page_num - 1]  # convert to 0-indexed

    for issue in issues:
        if issue.bbox:
            try:
                rect = fitz.Rect(issue.bbox)
                color = COLORS.get(issue.severity, (0.5, 0.5, 0.5))
                page.draw_rect(rect, color=color, width=2.0)
            except Exception:
                pass  # skip invalid bbox

    mat = fitz.Matrix(2, 2)  # 2× zoom for screen clarity
    pix = page.get_pixmap(matrix=mat)
    doc.close()
    return pix.tobytes("png")
