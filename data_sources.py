"""Functions for retrieving public company financial data."""

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import yfinance as yf


MARKET_PEER_FALLBACKS = {
    "RELIANCE.NS": ["ONGC.NS", "IOC.NS", "BPCL.NS", "HINDPETRO.NS", "GAIL.NS"],
    "TCS.NS": ["INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS"],
    "500325.BO": ["ONGC.NS", "IOC.NS", "BPCL.NS", "HINDPETRO.NS", "GAIL.NS"],
    "AAPL": ["MSFT", "GOOGL", "DELL", "HPQ", "SONY"],
    "TSCO.L": ["SBRY.L", "MRW.L", "B&M.L", "OCDO.L", "CPG.L"],
}


def _peer_region(ticker: str, country: str | None) -> str:
    """Return the Yahoo screener region best suited to the listed ticker."""

    ticker = ticker.upper()
    if ticker.endswith((".NS", ".BO")):
        return "in"
    if ticker.endswith(".L"):
        return "gb"
    if str(country or "").lower() in {"united kingdom", "uk"}:
        return "gb"
    return "us"


def get_automatic_peer_tickers(
    ticker: str,
    sector: str | None = None,
    industry: str | None = None,
    country: str | None = None,
    maximum_peers: int = 5,
) -> list[str]:
    """Suggest listed peers from the same market and Yahoo industry data.

    Yahoo's screener availability differs by market, so a small, transparent
    fallback list is used for supported widely followed companies when the
    screener cannot return enough matching listings.
    """

    cleaned_ticker = ticker.strip().upper()
    maximum_peers = max(3, min(int(maximum_peers), 10))
    candidates: list[str] = []

    try:
        equity_query = getattr(yf, "EquityQuery", None)
        screener = getattr(yf, "screen", None)
        if equity_query is not None and screener is not None:
            filters = [
                equity_query("eq", ["region", _peer_region(cleaned_ticker, country)]),
                equity_query("gt", ["intradaymarketcap", 500_000_000]),
            ]
            query = equity_query("and", filters)
            results = screener(
                query,
                size=50,
                sortField="intradaymarketcap",
                sortAsc=False,
            )
            quotes = results.get("quotes", []) if isinstance(results, dict) else []
            target_industry = str(industry or "").strip().lower()
            target_sector = str(sector or "").strip().lower()

            for quote in quotes:
                symbol = str(quote.get("symbol", "")).upper()
                quote_industry = str(quote.get("industry", "")).lower()
                quote_sector = str(quote.get("sector", "")).lower()
                if not symbol or symbol == cleaned_ticker:
                    continue
                if target_industry and quote_industry == target_industry:
                    candidates.append(symbol)
                elif not target_industry and target_sector and quote_sector == target_sector:
                    candidates.append(symbol)
                if len(candidates) >= maximum_peers:
                    break
    except Exception:
        # The fallback below keeps peer loading available if Yahoo's screener
        # blocks a market or changes its response format.
        candidates = []

    if len(candidates) < 3:
        candidates.extend(MARKET_PEER_FALLBACKS.get(cleaned_ticker, []))

    return list(
        dict.fromkeys(
            candidate
            for candidate in candidates
            if candidate and candidate != cleaned_ticker
        )
    )[:maximum_peers]


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


def find_latest_value_with_label(
    statement: pd.DataFrame,
    possible_names: list[str],
) -> tuple[float | None, str]:
    """Return the latest value and the statement label used for it."""

    if statement is None or statement.empty:
        return None, ""

    for name in possible_names:
        if name in statement.index:
            values = statement.loc[name].dropna()
            if not values.empty:
                return float(values.iloc[0]), name

    return None, ""


def latest_statement_period(statement: pd.DataFrame) -> str:
    """Return the latest available statement-column date."""

    if statement is None or statement.empty or len(statement.columns) == 0:
        return "N/A"

    period = statement.columns[0]
    try:
        return pd.Timestamp(period).strftime("%Y-%m-%d")
    except Exception:
        return str(period)


