"""Retrieve official corporate announcements for NSE-listed companies."""

from datetime import date, datetime, timedelta
from urllib.parse import urljoin

import requests


NSE_HOME = "https://www.nseindia.com"
NSE_ANNOUNCEMENTS_API = (
    "https://www.nseindia.com/api/corporate-announcements"
)
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": (
        "https://www.nseindia.com/companies-listing/"
        "corporate-filings-announcements"
    ),
}


def clean_nse_symbol(ticker: str) -> str:
    """Convert a Yahoo-style Indian ticker into an NSE symbol."""

    cleaned_ticker = ticker.strip().upper()

    if cleaned_ticker.endswith(".NS"):
        cleaned_ticker = cleaned_ticker[:-3]

    if not cleaned_ticker:
        raise ValueError("Please enter an NSE company symbol.")

    return cleaned_ticker


def _create_nse_session() -> requests.Session:
    """Create an NSE session and obtain the cookies required by its API."""

    session = requests.Session()
    session.headers.update(NSE_HEADERS)

    response = session.get(NSE_HOME, timeout=30)
    response.raise_for_status()
    return session


def _normalise_attachment_url(value: str | None) -> str:
    """Return an absolute URL for an NSE filing attachment."""

    if not value:
        return ""

    if value.startswith(("https://", "http://")):
        return value

    return urljoin("https://nsearchives.nseindia.com/", value)


def _normalise_date(value: object) -> str:
    """Convert common NSE date formats into an ISO date string."""

    date_text = str(value or "").strip()

    for date_format in (
        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(date_text, date_format).strftime(
                "%Y-%m-%d"
            )
        except ValueError:
            continue

    return date_text


def _normalise_filing(record: dict, symbol: str) -> dict:
    """Convert an NSE announcement into the platform filing schema."""

    filing_date = (
        record.get("an_dt")
        or record.get("sort_date")
        or record.get("broadcast_date_time")
        or ""
    )
    filing_date = _normalise_date(filing_date)

    category = (
        record.get("desc")
        or record.get("subject")
        or record.get("category")
        or "Corporate announcement"
    )
    title = (
        record.get("attchmntText")
        or record.get("subject")
        or category
    )
    attachment = (
        record.get("attchmntFile")
        or record.get("attachment")
        or record.get("fileName")
    )

    return {
        "Exchange": "NSE India",
        "Symbol": record.get("symbol") or symbol,
        "Company": record.get("sm_name") or "",
        "Category": str(category),
        "Title": str(title),
        "Filing date": filing_date,
        "URL": _normalise_attachment_url(attachment),
    }


def get_nse_company_filings(
    ticker: str,
    years: int = 5,
) -> tuple[str, list[dict]]:
    """Retrieve current and historical NSE corporate announcements."""

    symbol = clean_nse_symbol(ticker)
    years = max(1, min(int(years), 20))
    session = _create_nse_session()
    filings = []
    seen_filings = set()

    period_end = date.today()
    earliest_date = period_end - timedelta(days=365 * years)

    while period_end > earliest_date:
        period_start = max(
            earliest_date,
            period_end - timedelta(days=364),
        )
        parameters = {
            "index": "equities",
            "symbol": symbol,
            "from_date": period_start.strftime("%d-%m-%Y"),
            "to_date": period_end.strftime("%d-%m-%Y"),
        }

        response = session.get(
            NSE_ANNOUNCEMENTS_API,
            params=parameters,
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict):
            records = payload.get("data", payload.get("records", []))
        else:
            records = payload

        for record in records or []:
            filing = _normalise_filing(record, symbol)
            unique_key = (
                filing["URL"],
                filing["Filing date"],
                filing["Title"],
            )

            if unique_key not in seen_filings:
                seen_filings.add(unique_key)
                filings.append(filing)

        period_end = period_start - timedelta(days=1)

    filings.sort(
        key=lambda filing: filing["Filing date"],
        reverse=True,
    )

    company_name = next(
        (
            filing["Company"]
            for filing in filings
            if filing["Company"]
        ),
        symbol,
    )

    return company_name, filings
