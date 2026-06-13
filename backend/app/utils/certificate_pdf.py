"""
Certificate PDF generator.

Generates A4 professional PDFs for:
  - Bonafide Certificate
  - Character Certificate
  - Course Completion Certificate
  - Transfer Certificate
  - Provisional Certificate

Each PDF embeds a QR code pointing to the public verification URL.
"""
import io
import uuid
from datetime import date, datetime
from typing import Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import qrcode
    import qrcode.image.pil
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False


def _check_deps() -> None:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab not installed. Run: pip install reportlab")


def _make_qr_image(data: str, size_cm: float = 3) -> Optional[object]:
    if not QR_AVAILABLE:
        return None
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return Image(buf, width=size_cm * cm, height=size_cm * cm)


def _base_styles():
    styles = getSampleStyleSheet()
    institution = ParagraphStyle(
        "institution",
        parent=styles["Normal"],
        fontSize=20,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a237e"),
        alignment=TA_CENTER,
        spaceAfter=2,
    )
    dept = ParagraphStyle(
        "dept",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#1a237e"),
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    cert_title = ParagraphStyle(
        "cert_title",
        parent=styles["Normal"],
        fontSize=16,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0d47a1"),
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=10,
        underline=True,
    )
    body = ParagraphStyle(
        "body",
        parent=styles["Normal"],
        fontSize=11,
        leading=20,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
    )
    small = ParagraphStyle(
        "small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    label_style = ParagraphStyle(
        "label", parent=styles["Normal"], fontSize=9, textColor=colors.grey
    )
    return styles, institution, dept, cert_title, body, small, label_style


def _build_header(story, institution_name: str, department: str, s_inst, s_dept):
    story.append(Paragraph(institution_name, s_inst))
    story.append(Paragraph(department, s_dept))
    story.append(
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a237e"), spaceAfter=4)
    )
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1a237e"), spaceAfter=16)
    )


def _build_footer(story, cert_number: str, issued_date: date, verify_url: str, s_small):
    story.append(Spacer(1, 0.8 * cm))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=8)
    )

    # Signature block + QR side by side
    qr_img = _make_qr_image(verify_url, size_cm=2.5)
    sig_content = (
        f"<br/><br/><br/>_________________________<br/>"
        f"Authorised Signatory<br/>"
        f"Date: {issued_date.strftime('%d %B %Y')}"
    )
    sig_para = Paragraph(sig_content, ParagraphStyle(
        "sig", fontSize=9, alignment=TA_CENTER
    ))

    if qr_img:
        qr_label = Paragraph(
            f"Scan to verify<br/><font size='7' color='grey'>{cert_number}</font>",
            ParagraphStyle("qrlabel", fontSize=8, alignment=TA_CENTER),
        )
        footer_table = Table(
            [[sig_para, ""], ["", [qr_img, qr_label]]],
            colWidths=[10 * cm, 7 * cm],
        )
        footer_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(footer_table)
    else:
        story.append(sig_para)
        story.append(Paragraph(f"Certificate No: {cert_number}", s_small))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(
        "This is a computer-generated certificate. Verify authenticity at: " + verify_url,
        s_small,
    ))


# ── Bonafide Certificate ───────────────────────────────────────────────────────

def generate_bonafide(
    *,
    student_name: str,
    roll_number: str,
    department: str,
    semester: int,
    section: str,
    academic_year: str,
    purpose: str,
    certificate_number: str,
    issued_date: date,
    institution_name: str = "Smart Campus",
    verify_url: str = "",
) -> bytes:
    _check_deps()
    _, s_inst, s_dept, s_title, s_body, s_small, _ = _base_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    _build_header(story, institution_name, department, s_inst, s_dept)
    story.append(Paragraph("BONAFIDE CERTIFICATE", s_title))
    story.append(Paragraph(
        f"This is to certify that <b>{student_name}</b>, bearing Roll Number <b>{roll_number}</b>, "
        f"is a bonafide student of the <b>{department}</b> in <b>Semester {semester}</b>, "
        f"<b>Section {section}</b> for the academic year <b>{academic_year}</b>.",
        s_body,
    ))
    story.append(Paragraph(
        f"This certificate is issued for the purpose of <b>{purpose}</b> as requested by the student.",
        s_body,
    ))
    story.append(Paragraph(
        "The student bears good conduct and is known to us.",
        s_body,
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Certificate Number: <b>{certificate_number}</b> &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"Issued On: <b>{issued_date.strftime('%d %B %Y')}</b>",
        ParagraphStyle("cert_meta", fontSize=9, alignment=TA_CENTER,
                       textColor=colors.HexColor("#455a64")),
    ))
    _build_footer(story, certificate_number, issued_date, verify_url, s_small)
    doc.build(story)
    return buf.getvalue()


