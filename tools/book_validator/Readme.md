# Book Validator

Streamlit app that validates a book PDF before it goes to print. Drop a PDF in → click **Run Validation**.

## What it checks

| Layer | What it catches | Cost |
|---|---|---|
| **Spelling** | English misspellings (auto-ignores Sanskrit/Kannada/Hindi words *and* Roman pronunciation guides) | Free, offline |
| **Alignment** | Text outside the 8% safe zone, overlapping text blocks, images off-page, fonts < 7pt | Free, offline |
| **Pronunciation** | Roman pronunciation guides that don't match the Indic word they sit next to | Free, offline |
| **AI Visual Review** | GPT-4o looks at each rendered page — contrast, readability for kids, print risk, content accuracy, garbled Indic glyphs | ~₹0.50–1.50/page |

## Pronunciation check (regional-language books)

Verifies that the Roman guide printed next to an Indic word matches how that word
is actually read:

```
ಆನೆ (aane)        ✅        ಮನೆ (mana)      ⚠️  reads as "mane"
आम (aam)          ✅        गणेश (Ganpati)  ⚠️  reads as "ganesh"
ಪುಸ್ತಕ            ✅        ಶ್ರೀ            ⚠️  reads as "shree"
pusthaka                     shroo
```

Supported scripts: **Kannada, Devanagari (Hindi/Sanskrit/Marathi), Telugu, Tamil,
Malayalam, Bengali, Gujarati, Gurmukhi, Odia.**

How it works: the Indic word is transliterated to ISO-15919 with
`indic-transliteration`, then both sides are reduced to a comparison skeleton that
folds the things Indian romanisation is inconsistent about — vowel length,
aspiration (`th`/`t`), retroflex vs dental, `sh`/`s`, `w`/`v`, doubled consonants
and the silent final schwa. So `aane` / `ane` / `aanay` all pass, while `anne` or
`mana` get flagged.

Layouts recognised: `ಆನೆ (aane)` inline, `ಆನೆ  aane` side by side, and stacked
flashcard style (Indic word with the guide on the line below).

Severity: ≥ 86% similarity = pass · 60–86% = warning · < 60% = error.

Notes:
- An English *translation* next to an Indic word (`ಆನೆ Elephant`) is recognised as
  a translation, not a bad pronunciation guide, and is not flagged.
- Pronunciation guides are automatically excluded from the English spell check, so
  words like `aane` and `pusthaka` no longer show up as misspellings.

### Options (sidebar → 🗣️ Pronunciation Options)
- **Languages in this book** — restrict checking to specific scripts, or leave
  empty to auto-detect.
- **Report Indic words with no pronunciation guide** — for workbooks where every
  word must carry a Roman guide.

## Output

- Summary metrics: errors vs warnings vs pages affected, plus a per-category breakdown
- Per-page view: annotated page image (🔴 errors, 🟠 warnings boxed directly on the design) + issue list
- Downloadable `.txt` report for printer/designer handoff

## Run

```bash
cd tools/book_validator
pip install -r requirements.txt
streamlit run app.py
```

## Using it from Python

```python
from validator import BookValidator

validator = BookValidator(
    pronunciation_languages=["kannada"],          # None = auto-detect
    flag_missing_pronunciation=False,
    pronunciation_exceptions={"ಶ್ರೀ": ["Shri"]},   # accepted brand spellings
)
report = validator.validate("book.pdf", run_ai=False)
print(report.summary())
```
