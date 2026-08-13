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
        name="SmallCenter",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
        spaceAfter=2 * mm,
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
        # Allow cells to wrap and rows to grow vertically so long asset
        # names or evidence entries never clip or overflow the column.
        wordWrap="CJK",
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
    """Return a color based on the *configured* risk thresholds.

    Uses ``backend.risk.risk_level_for`` so the PDF always agrees with the
    risk register, the CLI and the frontend -- there is exactly one
    threshold definition (``risk_thresholds`` in settings).
    """
    from backend.risk import risk_level_for

    level = risk_level_for(float(risk_value)).lower()
    return {
        "critical": COLOR_RISK_CRITICAL,
        "high": COLOR_RISK_HIGH,
        "moderate": COLOR_RISK_MODERATE,
        "low": COLOR_RISK_LOW,
    }[level]


def _format_pct(value: float | None) -> str:
    """Format a probability/score value."""
    if value is None:
        return "—"
    return f"{value:.3f}"


# Risk-level labels and their colours, matching the frontend palette so the
# printed report and the dashboard tell the same visual story.
_RISK_LEVEL_COLORS = {
    "Critical": COLOR_RISK_CRITICAL,
    "High": COLOR_RISK_HIGH,
    "Moderate": COLOR_RISK_MODERATE,
    "Low": COLOR_RISK_LOW,
}


