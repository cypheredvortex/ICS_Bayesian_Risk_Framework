"""
PDF report generation for the ICS Risk Assessment Framework.

Uses reportlab for professional, production-grade PDF output.
"""

import logging
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# Color scheme matching the frontend
COLOR_PRIMARY = colors.HexColor("#06b6d4")  # cyan-500
COLOR_DARK = colors.HexColor("#0f172a")  # slate-900
COLOR_MUTED = colors.HexColor("#64748b")  # slate-500
COLOR_TEXT = colors.HexColor("#1e293b")  # slate-800
COLOR_BORDER = colors.HexColor("#e2e8f0")  # slate-200
COLOR_RISK_CRITICAL = colors.HexColor("#fb7185")
COLOR_RISK_HIGH = colors.HexColor("#f59e0b")
COLOR_RISK_MODERATE = colors.HexColor("#38bdf8")
COLOR_RISK_LOW = colors.HexColor("#34d399")
COLOR_WHITE = colors.white


def _build_styles() -> dict[str, ParagraphStyle]:
    """Build and return reusable paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        textColor=COLOR_PRIMARY,
        spaceAfter=6 * mm,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=COLOR_PRIMARY,
        spaceBefore=8 * mm,
        spaceAfter=4 * mm,
        borderPadding=(0, 0, 2, 0),
    ))
    styles.add(ParagraphStyle(
        name="SubHeading",
        parent=styles["Heading3"],
        fontSize=11,
        leading=14,
        textColor=COLOR_DARK,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=COLOR_TEXT,
        spaceAfter=2 * mm,
    ))
    styles.add(ParagraphStyle(
        name="Small",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=COLOR_MUTED,
        spaceAfter=1 * mm,
    ))
    styles.add(ParagraphStyle(
        name="TableHeader",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        textColor=COLOR_WHITE,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="TableCell",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=COLOR_TEXT,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="TableCellRight",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        textColor=COLOR_TEXT,
        alignment=TA_RIGHT,
    ))
    return styles


def _build_header_footer(canvas, doc):
    """Draw header and footer on each page."""
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(COLOR_PRIMARY)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, A4[1] - 1.5 * cm, A4[0] - 2 * cm, A4[1] - 1.5 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(COLOR_MUTED)
    canvas.drawString(2 * cm, A4[1] - 1.3 * cm, "ICS Risk Assessment Framework")
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.3 * cm, "Confidential")

    # Footer
    canvas.setStrokeColor(COLOR_BORDER)
    canvas.line(2 * cm, 1.5 * cm, A4[0] - 2 * cm, 1.5 * cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(COLOR_MUTED)
    canvas.drawString(2 * cm, 1.2 * cm, f"Generated: {doc.generated_at}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _risk_color(risk_value: float) -> colors.Color:
    """Return a color based on the risk value threshold."""
    if risk_value >= 1.5:
        return COLOR_RISK_CRITICAL
    if risk_value >= 0.8:
        return COLOR_RISK_HIGH
    if risk_value >= 0.3:
        return COLOR_RISK_MODERATE
    return COLOR_RISK_LOW


def _format_pct(value: float | None) -> str:
    """Format a probability/score value."""
    if value is None:
        return "—"
    return f"{value:.3f}"


def generate_pdf_report(
    result: dict[str, Any],
    output_path: str | Path = "output/assessment.pdf",
) -> Path:
    """
    Generate a professional PDF assessment report using reportlab.

    Args:
        result: Assessment result dictionary from the framework.
        output_path: Path to write the PDF file.

    Returns:
        Path to the generated PDF file.
    """
    from datetime import datetime, timezone
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = _build_styles()
    summary = result.get("summary", {}) or {}
    risk_scores = result.get("risk_scores", []) or []
    attack_paths = result.get("attack_paths", []) or []
    evidence_used = result.get("evidence_used", {}) or {}

    # Build the document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="ICS Bayesian Risk Assessment Report",
        author="ICS Risk Assessment Framework",
        subject="Bayesian Risk Assessment Report",
    )
    doc.generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    doc.page = 0

    story: list[Any] = []

    # ---- Title ----
    story.append(Paragraph("ICS Bayesian Risk Assessment Report", styles["ReportTitle"]))
    story.append(Spacer(1, 3 * mm))

    # ---- Executive Summary ----
    story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    risk_level = str(summary.get("risk_level", "unknown")).title()
    overall_risk = summary.get("overall_risk", "—")
    story.append(Paragraph(
        f"This report presents the results of a quantitative Bayesian risk assessment "
        f"for an Industrial Control System (ICS) environment. The assessment uses a "
        f"Bayesian network model to compute compromise probabilities and risk scores "
        f"based on the system topology, asset attributes, and any observed evidence.",
        styles["Body"],
    ))

    # Key metrics table
    metrics_data = [
        ["Metric", "Value"],
        ["Overall Risk Score", str(_format_pct(overall_risk) if isinstance(overall_risk, (int, float)) else str(overall_risk))],
        ["Risk Level", risk_level],
        ["Assets Assessed", str(summary.get("asset_count", "—"))],
        ["Connections Assessed", str(summary.get("relationship_count", "—"))],
        ["Evidence Used", ", ".join(
            f"{k}: {'Compromised' if v == 1 else 'Safe'}"
            for k, v in evidence_used.items()
        ) or "None"],
    ]
    metrics_table = Table(metrics_data, colWidths=[4.5 * cm, 10 * cm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXT),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metrics_table)

    # ---- Risk Register ----
    story.append(Paragraph("Risk Register", styles["SectionHeading"]))
    story.append(Paragraph(
        "Assets ranked by risk score (posterior probability × consequence impact). "
        "Higher scores indicate higher priority for investigation or treatment.",
        styles["Body"],
    ))

    if risk_scores:
        header = ["Rank", "Asset", "Risk Score", "Probability", "Risk Level"]
        risk_rows = [header]
        for rank, row in enumerate(risk_scores[:20], start=1):  # Top 20
            risk_val = row.get("risk", 0)
            risk_rows.append([
                str(rank),
                str(row.get("asset", "—")),
                _format_pct(risk_val),
                _format_pct(row.get("P(compromised|evidence)", None)),
                str(row.get("risk_level", "—")).title(),
            ])

        risk_table = Table(
            risk_rows,
            colWidths=[1.2 * cm, 5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm],
            repeatRows=1,
        )

        # Build table style with alternating row colors
        table_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("ALIGN", (4, 0), (4, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]

        # Alternating row colors
        for i in range(1, len(risk_rows)):
            bg = colors.HexColor("#f8fafc") if i % 2 == 0 else COLOR_WHITE
            table_style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

        risk_table.setStyle(TableStyle(table_style_cmds))
        story.append(risk_table)

        if len(risk_scores) > 20:
            story.append(Paragraph(
                f"Showing top 20 of {len(risk_scores)} assets. "
                f"Full register available in the CSV export.",
                styles["Small"],
            ))
    else:
        story.append(Paragraph("No risk scores were generated.", styles["Body"]))

    # ---- Attack Path Analysis ----
    if attack_paths:
        story.append(Paragraph("Attack Path Analysis", styles["SectionHeading"]))
        story.append(Paragraph(
            "The following attack paths represent the most likely routes an adversary "
            "could take through the network to reach high-value targets, ranked by "
            "combined propagation-and-target-risk score.",
            styles["Body"],
        ))

        for i, path in enumerate(attack_paths[:5]):
            path_nodes = path.get("path", []) or path.get("nodes", []) or path.get("assets", [])
            path_str = " → ".join(str(n) for n in path_nodes) if path_nodes else "No path available"
            score = path.get("score", "—")

            story.append(Paragraph(
                f"<b>Path {i + 1}</b> &mdash; Score: {_format_pct(score) if isinstance(score, (int, float)) else str(score)}",
                styles["SubHeading"],
            ))
            story.append(Paragraph(path_str, styles["Body"]))

    # ---- Methodology Note ----
    story.append(Paragraph("Methodology", styles["SectionHeading"]))
    story.append(Paragraph(
        "This assessment uses a Bayesian network model constructed from the system topology. "
        "Each asset's base compromise probability is computed from its attributes (CVSS score, "
        "exposure, patch level). The Noisy-OR model generates conditional probability tables, "
        "and Variable Elimination performs inference given observed evidence. Risk scores "
        "combine posterior compromise probabilities with consequence impact scores.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "<b>Important:</b> This report is a decision-support tool, not a guarantee of security. "
        "Risk scores are calculated approximations based on the configured model parameters "
        "and available evidence. They should be used alongside domain expertise and other "
        "security assessments.",
        styles["Small"],
    ))

    # Build the PDF
    doc.build(story, onFirstPage=_build_header_footer, onLaterPages=_build_header_footer)
    logger.info("PDF report generated at %s", output_path)
    return output_path

