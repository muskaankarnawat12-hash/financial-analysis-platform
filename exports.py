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
) -> bytes:
    """Create a formatted Excel workbook and return its bytes."""

    output = BytesIO()
    assumptions_table = pd.DataFrame(
        {"Assumption": assumptions.keys(), "Value": assumptions.values()}
    )
    valuation_table = pd.DataFrame(
        {"Valuation item": valuation.keys(), "Value": valuation.values()}
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