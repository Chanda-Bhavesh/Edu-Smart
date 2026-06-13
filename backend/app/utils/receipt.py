"""
PDF fee receipt generator using ReportLab.

Generates an A4 receipt with:
 - Campus header
 - Student details
 - Fee breakdown table
 - Payment details
 - Stamp-style PAID / PARTIAL banner
"""
import io
from datetime import date
from typing import Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _check_reportlab() -> None:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError(
            "reportlab is not installed. Run: pip install reportlab"
        )


def generate_fee_receipt(
    *,
    receipt_number: str,
    student_name: str,
    roll_number: str,
    department: str,
    semester: str,
    academic_year: str,
    payment_date: date,
    payment_mode: str,
    transaction_id: Optional[str],
    amount_paid: float,
    total_fee: float,
    discount: float,
    fine: float,
    net_amount: float,
    previous_paid: float,
    balance_after: float,
    fee_breakdown: dict,      # {"Tuition Fee": 50000, "Exam Fee": 2000, ...}
    status: str,              # "paid" | "partial"
    campus_name: str = "Smart Campus",
) -> bytes:
    """Return PDF bytes for the fee receipt."""
    _check_reportlab()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "heading", parent=styles["Heading1"],
        fontSize=18, textColor=colors.HexColor("#1a237e"),
        spaceAfter=4,
    )
    subheading = ParagraphStyle(
        "subheading", parent=styles["Normal"],
        fontSize=11, textColor=colors.grey,
        spaceAfter=12,
    )
    label = ParagraphStyle("label", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    value = ParagraphStyle("value", parent=styles["Normal"], fontSize=10)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph(campus_name, heading))
    story.append(Paragraph("Fee Payment Receipt", subheading))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1a237e")))
    story.append(Spacer(1, 0.4 * cm))

    # Receipt meta
    meta_data = [
        ["Receipt No.", receipt_number, "Payment Date", str(payment_date)],
        ["Academic Year", academic_year, "Payment Mode", payment_mode.replace("_", " ").title()],
    ]
    if transaction_id:
        meta_data.append(["Transaction ID", transaction_id, "", ""])

    meta_table = Table(meta_data, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 4 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Student Details ───────────────────────────────────────────────────────
    story.append(Paragraph("Student Details", styles["Heading3"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.3 * cm))

    student_data = [
        ["Name", student_name, "Roll Number", roll_number],
        ["Department", department, "Semester", semester],
    ]
    student_table = Table(student_data, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 4 * cm])
    student_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.grey),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Fee Breakdown ─────────────────────────────────────────────────────────
    story.append(Paragraph("Fee Breakdown", styles["Heading3"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.3 * cm))

    breakdown_rows = [["Fee Component", "Amount (₹)"]]
    for label_text, amount in fee_breakdown.items():
        breakdown_rows.append([label_text, f"{float(amount):,.2f}"])

    breakdown_rows.append(["", ""])
    breakdown_rows.append(["Total Fee", f"{total_fee:,.2f}"])
    if discount > 0:
        breakdown_rows.append(["Discount / Scholarship", f"- {discount:,.2f}"])
    if fine > 0:
        breakdown_rows.append(["Late Payment Fine", f"+ {fine:,.2f}"])
    breakdown_rows.append(["Net Payable", f"{net_amount:,.2f}"])

    bd_table = Table(breakdown_rows, colWidths=[12 * cm, 5 * cm])
    bd_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.whitesmoke, colors.white]),
        ("LINEBELOW", (0, -3), (-1, -3), 0.5, colors.lightgrey),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8eaf6")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 8),
    ])
    bd_table.setStyle(bd_style)
    story.append(bd_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Payment Summary ───────────────────────────────────────────────────────
    story.append(Paragraph("Payment Summary", styles["Heading3"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.3 * cm))

    pay_data = [
        ["Previous Amount Paid", f"₹ {previous_paid:,.2f}"],
        ["Amount Paid (This Receipt)", f"₹ {amount_paid:,.2f}"],
        ["Balance Remaining", f"₹ {balance_after:,.2f}"],
    ]
    pay_table = Table(pay_data, colWidths=[12 * cm, 5 * cm])
    pay_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 2), (-1, 2),
         colors.green if balance_after == 0 else colors.HexColor("#e65100")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (0, -1), 8),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 0.8 * cm))

    # ── PAID / PARTIAL stamp ──────────────────────────────────────────────────
    stamp_text = "✓ PAID IN FULL" if status == "paid" else "◑ PARTIALLY PAID"
    stamp_color = colors.green if status == "paid" else colors.HexColor("#e65100")
    stamp_style = ParagraphStyle(
        "stamp",
        parent=styles["Normal"],
        fontSize=16,
        textColor=stamp_color,
        borderColor=stamp_color,
        borderWidth=2,
        borderPadding=8,
        alignment=1,  # center
        fontName="Helvetica-Bold",
    )
    story.append(Paragraph(stamp_text, stamp_style))
    story.append(Spacer(1, 1 * cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.2 * cm))
    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=1
    )
    story.append(Paragraph(
        "This is a computer-generated receipt and does not require a physical signature.",
        footer_style,
    ))
    story.append(Paragraph(
        f"{campus_name} — Fee Management System",
        footer_style,
    ))

    doc.build(story)
    return buffer.getvalue()