def _colored_level(level: str) -> str:
    """Wrap a risk-level label in a coloured font tag (reportlab markup).

    Unknown labels (e.g. "—" when a level is missing) pass through unchanged.
    """
    color = _RISK_LEVEL_COLORS.get(str(level).title())
    if color is None:
        return str(level)
    return f'<font color="{color.hexval()}">{level}</font>'


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
    story.append(Paragraph(f"Generated: {doc.generated_at}", styles["SmallCenter"]))
    story.append(Spacer(1, 3 * mm))

    # ---- Executive Summary ----
    story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    risk_level = str(summary.get("risk_level", "unknown")).title()
    overall_risk = summary.get("overall_risk", "—")
    story.append(Paragraph(
        "This report presents the results of a quantitative Bayesian risk assessment "
        "for an Industrial Control System (ICS) environment. The assessment uses a "
        "Bayesian network model to compute compromise probabilities and risk scores "
        "based on the system topology, asset attributes, and any observed evidence.",
        styles["Body"],
    ))

    # Key metrics table (the evidence itself gets its own section below so a
    # large evidence set can wrap and span pages instead of overflowing one row)
    aggregate = summary.get("aggregate_risk", {}) or {}
    level_counts = aggregate.get("level_counts") or {}
    if level_counts:
        # Analyst-facing distribution, e.g. "Critical 2, High 5, Moderate 8, Low 12"
        distribution = ", ".join(
            f"{level.title()} {int(level_counts.get(level, 0) or 0)}"
            for level in ("critical", "high", "moderate", "low")
        )
    else:
        distribution = "—"

    metrics_data = [
        ["Metric", "Value"],
        ["Overall Risk Score", str(_format_pct(overall_risk) if isinstance(overall_risk, (int, float)) else str(overall_risk))],
        ["Risk Level", risk_level],
        ["Assets Assessed", str(summary.get("asset_count", "—"))],
        ["Connections Assessed", str(summary.get("relationship_count", "—"))],
        ["Evidence Items", str(len(evidence_used)) if evidence_used else "None"],
        ["Assets by Risk Level", distribution],
        ["Attack Paths Identified", str(len(attack_paths))],
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

    # ---- Highest-Risk Assets (executive view) ----
    top_assets = risk_scores[:5]
    if top_assets:
        story.append(Paragraph("Highest-Risk Assets", styles["SubHeading"]))
        story.append(Paragraph(
            "The five assets with the highest risk index, in register order. "
            "The complete register appears later in this report.",
            styles["Small"],
        ))
        top_header = ["Rank", "Asset", "Risk Index", "Risk Level"]
        top_rows: list[list[Any]] = [
            [Paragraph(cell, styles["TableHeader"]) for cell in top_header]
        ]
        for rank, row in enumerate(top_assets, start=1):
            top_rows.append([
                str(rank),
                Paragraph(str(row.get("asset", "—")), styles["TableCell"]),
                _format_pct(row.get("risk", 0)),
                Paragraph(
                    _colored_level(str(row.get("risk_level", "—")).title()),
                    styles["TableCell"],
                ),
            ])

        top_table = Table(
            top_rows,
            colWidths=[1.2 * cm, 6.8 * cm, 3.0 * cm, 3.5 * cm],
            repeatRows=1,
        )
        top_style = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
        for i in range(1, len(top_rows)):
            bg = colors.HexColor("#f8fafc") if i % 2 == 0 else COLOR_WHITE
            top_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        top_table.setStyle(TableStyle(top_style))
        story.append(top_table)
        story.append(Spacer(1, 2 * mm))

    # ---- Selected Evidence ----
    story.append(Paragraph("Selected Evidence", styles["SectionHeading"]))
    if evidence_used:
        story.append(Paragraph(
            "Assets pinned to a known state before inference. Pinned assets keep "
            "their assigned value exactly; every other probability is recomputed "
            "from them through the Bayesian network.",
            styles["Body"],
        ))
        evidence_rows: list[list[Any]] = [
            [
                Paragraph("Asset", styles["TableHeader"]),
                Paragraph("State", styles["TableHeader"]),
            ]
        ]
        for asset, state in evidence_used.items():
            evidence_rows.append([
                Paragraph(str(asset), styles["TableCell"]),
                Paragraph("Compromised" if state == 1 else "Safe", styles["TableCell"]),
            ])

        evidence_table = Table(
            evidence_rows,
            colWidths=[11 * cm, 3.5 * cm],
            repeatRows=1,  # repeat the header when the table splits across pages
        )
        evidence_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        # Alternating row shading for readability on long lists
        for i in range(1, len(evidence_rows)):
            bg = colors.HexColor("#f8fafc") if i % 2 == 0 else COLOR_WHITE
            evidence_table.setStyle(TableStyle([
                ("BACKGROUND", (0, i), (-1, i), bg)
            ]))
        story.append(evidence_table)
    else:
        story.append(Paragraph(
            "No evidence was supplied for this run; the probabilities below are "
            "based on the topology and the configured model assumptions only.",
            styles["Body"],
        ))
    story.append(Spacer(1, 2 * mm))

    # ---- Model Parameters (traceability) ----
    settings_used = result.get("settings_used", {}) or {}
    if settings_used:
        story.append(Paragraph("Model Parameters Used", styles["SectionHeading"]))
        story.append(Paragraph(
            "The following settings produced the numbers in this report. "
            "They are recorded so the assessment is traceable and reproducible; "
            "changing any of them changes the results.",
            styles["Body"],
        ))

        param_rows: list[list[str]] = [["Parameter", "Value"]]
        mapping = settings_used.get("cvss_mapping", "logistic")
        params = settings_used.get("cvss_logistic_params", {})
        param_rows.append(["CVSS → probability mapping", str(mapping)])
        param_rows.append(["Logistic k (steepness)", str(params.get("k", "—"))])
        param_rows.append(["Logistic x0 (midpoint)", str(params.get("x0", "—"))])
        param_rows.append(["Exposure multiplier (exposed)", str(settings_used.get("exposure_multipliers", {}).get("true", "—"))])
        param_rows.append(["Exposure multiplier (not exposed)", str(settings_used.get("exposure_multipliers", {}).get("false", "—"))])
        param_rows.append(["Patch multiplier (patched)", str(settings_used.get("patch_multipliers", {}).get("true", "—"))])
        param_rows.append(["Patch multiplier (unpatched)", str(settings_used.get("patch_multipliers", {}).get("false", "—"))])
        param_rows.append(["Impact weight", str(settings_used.get("impact_weight", "—"))])
        param_rows.append(["Risk thresholds", str(settings_used.get("risk_thresholds", "—"))])

        prop_weights = settings_used.get("propagation_weights", {})
        for rel_type in sorted(prop_weights):
            param_rows.append([f"Propagation weight '{rel_type}'", str(prop_weights[rel_type])])

        params_table = Table(param_rows, colWidths=[6 * cm, 8.5 * cm])
        params_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXT),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(params_table)

        non_default = result.get("summary", {}).get("non_default_settings") or []
        if non_default:
            story.append(Paragraph(
                "<b>Note:</b> one or more settings differ from the framework defaults. "
                "The values above are the ones actually used; the defaults are "
                "documented in docs/parameter-provenance.md.",
                styles["Small"],
            ))
        story.append(Spacer(1, 2 * mm))

    # ---- Risk Register ----
    story.append(Paragraph("Risk Register", styles["SectionHeading"]))
    story.append(Paragraph(
        "Assets ranked by risk index (posterior probability × normalised "
        "consequence impact). Higher scores indicate higher priority for "
        "investigation or treatment.",
        styles["Body"],
    ))

    if risk_scores:
        # The complete register: every asset the framework ranked, in the same
        # order and with the same values as the dashboard and CSV. The table
        # splits across pages automatically and repeats its header row.
        header = ["Rank", "Asset", "Risk Index", "P(Compromised)", "Impact", "Risk Level"]
        risk_rows: list[list[Any]] = [
            [Paragraph(cell, styles["TableHeader"]) for cell in header]
        ]
        for rank, row in enumerate(risk_scores, start=1):
            risk_val = row.get("risk", 0)
            risk_rows.append([
                str(rank),
                Paragraph(str(row.get("asset", "—")), styles["TableCell"]),
                _format_pct(risk_val),
                _format_pct(row.get("P(compromised|evidence)", None)),
                _format_pct(row.get("impact", None)),
                Paragraph(
                    _colored_level(str(row.get("risk_level", "—")).title()),
                    styles["TableCell"],
                ),
            ])

        risk_table = Table(
            risk_rows,
            colWidths=[1.2 * cm, 4.6 * cm, 2.3 * cm, 2.3 * cm, 2.0 * cm, 2.3 * cm],
            repeatRows=1,
        )

        # Build table style with alternating row colors
        table_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (4, -1), "RIGHT"),
            ("ALIGN", (5, 0), (5, -1), "CENTER"),
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

        story.append(Paragraph(
            f"{len(risk_scores)} asset(s) ranked by risk index, highest first. "
            f"The same register is available as CSV for further analysis.",
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
        if len(attack_paths) > 5:
            story.append(Paragraph(
                f"Showing the 5 highest-scoring of {len(attack_paths)} calculated paths.",
                styles["Small"],
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

            # Analyst context for each path: where it leads, how viable it is
            # and how long it is.  Only genuinely present values are shown.
            details: list[str] = []
            target = path.get("target")
            if target:
                target_risk = path.get("target_risk")
                if isinstance(target_risk, (int, float)):
                    details.append(f"Target: {target} (risk index {_format_pct(target_risk)})")
                else:
                    details.append(f"Target: {target}")
            path_prob = path.get("path_probability")
            if isinstance(path_prob, (int, float)):
                details.append(f"Weakest-link probability: {_format_pct(path_prob)}")
            hops = path.get("hops")
            if hops is None and path_nodes:
                hops = len(path_nodes) - 1
            if hops is not None:
                details.append(f"Hops: {int(hops)}")
            if details:
                story.append(Paragraph(" · ".join(details), styles["Small"]))

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

