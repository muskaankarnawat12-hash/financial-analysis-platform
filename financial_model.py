"""Core forecasting and valuation calculations."""

from typing import Dict, List

import pandas as pd


def forecast_financials(
    starting_revenue: float,
    revenue_growth: float,
    ebitda_margin: float,
    depreciation_percent: float,
    tax_rate: float,
    capex_percent: float,
    nwc_percent: float,
    forecast_years: int = 5,
    first_forecast_year: int = 2027,
) -> pd.DataFrame:
    """
    Create a five-year forecast from editable financial assumptions.

    Percentage assumptions must be entered as decimals.
    For example, enter 10% as 0.10.
    """

    if starting_revenue < 0:
        raise ValueError("Starting revenue cannot be negative.")

    if forecast_years < 1:
        raise ValueError("Forecast years must be at least 1.")

    results: List[Dict[str, float]] = []
    previous_revenue = starting_revenue
    previous_nwc = starting_revenue * nwc_percent

    for year_number in range(forecast_years):
        year = first_forecast_year + year_number

        revenue = previous_revenue * (1 + revenue_growth)
        gross_profit = revenue * 0.40
        ebitda = revenue * ebitda_margin
        depreciation = revenue * depreciation_percent
        ebit = ebitda - depreciation

        taxes = max(ebit, 0) * tax_rate
        nopat = ebit - taxes

        capex = revenue * capex_percent
        net_working_capital = revenue * nwc_percent
        change_in_nwc = net_working_capital - previous_nwc

        free_cash_flow = (
            nopat
            + depreciation
            - capex
            - change_in_nwc
        )

        results.append(
            {
                "Year": year,
                "Revenue": revenue,
                "Gross Profit": gross_profit,
                "EBITDA": ebitda,
                "EBITDA Margin": ebitda / revenue if revenue else 0,
                "Depreciation": depreciation,
                "EBIT": ebit,
                "Taxes": taxes,
                "NOPAT": nopat,
                "Capital Expenditure": capex,
                "Net Working Capital": net_working_capital,
                "Change in NWC": change_in_nwc,
                "Free Cash Flow": free_cash_flow,
            }
        )

        previous_revenue = revenue
        previous_nwc = net_working_capital

    return pd.DataFrame(results)


def calculate_dcf(
    forecast: pd.DataFrame,
    wacc: float,
    terminal_growth: float,
    cash: float,
    debt: float,
    diluted_shares: float,
) -> Dict[str, float]:
    """Calculate enterprise value, equity value and value per share."""

    if forecast.empty:
        raise ValueError("The forecast cannot be empty.")

    if wacc <= terminal_growth:
        raise ValueError(
            "WACC must be greater than the terminal growth rate."
        )

    if diluted_shares <= 0:
        raise ValueError("Diluted shares must be greater than zero.")

    cash_flows = forecast["Free Cash Flow"].tolist()

    present_value_of_forecast = sum(
        cash_flow / ((1 + wacc) ** year)
        for year, cash_flow in enumerate(cash_flows, start=1)
    )

    final_cash_flow = cash_flows[-1]

    terminal_value = (
        final_cash_flow
        * (1 + terminal_growth)
        / (wacc - terminal_growth)
    )

    present_value_of_terminal = (
        terminal_value
        / ((1 + wacc) ** len(cash_flows))
    )

    enterprise_value = (
        present_value_of_forecast
        + present_value_of_terminal
    )

    equity_value = enterprise_value + cash - debt
    implied_value_per_share = equity_value / diluted_shares

    return {
        "Present Value of Forecast": present_value_of_forecast,
        "Terminal Value": terminal_value,
        "Present Value of Terminal Value": present_value_of_terminal,
        "Enterprise Value": enterprise_value,
        "Cash": cash,
        "Debt": debt,
        "Equity Value": equity_value,
        "Diluted Shares": diluted_shares,
        "Implied Value Per Share": implied_value_per_share,
    }