def _historical_metric(
    statement: pd.DataFrame,
    possible_names: list[str],
    divisor: float = 1_000_000,
) -> dict[str, float]:
    """Return a normalized annual history for the first matching line item."""

    if statement is None or statement.empty:
        return {}

    for name in possible_names:
        if name not in statement.index:
            continue

        values = {}
        for period, value in statement.loc[name].items():
            if pd.isna(value):
                continue
            try:
                period_label = pd.Timestamp(period).strftime("%Y-%m-%d")
                values[period_label] = float(value) / divisor
            except (TypeError, ValueError):
                continue
        if values:
            return values

    return {}


def build_ticker_historical_analysis(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cash_flow_statement: pd.DataFrame,
) -> pd.DataFrame:
    """Create a multi-year analysis from annual ticker financial statements."""

    metrics = {
        "Revenue": _historical_metric(
            income_statement, ["Total Revenue", "Operating Revenue"]
        ),
        "Cost of Revenue": _historical_metric(
            income_statement, ["Cost Of Revenue", "Cost of Revenue"]
        ),
        "Gross Profit": _historical_metric(
            income_statement, ["Gross Profit"]
        ),
        "Operating Income": _historical_metric(
            income_statement, ["Operating Income", "Operating Income Loss"]
        ),
        "Depreciation and Amortisation": _historical_metric(
            cash_flow_statement,
            ["Depreciation And Amortization", "Depreciation", "Depreciation And Amortisation"],
        ),
        "EBITDA": _historical_metric(
            income_statement, ["EBITDA", "Normalized EBITDA"]
        ),
        "Net Income": _historical_metric(
            income_statement, ["Net Income", "Net Income Common Stockholders"]
        ),
        "Cash": _historical_metric(
            balance_sheet,
            [
                "Cash Cash Equivalents And Short Term Investments",
                "Cash And Cash Equivalents",
                "Cash Financial",
            ],
        ),
        "Accounts Receivable": _historical_metric(
            balance_sheet, ["Accounts Receivable", "Receivables"]
        ),
        "Inventory": _historical_metric(balance_sheet, ["Inventory"]),
        "Current Assets": _historical_metric(balance_sheet, ["Current Assets"]),
        "Total Assets": _historical_metric(balance_sheet, ["Total Assets"]),
        "Accounts Payable": _historical_metric(
            balance_sheet, ["Accounts Payable", "Payables And Accrued Expenses"]
        ),
        "Current Liabilities": _historical_metric(
            balance_sheet, ["Current Liabilities"]
        ),
        "Long-Term Debt": _historical_metric(
            balance_sheet,
            [
                "Long Term Debt And Capital Lease Obligation",
                "Long Term Debt",
                "Total Debt",
            ],
        ),
        "Total Liabilities": _historical_metric(
            balance_sheet, ["Total Liabilities Net Minority Interest", "Total Liabilities"]
        ),
        "Total Equity": _historical_metric(
            balance_sheet,
            ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"],
        ),
        "Operating Cash Flow": _historical_metric(
            cash_flow_statement,
            ["Total Cash From Operating Activities", "Operating Cash Flow"],
        ),
        "Capital Expenditure": _historical_metric(
            cash_flow_statement, ["Capital Expenditure"]
        ),
    }

    periods = sorted({period for series in metrics.values() for period in series})
    if not periods or not metrics["Revenue"]:
        return pd.DataFrame()

    history = pd.DataFrame({"Period": periods})
    for metric_name, values in metrics.items():
        history[metric_name] = history["Period"].map(values)

    # Cash-flow capex is commonly reported as a negative outflow by Yahoo.
    history["Capital Expenditure"] = history["Capital Expenditure"].abs()
    history["Free Cash Flow"] = (
        history["Operating Cash Flow"] - history["Capital Expenditure"]
    )
    history["Net Debt"] = history["Long-Term Debt"] - history["Cash"]
    history["Revenue Growth"] = history["Revenue"].pct_change()

    for metric_name, numerator in (
        ("Gross Margin", "Gross Profit"),
        ("Operating Margin", "Operating Income"),
        ("EBITDA Margin", "EBITDA"),
        ("Net Margin", "Net Income"),
        ("Free Cash Flow Margin", "Free Cash Flow"),
    ):
        history[metric_name] = history[numerator] / history["Revenue"]

    return history


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

    revenue, revenue_line_item = find_latest_value_with_label(
        income_statement,
        ["Total Revenue", "Operating Revenue"],
    )

    ebitda, ebitda_line_item = find_latest_value_with_label(
        income_statement,
        ["EBITDA", "Normalized EBITDA"],
    )

    cash, cash_line_item = find_latest_value_with_label(
        balance_sheet,
        [
            "Cash Cash Equivalents And Short Term Investments",
            "Cash And Cash Equivalents",
            "Cash Financial",
        ],
    )

    debt, debt_line_item = find_latest_value_with_label(
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
    quote_currency = information.get("currency", "USD")
    currency = information.get("financialCurrency") or quote_currency
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
    enterprise_value = information.get("enterpriseValue")
    trailing_pe = information.get("trailingPE")
    fifty_two_week_high = information.get("fiftyTwoWeekHigh")
    fifty_two_week_low = information.get("fiftyTwoWeekLow")
    dividend_yield = information.get("dividendYield")
    beta = information.get("beta")
    divisor = 1_000_000

    if str(quote_currency) in {"GBp", "GBX", "GBx"}:
        current_price = (
            float(current_price) / 100
            if current_price is not None
            else None
        )
        fifty_two_week_high = (
            float(fifty_two_week_high) / 100
            if fifty_two_week_high is not None
            else None
        )
        fifty_two_week_low = (
            float(fifty_two_week_low) / 100
            if fifty_two_week_low is not None
            else None
        )
        currency = "GBP"

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

    income_period = latest_statement_period(income_statement)
    balance_period = latest_statement_period(balance_sheet)
    market_data_date = (
        pd.Timestamp(price_history.index[-1]).strftime("%Y-%m-%d")
        if not price_history.empty
        else "N/A"
    )
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

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
        "enterprise_value": enterprise_value,
        "trailing_pe": trailing_pe,
        "fifty_two_week_high": fifty_two_week_high,
        "fifty_two_week_low": fifty_two_week_low,
        "dividend_yield": dividend_yield,
        "beta": beta,
        "sector": information.get("sector"),
        "industry": information.get("industry"),
        "country": information.get("country"),
        "website": information.get("website"),
        "employees": information.get("fullTimeEmployees"),
        "business_summary": information.get("longBusinessSummary"),
        "quote_currency": quote_currency,
        "market_data_date": market_data_date,
        "fetched_at": fetched_at,
        "audit_metadata": {
            "Latest reported revenue": {
                "Source": "Yahoo Finance financial statements",
                "Reporting date": income_period,
                "Line item": revenue_line_item or "N/A",
                "Definition note": "Latest reported consolidated revenue",
            },
            "Annual revenue growth": {
                "Source": "Yahoo Finance company statistics",
                "Reporting date": fetched_at,
                "Line item": "Revenue growth",
                "Definition note": "Provider growth metric or 10% fallback",
            },
            "EBITDA margin": {
                "Source": "Yahoo Finance financial statements",
                "Reporting date": income_period,
                "Line item": (
                    f"{ebitda_line_item or 'EBITDA fallback'} / "
                    f"{revenue_line_item or 'Revenue'}"
                ),
                "Definition note": "EBITDA divided by revenue",
            },
            "Cash": {
                "Source": "Yahoo Finance balance sheet",
                "Reporting date": balance_period,
                "Line item": cash_line_item or "N/A",
                "Definition note": "May include short-term investments",
            },
            "Debt": {
                "Source": "Yahoo Finance balance sheet",
                "Reporting date": balance_period,
                "Line item": debt_line_item or "N/A",
                "Definition note": "Lease treatment depends on source line item",
            },
            "Diluted shares": {
                "Source": "Yahoo Finance company statistics",
                "Reporting date": fetched_at,
                "Line item": "Shares outstanding",
                "Definition note": "Period-end shares; may differ from diluted weighted average",
            },
            "Current price": {
                "Source": "Yahoo Finance market data",
                "Reporting date": market_data_date,
                "Line item": "Current/regular market price",
                "Definition note": (
                    f"Original quote currency {quote_currency}; normalized to {currency}"
                ),
            },
        },
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
