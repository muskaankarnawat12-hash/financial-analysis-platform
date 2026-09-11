"""Retrieve official corporate announcements for NSE-listed companies."""

from datetime import date, datetime, timedelta
from urllib.parse import urljoin

import requests


NSE_HOME = "https://www.nseindia.com"
NSE_ANNOUNCEMENTS_API = (
    "https://www.nseindia.com/api/corporate-announcements"
)
BSE_ANNOUNCEMENTS_API = (
    "https://api.bseindia.com/BseIndiaAPI/api/"
    "AnnSubCategoryGetData/w"
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
BSE_HEADERS = {
    "User-Agent": NSE_HEADERS["User-Agent"],
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
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


def clean_bse_scrip_code(scrip_code: str) -> str:
    """Validate and return a six-digit BSE scrip code."""

    cleaned_code = str(scrip_code).strip()

    if not cleaned_code.isdigit() or len(cleaned_code) != 6:
        raise ValueError(
            "Enter a valid six-digit BSE scrip code, such as 500325."
        )

    return cleaned_code


def _normalise_bse_filing(record: dict, scrip_code: str) -> dict:
    """Convert a BSE announcement into the platform filing schema."""

    attachment = (
        record.get("NSURL")
        or record.get("ATTACHMENTNAME")
        or record.get("AttachmentName")
        or ""
    )

    if attachment and not attachment.startswith(("http://", "https://")):
        attachment = urljoin(
            "https://www.bseindia.com/xml-data/corpfiling/AttachLive/",
            attachment,
        )

    category = (
        record.get("CATEGORYNAME")
        or record.get("ANNOUNCEMENT_TYPE")
        or record.get("HEADLINE")
        or "Corporate announcement"
    )
    title = (
        record.get("NEWSSUB")
        or record.get("SUBJECT")
        or record.get("HEADLINE")
        or category
    )
    filing_date = (
        record.get("NEWS_DT")
        or record.get("DT_TM")
        or record.get("DissemDT")
        or ""
    )

    return {
        "Exchange": "BSE India",
        "Scrip code": str(record.get("SCRIP_CD") or scrip_code),
        "Company": (
            record.get("SLONGNAME")
            or record.get("SCRIP_NAME")
            or ""
        ),
        "Category": str(category),
        "Title": str(title),
        "Filing date": _normalise_date(filing_date),
        "URL": attachment,
    }


def get_bse_company_filings(
    scrip_code: str,
    years: int = 5,
) -> tuple[str, list[dict]]:
    """Retrieve current and historical BSE corporate announcements."""

    cleaned_code = clean_bse_scrip_code(scrip_code)
    years = max(1, min(int(years), 20))
    session = requests.Session()
    session.headers.update(BSE_HEADERS)
    filings = []
    seen_filings = set()

    period_end = date.today()
    earliest_date = period_end - timedelta(days=365 * years)

    while period_end > earliest_date:
        period_start = max(
            earliest_date,
            period_end - timedelta(days=364),
        )
        page_number = 1

        while page_number <= 100:
            parameters = {
                "pageno": page_number,
                "strCat": -1,
                "strPrevDate": period_start.strftime("%Y%m%d"),
                "strScrip": cleaned_code,
                "strSearch": "P",
                "strToDate": period_end.strftime("%Y%m%d"),
                "strType": "C",
                "subcategory": -1,
            }

            response = session.get(
                BSE_ANNOUNCEMENTS_API,
                params=parameters,
                timeout=45,
            )
            response.raise_for_status()
            payload = response.json()

            if isinstance(payload, dict):
                records = payload.get("Table", payload.get("data", []))
            else:
                records = payload

            if not records:
                break

            for record in records:
                filing = _normalise_bse_filing(record, cleaned_code)
                unique_key = (
                    filing["URL"],
                    filing["Filing date"],
                    filing["Title"],
                )

                if unique_key not in seen_filings:
                    seen_filings.add(unique_key)
                    filings.append(filing)

            total_pages = page_number
            if isinstance(payload, dict) and payload.get("Table1"):
                page_details = payload["Table1"][0]
                total_pages = int(
                    page_details.get("TotalPageCnt")
                    or page_details.get("TOTAL_PAGE_COUNT")
                    or page_number
                )

            if page_number >= total_pages:
                break

            page_number += 1

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
        cleaned_code,
    )

    return company_name, filings
