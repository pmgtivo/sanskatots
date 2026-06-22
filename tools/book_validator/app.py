"""
SanskaTots Book Validator — Streamlit UI
Run: streamlit run app.py
"""

import streamlit as st
import tempfile
import os
from validator import BookValidator, ValidationReport, render_page_annotated

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="SanskaTots Book Validator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📚 SanskaTots Book Validator")
st.caption("Upload a PDF book design to check for spelling errors, alignment issues, and design problems.")

# ─── Sidebar — Settings ───────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("Checks to Run")
    run_spell = st.checkbox(
        "🔤 Spelling Check",
        value=True,
        help="Detects English spelling mistakes. Ignores Sanskrit/Kannada/Hindi/regional language words automatically.",
    )
    run_alignment = st.checkbox(
        "📐 Alignment & Layout Check",
        value=True,
        help="Checks safe zone margins, overlapping text blocks, images off-page, and fonts too small for children.",
    )

    if not run_spell and not run_alignment:
        st.warning("Select at least one check to run.")

    st.divider()

    # AI Visual Review — advanced / optional
    with st.expander("🤖 AI Visual Review (Advanced)", expanded=False):
        run_ai = st.checkbox(
            "Enable AI Review (GPT-4o)",
            value=False,
            help="Sends each page image to GPT-4o Vision for deeper design, content, and print-risk analysis.",
        )
        if run_ai:
            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-...",
                help="Get yours at platform.openai.com",
            )
            if not api_key:
                st.info("Enter API key above to enable AI review.")
            st.caption("~₹0.50–1.50 per page (GPT-4o Vision pricing)")
        else:
            api_key = None
            st.caption("Spelling + Alignment checks are 100% free and offline.")

# ─── Main — File Upload ───────────────────────────────────────────────────────

uploaded_file = st.file_uploader(
    "Drop your book PDF here",
    type=["pdf"],
    help="Upload the final or draft PDF of your book design",
)

# ─── Validation ──────────────────────────────────────────────────────────────

if uploaded_file is not None:
    # Save to temp file (validator needs a file path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    st.divider()

    # Validate on button click
    if st.button(
        "🔍 Run Validation",
        type="primary",
        use_container_width=True,
        disabled=(not run_spell and not run_alignment and not run_ai),
    ):
        # Sanity checks
        if not run_spell and not run_alignment and not run_ai:
            st.error("Please select at least one check (Spelling or Alignment) in the sidebar.")
            st.stop()

        if run_ai and not api_key:
            st.warning("AI Visual Review is enabled but no API key was provided. Running without AI review.")
            run_ai = False

        validator = BookValidator(openai_api_key=api_key if run_ai else None)

        # Progress bar — page by page
        import fitz
        doc = fitz.open(tmp_path)
        total_pages = len(doc)
        doc.close()

        progress = st.progress(0, text="Starting validation...")
        report_placeholder = st.empty()

        # Run validation with progress feedback
        import time
        with st.spinner(f"Validating {total_pages} page(s)..."):
            # We re-implement page-by-page for progress tracking
            import fitz as _fitz
            from validator import Issue

            doc = _fitz.open(tmp_path)
            report = ValidationReport(filename=uploaded_file.name, total_pages=total_pages)

            for idx in range(total_pages):
                page_label = idx + 1
                progress.progress(
                    (idx) / total_pages,
                    text=f"Checking page {page_label} of {total_pages}..."
                )

                page = doc[idx]

                if run_spell and validator.spell:
                    report.issues.extend(validator._check_spelling(page, page_label))

                if run_alignment:
                    report.issues.extend(validator._check_alignment(page, page_label))

                if run_ai and validator.openai_client:
                    report.issues.extend(validator._ai_visual_review(page, page_label))

            doc.close()
            progress.progress(1.0, text="Validation complete!")

        # Store in session state so results persist on re-render
        st.session_state["report"] = report
        st.session_state["pdf_path"] = tmp_path
        st.session_state["filename"] = uploaded_file.name

# ─── Results Display ──────────────────────────────────────────────────────────

