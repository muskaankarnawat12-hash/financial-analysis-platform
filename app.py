"""Interactive financial modelling dashboard."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai_analysis import generate_rule_based_analysis
from data_sources import get_company_data
from sec_data import (
    get_sec_cik_from_ticker,
    get_sec_company_filings,
    get_sec_financial_facts,
)
from exports import create_excel_model, create_pdf_report
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

    if st.button("Use SEC actuals as model inputs"):
        try:
            model_ticker = st.session_state.loaded_ticker
            model_cik = get_sec_cik_from_ticker(model_ticker)
            model_sec_data = get_sec_financial_facts(model_cik)

            sec_metrics = model_sec_data["Financial Data"]

            revenue_records = sec_metrics.get("Revenue", [])
            cash_records = sec_metrics.get("Cash", [])
            debt_records = sec_metrics.get("Long-Term Debt", [])

            if revenue_records:
                st.session_state.starting_revenue = (
                    revenue_records[0]["Value"] / 1_000_000
                )

            if cash_records:
                st.session_state.cash = (
                    cash_records[0]["Value"] / 1_000_000
                )

            if debt_records:
                st.session_state.debt = (
                    debt_records[0]["Value"] / 1_000_000
                )

            st.success(
                "SEC actuals applied in USD millions. "
                "Revenue, cash and debt inputs were updated."
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

    growth_default = max(
        -20.0,
        min(50.0, st.session_state.revenue_growth_input),
    )

    revenue_growth_input = st.slider(
        "Annual revenue growth",
        min_value=-20.0,
        max_value=50.0,
        value=float(growth_default),
        step=0.5,
        format="%.1f%%",
    )

    margin_default = max(
        -30.0,
        min(60.0, st.session_state.ebitda_margin_input),
    )

    ebitda_margin_input = st.slider(
        "EBITDA margin",
        min_value=-30.0,
        max_value=60.0,
        value=float(margin_default),
        step=0.5,
        format="%.1f%%",
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
        value=float(st.session_state.diluted_shares),
        step=1.0,
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
st.header("Official SEC filings")

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
