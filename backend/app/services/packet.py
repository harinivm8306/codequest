"""Application packet: one PDF per scheme, for the citizen to carry to the office.

It is clearly labelled as a helper sheet, not an official form. The PDF is in
English because it is read by office staff; the in-app checklist and the print
view show the same content in the citizen's own language (browsers shape Tamil
and Devanagari correctly, the PDF library does not).
"""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.fields import FIELD_BY_NAME, label
from app.services import rules
from app.services.doc_doctor import checklist

PROFILE_ROWS = [
    "name",
    "age",
    "gender",
    "marital_status",
    "district",
    "state",
    "annual_family_income",
    "caste_category",
    "occupation",
    "land_acres",
    "disability_percent",
    "bpl_card",
    "has_bank_account",
]
NICE = {
    "name": "Name",
    "age": "Age",
    "gender": "Gender",
    "marital_status": "Marital status",
    "district": "District",
    "state": "State",
    "annual_family_income": "Annual family income (Rs)",
    "caste_category": "Community category",
    "occupation": "Occupation",
    "land_acres": "Farm land (acres)",
    "disability_percent": "Disability (%)",
    "bpl_card": "BPL / PHH / AAY card",
    "has_bank_account": "Bank account",
}


TICK = '<font name="ZapfDingbats" color="#1B7F4B">4</font>'
CROSS = '<font name="ZapfDingbats" color="#B3261E">8</font>'


def pdf_text(s: str) -> str:
    """The standard PDF fonts have no rupee sign; write it as Rs."""
    return s.replace("₹", "Rs. ").replace("Rs.  ", "Rs. ")


def _fmt(field: str, v) -> str:
    if v is None:
        return "—"
    f = FIELD_BY_NAME.get(field)
    if f:
        for o in f.options:
            if o.value == v and field not in ("annual_family_income", "land_acres", "disability_percent", "state"):
                return label(o, "en")
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if field == "annual_family_income":
        return f"{v:,} (as stated by applicant)"
    return str(v)


def build_pdf(scheme_id: str, profile: dict, docs: list[dict], today: date | None = None) -> bytes:
    today = today or date.today()
    s = rules.load_schemes()[scheme_id]
    result = rules.explain(rules.evaluate(s, profile), "en")
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13)
    h = ParagraphStyle("h", parent=styles["Heading2"], fontSize=12.5, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#0b5d4b"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"SchemeSathi packet - {s['name']['en']}",
        author="SchemeSathi",
    )
    el = []
    banner = Table(
        [
            [
                Paragraph(
                    "<b>HELPER SHEET — NOT AN OFFICIAL APPLICATION FORM</b><br/>Prepared with SchemeSathi to help the applicant and the office. "
                    "The final decision is made by the department.",
                    ParagraphStyle("b", parent=body, textColor=colors.white),
                )
            ]
        ],
        colWidths=[178 * mm],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0b5d4b")),
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    el += [banner, Spacer(1, 8)]
    el.append(Paragraph(f"<b>{s['name']['en']}</b>", ParagraphStyle("t", parent=styles["Title"], fontSize=16, alignment=0, spaceAfter=2)))
    status = {"eligible": "Likely eligible", "needs_info": "More information needed", "not_eligible": "Not eligible on stated facts"}[result["status"]]
    el.append(
        Paragraph(f"Status: <b>{status}</b> &nbsp;·&nbsp; Prepared on {today.strftime('%d %b %Y')} &nbsp;·&nbsp; Rules version {rules.rules_version()}", small)
    )
    el.append(Paragraph(f"<b>Benefit:</b> {pdf_text(s['benefit']['en'])}", body))
    el.append(Paragraph(f"<b>Where to apply:</b> {s['apply_at']['en']}", body))

    el.append(Paragraph("Applicant details (as told to SchemeSathi)", h))
    rows = [[NICE[k], _fmt(k, profile.get(k))] for k in PROFILE_ROWS if profile.get(k) is not None]
    if rows:
        t = Table(rows, colWidths=[62 * mm, 116 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d3cf")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4f2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        el.append(t)

    el.append(Paragraph("Why the applicant matches", h))
    for c in result["passed"]:
        src = c["source"]
        el.append(
            Paragraph(f"{TICK} {pdf_text(c['text'])}<br/><font size=8 color='#555555'>Source: {src['title']} — {src['locator']} — {src['url']}</font>", body)
        )
    for c in result["failed"]:
        el.append(Paragraph(f"{CROSS} {pdf_text(c['text'])}", body))
    if result["missing"]:
        el.append(Paragraph("Still to confirm: " + ", ".join(NICE.get(m, m.replace("_", " ")) for m in result["missing"]), body))
    if result["office_checks"]:
        el.append(Paragraph("The office will also check", h))
        for o in result["office_checks"]:
            el.append(Paragraph(f"• {pdf_text(o)}", body))

    el.append(Paragraph("Documents to carry", h))
    cl = checklist(s["required_documents"], docs, "en")
    mark = {"ok": "Checked", "problem": "Problem - see note", "missing": "Bring original + 1 copy"}
    t = Table(
        [["Document", "Status", "Note"]] + [[c["label"], mark[c["status"]], Paragraph("; ".join(i["message"] for i in c["issues"]) or "", small)] for c in cl],
        colWidths=[70 * mm, 38 * mm, 70 * mm],
    )
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8d3cf")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b5d4b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    el.append(t)
    el.append(Spacer(1, 10))
    el.append(
        Paragraph(
            f"Official scheme page: {s['source_url']} · Rules verified on {s['verified_on']}. "
            "Aadhaar numbers are never stored by SchemeSathi; only the last 4 digits may appear.",
            small,
        )
    )
    doc.build(el)
    return buf.getvalue()
