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
