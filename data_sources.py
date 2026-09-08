"""Functions for retrieving public company financial data."""

from typing import Any

import pandas as pd
import yfinance as yf


def find_latest_value(
    statement: pd.DataFrame,
    possible_names: list[str],
) -> float | None:
    """Find the latest available value for a financial metric."""

    if statement is None or statement.empty:
        return None

    for name in possible_names:
        if name in statement.index:
            values = statement.loc[name].dropna()

            if not values.empty:
                return float(values.iloc[0])

    return None


def get_company_data(ticker: str) -> dict[str, Any]:
    """Retrieve company details and financial data."""

    cleaned_ticker = ticker.strip().upper()

    if not cleaned_ticker:
        raise ValueError("Please enter a company ticker.")

    try:
        company = yf.Ticker(cleaned_ticker)

        information = company.info or {}
        income_statement = company.financials
        balance_sheet = company.balance_sheet
        cash_flow_statement = company.cashflow
        price_history = company.history(period="1y")

    except Exception as error:
        raise ValueError(
            f"Could not retrieve data for {cleaned_ticker}."
        ) from error

    if income_statement.empty and price_history.empty:
        raise ValueError(
            f"No financial information was found for {cleaned_ticker}. "
            "Please check the ticker and try again."
        )

    revenue = find_latest_value(
        income_statement,
        ["Total Revenue", "Operating Revenue"],
    )

    ebitda = find_latest_value(
        income_statement,
        ["EBITDA", "Normalized EBITDA"],
    )

    cash = find_latest_value(
        balance_sheet,
        [
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Cash Equivalents",
            "Cash Financial",
        ],
    )

    debt = find_latest_value(
        balance_sheet,
        [
            "Total Debt",
            "Long Term Debt And Capital Lease Obligation",
            "Long Term Debt",
        ],
    )

    if revenue is None:
        raise ValueError(
            f"Revenue data was not available for {cleaned_ticker}."
        )

    company_name = information.get(
        "longName",
        information.get("shortName", cleaned_ticker),
    )
    currency = information.get("currency", "USD")
    shares = information.get(
        "sharesOutstanding",
        information.get("impliedSharesOutstanding"),
    )
    current_price = information.get(
        "currentPrice",
        information.get("regularMarketPrice"),
    )
    market_cap = information.get("marketCap")
    revenue_growth = information.get("revenueGrowth")
    divisor = 1_000_000

    revenue_millions = revenue / divisor
    cash_millions = (cash or 0) / divisor
    debt_millions = (debt or 0) / divisor
    shares_millions = (shares or divisor) / divisor

    if ebitda is not None and revenue != 0:
        ebitda_margin = ebitda / revenue
    else:
        ebitda_margin = 0.15

    if revenue_growth is None:
        revenue_growth = 0.10

    historical_revenue = []

    for line_item in ["Total Revenue", "Operating Revenue"]:
        if line_item in income_statement.index:
            revenue_series = income_statement.loc[line_item].dropna()

            for period, value in revenue_series.items():
                historical_revenue.append(
                    {
                        "Year": int(period.year),
                        "Revenue": float(value) / divisor,
                    }
                )

            break

    historical_revenue_df = pd.DataFrame(historical_revenue)

    if not historical_revenue_df.empty:
        historical_revenue_df = (
            historical_revenue_df
            .drop_duplicates(subset=["Year"])
            .sort_values("Year")
            .reset_index(drop=True)
        )

    return {
        "ticker": cleaned_ticker,
        "company_name": company_name,
        "currency": currency,
        "revenue": revenue_millions,
        "revenue_growth": revenue_growth,
        "ebitda_margin": ebitda_margin,
        "cash": cash_millions,
        "debt": debt_millions,
        "diluted_shares": max(shares_millions, 0.01),
        "current_price": current_price,
        "market_cap": market_cap,
        "historical_revenue": historical_revenue_df,
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow_statement": cash_flow_statement,
        "source": "Yahoo Finance",
    }


def get_comparable_companies(tickers: list[str]) -> pd.DataFrame:
    """Retrieve headline operating and valuation data for peer companies."""

    cleaned_tickers = list(
        dict.fromkeys(
            ticker.strip().upper()
            for ticker in tickers
            if ticker and ticker.strip()
        )
    )

    if not cleaned_tickers:
        raise ValueError("Please enter at least one peer ticker.")

    comparison_rows = []
    failed_tickers = []

    for cleaned_ticker in cleaned_tickers:
        try:
            information = yf.Ticker(cleaned_ticker).info or {}

            market_cap = information.get("marketCap")
            enterprise_value = information.get("enterpriseValue")
            revenue = information.get("totalRevenue")
            ebitda = information.get("ebitda")

            ev_to_revenue = information.get("enterpriseToRevenue")
            if ev_to_revenue is None and enterprise_value and revenue:
                ev_to_revenue = enterprise_value / revenue

            ev_to_ebitda = information.get("enterpriseToEbitda")
            if ev_to_ebitda is None and enterprise_value and ebitda:
                ev_to_ebitda = enterprise_value / ebitda

            comparison_rows.append(
                {
                    "Ticker": cleaned_ticker,
                    "Company": information.get(
                        "longName",
                        information.get("shortName", cleaned_ticker),
                    ),
                    "Market cap": (
                        market_cap / 1_000_000
                        if market_cap is not None
                        else None
                    ),
                    "Enterprise value": (
                        enterprise_value / 1_000_000
                        if enterprise_value is not None
                        else None
                    ),
                    "Revenue": (
                        revenue / 1_000_000
                        if revenue is not None
                        else None
                    ),
                    "EBITDA": (
                        ebitda / 1_000_000
                        if ebitda is not None
                        else None
                    ),
                    "P/E": information.get("trailingPE"),
                    "EV/Revenue": ev_to_revenue,
                    "EV/EBITDA": ev_to_ebitda,
                    "Revenue growth": information.get("revenueGrowth"),
                    "EBITDA margin": information.get("ebitdaMargins"),
                }
            )

        except Exception:
            failed_tickers.append(cleaned_ticker)

    if not comparison_rows:
        raise ValueError(
            "Comparable-company data could not be retrieved. "
            "Please verify the tickers and try again."
        )

    comparison = pd.DataFrame(comparison_rows)
    comparison.attrs["failed_tickers"] = failed_tickers
    return comparison