# ── Character Certificate ──────────────────────────────────────────────────────

def generate_character(
    *,
    student_name: str,
    roll_number: str,
    department: str,
    semester: int,
    section: str,
    academic_year: str,
    purpose: str,
    certificate_number: str,
    issued_date: date,
    institution_name: str = "Smart Campus",
    verify_url: str = "",
) -> bytes:
    _check_deps()
    _, s_inst, s_dept, s_title, s_body, s_small, _ = _base_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    _build_header(story, institution_name, department, s_inst, s_dept)
    story.append(Paragraph("CHARACTER CERTIFICATE", s_title))
    story.append(Paragraph(
        f"This is to certify that <b>{student_name}</b>, Roll Number <b>{roll_number}</b>, "
        f"student of <b>{department}</b> — Semester <b>{semester}</b>, Section <b>{section}</b>, "
        f"Academic Year <b>{academic_year}</b>, has been known to us during the course of their study.",
        s_body,
    ))
    story.append(Paragraph(
        "To the best of our knowledge, the student has maintained <b>good moral character</b> "
        "and has been disciplined throughout their association with this institution. "
        "No adverse remarks have been recorded against the student.",
        s_body,
    ))
    story.append(Paragraph(
        f"This certificate is issued on request for the purpose of <b>{purpose}</b>.",
        s_body,
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Certificate Number: <b>{certificate_number}</b> &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"Issued On: <b>{issued_date.strftime('%d %B %Y')}</b>",
        ParagraphStyle("cert_meta", fontSize=9, alignment=TA_CENTER,
                       textColor=colors.HexColor("#455a64")),
    ))
    _build_footer(story, certificate_number, issued_date, verify_url, s_small)
    doc.build(story)
    return buf.getvalue()


# ── Course Completion Certificate ─────────────────────────────────────────────

def generate_course_completion(
    *,
    student_name: str,
    roll_number: str,
    department: str,
    program: str,
    academic_year: str,
    purpose: str,
    certificate_number: str,
    issued_date: date,
    institution_name: str = "Smart Campus",
    verify_url: str = "",
) -> bytes:
    _check_deps()
    styles, s_inst, s_dept, s_title, s_body, s_small, _ = _base_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    _build_header(story, institution_name, department, s_inst, s_dept)
    story.append(Paragraph("COURSE COMPLETION CERTIFICATE", s_title))

    # Decorative border line
    story.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#1a237e"),
                             hAlign="CENTER", spaceAfter=12))

    story.append(Paragraph(
        f"This is to certify that <b>{student_name}</b>, Roll Number <b>{roll_number}</b>, "
        f"has successfully completed the <b>{program}</b> programme offered by the "
        f"<b>{department}</b>.",
        s_body,
    ))
    story.append(Paragraph(
        f"The student has fulfilled all the academic requirements as prescribed by the institution "
        f"for the academic year <b>{academic_year}</b>.",
        s_body,
    ))
    story.append(Paragraph(
        f"This certificate is issued for the purpose of <b>{purpose}</b>.",
        s_body,
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Certificate Number: <b>{certificate_number}</b> &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"Issued On: <b>{issued_date.strftime('%d %B %Y')}</b>",
        ParagraphStyle("cert_meta", fontSize=9, alignment=TA_CENTER,
                       textColor=colors.HexColor("#455a64")),
    ))
    _build_footer(story, certificate_number, issued_date, verify_url, s_small)
    doc.build(story)
    return buf.getvalue()


