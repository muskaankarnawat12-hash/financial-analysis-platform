"""Excel export functions for the financial model."""

from io import BytesIO

import pandas as pd


def create_excel_model(
    company_name: str,
    ticker: str,
    scenario: str,
    currency: str,
    units: str,
    assumptions: dict,
    forecast: pd.DataFrame,
    valuation: dict,
    sensitivity: pd.DataFrame,
    historical: pd.DataFrame | None = None,
    comparables: pd.DataFrame | None = None,
    audit_trail: pd.DataFrame | None = None,
    source_summary: dict | None = None,
) -> bytes:
    """Create a formatted Excel workbook and return its bytes."""

    output = BytesIO()
    assumptions_table = pd.DataFrame(
        {"Assumption": assumptions.keys(), "Value": assumptions.values()}
    )
    valuation_table = pd.DataFrame(
        {"Valuation item": valuation.keys(), "Value": valuation.values()}
    )
    historical = historical if historical is not None else pd.DataFrame()
    comparables = comparables if comparables is not None else pd.DataFrame()
    audit_trail = audit_trail if audit_trail is not None else pd.DataFrame()
    source_table = pd.DataFrame(
        {
            "Source detail": (source_summary or {}).keys(),
            "Value": (source_summary or {}).values(),
        }
    )

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        title = workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "font_color": "white",
                "bg_color": "#1F4E78",
            }
        )
        header = workbook.add_format(
            {
                "bold": True,
                "font_color": "white",
                "bg_color": "#4472C4",
                "border": 1,
            }
        )
        number = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        percent = workbook.add_format({"num_format": "0.0%", "border": 1})

        cover = workbook.add_worksheet("Cover")
        cover.set_column("A:A", 24)
        cover.set_column("B:B", 42)
        cover.merge_range("A2:B2", "AI Financial Analysis Platform", title)
        cover.write("A4", "Company", header)
        cover.write("B4", company_name)
        cover.write("A5", "Ticker", header)
        cover.write("B5", ticker)
        cover.write("A6", "Scenario", header)
        cover.write("B6", scenario)
        cover.write("A7", "Currency", header)
        cover.write("B7", currency)
        cover.write("A8", "Units", header)
        cover.write("B8", units)
        cover.write("A10", "Important", header)
        cover.write("B10", "Review imported data against the original filing.")

        assumptions_table.to_excel(writer, sheet_name="Assumptions", index=False)
        forecast.to_excel(writer, sheet_name="Forecast", index=False)
        valuation_table.to_excel(writer, sheet_name="Valuation", index=False)
        sensitivity.to_excel(writer, sheet_name="Sensitivity")

        if not historical.empty:
            historical.to_excel(writer, sheet_name="Historical", index=False)
        if not comparables.empty:
            comparables.to_excel(writer, sheet_name="Comparables", index=False)
        if not audit_trail.empty:
            audit_trail.to_excel(writer, sheet_name="Input Audit", index=False)
        if not source_table.empty:
            source_table.to_excel(writer, sheet_name="Sources", index=False)

        for sheet_name in ["Assumptions", "Forecast", "Valuation", "Sensitivity"]:
            sheet = writer.sheets[sheet_name]
            sheet.freeze_panes(1, 0)
            sheet.set_column("A:A", 32)
            sheet.set_column("B:Z", 20, number)

        assumptions_sheet = writer.sheets["Assumptions"]
        assumptions_sheet.write_row(0, 0, assumptions_table.columns, header)

        forecast_sheet = writer.sheets["Forecast"]
        forecast_sheet.write_row(0, 0, forecast.columns, header)
        if "EBITDA Margin" in forecast.columns:
            margin_column = forecast.columns.get_loc("EBITDA Margin")
            forecast_sheet.set_column(margin_column, margin_column, 18, percent)

        valuation_sheet = writer.sheets["Valuation"]
        valuation_sheet.write_row(0, 0, valuation_table.columns, header)

        sensitivity_sheet = writer.sheets["Sensitivity"]
        sensitivity_sheet.write_row(
            0,
            0,
            ["WACC / Terminal Growth", *list(sensitivity.columns)],
            header,
        )

        optional_sheets = {
            "Historical": historical,
            "Comparables": comparables,
            "Input Audit": audit_trail,
            "Sources": source_table,
        }
        for sheet_name, table in optional_sheets.items():
            if table.empty:
                continue
            sheet = writer.sheets[sheet_name]
            sheet.freeze_panes(1, 0)
            sheet.write_row(0, 0, table.columns, header)
            for column_index, column_name in enumerate(table.columns):
                values = table[column_name].astype(str)
                width = min(
                    45,
                    max(len(str(column_name)), values.map(len).max()) + 2,
                )
                sheet.set_column(column_index, column_index, max(12, width))

    output.seek(0)
    return output.getvalue()