def create_sensitivity_table(
    forecast: pd.DataFrame,
    cash: float,
    debt: float,
    diluted_shares: float,
) -> pd.DataFrame:
    """Create a value-per-share sensitivity table."""

    wacc_values = [0.08, 0.09, 0.10, 0.11, 0.12]
    growth_values = [0.01, 0.02, 0.03, 0.04, 0.05]

    sensitivity = pd.DataFrame(
        index=[f"{wacc:.0%}" for wacc in wacc_values],
        columns=[f"{growth:.0%}" for growth in growth_values],
        dtype=float,
    )

    for wacc in wacc_values:
        for growth in growth_values:
            valuation = calculate_dcf(
                forecast=forecast,
                wacc=wacc,
                terminal_growth=growth,
                cash=cash,
                debt=debt,
                diluted_shares=diluted_shares,
            )

            sensitivity.loc[
                f"{wacc:.0%}",
                f"{growth:.0%}",
            ] = valuation["Implied Value Per Share"]

    sensitivity.index.name = "WACC / Terminal Growth"

    return sensitivity


def identify_financial_red_flags(
    forecast: pd.DataFrame,
    debt: float,
    cash: float,
) -> List[str]:
    """Identify basic financial and forecasting risks."""

    flags: List[str] = []

    if forecast.empty:
        return ["No forecast data is available."]

    latest = forecast.iloc[-1]

    if latest["Free Cash Flow"] < 0:
        flags.append("Free cash flow remains negative in the final forecast year.")

    if latest["EBITDA"] < 0:
        flags.append("EBITDA remains negative in the final forecast year.")

    if debt > cash * 3:
        flags.append("Debt is more than three times the available cash balance.")

    if latest["Capital Expenditure"] > latest["EBITDA"]:
        flags.append("Capital expenditure exceeds EBITDA.")

    if latest["EBITDA Margin"] < 0.10:
        flags.append("The forecast EBITDA margin remains below 10%.")

    if not flags:
        flags.append(
            "No major rule-based red flags were identified from the forecast."
        )

    return flags
def build_historical_analysis(sec_financial_data):
    """Convert SEC financial facts into a historical analysis table."""

    financial_data = sec_financial_data.get("Financial Data", {})
    rows = []

    for metric, records in financial_data.items():
        for record in records:
            value = record.get("Value")
            period = record.get("Period")

            if value is not None and period:
                rows.append(
                    {
                        "Period": period,
                        "Metric": metric,
                        "Value": value / 1_000_000,
                    }
                )

    if not rows:
        return pd.DataFrame()

    historical = pd.DataFrame(rows)

    historical = historical.pivot_table(
        index="Period",
        columns="Metric",
        values="Value",
        aggfunc="first",
    ).sort_index()
    
     # Keep fiscal-year periods with reported total assets.
    if "Total Assets" in historical.columns:
        historical = historical[
            historical["Total Assets"].notna()
        ]

    if "Revenue" in historical.columns:
        historical["Revenue Growth"] = (
            historical["Revenue"].pct_change()
        )

    if {
        "Gross Profit",
        "Revenue",
    }.issubset(historical.columns):
        historical["Gross Margin"] = (
            historical["Gross Profit"]
            / historical["Revenue"]
        )

    if {
        "Operating Income",
        "Revenue",
    }.issubset(historical.columns):
        historical["Operating Margin"] = (
            historical["Operating Income"]
            / historical["Revenue"]
        )
    if {
        "Operating Income",
        "Depreciation and Amortisation",
    }.issubset(historical.columns):
        historical["EBITDA"] = (
            historical["Operating Income"]
            + historical["Depreciation and Amortisation"]
        )

    if {
        "EBITDA",
        "Revenue",
    }.issubset(historical.columns):
        historical["EBITDA Margin"] = (
            historical["EBITDA"]
            / historical["Revenue"]
        )    

    if {
        "Net Income",
        "Revenue",
    }.issubset(historical.columns):
        historical["Net Margin"] = (
            historical["Net Income"]
            / historical["Revenue"]
        )

    if {
        "Operating Cash Flow",
        "Capital Expenditure",
    }.issubset(historical.columns):
        historical["Free Cash Flow"] = (
            historical["Operating Cash Flow"]
            - historical["Capital Expenditure"]
        )

    if {
        "Free Cash Flow",
        "Revenue",
    }.issubset(historical.columns):
        historical["Free Cash Flow Margin"] = (
            historical["Free Cash Flow"]
            / historical["Revenue"]
        )

    if {
        "Long-Term Debt",
        "Cash",
    }.issubset(historical.columns):
        historical["Net Debt"] = (
            historical["Long-Term Debt"]
            - historical["Cash"]
        )

    return historical.reset_index()