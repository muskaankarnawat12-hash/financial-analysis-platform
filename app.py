"""Interactive financial modelling dashboard."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai_analysis import generate_rule_based_analysis
from data_sources import get_comparable_companies, get_company_data
from sec_data import (
    get_sec_cik_from_ticker,
    get_sec_company_filings,
    get_sec_financial_facts,
)
from exports import create_excel_model, create_pdf_report
from india_data import get_bse_company_filings, get_nse_company_filings
from uk_data import (
    get_uk_company_filings,
    get_uk_financial_facts,
)
from global_filings import build_global_filings_table, filter_global_filings
from financial_model import (
    build_historical_analysis,
    calculate_dcf,
    create_sensitivity_table,
    forecast_financials,
    identify_financial_red_flags,
)


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="AI Financial Analysis Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Session-state defaults
# ---------------------------------------------------------

if "company_name" not in st.session_state:
    st.session_state.company_name = "Apple Inc."

if "loaded_ticker" not in st.session_state:
    st.session_state.loaded_ticker = "AAPL"

if "starting_revenue" not in st.session_state:
    st.session_state.starting_revenue = 1000.0

if "revenue_growth_input" not in st.session_state:
    st.session_state.revenue_growth_input = 10.0

if "ebitda_margin_input" not in st.session_state:
    st.session_state.ebitda_margin_input = 20.0

if "cash" not in st.session_state:
    st.session_state.cash = 100.0

if "debt" not in st.session_state:
    st.session_state.debt = 50.0

if "diluted_shares" not in st.session_state:
    st.session_state.diluted_shares = 100.0

if "currency" not in st.session_state:
    st.session_state.currency = "USD"

if "current_price" not in st.session_state:
    st.session_state.current_price = None

if "historical_revenue" not in st.session_state:
    st.session_state.historical_revenue = pd.DataFrame()

if "sec_historical_analysis" not in st.session_state:
    st.session_state.sec_historical_analysis = pd.DataFrame()

if "comparable_companies" not in st.session_state:
    st.session_state.comparable_companies = pd.DataFrame()

if "company_snapshot" not in st.session_state:
    st.session_state.company_snapshot = {}

if "uk_pdf_actuals_preview" not in st.session_state:
    st.session_state.uk_pdf_actuals_preview = {}

if "input_audit_metadata" not in st.session_state:
    st.session_state.input_audit_metadata = {}

if "loaded_input_baseline" not in st.session_state:
    st.session_state.loaded_input_baseline = {}


# ---------------------------------------------------------
# Formatting functions
# ---------------------------------------------------------

def format_currency(value: float, currency: str) -> str:
    """Format a number using the selected currency."""

    symbols = {
        "USD": "$",
        "INR": "₹",
        "GBP": "£",
        "EUR": "€",
        "AED": "AED ",
    }

    symbol = symbols.get(currency, f"{currency} ")
    return f"{symbol}{value:,.2f}"


def apply_scenario(
    scenario: str,
    revenue_growth: float,
    ebitda_margin: float,
) -> tuple[float, float]:
    """Adjust assumptions according to the selected scenario."""

    if scenario == "Upside":
        return revenue_growth + 0.03, ebitda_margin + 0.03

    if scenario == "Downside":
        return max(revenue_growth - 0.03, -0.50), ebitda_margin - 0.03

    return revenue_growth, ebitda_margin


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.title("AI Financial Analysis Platform")

st.caption(
    "Create a driver-based forecast, calculate valuation and "
    "identify financial risks."
)


# ---------------------------------------------------------
# Company details
# ---------------------------------------------------------

with st.sidebar:
    st.header("Company setup")

    ticker = st.text_input(
        "Company ticker",
        value=st.session_state.loaded_ticker,
        help="Examples: AAPL, MSFT, RELIANCE.NS or TCS.NS",
    ).strip().upper()

    load_company = st.button(
        "Load company financials",
        type="primary",
        width="stretch",
    )

    if load_company:
        with st.spinner(
            f"Retrieving financial data for {ticker}..."
        ):
            try:
                company_data = get_company_data(ticker)

                st.session_state.company_name = (
                    company_data["company_name"]
                )
                st.session_state.loaded_ticker = (
                    company_data["ticker"]
                )
                st.session_state.starting_revenue = float(
                    company_data["revenue"]
                )
                st.session_state.revenue_growth_input = float(
                    company_data["revenue_growth"] * 100
                )
                st.session_state.ebitda_margin_input = float(
                    company_data["ebitda_margin"] * 100
                )
                st.session_state.cash = float(
                    company_data["cash"]
                )
                st.session_state.debt = float(
                    company_data["debt"]
                )
                st.session_state.diluted_shares = float(
                    company_data["diluted_shares"]
                )
                st.session_state.currency = (
                    company_data["currency"]
                )
                st.session_state.current_price = (
                    company_data["current_price"]
                )
                st.session_state.historical_revenue = (
                    company_data["historical_revenue"]
                )
                st.session_state.company_snapshot = {
                    "ticker": company_data["ticker"],
                    "company_name": company_data["company_name"],
                    "currency": company_data["currency"],
                    "current_price": company_data["current_price"],
                    "market_cap": company_data["market_cap"],
                    "enterprise_value": company_data[
                        "enterprise_value"
                    ],
                    "trailing_pe": company_data["trailing_pe"],
                    "fifty_two_week_high": company_data[
                        "fifty_two_week_high"
                    ],
                    "fifty_two_week_low": company_data[
                        "fifty_two_week_low"
                    ],
                    "dividend_yield": company_data["dividend_yield"],
                    "beta": company_data["beta"],
                    "sector": company_data["sector"],
                    "industry": company_data["industry"],
                    "country": company_data["country"],
                    "website": company_data["website"],
                    "employees": company_data["employees"],
                    "business_summary": company_data[
                        "business_summary"
                    ],
                    "quote_currency": company_data.get("quote_currency"),
                    "market_data_date": company_data.get(
                        "market_data_date"
                    ),
                }
                st.session_state.input_audit_metadata = company_data.get(
                    "audit_metadata", {}
                )
                st.session_state.loaded_input_baseline = {
                    "Latest reported revenue": float(
                        company_data["revenue"]
                    ),
                    "Annual revenue growth": float(
                        company_data["revenue_growth"] * 100
                    ),
                    "EBITDA margin": float(
                        company_data["ebitda_margin"] * 100
                    ),
                    "Cash": float(company_data["cash"]),
                    "Debt": float(company_data["debt"]),
                    "Diluted shares": float(
                        company_data["diluted_shares"]
                    ),
                    "Current price": company_data.get("current_price"),
                }

                st.success(
                    f"Loaded {company_data['company_name']}."
                )

            except ValueError as error:
                st.error(str(error))

    company_name = st.text_input(
        "Company name",
        value=st.session_state.company_name,
    )

    currency_options = ["USD", "INR", "GBP", "EUR", "AED"]

    selected_currency = st.session_state.currency

    if selected_currency not in currency_options:
        selected_currency = "USD"

    currency = st.selectbox(
        "Currency",
        options=currency_options,
        index=currency_options.index(selected_currency),
    )

    units = st.selectbox(
        "Financial units",
        options=[
            "millions",
            "crores",
            "thousands",
            "whole units",
        ],
    )
    first_forecast_year = st.number_input(
        "First forecast year",
        min_value=2024,
        max_value=2040,
        value=2027,
        step=1,
    )

    forecast_years = st.slider(
        "Forecast years",
        min_value=3,
        max_value=10,
        value=5,
    )

    st.divider()

    st.header("Scenario")

    scenario = st.selectbox(
        "Active scenario",
        options=["Base", "Upside", "Downside"],
    )

    st.divider()

    loaded_ticker_for_source = st.session_state.loaded_ticker.upper()
    default_actuals_source = (
        "India — NSE/BSE"
        if loaded_ticker_for_source.endswith((".NS", ".BO"))
        else "United States — SEC"
    )
    official_actuals_sources = [
        "United States — SEC",
        "India — NSE/BSE",
        "United Kingdom — Companies House",
    ]
    official_actuals_source = st.selectbox(
        "Official actuals source",
        official_actuals_sources,
        index=official_actuals_sources.index(default_actuals_source),
        help=(
            "SEC structured actuals and UK structured/PDF-assisted actuals "
            "are available. India structured extraction will be added next."
        ),
    )

    apply_official_actuals = st.button(
        "Use official filing actuals as model inputs"
    )

    if apply_official_actuals and official_actuals_source == "India — NSE/BSE":
        st.warning(
            "Structured financial actuals for India are not "
            "connected yet. Existing model inputs were preserved, and "
            "missing filing values were not treated as zero."
        )

    if (
        apply_official_actuals
        and official_actuals_source == "United Kingdom — Companies House"
    ):
        try:
            uk_model_company_number = st.session_state.get(
                "uk_company_number", ""
            )
            if not uk_model_company_number:
                raise ValueError(
                    "Load UK filings below first so the Companies House "
                    "company number is available."
                )

            uk_model_data = get_uk_financial_facts(
                uk_model_company_number
            )
            uk_metrics = uk_model_data["Financial Data"]
            uk_revenue_records = uk_metrics.get("Revenue", [])
            uk_cash_records = uk_metrics.get("Cash", [])
            uk_debt_records = uk_metrics.get("Long-Term Debt", [])
            uk_applied_metrics = []

            if (
                uk_revenue_records
                and uk_revenue_records[0].get("Value") is not None
            ):
                st.session_state.starting_revenue = (
                    uk_revenue_records[0]["Value"] / 1_000_000
                )
                uk_applied_metrics.append("revenue")

                ordered_uk_revenue = sorted(
                    uk_revenue_records,
                    key=lambda record: record["Period"],
                )[-4:]
                if len(ordered_uk_revenue) >= 2:
                    beginning_uk_revenue = ordered_uk_revenue[0]["Value"]
                    ending_uk_revenue = ordered_uk_revenue[-1]["Value"]
                    uk_growth_periods = len(ordered_uk_revenue) - 1
                    if beginning_uk_revenue > 0 and ending_uk_revenue >= 0:
                        uk_historical_cagr = (
                            ending_uk_revenue / beginning_uk_revenue
                        ) ** (1 / uk_growth_periods) - 1
                        st.session_state.revenue_growth_input = max(
                            -20.0,
                            min(50.0, uk_historical_cagr * 100),
                        )

            if (
                uk_cash_records
                and uk_cash_records[0].get("Value") is not None
            ):
                st.session_state.cash = (
                    uk_cash_records[0]["Value"] / 1_000_000
                )
                uk_applied_metrics.append("cash")

            if (
                uk_debt_records
                and uk_debt_records[0].get("Value") is not None
            ):
                st.session_state.debt = (
                    uk_debt_records[0]["Value"] / 1_000_000
                )
                uk_applied_metrics.append("debt")

            if not uk_applied_metrics:
                raise ValueError(
                    "No supported UK account values were available. "
                    "Existing model inputs were preserved."
                )

            uk_audit_metadata = dict(
                st.session_state.get("input_audit_metadata", {})
            )
            uk_loaded_baseline = dict(
                st.session_state.get("loaded_input_baseline", {})
            )
            uk_loaded_baseline["Annual revenue growth"] = (
                st.session_state.revenue_growth_input
            )
            uk_audit_metadata["Annual revenue growth"] = {
                "Source": "UK Companies House structured accounts",
                "Reporting date": (
                    uk_revenue_records[0].get("Period", "N/A")
                    if uk_revenue_records
                    else "N/A"
                ),
                "Line item": "Revenue CAGR",
                "Definition note": "Calculated from available annual revenue history",
            }
            for metric_name, records, model_input_name in (
                ("Revenue", uk_revenue_records, "Latest reported revenue"),
                ("Cash", uk_cash_records, "Cash"),
                ("Long-Term Debt", uk_debt_records, "Debt"),
            ):
                if records and records[0].get("Value") is not None:
                    value_millions = records[0]["Value"] / 1_000_000
                    uk_loaded_baseline[model_input_name] = value_millions
                    uk_audit_metadata[model_input_name] = {
                        "Source": "UK Companies House structured accounts",
                        "Reporting date": records[0].get("Period", "N/A"),
                        "Line item": metric_name,
                        "Definition note": (
                            "Official structured filing value; unavailable "
                            "metrics retain their prior input"
                        ),
                    }

            st.session_state.input_audit_metadata = uk_audit_metadata
            st.session_state.loaded_input_baseline = uk_loaded_baseline
            st.session_state.currency = "GBP"
            st.session_state.uk_pdf_actuals_preview = {}
            st.success(
                "Companies House actuals applied in GBP millions. Updated: "
                + ", ".join(uk_applied_metrics)
                + ". Unavailable values were preserved, not set to zero."
            )

        except Exception:
            st.session_state.uk_pdf_actuals_preview = {}
            loaded_uk_ticker = (
                st.session_state.get("loaded_ticker", "")
                .strip()
                .upper()
            )
            ticker_data_loaded = bool(
                st.session_state.get("company_snapshot")
            )

            if loaded_uk_ticker.endswith(".L") and ticker_data_loaded:
                st.session_state.currency = "GBP"
                st.warning(
                    "Official Companies House accounts are available for "
                    "viewing, but this filing does not provide reliable "
                    "structured model inputs. The existing "
                    f"{loaded_uk_ticker} ticker-based inputs were retained "
                    "in GBP. No values were replaced or set to zero."
                )
            else:
                st.warning(
                    "Official UK accounts could not provide reliable model "
                    "inputs. Load the company's London ticker, such as "
                    "TSCO.L, using 'Load company financials'. Existing "
                    "inputs were preserved."
                )

    uk_pdf_preview = st.session_state.get("uk_pdf_actuals_preview", {})
    if (
        official_actuals_source == "United Kingdom — Companies House"
        and uk_pdf_preview
    ):
        st.subheader("Review UK PDF actuals")
        st.warning(
            "These figures were extracted from a PDF and are unverified. "
            "Compare each value with the cited page before selecting it."
        )
        st.caption(
            f"{uk_pdf_preview.get('Company', '')} | Filing date: "
            f"{uk_pdf_preview.get('Filing date', 'N/A')}"
        )
        document_url = uk_pdf_preview.get("Document URL", "")
        if document_url:
            st.link_button("Open official accounts PDF", document_url)

        reviewed_uk_values = {}
        for candidate in uk_pdf_preview.get("Candidates", []):
            metric = candidate["Metric"]
            safe_metric_key = metric.lower().replace(" ", "_")
            with st.expander(
                f"{metric} — page {candidate['Page']}",
                expanded=True,
            ):
                reviewed_value = st.number_input(
                    f"{metric} (GBP millions)",
                    value=float(candidate["Value (GBP millions)"]),
                    key=f"uk_pdf_value_{safe_metric_key}",
                )
                st.caption(
                    f"Detected unit: {candidate['Unit detected']}"
                )
                st.code(candidate["Evidence"], language=None)
                use_value = st.checkbox(
                    f"I verified this {metric.lower()} value",
                    key=f"uk_pdf_confirm_{safe_metric_key}",
                )
                if use_value:
                    reviewed_uk_values[metric] = reviewed_value

        if st.button("Apply verified UK PDF values"):
            if not reviewed_uk_values:
                st.warning(
                    "Verify and select at least one value before applying."
                )
            else:
                if "Revenue" in reviewed_uk_values:
                    st.session_state.starting_revenue = reviewed_uk_values[
                        "Revenue"
                    ]
                if "Cash" in reviewed_uk_values:
                    st.session_state.cash = reviewed_uk_values["Cash"]
                if "Debt" in reviewed_uk_values:
                    st.session_state.debt = reviewed_uk_values["Debt"]

                st.session_state.currency = "GBP"
                st.success(
                    "Verified UK PDF values applied in GBP millions: "
                    + ", ".join(reviewed_uk_values)
                    + ". Unselected values were preserved."
                )

    if apply_official_actuals and official_actuals_source == "United States — SEC":
        try:
            model_ticker = st.session_state.loaded_ticker
            if model_ticker.upper().endswith((".NS", ".BO")):
                raise ValueError(
                    "Select a US ticker before applying SEC actuals."
                )
            model_cik = get_sec_cik_from_ticker(model_ticker)
            model_sec_data = get_sec_financial_facts(model_cik)

            sec_metrics = model_sec_data["Financial Data"]

            revenue_records = sec_metrics.get("Revenue", [])
            cash_records = sec_metrics.get("Cash", [])
            debt_records = sec_metrics.get("Long-Term Debt", [])
            historical_model_data = build_historical_analysis(
                model_sec_data
            )

            if (
                not historical_model_data.empty
                and "Total Assets" in historical_model_data.columns
            ):
                historical_model_data = historical_model_data[
                    historical_model_data["Total Assets"].notna()
                ]

            st.session_state.sec_historical_analysis = (
                historical_model_data.copy()
            )

            if (
                not historical_model_data.empty
                and "Revenue" in historical_model_data.columns
            ):
                revenue_history = (
                    historical_model_data
                    .dropna(subset=["Revenue"])
                    .sort_values("Period")
                    .tail(4)
                )

                if len(revenue_history) >= 2:
                    beginning_revenue = revenue_history.iloc[0][
                        "Revenue"
                    ]
                    ending_revenue = revenue_history.iloc[-1][
                        "Revenue"
                    ]
                    growth_periods = len(revenue_history) - 1

                    if beginning_revenue > 0:
                        historical_cagr = (
                            ending_revenue
                            / beginning_revenue
                        ) ** (1 / growth_periods) - 1

                        st.session_state.revenue_growth_input = max(
                            -20.0,
                            min(50.0, historical_cagr * 100),
                        )

            if (
                not historical_model_data.empty
                and "EBITDA Margin"
                in historical_model_data.columns
            ):
                ebitda_margin_history = (
                    historical_model_data["EBITDA Margin"]
                    .dropna()
                    .tail(3)
                )

                if not ebitda_margin_history.empty:
                    average_ebitda_margin = (
                        ebitda_margin_history.mean()
                    )

                    st.session_state.ebitda_margin_input = max(
                        -30.0,
                        min(60.0, average_ebitda_margin * 100),
                    )

            applied_metrics = []

            if revenue_records and revenue_records[0].get("Value") is not None:
                st.session_state.starting_revenue = (
                    revenue_records[0]["Value"] / 1_000_000
                )
                applied_metrics.append("revenue")

            if cash_records and cash_records[0].get("Value") is not None:
                st.session_state.cash = (
                    cash_records[0]["Value"] / 1_000_000
                )
                applied_metrics.append("cash")

            if debt_records and debt_records[0].get("Value") is not None:
                st.session_state.debt = (
                    debt_records[0]["Value"] / 1_000_000
                )
                applied_metrics.append("debt")

            if not applied_metrics:
                raise ValueError(
                    "No supported SEC values were available. Existing "
                    "model inputs were preserved."
                )

            sec_audit_metadata = dict(
                st.session_state.get("input_audit_metadata", {})
            )
            sec_loaded_baseline = dict(
                st.session_state.get("loaded_input_baseline", {})
            )
            sec_loaded_baseline["Annual revenue growth"] = (
                st.session_state.revenue_growth_input
            )
            sec_loaded_baseline["EBITDA margin"] = (
                st.session_state.ebitda_margin_input
            )
            sec_audit_metadata["Annual revenue growth"] = {
                "Source": "SEC company facts",
                "Reporting date": (
                    revenue_records[0].get("Period", "N/A")
                    if revenue_records
                    else "N/A"
                ),
                "Line item": "Revenue CAGR",
                "Definition note": "Calculated from recent SEC annual revenue",
            }
            sec_audit_metadata["EBITDA margin"] = {
                "Source": "SEC company facts",
                "Reporting date": (
                    revenue_records[0].get("Period", "N/A")
                    if revenue_records
                    else "N/A"
                ),
                "Line item": "Average EBITDA margin",
                "Definition note": "Calculated from recent SEC annual history",
            }
            for metric_name, records, model_input_name in (
                ("Revenue", revenue_records, "Latest reported revenue"),
                ("Cash", cash_records, "Cash"),
                ("Long-Term Debt", debt_records, "Debt"),
            ):
                if records and records[0].get("Value") is not None:
                    value_millions = records[0]["Value"] / 1_000_000
                    sec_loaded_baseline[model_input_name] = value_millions
                    sec_audit_metadata[model_input_name] = {
                        "Source": "SEC company facts",
                        "Reporting date": records[0].get("Period", "N/A"),
                        "Line item": metric_name,
                        "Definition note": "Official SEC XBRL filing value",
                    }

            st.session_state.input_audit_metadata = sec_audit_metadata
            st.session_state.loaded_input_baseline = sec_loaded_baseline
            st.session_state.currency = "USD"
            st.success(
                "SEC actuals applied in USD millions. Updated: "
                + ", ".join(applied_metrics)
                + ". Unavailable values were preserved, not set to zero."
            )

        except Exception as error:
            st.error(f"Could not apply SEC actuals: {error}")

    st.header("Operating assumptions")

    starting_revenue = st.number_input(
        "Latest reported revenue",
        min_value=0.0,
        step=100.0,
        key="starting_revenue",
    )

    revenue_growth_input = st.slider(
        "Annual revenue growth",
        min_value=-20.0,
        max_value=50.0,
        step=0.5,
        format="%.1f%%",
        key="revenue_growth_input",
        help="Defaults to the recent historical SEC revenue CAGR.",
    )

    ebitda_margin_input = st.slider(
        "EBITDA margin",
        min_value=-30.0,
        max_value=100.0,
        step=0.5,
        format="%.1f%%",
        key="ebitda_margin_input",
        help="Defaults to the recent historical SEC EBITDA margin.",
    )

    depreciation_input = st.slider(
        "Depreciation as % of revenue",
        min_value=0.0,
        max_value=20.0,
        value=3.0,
        step=0.5,
        format="%.1f%%",
    )

    tax_rate_input = st.slider(
        "Tax rate",
        min_value=0.0,
        max_value=50.0,
        value=25.0,
        step=0.5,
        format="%.1f%%",
    )

    capex_input = st.slider(
        "Capital expenditure as % of revenue",
        min_value=0.0,
        max_value=30.0,
        value=5.0,
        step=0.5,
        format="%.1f%%",
    )

    nwc_input = st.slider(
        "Net working capital as % of revenue",
        min_value=-10.0,
        max_value=30.0,
        value=2.0,
        step=0.5,
        format="%.1f%%",
    )

    st.divider()

    st.header("Valuation assumptions")

    cash = st.number_input(
        "Cash",
        min_value=0.0,
        step=10.0,
        key="cash",
    )

    debt = st.number_input(
        "Debt",
        min_value=0.0,
        step=10.0,
        key="debt",
    )

    diluted_shares = st.number_input(
        "Diluted shares",
        min_value=0.01,
        step=1.0,
        key="diluted_shares",
    )

    wacc_input = st.slider(
        "WACC",
        min_value=5.0,
        max_value=30.0,
        value=10.0,
        step=0.5,
        format="%.1f%%",
    )

    terminal_growth_input = st.slider(
        "Terminal growth rate",
        min_value=0.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
        format="%.1f%%",
    )


# ---------------------------------------------------------
# Model input audit trail
# ---------------------------------------------------------

audit_metadata = st.session_state.get("input_audit_metadata", {})
loaded_baseline = st.session_state.get("loaded_input_baseline", {})
current_audit_values = {
    "Latest reported revenue": starting_revenue,
    "Annual revenue growth": revenue_growth_input,
    "EBITDA margin": ebitda_margin_input,
    "Depreciation": depreciation_input,
    "Tax rate": tax_rate_input,
    "Capital expenditure": capex_input,
    "Net working capital": nwc_input,
    "Cash": cash,
    "Debt": debt,
    "Diluted shares": diluted_shares,
    "WACC": wacc_input,
    "Terminal growth rate": terminal_growth_input,
    "Current price": st.session_state.get("current_price"),
}
percentage_inputs = {
    "Annual revenue growth",
    "EBITDA margin",
    "Depreciation",
    "Tax rate",
    "Capital expenditure",
    "Net working capital",
    "WACC",
    "Terminal growth rate",
}
user_assumption_inputs = {
    "Depreciation",
    "Tax rate",
    "Capital expenditure",
    "Net working capital",
    "WACC",
    "Terminal growth rate",
}

audit_rows = []
for input_name, current_value in current_audit_values.items():
    metadata = audit_metadata.get(input_name, {})
    original_value = loaded_baseline.get(input_name)

    if input_name in user_assumption_inputs:
        source_name = "User assumption"
        reporting_date = "N/A"
        line_item = "Model assumption"
        definition_note = "Editable forecast or valuation assumption"
        status = "User input"
    else:
        source_name = metadata.get("Source", "Manual input")
        reporting_date = metadata.get("Reporting date", "N/A")
        line_item = metadata.get("Line item", "N/A")
        definition_note = metadata.get("Definition note", "")

        if original_value is None or current_value is None:
            status = "Review source"
        else:
            tolerance = max(0.0001, abs(float(original_value)) * 0.000001)
            status = (
                "Source value"
                if abs(float(current_value) - float(original_value)) <= tolerance
                else "Manual override"
            )

        if (
            input_name in {"Cash", "Debt"}
            and line_item == "N/A"
            and source_name != "Manual input"
        ):
            status = "Missing source value"

    if input_name in percentage_inputs:
        unit_label = "%"
    elif input_name == "Diluted shares":
        unit_label = "millions of shares"
    elif input_name == "Current price":
        unit_label = f"{currency} per share"
    else:
        unit_label = f"{currency} {units}"

    if (
        input_name in {"Latest reported revenue", "Cash", "Debt"}
        and source_name != "Manual input"
        and units != "millions"
    ):
        status = "Check units"

    audit_rows.append(
        {
            "Model input": input_name,
            "Value used": (
                "N/A" if current_value is None else current_value
            ),
            "Original loaded value": (
                "N/A" if original_value is None else original_value
            ),
            "Units": unit_label,
            "Source": source_name,
            "Reporting date": reporting_date,
            "Source line item": line_item,
            "Status": status,
            "Definition note": definition_note,
        }
    )

with st.expander("Model input audit trail", expanded=True):
    st.caption(
        "Source value means the input still matches the loaded data. Manual "
        "override means it has been edited since loading."
    )
    st.dataframe(
        pd.DataFrame(audit_rows),
        hide_index=True,
        width="stretch",
    )

    loaded_reporting_dates = {
        audit_metadata.get(name, {}).get("Reporting date")
        for name in ("Latest reported revenue", "Cash", "Debt")
        if audit_metadata.get(name, {}).get("Reporting date") not in {
            None,
            "",
            "N/A",
        }
    }
    if len(loaded_reporting_dates) > 1:
        st.warning(
            "Revenue, cash and debt come from different reporting dates. "
            "Review the source periods before relying on the valuation."
        )

    if units != "millions" and audit_metadata:
        st.warning(
            "Loaded ticker values are normalized to millions. Change "
            "Financial units back to 'millions' or manually convert every "
            "monetary input before using another unit setting."
        )


# ---------------------------------------------------------
# Convert percentages into decimals
# ---------------------------------------------------------

revenue_growth = revenue_growth_input / 100
ebitda_margin = ebitda_margin_input / 100
depreciation_percent = depreciation_input / 100
tax_rate = tax_rate_input / 100
capex_percent = capex_input / 100
nwc_percent = nwc_input / 100
wacc = wacc_input / 100
terminal_growth = terminal_growth_input / 100

revenue_growth, ebitda_margin = apply_scenario(
    scenario=scenario,
    revenue_growth=revenue_growth,
    ebitda_margin=ebitda_margin,
)


# ---------------------------------------------------------
# Run the financial model
# ---------------------------------------------------------

try:
    forecast = forecast_financials(
        starting_revenue=starting_revenue,
        revenue_growth=revenue_growth,
        ebitda_margin=ebitda_margin,
        depreciation_percent=depreciation_percent,
        tax_rate=tax_rate,
        capex_percent=capex_percent,
        nwc_percent=nwc_percent,
        forecast_years=forecast_years,
        first_forecast_year=int(first_forecast_year),
    )

except ValueError as error:
    st.error(str(error))
    st.stop()


# ---------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------

st.subheader(f"{company_name} ({ticker})")

st.caption(
    f"{scenario} scenario | {currency} {units} | "
    f"Forecast beginning {int(first_forecast_year)}"
)

company_snapshot = st.session_state.get("company_snapshot", {})

if company_snapshot.get("ticker") == ticker:
    st.subheader("Company snapshot")

    snapshot_currency = company_snapshot.get("currency") or currency
    snapshot_price = company_snapshot.get("current_price")
    snapshot_market_cap = company_snapshot.get("market_cap")
    snapshot_pe = company_snapshot.get("trailing_pe")
    snapshot_low = company_snapshot.get("fifty_two_week_low")
    snapshot_high = company_snapshot.get("fifty_two_week_high")

    def display_snapshot_item(column, label, value):
        with column:
            st.caption(label)
            st.markdown(f"#### {value}")


    snapshot_1, snapshot_2, snapshot_3, snapshot_4 = st.columns(4)

    current_price_display = (
        format_currency(float(snapshot_price), snapshot_currency)
        if snapshot_price is not None
        else "N/A"
    )

    market_cap_display = (
        f"{snapshot_currency} "
        f"{float(snapshot_market_cap) / 1_000_000_000:,.2f}B"
        if snapshot_market_cap is not None
        else "N/A"
    )

    pe_display = (
        f"{float(snapshot_pe):.2f}x"
        if snapshot_pe is not None
        else "N/A"
    )

    range_display = (
        f"{snapshot_currency} {float(snapshot_low):,.0f} – "
        f"{float(snapshot_high):,.0f}"
        if snapshot_low is not None and snapshot_high is not None
        else "N/A"
    )

    display_snapshot_item(
        snapshot_1,
        "Current price",
        current_price_display,
    )
    display_snapshot_item(
        snapshot_2,
        "Market capitalisation",
        market_cap_display,
    )
    display_snapshot_item(
        snapshot_3,
        "Trailing P/E",
        pe_display,
    )
    display_snapshot_item(
        snapshot_4,
        "52-week range",
        range_display,
    )


    profile_1, profile_2, profile_3, profile_4 = st.columns(4)

    employee_count = company_snapshot.get("employees")
    employees_display = (
        f"{int(employee_count):,}"
        if employee_count
        else "N/A"
    )

    display_snapshot_item(
        profile_1,
        "Sector",
        company_snapshot.get("sector") or "N/A",
    )
    display_snapshot_item(
        profile_2,
        "Industry",
        company_snapshot.get("industry") or "N/A",
    )
    display_snapshot_item(
        profile_3,
        "Country",
        company_snapshot.get("country") or "N/A",
    )
    display_snapshot_item(
        profile_4,
        "Employees",
        employees_display,
    )


    detail_1, detail_2, detail_3 = st.columns(3)

    dividend_yield = company_snapshot.get("dividend_yield")
    dividend_display = (
        f"{float(dividend_yield):.2f}%"
        if dividend_yield is not None
        else "N/A"
    )

    beta = company_snapshot.get("beta")
    beta_display = (
        f"{float(beta):.2f}"
        if beta is not None
        else "N/A"
    )

    enterprise_value = company_snapshot.get("enterprise_value")
    enterprise_value_display = (
        f"{snapshot_currency} "
        f"{float(enterprise_value) / 1_000_000_000:,.2f}B"
        if enterprise_value is not None
        else "N/A"
    )

    display_snapshot_item(
        detail_1,
        "Dividend yield",
        dividend_display,
    )
    display_snapshot_item(
        detail_2,
        "Beta",
        beta_display,
    )
    display_snapshot_item(
        detail_3,
        "Enterprise value",
        enterprise_value_display,
    )

    website = company_snapshot.get("website")
    business_summary = company_snapshot.get("business_summary")

    with st.expander("Company profile"):
        if business_summary:
            st.write(business_summary)
        else:
            st.write("No company description was available.")

        if website:
            st.markdown(f"[Visit company website]({website})")

    st.caption(
        "Snapshot source: Yahoo Finance. Market information may be "
        "delayed and should be verified before use."
    )

else:
    st.info(
        "Click 'Load company financials' to display the company snapshot."
    )

latest_forecast = forecast.iloc[-1]

metric_1, metric_2, metric_3, metric_4 = st.columns(4)

metric_1.metric(
    "Final-year revenue",
    format_currency(latest_forecast["Revenue"], currency),
)

metric_2.metric(
    "Final-year EBITDA",
    format_currency(latest_forecast["EBITDA"], currency),
)

metric_3.metric(
    "EBITDA margin",
    f"{latest_forecast['EBITDA Margin']:.1%}",
)

metric_4.metric(
    "Final-year free cash flow",
    format_currency(latest_forecast["Free Cash Flow"], currency),
)

# ---------------------------------------------------------
# Historical reported revenue
# ---------------------------------------------------------

historical_revenue = st.session_state.get(
    "historical_revenue",
    pd.DataFrame(),
)

st.subheader("Historical reported revenue")

if (
    isinstance(historical_revenue, pd.DataFrame)
    and not historical_revenue.empty
):
    historical_chart = go.Figure()

    historical_chart.add_trace(
        go.Bar(
            x=historical_revenue["Year"],
            y=historical_revenue["Revenue"],
            name="Reported revenue",
            marker_color="#4472C4",
        )
    )

    historical_chart.update_layout(
        xaxis_title="Financial year",
        yaxis_title=f"{currency} millions",
        hovermode="x unified",
    )

    st.plotly_chart(
        historical_chart,
        width="stretch",
    )

    st.dataframe(
        historical_revenue,
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "Source: Yahoo Finance. Verify the values against the "
        "company's original financial filings."
    )

else:
    st.info(
        "No historical revenue has been loaded. Enter a ticker "
        "and click 'Load company financials'."
    )

# ---------------------------------------------------------
# Actual versus forecast bridge
# ---------------------------------------------------------

st.subheader("Actual vs Forecast")

sec_history = st.session_state.get(
    "sec_historical_analysis",
    pd.DataFrame(),
)

bridge_metrics = ["Revenue", "EBITDA", "Free Cash Flow"]

if isinstance(sec_history, pd.DataFrame) and not sec_history.empty:
    actual_columns = [
        column
        for column in bridge_metrics
        if column in sec_history.columns
    ]

    actuals = sec_history[["Period", *actual_columns]].copy()
    actuals["Year"] = pd.to_datetime(
        actuals["Period"],
        errors="coerce",
    ).dt.year
    actuals = (
        actuals
        .dropna(subset=["Year"])
        .sort_values("Year")
        .drop_duplicates(subset=["Year"], keep="last")
        .tail(5)
    )
    actuals["Year"] = actuals["Year"].astype(int)

    forecast_columns = [
        column
        for column in bridge_metrics
        if column in forecast.columns
    ]
    projections = forecast[["Year", *forecast_columns]].copy()

    actual_long = actuals.melt(
        id_vars="Year",
        value_vars=actual_columns,
        var_name="Financial item",
        value_name="Value",
    )
    actual_long["Type"] = "Actual"

    forecast_long = projections.melt(
        id_vars="Year",
        value_vars=forecast_columns,
        var_name="Financial item",
        value_name="Value",
    )
    forecast_long["Type"] = "Forecast"

    bridge_data = pd.concat(
        [actual_long, forecast_long],
        ignore_index=True,
    ).dropna(subset=["Value"])

    bridge_chart = go.Figure()
    chart_colours = {
        "Revenue": "#4472C4",
        "EBITDA": "#70AD47",
        "Free Cash Flow": "#ED7D31",
    }

    for financial_item in bridge_metrics:
        for data_type, dash_style in [
            ("Actual", "solid"),
            ("Forecast", "dash"),
        ]:
            series = bridge_data[
                (bridge_data["Financial item"] == financial_item)
                & (bridge_data["Type"] == data_type)
            ]

            if not series.empty:
                bridge_chart.add_trace(
                    go.Scatter(
                        x=series["Year"],
                        y=series["Value"],
                        name=f"{financial_item} - {data_type}",
                        mode="lines+markers",
                        line={
                            "color": chart_colours[financial_item],
                            "dash": dash_style,
                        },
                    )
                )

    bridge_chart.update_layout(
        xaxis_title="Financial year",
        yaxis_title="USD millions",
        hovermode="x unified",
        legend_title="Metric and period type",
    )

    st.plotly_chart(bridge_chart, width="stretch")

    actual_table = actuals.set_index("Year")[actual_columns].transpose()
    actual_table.columns = [
        f"{int(year)}A" for year in actual_table.columns
    ]

    forecast_table = (
        projections
        .set_index("Year")[forecast_columns]
        .transpose()
    )
    forecast_table.columns = [
        f"{int(year)}F" for year in forecast_table.columns
    ]

    bridge_table = pd.concat(
        [actual_table, forecast_table],
        axis=1,
    )
    bridge_table.index.name = "Financial item"
    bridge_table = bridge_table.reset_index()

    st.dataframe(
        bridge_table,
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "A = SEC-reported actual. F = model forecast. "
        "Figures are shown in USD millions."
    )

else:
    st.info(
        "Click 'Use official filing actuals as model inputs' in the sidebar "
        "to build the Actual vs Forecast comparison."
    )

# ---------------------------------------------------------
# Forecast chart
# ---------------------------------------------------------

st.subheader("Revenue, EBITDA and free cash flow")

chart = go.Figure()

chart.add_trace(
    go.Scatter(
        x=forecast["Year"],
        y=forecast["Revenue"],
        name="Revenue",
        mode="lines+markers",
    )
)

chart.add_trace(
    go.Scatter(
        x=forecast["Year"],
        y=forecast["EBITDA"],
        name="EBITDA",
        mode="lines+markers",
    )
)

chart.add_trace(
    go.Scatter(
        x=forecast["Year"],
        y=forecast["Free Cash Flow"],
        name="Free Cash Flow",
        mode="lines+markers",
    )
)

chart.update_layout(
    xaxis_title="Forecast year",
    yaxis_title=f"{currency} {units}",
    hovermode="x unified",
    legend_title="Financial metric",
)

st.plotly_chart(chart, use_container_width=True)


# ---------------------------------------------------------
# Forecast table
# ---------------------------------------------------------

st.subheader("Forecast financials")

display_forecast = forecast.copy()

percentage_columns = ["EBITDA Margin"]

currency_columns = [
    column
    for column in display_forecast.columns
    if column not in ["Year", *percentage_columns]
]

column_configuration = {
    "Year": st.column_config.NumberColumn(
        "Year",
        format="%d",
    ),
    "EBITDA Margin": st.column_config.NumberColumn(
        "EBITDA Margin",
        format="percent",
    ),
}

for column in currency_columns:
    column_configuration[column] = st.column_config.NumberColumn(
        column,
        format="%.2f",
    )

st.dataframe(
    display_forecast,
    column_config=column_configuration,
    hide_index=True,
    use_container_width=True,
)


# ---------------------------------------------------------
# Valuation
# ---------------------------------------------------------

st.subheader("Discounted cash-flow valuation")

if wacc <= terminal_growth:
    st.error(
        "WACC must be greater than the terminal growth rate. "
        "Increase WACC or reduce terminal growth."
    )

else:
    try:
        valuation = calculate_dcf(
            forecast=forecast,
            wacc=wacc,
            terminal_growth=terminal_growth,
            cash=cash,
            debt=debt,
            diluted_shares=diluted_shares,
        )

        valuation_1, valuation_2, valuation_3 = st.columns(3)

        valuation_1.metric(
            "Enterprise value",
            format_currency(
                valuation["Enterprise Value"],
                currency,
            ),
        )

        valuation_2.metric(
            "Equity value",
            format_currency(
                valuation["Equity Value"],
                currency,
            ),
        )

        valuation_3.metric(
            "Implied value per share",
            format_currency(
                valuation["Implied Value Per Share"],
                currency,
            ),
        )

        st.subheader("Valuation benchmark")

        current_price = st.session_state.get("current_price")
        loaded_ticker = st.session_state.get("loaded_ticker")
        implied_value_per_share = float(
            valuation["Implied Value Per Share"]
        )

        if (
            current_price is not None
            and float(current_price) > 0
            and loaded_ticker == ticker
        ):
            current_price = float(current_price)
            implied_upside = (
                implied_value_per_share / current_price - 1
            )

            benchmark_1, benchmark_2, benchmark_3 = st.columns(3)

            benchmark_1.metric(
                "Current market price",
                format_currency(current_price, currency),
            )

            benchmark_2.metric(
                "DCF value per share",
                format_currency(implied_value_per_share, currency),
            )

            benchmark_3.metric(
                "Implied upside / downside",
                f"{implied_upside:.1%}",
            )

            if implied_upside >= 0.10:
                st.success(
                    "The DCF estimate is above the current market price. "
                    "This indicates potential upside under the selected "
                    "assumptions."
                )
            elif implied_upside <= -0.10:
                st.warning(
                    "The DCF estimate is below the current market price. "
                    "This indicates potential downside under the selected "
                    "assumptions."
                )
            else:
                st.info(
                    "The DCF estimate is broadly in line with the current "
                    "market price under the selected assumptions."
                )

            st.caption(
                "This model output is for analytical and educational "
                "purposes and is not investment advice."
            )

        else:
            st.info(
                "Click 'Load company financials' for the selected ticker "
                "to compare its market price with the DCF value."
            )

        st.subheader("Scenario comparison")

        scenario_rows = []
        base_revenue_growth = revenue_growth_input / 100
        base_ebitda_margin = ebitda_margin_input / 100

        for scenario_name in ["Downside", "Base", "Upside"]:
            scenario_growth, scenario_margin = apply_scenario(
                scenario=scenario_name,
                revenue_growth=base_revenue_growth,
                ebitda_margin=base_ebitda_margin,
            )

            scenario_forecast = forecast_financials(
                starting_revenue=starting_revenue,
                revenue_growth=scenario_growth,
                ebitda_margin=scenario_margin,
                depreciation_percent=depreciation_percent,
                tax_rate=tax_rate,
                capex_percent=capex_percent,
                nwc_percent=nwc_percent,
                forecast_years=forecast_years,
                first_forecast_year=int(first_forecast_year),
            )

            scenario_valuation = calculate_dcf(
                forecast=scenario_forecast,
                wacc=wacc,
                terminal_growth=terminal_growth,
                cash=cash,
                debt=debt,
                diluted_shares=diluted_shares,
            )

            scenario_final_year = scenario_forecast.iloc[-1]
            scenario_value_per_share = float(
                scenario_valuation["Implied Value Per Share"]
            )

            scenario_upside = None

            if (
                current_price is not None
                and float(current_price) > 0
                and loaded_ticker == ticker
            ):
                scenario_upside = (
                    scenario_value_per_share / float(current_price) - 1
                )

            scenario_rows.append(
                {
                    "Scenario": scenario_name,
                    "Revenue growth": scenario_growth,
                    "EBITDA margin": scenario_margin,
                    "Final-year revenue": float(
                        scenario_final_year["Revenue"]
                    ),
                    "Final-year EBITDA": float(
                        scenario_final_year["EBITDA"]
                    ),
                    "Final-year free cash flow": float(
                        scenario_final_year["Free Cash Flow"]
                    ),
                    "Enterprise value": float(
                        scenario_valuation["Enterprise Value"]
                    ),
                    "Equity value": float(
                        scenario_valuation["Equity Value"]
                    ),
                    "Value per share": scenario_value_per_share,
                    "Upside / downside": scenario_upside,
                }
            )

        scenario_table = pd.DataFrame(scenario_rows)

        st.dataframe(
            scenario_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Revenue growth": st.column_config.NumberColumn(
                    "Revenue growth",
                    format="percent",
                ),
                "EBITDA margin": st.column_config.NumberColumn(
                    "EBITDA margin",
                    format="percent",
                ),
                "Final-year revenue": st.column_config.NumberColumn(
                    "Final-year revenue",
                    format="%.2f",
                ),
                "Final-year EBITDA": st.column_config.NumberColumn(
                    "Final-year EBITDA",
                    format="%.2f",
                ),
                "Final-year free cash flow": (
                    st.column_config.NumberColumn(
                        "Final-year free cash flow",
                        format="%.2f",
                    )
                ),
                "Enterprise value": st.column_config.NumberColumn(
                    "Enterprise value",
                    format="%.2f",
                ),
                "Equity value": st.column_config.NumberColumn(
                    "Equity value",
                    format="%.2f",
                ),
                "Value per share": st.column_config.NumberColumn(
                    "Value per share",
                    format="%.2f",
                ),
                "Upside / downside": st.column_config.NumberColumn(
                    "Upside / downside",
                    format="percent",
                ),
            },
        )

        scenario_chart = go.Figure(
            go.Bar(
                x=scenario_table["Scenario"],
                y=scenario_table["Value per share"],
                marker_color=["#C00000", "#4472C4", "#70AD47"],
                name="DCF value per share",
            )
        )

        if (
            current_price is not None
            and float(current_price) > 0
            and loaded_ticker == ticker
        ):
            scenario_chart.add_hline(
                y=float(current_price),
                line_dash="dash",
                line_color="#FFC000",
                annotation_text="Current market price",
            )

        scenario_chart.update_layout(
            xaxis_title="Scenario",
            yaxis_title=f"{currency} per share",
            showlegend=False,
        )

        st.plotly_chart(scenario_chart, width="stretch")

        st.caption(
            "Scenario values use the same WACC, terminal growth, cash, "
            "debt and diluted-share assumptions."
        )

        with st.expander("View valuation calculation"):
            valuation_table = pd.DataFrame(
                {
                    "Valuation item": valuation.keys(),
                    "Value": valuation.values(),
                }
            )

            st.dataframe(
                valuation_table,
                hide_index=True,
                use_container_width=True,
            )

        st.subheader("DCF sensitivity analysis")

        sensitivity = create_sensitivity_table(
            forecast=forecast,
            cash=cash,
            debt=debt,
            diluted_shares=diluted_shares,
        )

        st.dataframe(
            sensitivity.style.format("{:,.2f}"),
            use_container_width=True,
        )

        assumptions = {
            "Starting revenue": starting_revenue,
            "Revenue growth": revenue_growth,
            "EBITDA margin": ebitda_margin,
            "Depreciation %": depreciation_percent,
            "Tax rate": tax_rate,
            "Capital expenditure %": capex_percent,
            "Net working capital %": nwc_percent,
            "Cash": cash,
            "Debt": debt,
            "Diluted shares": diluted_shares,
            "WACC": wacc,
            "Terminal growth": terminal_growth,
            "First forecast year": int(first_forecast_year),
            "Forecast years": forecast_years,
        }

        excel_file = create_excel_model(
            company_name=company_name,
            ticker=ticker,
            scenario=scenario,
            currency=currency,
            units=units,
            assumptions=assumptions,
            forecast=forecast,
            valuation=valuation,
            sensitivity=sensitivity,
        )

        safe_company_name = (
            company_name.lower().replace(" ", "_").replace(".", "")
        )

        st.download_button(
            label="Download Excel financial model",
            data=excel_file,
            file_name=f"{safe_company_name}_financial_model.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            type="primary",
        )

    except ValueError as error:
        st.error(str(error))


# ---------------------------------------------------------
# Comparable companies
# ---------------------------------------------------------

st.subheader("Comparable companies")

st.caption(
    "Compare the selected company with listed peers. "
    "Enter Yahoo Finance ticker symbols separated by commas."
)

peer_tickers_text = st.text_input(
    "Peer tickers",
    value="MSFT, GOOGL, AMZN, META",
    help="Examples: MSFT, GOOGL, AMZN, META",
)

if st.button("Load comparable companies"):
    peer_tickers = [
        peer.strip().upper()
        for peer in peer_tickers_text.split(",")
        if peer.strip()
    ]

    comparison_tickers = [ticker, *peer_tickers]

    with st.spinner("Loading comparable-company data..."):
        try:
            comparable_companies = get_comparable_companies(
                comparison_tickers
            )
            comparable_companies.insert(
                0,
                "Role",
                comparable_companies["Ticker"].apply(
                    lambda peer: (
                        "Selected company"
                        if peer == ticker
                        else "Peer"
                    )
                ),
            )

            st.session_state.comparable_companies = (
                comparable_companies
            )

            failed_tickers = comparable_companies.attrs.get(
                "failed_tickers",
                [],
            )

            if failed_tickers:
                st.warning(
                    "No data was returned for: "
                    + ", ".join(failed_tickers)
                )

        except ValueError as error:
            st.error(str(error))

comparable_companies = st.session_state.get(
    "comparable_companies",
    pd.DataFrame(),
)

if not comparable_companies.empty:
    st.dataframe(
        comparable_companies,
        hide_index=True,
        width="stretch",
        column_config={
            "Market cap": st.column_config.NumberColumn(
                "Market cap (millions)",
                format="%.2f",
            ),
            "Enterprise value": st.column_config.NumberColumn(
                "Enterprise value (millions)",
                format="%.2f",
            ),
            "Revenue": st.column_config.NumberColumn(
                "Revenue (millions)",
                format="%.2f",
            ),
            "EBITDA": st.column_config.NumberColumn(
                "EBITDA (millions)",
                format="%.2f",
            ),
            "P/E": st.column_config.NumberColumn(
                "P/E",
                format="%.2fx",
            ),
            "EV/Revenue": st.column_config.NumberColumn(
                "EV/Revenue",
                format="%.2fx",
            ),
            "EV/EBITDA": st.column_config.NumberColumn(
                "EV/EBITDA",
                format="%.2fx",
            ),
            "Revenue growth": st.column_config.NumberColumn(
                "Revenue growth",
                format="percent",
            ),
            "EBITDA margin": st.column_config.NumberColumn(
                "EBITDA margin",
                format="percent",
            ),
        },
    )

    multiple_columns = ["P/E", "EV/Revenue", "EV/EBITDA"]
    peer_medians = (
        comparable_companies[
            comparable_companies["Role"] == "Peer"
        ][multiple_columns]
        .median(numeric_only=True)
    )

    median_columns = st.columns(3)

    for metric_column, metric_name in zip(
        median_columns,
        multiple_columns,
    ):
        median_value = peer_medians.get(metric_name)

        metric_column.metric(
            f"Peer median {metric_name}",
            (
                f"{median_value:.2f}x"
                if pd.notna(median_value)
                else "N/A"
            ),
        )

    multiple_chart_data = comparable_companies[
        ["Ticker", "EV/Revenue", "EV/EBITDA"]
    ].set_index("Ticker")

    st.bar_chart(multiple_chart_data)

    st.caption(
        "Source: Yahoo Finance. Peer outputs are indicative and should "
        "be verified against primary filings or a licensed data source."
    )

else:
    st.info(
        "Enter peer tickers and click 'Load comparable companies'."
    )


# ---------------------------------------------------------
# Financial red flags
# ---------------------------------------------------------

st.subheader("Financial red flags")

red_flags = identify_financial_red_flags(
    forecast=forecast,
    debt=debt,
    cash=cash,
)

for flag in red_flags:
    if flag.startswith("No major"):
        st.success(flag)
    else:
        st.warning(flag)

    
# ---------------------------------------------------------
# Automated investment commentary
# ---------------------------------------------------------

st.subheader("Automated investment commentary")

st.caption(
    "Generate commentary using the model calculations. "
    "This version does not require API credits."
)

if st.button(
    "Generate investment commentary",
    type="primary",
):
    if "valuation" not in locals():
        st.error(
            "A valid DCF valuation is required before generating commentary."
        )
    else:
        commentary_summary = {
            "revenue_growth": revenue_growth,
            "ebitda_margin": ebitda_margin,
            "final_revenue": float(latest_forecast["Revenue"]),
            "final_ebitda": float(latest_forecast["EBITDA"]),
            "final_fcf": float(latest_forecast["Free Cash Flow"]),
            "cash": cash,
            "debt": debt,
            "enterprise_value": valuation["Enterprise Value"],
            "implied_value_per_share": valuation[
                "Implied Value Per Share"
            ],
            "current_price": st.session_state.get("current_price"),
            "red_flags": red_flags,
        }

        st.session_state["investment_commentary"] = (
            generate_rule_based_analysis(
                company_name=company_name,
                ticker=ticker,
                scenario=scenario,
                financial_summary=commentary_summary,
            )
        )

if st.session_state.get("investment_commentary"):
    st.markdown(
        st.session_state["investment_commentary"]
    )
st.subheader("PDF investment report")

if "valuation" in locals():
    pdf_file = create_pdf_report(
        company_name=company_name,
        ticker=ticker,
        scenario=scenario,
        currency=currency,
        units=units,
        forecast=forecast,
        valuation=valuation,
        red_flags=red_flags,
        commentary=st.session_state.get(
            "investment_commentary",
            "",
        ),
    )

    safe_pdf_name = (
        company_name.lower()
        .replace(" ", "_")
        .replace(".", "")
    )

    st.download_button(
        label="Download PDF investment report",
        data=pdf_file,
        file_name=f"{safe_pdf_name}_investment_report.pdf",
        mime="application/pdf",
        type="primary",
    )
else:
    st.info(
        "Enter valid valuation assumptions to generate the PDF report."
    )

# ---------------------------------------------------------
# Model notes
# ---------------------------------------------------------

with st.expander("Model methodology"):
    st.markdown(
        """
        - Revenue is forecast using the latest reported revenue and an
          annual growth assumption.
        - EBITDA is calculated using the selected EBITDA margin.
        - EBIT equals EBITDA less depreciation.
        - Taxes are applied only when EBIT is positive.
        - Free cash flow equals NOPAT plus depreciation, less capital
          expenditure and the change in net working capital.
        - Terminal value uses the Gordon Growth Method.
        - This model is for analytical and educational purposes and is
          not investment advice.
        """
    )


st.divider()
st.header("Global regulatory filings")

st.subheader("India — Official NSE filings")

if "nse_filings_data" not in st.session_state:
    st.session_state.nse_filings_data = []

if "nse_company_name" not in st.session_state:
    st.session_state.nse_company_name = ""

if "nse_company_symbol" not in st.session_state:
    st.session_state.nse_company_symbol = ""

india_column_1, india_column_2 = st.columns([2, 1])

with india_column_1:
    nse_ticker = st.text_input(
        "NSE company symbol",
        value="RELIANCE",
        help=(
            "Enter an NSE symbol such as RELIANCE, TCS or INFY. "
            "The .NS suffix is optional."
        ),
    ).strip().upper()

with india_column_2:
    nse_history_years = st.slider(
        "NSE filing history (years)",
        min_value=1,
        max_value=20,
        value=5,
    )

if st.button("Load official NSE filings"):
    with st.spinner(
        f"Retrieving NSE filings for {nse_ticker}..."
    ):
        try:
            nse_company, nse_filings = get_nse_company_filings(
                nse_ticker,
                years=nse_history_years,
            )

            st.session_state.nse_filings_data = nse_filings
            st.session_state.nse_company_name = nse_company
            st.session_state.nse_company_symbol = (
                nse_ticker.removesuffix(".NS")
            )

            if not nse_filings:
                st.warning(
                    "No NSE filings were returned for this symbol and "
                    "date range. Check the symbol and try again."
                )

        except Exception as error:
            st.error(
                "Could not retrieve NSE filings. NSE may temporarily "
                f"restrict automated requests. Details: {error}"
            )
            st.markdown(
                "[Open the official NSE corporate-filings page]"
                "(https://www.nseindia.com/companies-listing/"
                "corporate-filings-announcements)"
            )

if st.session_state.nse_filings_data:
    nse_filings = st.session_state.nse_filings_data
    nse_filings_table = pd.DataFrame(nse_filings)
    parsed_nse_dates = pd.to_datetime(
        nse_filings_table["Filing date"],
        errors="coerce",
        dayfirst=True,
    )
    nse_filings_table["Year"] = parsed_nse_dates.dt.year.astype(
        "Int64"
    )

    st.success(
        f"{len(nse_filings):,} official NSE filings loaded for "
        f"{st.session_state.nse_company_name} "
        f"({st.session_state.nse_company_symbol})."
    )

    nse_categories = sorted(
        nse_filings_table["Category"].dropna().unique().tolist()
    )
    nse_years = sorted(
        nse_filings_table["Year"].dropna().astype(int).unique().tolist(),
        reverse=True,
    )

    nse_filter_1, nse_filter_2 = st.columns(2)

    with nse_filter_1:
        selected_nse_categories = st.multiselect(
            "Filter NSE filing categories",
            options=nse_categories,
            help="Leave empty to display every category.",
        )

    with nse_filter_2:
        selected_nse_year = st.selectbox(
            "Filter NSE filing year",
            options=["All years", *nse_years],
        )

    nse_search = st.text_input(
        "Search NSE filings",
        placeholder="Example: annual report, results or dividend",
    ).strip().lower()

    filtered_nse_filings = nse_filings_table.copy()

    if selected_nse_categories:
        filtered_nse_filings = filtered_nse_filings[
            filtered_nse_filings["Category"].isin(
                selected_nse_categories
            )
        ]

    if selected_nse_year != "All years":
        filtered_nse_filings = filtered_nse_filings[
            filtered_nse_filings["Year"] == selected_nse_year
        ]

    if nse_search:
        searchable_nse_text = (
            filtered_nse_filings["Category"].fillna("")
            + " "
            + filtered_nse_filings["Title"].fillna("")
        ).str.lower()
        filtered_nse_filings = filtered_nse_filings[
            searchable_nse_text.str.contains(
                nse_search,
                regex=False,
            )
        ]

    maximum_nse_results = st.slider(
        "Maximum NSE filings displayed",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
    )

    displayed_nse_filings = filtered_nse_filings.head(
        maximum_nse_results
    )

    st.info(
        f"Displaying {len(displayed_nse_filings):,} of "
        f"{len(filtered_nse_filings):,} matching NSE filings."
    )

    st.dataframe(
        displayed_nse_filings.drop(columns=["Year"]),
        hide_index=True,
        width="stretch",
        column_config={
            "URL": st.column_config.LinkColumn(
                "Official NSE document",
                display_text="Open filing",
            )
        },
    )

    st.caption(
        "Source: National Stock Exchange of India. Filing availability "
        "and metadata are controlled by the exchange."
    )


st.subheader("India — Official BSE filings")

if "bse_filings_data" not in st.session_state:
    st.session_state.bse_filings_data = []

if "bse_company_name" not in st.session_state:
    st.session_state.bse_company_name = ""

if "bse_company_code" not in st.session_state:
    st.session_state.bse_company_code = ""

bse_column_1, bse_column_2 = st.columns([2, 1])

with bse_column_1:
    bse_scrip_code = st.text_input(
        "BSE scrip code",
        value="500325",
        help=(
            "Enter a six-digit BSE code. Examples: "
            "500325 for Reliance Industries or 532540 for TCS."
        ),
    ).strip()

with bse_column_2:
    bse_history_years = st.slider(
        "BSE filing history (years)",
        min_value=1,
        max_value=20,
        value=5,
    )

if st.button("Load official BSE filings"):
    with st.spinner(
        f"Retrieving BSE filings for {bse_scrip_code}..."
    ):
        try:
            bse_company, bse_filings = get_bse_company_filings(
                bse_scrip_code,
                years=bse_history_years,
            )

            st.session_state.bse_filings_data = bse_filings
            st.session_state.bse_company_name = bse_company
            st.session_state.bse_company_code = bse_scrip_code

            if not bse_filings:
                st.warning(
                    "No BSE filings were returned for this scrip code "
                    "and date range. Check the code and try again."
                )

        except Exception as error:
            st.error(
                "Could not retrieve BSE filings. BSE may temporarily "
                f"restrict automated requests. Details: {error}"
            )
            st.markdown(
                "[Open the official BSE corporate-announcements page]"
                "(https://www.bseindia.com/corporates/ann.html)"
            )

if st.session_state.bse_filings_data:
    bse_filings_table = pd.DataFrame(
        st.session_state.bse_filings_data
    )
    parsed_bse_dates = pd.to_datetime(
        bse_filings_table["Filing date"],
        errors="coerce",
    )
    bse_filings_table["Year"] = parsed_bse_dates.dt.year.astype(
        "Int64"
    )

    st.success(
        f"{len(bse_filings_table):,} official BSE filings loaded for "
        f"{st.session_state.bse_company_name} "
        f"({st.session_state.bse_company_code})."
    )

    bse_categories = sorted(
        bse_filings_table["Category"].dropna().unique().tolist()
    )
    bse_years = sorted(
        bse_filings_table["Year"].dropna().astype(int).unique().tolist(),
        reverse=True,
    )

    bse_filter_1, bse_filter_2 = st.columns(2)

    with bse_filter_1:
        selected_bse_categories = st.multiselect(
            "Filter BSE filing categories",
            options=bse_categories,
            help="Leave empty to display every category.",
        )

    with bse_filter_2:
        selected_bse_year = st.selectbox(
            "Filter BSE filing year",
            options=["All years", *bse_years],
        )

    bse_search = st.text_input(
        "Search BSE filings",
        placeholder="Example: annual report, results or dividend",
    ).strip().lower()

    filtered_bse_filings = bse_filings_table.copy()

    if selected_bse_categories:
        filtered_bse_filings = filtered_bse_filings[
            filtered_bse_filings["Category"].isin(
                selected_bse_categories
            )
        ]

    if selected_bse_year != "All years":
        filtered_bse_filings = filtered_bse_filings[
            filtered_bse_filings["Year"] == selected_bse_year
        ]

    if bse_search:
        searchable_bse_text = (
            filtered_bse_filings["Category"].fillna("")
            + " "
            + filtered_bse_filings["Title"].fillna("")
        ).str.lower()
        filtered_bse_filings = filtered_bse_filings[
            searchable_bse_text.str.contains(
                bse_search,
                regex=False,
            )
        ]

    maximum_bse_results = st.slider(
        "Maximum BSE filings displayed",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
    )
    displayed_bse_filings = filtered_bse_filings.head(
        maximum_bse_results
    )

    st.info(
        f"Displaying {len(displayed_bse_filings):,} of "
        f"{len(filtered_bse_filings):,} matching BSE filings."
    )

    st.dataframe(
        displayed_bse_filings.drop(columns=["Year"]),
        hide_index=True,
        width="stretch",
        column_config={
            "URL": st.column_config.LinkColumn(
                "Official BSE document",
                display_text="Open filing",
            )
        },
    )

    st.caption(
        "Source: BSE Limited. Filing availability and metadata are "
        "controlled by the exchange."
    )


st.divider()
st.subheader("United Kingdom — Official Companies House filings")

if "uk_filings_data" not in st.session_state:
    st.session_state.uk_filings_data = []

if "uk_company_name" not in st.session_state:
    st.session_state.uk_company_name = ""

if "uk_company_number" not in st.session_state:
    st.session_state.uk_company_number = ""

uk_column_1, uk_column_2 = st.columns([2, 1])

with uk_column_1:
    uk_company_number = st.text_input(
        "Companies House company number",
        value="00041424",
        help=(
            "Enter the official company number, not a stock ticker. "
            "Example: 00041424 for Unilever PLC."
        ),
    ).strip()

with uk_column_2:
    uk_history_years = st.slider(
        "UK filing history (years)",
        min_value=1,
        max_value=20,
        value=5,
    )

if st.button("Load official UK filings"):
    with st.spinner(
        f"Retrieving Companies House filings for {uk_company_number}..."
    ):
        try:
            uk_company, uk_filings = get_uk_company_filings(
                uk_company_number,
                years=uk_history_years,
            )
            st.session_state.uk_filings_data = uk_filings
            st.session_state.uk_company_name = uk_company
            st.session_state.uk_company_number = uk_company_number.upper()

            if not uk_filings:
                st.warning(
                    "No UK filings were returned for this company number "
                    "and date range."
                )

        except Exception as error:
            st.error(f"Could not retrieve UK filings: {error}")
            st.markdown(
                "[Open Companies House search]"
                "(https://find-and-update.company-information.service.gov.uk/)"
            )

if st.session_state.uk_filings_data:
    uk_filings_table = pd.DataFrame(st.session_state.uk_filings_data)
    parsed_uk_dates = pd.to_datetime(
        uk_filings_table["Filing date"],
        errors="coerce",
    )
    uk_filings_table["Year"] = parsed_uk_dates.dt.year.astype("Int64")

    st.success(
        f"{len(uk_filings_table):,} official UK filings loaded for "
        f"{st.session_state.uk_company_name} "
        f"({st.session_state.uk_company_number})."
    )

    uk_categories = sorted(
        uk_filings_table["Category"].dropna().unique().tolist()
    )
    uk_years = sorted(
        uk_filings_table["Year"].dropna().astype(int).unique().tolist(),
        reverse=True,
    )
    uk_filter_1, uk_filter_2 = st.columns(2)

    with uk_filter_1:
        selected_uk_categories = st.multiselect(
            "Filter UK filing categories",
            options=uk_categories,
            help="Leave empty to display every category.",
        )

    with uk_filter_2:
        selected_uk_year = st.selectbox(
            "Filter UK filing year",
            options=["All years", *uk_years],
        )

    uk_search = st.text_input(
        "Search UK filings",
        placeholder="Example: accounts, confirmation statement or capital",
    ).strip().lower()
    filtered_uk_filings = uk_filings_table.copy()

    if selected_uk_categories:
        filtered_uk_filings = filtered_uk_filings[
            filtered_uk_filings["Category"].isin(selected_uk_categories)
        ]

    if selected_uk_year != "All years":
        filtered_uk_filings = filtered_uk_filings[
            filtered_uk_filings["Year"] == selected_uk_year
        ]

    if uk_search:
        searchable_uk_text = (
            filtered_uk_filings["Category"].fillna("")
            + " "
            + filtered_uk_filings["Type"].fillna("")
            + " "
            + filtered_uk_filings["Title"].fillna("")
        ).str.lower()
        filtered_uk_filings = filtered_uk_filings[
            searchable_uk_text.str.contains(uk_search, regex=False)
        ]

    maximum_uk_results = st.slider(
        "Maximum UK filings displayed",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
    )
    displayed_uk_filings = filtered_uk_filings.head(maximum_uk_results)

    st.info(
        f"Displaying {len(displayed_uk_filings):,} of "
        f"{len(filtered_uk_filings):,} matching UK filings."
    )
    st.dataframe(
        displayed_uk_filings.drop(columns=["Year"]),
        hide_index=True,
        width="stretch",
        column_config={
            "URL": st.column_config.LinkColumn(
                "Official Companies House document",
                display_text="Open filing",
            )
        },
    )
    st.caption(
        "Source: UK Companies House Public Data API. Filing availability "
        "and metadata are controlled by Companies House."
    )


st.divider()
st.subheader("United States — Official SEC filings")

if "sec_filings_data" not in st.session_state:
    st.session_state.sec_filings_data = []

if "sec_company_name" not in st.session_state:
    st.session_state.sec_company_name = ""

if "sec_company_cik" not in st.session_state:
    st.session_state.sec_company_cik = ""

sec_ticker = st.text_input(
    "US company ticker",
    value=st.session_state.loaded_ticker or "AAPL",
    help="Enter a US-listed ticker such as AAPL, MSFT or AMZN.",
)

if st.button("Load SEC filings"):
    try:
        sec_cik = get_sec_cik_from_ticker(sec_ticker)
        sec_company, sec_filings = get_sec_company_filings(sec_cik)

        st.session_state.sec_filings_data = sec_filings
        st.session_state.sec_company_name = sec_company
        st.session_state.sec_company_cik = sec_cik

    except Exception as error:
        st.error(f"Could not retrieve SEC filings: {error}")

if st.session_state.sec_filings_data:
    sec_filings = st.session_state.sec_filings_data

    st.success(
        f"Filings loaded for {st.session_state.sec_company_name} "
        f"(CIK: {st.session_state.sec_company_cik})"
    )

    form_options = sorted(
        {
            filing["Form"]
            for filing in sec_filings
        }
    )

    year_options = sorted(
        {
            filing["Filing date"][:4]
            for filing in sec_filings
            if filing["Filing date"]
        },
        reverse=True,
    )

    filter_column_1, filter_column_2 = st.columns(2)

    with filter_column_1:
        selected_forms = st.multiselect(
            "Filter by filing type",
            options=form_options,
            default=[],
            help="Leave empty to include every filing type.",
        )

    with filter_column_2:
        selected_year = st.selectbox(
            "Filter by filing year",
            options=["All years"] + year_options,
        )

    filing_search = st.text_input(
        "Search filings",
        placeholder="Example: 10-K, 2023 or 8-K",
    )

    filtered_filings = sec_filings

    if selected_forms:
        filtered_filings = [
            filing
            for filing in filtered_filings
            if filing["Form"] in selected_forms
        ]

    if selected_year != "All years":
        filtered_filings = [
            filing
            for filing in filtered_filings
            if filing["Filing date"].startswith(selected_year)
        ]

    if filing_search:
        search_text = filing_search.strip().lower()

        filtered_filings = [
            filing
            for filing in filtered_filings
            if search_text in filing["Form"].lower()
            or search_text in filing["Filing date"].lower()
            or search_text in filing["Report date"].lower()
        ]

    maximum_results = st.slider(
        "Maximum filings displayed",
        min_value=10,
        max_value=500,
        value=50,
        step=10,
    )

    displayed_filings = filtered_filings[:maximum_results]

    st.info(
        f"Displaying {len(displayed_filings)} of "
        f"{len(filtered_filings)} matching filings. "
        f"{len(sec_filings)} total filings were retrieved."
    )

    filings_table = pd.DataFrame(displayed_filings)

    st.dataframe(
        filings_table,
        hide_index=True,
        width="stretch",
        column_config={
            "URL": st.column_config.LinkColumn(
                "Official SEC filing",
                display_text="Open filing",
            )
        },
    )
    st.subheader("SEC-reported financial data")

if st.button("Load SEC financial data"):
    try:
        financial_cik = get_sec_cik_from_ticker(sec_ticker)
        sec_financial_data = get_sec_financial_facts(financial_cik)

        financial_rows = []

        for metric, records in sec_financial_data["Financial Data"].items():
            for record in records[:5]:
                financial_rows.append(
                    {
                        "Metric": metric,
                        "Period": record["Period"],
                        "Value (USD millions)": record["Value"] / 1_000_000,
                        "Form": record["Form"],
                        "Filed": record["Filed"],
                    }
                )

        if financial_rows:
            financial_table = pd.DataFrame(financial_rows)

            st.success(
                f"Official financial data loaded for "
                f"{sec_financial_data['Company']}."
            )

            st.dataframe(
                financial_table,
                hide_index=True,
                width="stretch",
                column_config={
                    "Value (USD millions)": st.column_config.NumberColumn(
                        "Value (USD millions)",
                        format="$ %.2f",
                    )
                },
            )
        else:
            st.warning("No SEC financial data was found.")

    except Exception as error:
        st.error(f"Could not retrieve SEC financial data: {error}")


st.divider()
st.header("Historical financial analysis")

if st.button("Build historical analysis"):
    try:
        historical_cik = get_sec_cik_from_ticker(sec_ticker)
        historical_sec_data = get_sec_financial_facts(historical_cik)

        historical_analysis = build_historical_analysis(
            historical_sec_data
        )

        if historical_analysis.empty:
            st.warning("No historical financial data was found.")

        else:
            st.success(
                f"Historical analysis created for "
                f"{historical_sec_data['Company']}."
            )
            annual_history = historical_analysis.copy()

            # SEC company facts can include comparative quarterly periods
            # reported inside a 10-K. Keep periods with annual balance-sheet
            # data so the historical table contains fiscal years only.
            if "Total Assets" in annual_history.columns:
                annual_history = annual_history[
                    annual_history["Total Assets"].notna()
                ]

            display_history = (
                annual_history
                .tail(10)
                .set_index("Period")
                .transpose()
            )

            display_history.index.name = "Financial item"
            display_history = display_history.reset_index()
            display_history = display_history.astype(object)

            display_history = display_history.where(
                pd.notna(display_history),
                "N/A",
            )

            display_history = display_history.replace(
                {
                    None: "N/A",
                    "None": "N/A",
                    "nan": "N/A",
                    "<NA>": "N/A",
                }
            )

            st.caption(
                "Figures are shown in USD millions. N/A means the metric "
                "was unavailable in the SEC filing; it does not mean zero."
            )

            income_statement_items = [
                "Revenue",
                "Cost of Revenue",
                "Gross Profit",
                "Operating Income",
                "Depreciation and Amortisation",
                "EBITDA",
                "Net Income",
            ]

            balance_sheet_items = [
                "Cash",
                "Accounts Receivable",
                "Inventory",
                "Current Assets",
                "Total Assets",
                "Accounts Payable",
                "Current Liabilities",
                "Long-Term Debt",
                "Total Liabilities",
                "Total Equity",
                "Net Debt",
            ]

            cash_flow_items = [
                "Operating Cash Flow",
                "Capital Expenditure",
                "Depreciation and Amortisation",
                "Free Cash Flow",
            ]

            ratio_items = [
                "Revenue Growth",
                "Gross Margin",
                "Operating Margin",
                "EBITDA Margin",
                "Net Margin",
                "Free Cash Flow Margin",
            ]

            def select_financial_items(item_names):
                available_items = set(
                    display_history["Financial item"]
                )

                selected_items = [
                    item
                    for item in item_names
                    if item in available_items
                ]

                return (
                    display_history
                    .set_index("Financial item")
                    .reindex(selected_items)
                    .reset_index()
                )

            income_statement_table = select_financial_items(
                income_statement_items
            )

            balance_sheet_table = select_financial_items(
                balance_sheet_items
            )

            cash_flow_table = select_financial_items(
                cash_flow_items
            )

            ratios_table = select_financial_items(
                ratio_items
            )
            for column in ratios_table.columns:
                if column != "Financial item":
                    ratios_table[column] = ratios_table[column].apply(
                        lambda value: (
                              value
                              if value == "N/A"
                              else f"{float(value):.1%}"
                        )
            )

            income_tab, balance_tab, cash_flow_tab, ratios_tab = (
                st.tabs(
                    [
                        "Income Statement",
                        "Balance Sheet",
                        "Cash Flow",
                        "Ratios",
                    ]
                )
            )

            with income_tab:
                st.dataframe(
                    income_statement_table,
                    hide_index=True,
                    width="stretch",
                )

            with balance_tab:
                st.dataframe(
                    balance_sheet_table,
                    hide_index=True,
                    width="stretch",
                )

            with cash_flow_tab:
                st.dataframe(
                    cash_flow_table,
                    hide_index=True,
                    width="stretch",
                )

            with ratios_tab:
                st.dataframe(
                    ratios_table,
                    hide_index=True,
                    width="stretch",
                )

            chart_columns = [
                column
                for column in [
                    "Revenue",
                    "Net Income",
                    "Operating Cash Flow",
                    "Free Cash Flow",
                ]
                if column in annual_history.columns
            ]

            if chart_columns:
                historical_chart = annual_history.set_index(
                    "Period"
                )[chart_columns]

                st.subheader("Historical performance trend")
                st.line_chart(historical_chart)

    except Exception as error:
        st.error(
            f"Could not build historical analysis: {error}"
        )


# ---------------------------------------------------------
# Unified global filings workspace
# ---------------------------------------------------------

st.divider()
st.header("Unified global filings workspace")
st.caption(
    "Review loaded SEC, NSE, BSE and Companies House filings in one "
    "standardised table. Load filings in the sections above to populate it."
)

global_filing_sources = [
    {
        "source": "United States — SEC",
        "identifier": st.session_state.get("sec_company_cik", ""),
        "company_name": st.session_state.get("sec_company_name", ""),
        "filings": st.session_state.get("sec_filings_data", []),
    },
    {
        "source": "India — NSE",
        "identifier": st.session_state.get("nse_company_symbol", ""),
        "company_name": st.session_state.get("nse_company_name", ""),
        "filings": st.session_state.get("nse_filings_data", []),
    },
    {
        "source": "India — BSE",
        "identifier": st.session_state.get("bse_company_code", ""),
        "company_name": st.session_state.get("bse_company_name", ""),
        "filings": st.session_state.get("bse_filings_data", []),
    },
    {
        "source": "United Kingdom — Companies House",
        "identifier": st.session_state.get("uk_company_number", ""),
        "company_name": st.session_state.get("uk_company_name", ""),
        "filings": st.session_state.get("uk_filings_data", []),
    },
]

global_filings_table = build_global_filings_table(global_filing_sources)

if global_filings_table.empty:
    st.info("Load filings from at least one registry to use this workspace.")
else:
    available_sources = sorted(global_filings_table["Source"].unique())
    filing_year_values = pd.to_datetime(
        global_filings_table["Filing date"], errors="coerce"
    ).dt.year.dropna()
    available_years = sorted(
        filing_year_values.astype(int).unique().tolist(), reverse=True
    )

    global_filter_col, global_year_col = st.columns(2)
    with global_filter_col:
        selected_global_sources = st.multiselect(
            "Filter global filing sources",
            available_sources,
            default=available_sources,
        )
    with global_year_col:
        selected_global_year = st.selectbox(
            "Filter global filing year",
            ["All"] + available_years,
        )

    global_search = st.text_input(
        "Search all loaded filings",
        placeholder="Company, identifier, filing type, category or title",
    )

    filtered_global_filings = filter_global_filings(
        global_filings_table,
        sources=selected_global_sources,
        year=(
            None
            if selected_global_year == "All"
            else int(selected_global_year)
        ),
        search_text=global_search,
    )

    maximum_global_results = st.slider(
        "Maximum global filings displayed",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
    )
    displayed_global_filings = filtered_global_filings.head(
        maximum_global_results
    )

    st.success(
        f"{len(global_filings_table):,} filings loaded across "
        f"{len(available_sources)} source(s). Displaying "
        f"{len(displayed_global_filings):,} of "
        f"{len(filtered_global_filings):,} matching filings."
    )
    st.dataframe(
        displayed_global_filings,
        hide_index=True,
        width="stretch",
        column_config={
            "URL": st.column_config.LinkColumn(
                "Official document",
                display_text="Open filing",
            )
        },
    )