# ── Transfer Certificate ───────────────────────────────────────────────────────

def generate_transfer(
    *,
    student_name: str,
    roll_number: str,
    department: str,
    semester: int,
    academic_year: str,
    purpose: str,
    certificate_number: str,
    issued_date: date,
    institution_name: str = "Smart Campus",
    verify_url: str = "",
) -> bytes:
    _check_deps()
    _, s_inst, s_dept, s_title, s_body, s_small, _ = _base_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    _build_header(story, institution_name, department, s_inst, s_dept)
    story.append(Paragraph("TRANSFER CERTIFICATE", s_title))
    story.append(Paragraph(
        f"This is to certify that <b>{student_name}</b>, Roll Number <b>{roll_number}</b>, "
        f"was a student of <b>{department}</b>, Semester <b>{semester}</b>, "
        f"Academic Year <b>{academic_year}</b> at this institution.",
        s_body,
    ))
    story.append(Paragraph(
        "The student has been granted a <b>Transfer Certificate</b> upon request. "
        "All dues towards the institution have been cleared, and there is no pending "
        "disciplinary action against the student.",
        s_body,
    ))
    story.append(Paragraph(
        f"This certificate is issued for the purpose of <b>{purpose}</b>.",
        s_body,
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Certificate Number: <b>{certificate_number}</b> &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"Issued On: <b>{issued_date.strftime('%d %B %Y')}</b>",
        ParagraphStyle("cert_meta", fontSize=9, alignment=TA_CENTER,
                       textColor=colors.HexColor("#455a64")),
    ))
    _build_footer(story, certificate_number, issued_date, verify_url, s_small)
    doc.build(story)
    return buf.getvalue()


# ── Provisional Certificate ────────────────────────────────────────────────────

def generate_provisional(
    *,
    student_name: str,
    roll_number: str,
    department: str,
    program: str,
    academic_year: str,
    purpose: str,
    certificate_number: str,
    issued_date: date,
    institution_name: str = "Smart Campus",
    verify_url: str = "",
) -> bytes:
    _check_deps()
    _, s_inst, s_dept, s_title, s_body, s_small, _ = _base_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2.5*cm, leftMargin=2.5*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    story = []
    _build_header(story, institution_name, department, s_inst, s_dept)
    story.append(Paragraph("PROVISIONAL CERTIFICATE", s_title))
    story.append(Paragraph(
        f"This is to certify that <b>{student_name}</b>, Roll Number <b>{roll_number}</b>, "
        f"has <b>provisionally passed</b> all the examinations of the <b>{program}</b> programme "
        f"offered by the <b>{department}</b> for the academic year <b>{academic_year}</b>.",
        s_body,
    ))
    story.append(Paragraph(
        "This provisional certificate is issued pending the award of the official degree/diploma "
        "by the examining authority. The final certificate will be issued upon completion of all "
        "formalities.",
        s_body,
    ))
    story.append(Paragraph(
        f"This certificate is issued for the purpose of <b>{purpose}</b>.",
        s_body,
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Certificate Number: <b>{certificate_number}</b> &nbsp;&nbsp; | &nbsp;&nbsp; "
        f"Issued On: <b>{issued_date.strftime('%d %B %Y')}</b>",
        ParagraphStyle("cert_meta", fontSize=9, alignment=TA_CENTER,
                       textColor=colors.HexColor("#455a64")),
    ))
    _build_footer(story, certificate_number, issued_date, verify_url, s_small)
    doc.build(story)
    return buf.getvalue()


# ── Dispatcher ────────────────────────────────────────────────────────────────

def generate_certificate_pdf(cert_type: str, **kwargs) -> bytes:
    """Route to the correct generator based on certificate type."""
    generators = {
        "bonafide": generate_bonafide,
        "character": generate_character,
        "course_completion": generate_course_completion,
        "transfer": generate_transfer,
        "provisional": generate_provisional,
    }
    fn = generators.get(cert_type)
    if not fn:
        raise ValueError(f"Unknown certificate type: {cert_type}")
    return fn(**kwargs)