if "report" in st.session_state:
    report: ValidationReport = st.session_state["report"]
    pdf_path: str = st.session_state["pdf_path"]

    st.divider()

    # ── Summary metrics ───────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Pages", report.total_pages)
    with col2:
        st.metric(
            "Errors",
            report.error_count,
            delta=None,
            delta_color="inverse",
            help="Must fix before printing",
        )
        if report.error_count > 0:
            st.error(f"{report.error_count} error(s) found")
    with col3:
        st.metric(
            "Warnings",
            report.warning_count,
            help="Recommended to review before printing",
        )
        if report.warning_count > 0:
            st.warning(f"{report.warning_count} warning(s)")
    with col4:
        pages_affected = len(report.pages_with_issues)
        st.metric("Pages with Issues", pages_affected)
        if pages_affected == 0:
            st.success("✅ All pages clean!")

    # ── Overall banner ────────────────────────────────────────────────────
    st.divider()
    if len(report.issues) == 0:
        st.success("🎉 No issues found! Your book design looks clean and ready.")
    else:
        st.info(f"📋 {report.summary()} — Review each page below.")

    # ── Category breakdown ────────────────────────────────────────────────
    if report.issues:
        from collections import Counter
        cat_counts = Counter(i.category for i in report.issues)
        cat_cols = st.columns(len(cat_counts))
        CAT_ICONS = {
            "spelling":   "🔤",
            "alignment":  "📐",
            "design":     "🎨",
            "content":    "📝",
            "print_risk": "✂️",
        }
        for col, (cat, count) in zip(cat_cols, sorted(cat_counts.items())):
            with col:
                icon = CAT_ICONS.get(cat, "🔍")
                st.metric(f"{icon} {cat.replace('_', ' ').title()}", count)

    st.divider()

    # ── Per-page results ──────────────────────────────────────────────────
    st.subheader("Page-by-Page Results")

    SEV_COLOR = {
        "error":   "🔴",
        "warning": "🟠",
        "info":    "🔵",
    }

    if not report.pages_with_issues:
        st.success("No issues detected on any page.")
    else:
        # Tabs: "All Pages" + one per affected page
        tab_labels = ["📋 All Issues"] + [
            f"Page {p} ({len(report.issues_for_page(p))})"
            for p in report.pages_with_issues
        ]
        tabs = st.tabs(tab_labels)

        # Tab 0 — All issues flat list
        with tabs[0]:
            for issue in sorted(report.issues, key=lambda x: (x.page, x.severity)):
                icon = SEV_COLOR.get(issue.severity, "⚪")
                with st.expander(
                    f"{icon} Page {issue.page} | {issue.category.replace('_',' ').upper()} — {issue.description[:80]}",
                    expanded=False,
                ):
                    st.write(f"**Category:** {issue.category.replace('_',' ').title()}")
                    st.write(f"**Severity:** {issue.severity.upper()}")
                    st.write(f"**Description:** {issue.description}")
                    if issue.bbox:
                        st.caption(f"Location (PDF coords): {[round(x, 1) for x in issue.bbox]}")

        # Tabs per affected page
        for tab_idx, page_num in enumerate(report.pages_with_issues):
            with tabs[tab_idx + 1]:
                page_issues = report.issues_for_page(page_num)

                col_left, col_right = st.columns([1, 1])

                # Left: annotated page render
                with col_left:
                    st.caption(f"**Page {page_num}** — annotated (🔴 error · 🟠 warning · 🔵 info)")
                    try:
                        annotated_png = render_page_annotated(pdf_path, page_num, page_issues)
                        st.image(annotated_png, use_container_width=True)
                    except Exception as e:
                        st.error(f"Could not render page: {e}")

                # Right: issue list
                with col_right:
                    st.caption(f"**{len(page_issues)} issue(s) on this page**")
                    for issue in sorted(page_issues, key=lambda x: x.severity):
                        icon = SEV_COLOR.get(issue.severity, "⚪")
                        sev_label = issue.severity.upper()
                        cat_label = issue.category.replace("_", " ").title()

                        if issue.severity == "error":
                            st.error(f"{icon} **[{sev_label}] {cat_label}**  \n{issue.description}")
                        elif issue.severity == "warning":
                            st.warning(f"{icon} **[{sev_label}] {cat_label}**  \n{issue.description}")
                        else:
                            st.info(f"{icon} **[{sev_label}] {cat_label}**  \n{issue.description}")

    # ── Export: plain text report ─────────────────────────────────────────
    st.divider()
    st.subheader("Export Report")

    def build_text_report(report: ValidationReport) -> str:
        lines = [
            "SANSKATOTS BOOK VALIDATION REPORT",
            "=" * 50,
            f"File: {report.filename}",
            f"Total Pages: {report.total_pages}",
            f"Total Issues: {len(report.issues)}",
            f"  Errors:   {report.error_count}",
            f"  Warnings: {report.warning_count}",
            f"  Info:     {report.info_count}",
            "",
        ]
        if not report.issues:
            lines.append("✅ No issues found.")
        else:
            for page_num in sorted(set(i.page for i in report.issues)):
                lines.append(f"\n--- PAGE {page_num} ---")
                for issue in report.issues_for_page(page_num):
                    lines.append(
                        f"  [{issue.severity.upper()}] [{issue.category.upper()}] {issue.description}"
                    )
        return "\n".join(lines)

    report_text = build_text_report(report)
    st.download_button(
        label="⬇️ Download Report (.txt)",
        data=report_text,
        file_name=f"validation_{st.session_state['filename'].replace('.pdf', '')}.txt",
        mime="text/plain",
        use_container_width=True,
    )

# ─── Footer ───────────────────────────────────────────────────────────────────
st.divider()
st.caption("SanskaTots Book Validator · Deethya Enterprises · Bengaluru")