def create_pdf_report(
    company_name: str,
    ticker: str,
    scenario: str,
    currency: str,
    units: str,
    forecast: pd.DataFrame,
    valuation: dict,
    red_flags: list[str],
    commentary: str = "",
    assumptions: dict | None = None,
    historical: pd.DataFrame | None = None,
    comparables: pd.DataFrame | None = None,
    sensitivity: pd.DataFrame | None = None,
    audit_trail: pd.DataFrame | None = None,
    source_summary: dict | None = None,
) -> bytes:
    """Create a professional PDF investment report."""

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    output = BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"{company_name} Financial Analysis",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1F4E78"),
        alignment=TA_CENTER,
        spaceAfter=10,
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1F4E78"),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=5,
    )

    story = []

    story.append(
        Paragraph(
            f"{company_name} Financial Analysis",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"Ticker: {ticker} | Scenario: {scenario} | "
            f"Currency: {currency} {units}",
            body_style,
        )
    )

    story.append(Spacer(1, 8))

    latest = forecast.iloc[-1]

    summary_data = [
        ["Metric", "Value"],
        [
            "Final-year revenue",
            f"{latest['Revenue']:,.2f}",
        ],
        [
            "Final-year EBITDA",
            f"{latest['EBITDA']:,.2f}",
        ],
        [
            "EBITDA margin",
            f"{latest['EBITDA Margin']:.1%}",
        ],
        [
            "Final-year free cash flow",
            f"{latest['Free Cash Flow']:,.2f}",
        ],
        [
            "Enterprise value",
            f"{valuation['Enterprise Value']:,.2f}",
        ],
        [
            "Equity value",
            f"{valuation['Equity Value']:,.2f}",
        ],
        [
            "Implied value per share",
            f"{valuation['Implied Value Per Share']:,.2f}",
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[85 * mm, 70 * mm],
        repeatRows=1,
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1F4E78"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#B8C2CC"),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor("#F4F7FA"),
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(Paragraph("Executive summary", heading_style))
    story.append(summary_table)

    if source_summary:
        story.append(Paragraph("Data sources and verification", heading_style))
        source_data = [["Source detail", "Value"]]
        source_data.extend(
            [Paragraph(str(key), body_style), Paragraph(str(value or "N/A"), body_style)]
            for key, value in source_summary.items()
        )
        source_table = Table(source_data, colWidths=[48 * mm, 107 * mm], repeatRows=1)
        source_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(source_table)

    if assumptions:
        story.append(Paragraph("Model assumptions", heading_style))
        assumption_data = [["Assumption", "Value"]] + [
            [str(key), "N/A" if value is None else str(value)]
            for key, value in assumptions.items()
        ]
        assumption_table = Table(
            assumption_data, colWidths=[85 * mm, 70 * mm], repeatRows=1
        )
        assumption_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(assumption_table)

    story.append(Paragraph("Financial forecast", heading_style))

    forecast_data = [
        [
            "Year",
            "Revenue",
            "EBITDA",
            "EBIT",
            "Free Cash Flow",
        ]
    ]

    for _, row in forecast.iterrows():
        forecast_data.append(
            [
                str(int(row["Year"])),
                f"{row['Revenue']:,.1f}",
                f"{row['EBITDA']:,.1f}",
                f"{row['EBIT']:,.1f}",
                f"{row['Free Cash Flow']:,.1f}",
            ]
        )

    forecast_table = Table(
        forecast_data,
        colWidths=[
            22 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
            34 * mm,
        ],
        repeatRows=1,
    )

    forecast_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#4472C4"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#B8C2CC"),
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.append(forecast_table)

    historical = historical if historical is not None else pd.DataFrame()
    if not historical.empty:
        story.append(Paragraph("Historical actuals", heading_style))
        history_columns = list(historical.columns[:6])
        history_data = [history_columns]
        for _, row in historical.tail(8).iterrows():
            history_data.append([
                "N/A" if pd.isna(row[column]) else str(row[column])
                for column in history_columns
            ])
        history_table = Table(
            history_data,
            colWidths=[155 * mm / len(history_columns)] * len(history_columns),
            repeatRows=1,
        )
        history_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(history_table)

    comparables = comparables if comparables is not None else pd.DataFrame()
    if not comparables.empty:
        story.append(Paragraph("Comparable companies", heading_style))
        comparable_columns = [
            column for column in (
                "Ticker", "Role", "P/E", "EV/Revenue", "EV/EBITDA",
                "Revenue growth", "EBITDA margin"
            ) if column in comparables.columns
        ]
        comparable_data = [comparable_columns]
        for _, row in comparables.head(12).iterrows():
            comparable_data.append([
                "N/A" if pd.isna(row[column]) else str(row[column])
                for column in comparable_columns
            ])
        comparable_table = Table(
            comparable_data,
            colWidths=[155 * mm / len(comparable_columns)] * len(comparable_columns),
            repeatRows=1,
        )
        comparable_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(comparable_table)

    sensitivity = sensitivity if sensitivity is not None else pd.DataFrame()
    if not sensitivity.empty:
        story.append(Paragraph("DCF sensitivity", heading_style))
        sensitivity_display = sensitivity.reset_index()
        sensitivity_columns = list(sensitivity_display.columns)
        sensitivity_data = [sensitivity_columns]
        for _, row in sensitivity_display.iterrows():
            sensitivity_data.append([
                "N/A" if pd.isna(row[column]) else str(row[column])
                for column in sensitivity_columns
            ])
        sensitivity_table = Table(
            sensitivity_data,
            colWidths=[155 * mm / len(sensitivity_columns)] * len(sensitivity_columns),
            repeatRows=1,
        )
        sensitivity_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(sensitivity_table)

    audit_trail = audit_trail if audit_trail is not None else pd.DataFrame()
    if not audit_trail.empty:
        story.append(PageBreak())
        story.append(Paragraph("Model input audit trail", heading_style))
        audit_columns = [
            column for column in (
                "Model input", "Value used", "Units", "Source",
                "Reporting date", "Status"
            ) if column in audit_trail.columns
        ]
        audit_data = [audit_columns]
        for _, row in audit_trail.iterrows():
            audit_data.append([
                Paragraph(str(row[column] if pd.notna(row[column]) else "N/A"), body_style)
                for column in audit_columns
            ])
        audit_table = Table(
            audit_data,
            colWidths=[155 * mm / len(audit_columns)] * len(audit_columns),
            repeatRows=1,
        )
        audit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C2CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(audit_table)

    story.append(Paragraph("Financial red flags", heading_style))

    for flag in red_flags:
        story.append(
            Paragraph(
                f"• {flag}",
                body_style,
            )
        )

    if commentary:
        story.append(PageBreak())
        story.append(
            Paragraph(
                "Automated investment commentary",
                heading_style,
            )
        )

        clean_commentary = (
            commentary
            .replace("##", "")
            .replace("**", "")
        )

        for paragraph in clean_commentary.split("\n"):
            if paragraph.strip():
                story.append(
                    Paragraph(
                        paragraph.strip(),
                        body_style,
                    )
                )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "Disclaimer: This report is for analytical and educational "
            "purposes and does not constitute investment advice. "
            "Public financial data should be verified against original "
            "regulatory filings.",
            body_style,
        )
    )

    document.build(story)

    output.seek(0)
    return output.getvalue()
