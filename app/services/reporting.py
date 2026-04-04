from __future__ import annotations

import io

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DARK_BLUE = HexColor("#1A3A5C")
MED_BLUE = HexColor("#2563EB")
TEAL = HexColor("#0D9488")
GREEN = HexColor("#16A34A")
RED = HexColor("#DC2626")
LIGHT_GRAY = HexColor("#F9FAFB")
MID_GRAY = HexColor("#6B7280")


def build_applicant_report_pdf(record, lang: str = "ru") -> bytes:
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

    title_style = ParagraphStyle(
        "title",
        fontSize=20,
        textColor=DARK_BLUE,
        fontName="Helvetica-Bold",
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "sub",
        fontSize=11,
        textColor=MID_GRAY,
        fontName="Helvetica",
        spaceAfter=12,
    )
    body_style = ParagraphStyle(
        "body",
        fontSize=10,
        textColor=black,
        fontName="Helvetica",
        spaceAfter=6,
        leading=14,
    )
    label_style = ParagraphStyle(
        "label",
        fontSize=9,
        textColor=MID_GRAY,
        fontName="Helvetica",
        spaceAfter=2,
    )

    score = record.score
    score_color = GREEN if score >= 70 else (HexColor("#D97706") if score >= 50 else RED)

    if lang == "kz":
        title_text = "СУБСИДИЯ БЕРІЛУІ ТУРАЛЫ ҚОРЫТЫНДЫ"
        recommended_text = "ҰСЫНЫЛАДЫ" if record.recommended else "ҚАРАЛАДЫ"
        pos_label = "Күшті жақтары:"
        neg_label = "Тәуекелдер:"
        disclaimer = (
            "Бұл қорытынды AI жүйесі AgriScore KZ арқылы жасалған. "
            "Түпкілікті шешімді комиссия қабылдайды."
        )
    else:
        title_text = "ЗАКЛЮЧЕНИЕ ПО ЗАЯВКЕ НА СУБСИДИЮ"
        recommended_text = "РЕКОМЕНДОВАН" if record.recommended else "НА РАССМОТРЕНИЕ"
        pos_label = "Сильные стороны:"
        neg_label = "Факторы риска:"
        disclaimer = (
            "Заключение сформировано системой AgriScore KZ. "
            "Окончательное решение принимает комиссия."
        )

    story = []

    story.append(Paragraph("Министерство сельского хозяйства Республики Казахстан", label_style))
    story.append(Paragraph("AgriScore KZ — Система скоринга сельхозпроизводителей", label_style))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=12))
    story.append(Paragraph(title_text, title_style))
    story.append(
        Paragraph(
            f"ID заявки: {record.id}  |  Ранг: #{record.rank}  |  Решение: {record.decision}",
            sub_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    score_hex = score_color.hexval().replace("0x", "").replace("0X", "")
    score_table_data = [
        [
            Paragraph(
                f"<font size='32' color='#{score_hex}'><b>{score:.1f}</b></font>",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>{recommended_text}</b><br/>Уровень риска: {record.risk_level.upper()}",
                styles["Normal"],
            ),
        ]
    ]
    score_table = Table(score_table_data, colWidths=[5 * cm, 12 * cm])
    score_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
                ("ROUNDEDCORNERS", [8]),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    bd = record.breakdown
    breakdown_data = [
        ["Компонент", "Вес", "Балл"],
        ["ML-скор (Stacking Ensemble)", "60%", f"{bd.ml_score:.1f}"],
        ["Соответствие правилам (Compliance)", "20%", f"{bd.compliance_score:.1f}"],
        ["Потенциал роста (Growth)", "12%", f"{bd.growth_score:.1f}"],
        ["Безопасность (Fraud Safety)", "8%", f"{bd.fraud_safety_score:.1f}"],
        ["ИТОГОВЫЙ СКОР", "100%", f"{score:.1f}"],
    ]
    bd_table = Table(breakdown_data, colWidths=[10 * cm, 3 * cm, 4 * cm])
    bd_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, -1), (-1, -1), TEAL),
                ("TEXTCOLOR", (0, -1), (-1, -1), white),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [white, LIGHT_GRAY]),
                ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(Paragraph("Детализация скора:", sub_style))
    story.append(bd_table)
    story.append(Spacer(1, 0.5 * cm))

    pos_items = record.explanation.positive[:4]
    neg_items = record.explanation.negative[:3]
    story.append(
        Paragraph(
            pos_label,
            ParagraphStyle(
                "bold_label",
                fontSize=10,
                fontName="Helvetica-Bold",
                textColor=GREEN,
            ),
        )
    )
    for item in pos_items:
        story.append(Paragraph(f"• {item}", body_style))
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            neg_label,
            ParagraphStyle(
                "bold_neg",
                fontSize=10,
                fontName="Helvetica-Bold",
                textColor=RED,
            ),
        )
    )
    for item in neg_items:
        story.append(Paragraph(f"• {item}", body_style))
    story.append(Spacer(1, 0.5 * cm))

    failed_flags = [f for f in (record.compliance_flags or []) if not f.passed]
    if failed_flags:
        story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY, spaceAfter=8))
        story.append(
            Paragraph(
                "Нарушения compliance:",
                ParagraphStyle(
                    "warn",
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    textColor=RED,
                ),
            )
        )
        for flag in failed_flags[:5]:
            story.append(Paragraph(f"[{flag.severity.upper()}] {flag.code}: {flag.message}", body_style))

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY))
    story.append(
        Paragraph(
            disclaimer,
            ParagraphStyle(
                "disclaimer",
                fontSize=8,
                textColor=MID_GRAY,
                fontName="Helvetica-Oblique",
            ),
        )
    )

    doc.build(story)
    return buffer.getvalue()
