# Book Validator
This is a Streamlit application that validates the structure and content of books. It checks for various aspects such as formatting, metadata, and content consistency to ensure that the book meets the required standards.

What the tool does
Input: Drop any book PDF → Click "Run Validation"

3 check layers:

Layer	What it catches	Cost
Spelling	English misspellings (auto-ignores Sanskrit/Kannada/Hindi)	Free, offline
Alignment	Text outside 8% safe zone, overlapping text blocks, images off-page, font < 7pt	Free, offline
AI Visual Review	GPT-4o looks at each rendered page — contrast, readability for kids, print risk, content accuracy	~₹0.50–1.50/page
Output:

Summary metrics: errors vs warnings vs pages affected
Per-page view: annotated page image (🔴 errors, 🟠 warnings marked directly on the design) + issue list
Downloadable .txt report for printer/designer handoff
To run:
cd tools/book_validator
streamlit run app.py