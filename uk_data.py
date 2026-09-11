"""Retrieve official United Kingdom filings from Companies House."""

import os
import re
from datetime import date

import requests
from dotenv import load_dotenv


load_dotenv()

COMPANIES_HOUSE_API = "https://api.company-information.service.gov.uk"
COMPANIES_HOUSE_WEB = (
    "https://find-and-update.company-information.service.gov.uk"
)


def clean_uk_company_number(company_number: str) -> str:
    """Validate a Companies House company number."""

    cleaned_number = str(company_number).strip().upper().replace(" ", "")

    if not re.fullmatch(r"[A-Z0-9]{6,8}", cleaned_number):
        raise ValueError(
            "Enter a valid 6-8 character Companies House number."
        )

    return cleaned_number


def _get_api_key() -> str:
    """Return the configured Companies House API key."""

    api_key = os.getenv("COMPANIES_HOUSE_API_KEY", "").strip()

    if not api_key:
        raise ValueError(
            "Companies House is not configured. Add "
            "COMPANIES_HOUSE_API_KEY to the app secrets."
        )

    return api_key


def _request(path: str, parameters: dict | None = None) -> dict:
    """Request JSON from the Companies House Public Data API."""

    response = requests.get(
        f"{COMPANIES_HOUSE_API}{path}",
        params=parameters,
        auth=(_get_api_key(), ""),
        headers={"Accept": "application/json"},
        timeout=30,
    )

    if response.status_code == 401:
        raise ValueError(
            "The Companies House API key was rejected. Check the app secret."
        )

    if response.status_code == 404:
        raise ValueError("That Companies House company number was not found.")

    response.raise_for_status()
    return response.json()


def _filing_title(filing: dict) -> str:
    """Create a readable title from Companies House filing metadata."""

    description = str(filing.get("description") or "Official filing")
    description = description.replace("-", " ").replace("_", " ")
    description = " ".join(description.split()).capitalize()

    values = filing.get("description_values") or {}
    made_up_date = values.get("made_up_date")

    if made_up_date:
        description = f"{description} — period ended {made_up_date}"

    return description


def get_uk_company_filings(
    company_number: str,
    years: int = 5,
) -> tuple[str, list[dict]]:
    """Retrieve current and historical UK filings for one company."""

    cleaned_number = clean_uk_company_number(company_number)
    years = max(1, min(int(years), 20))
    profile = _request(f"/company/{cleaned_number}")
    company_name = profile.get("company_name") or cleaned_number

    filings = []
    start_index = 0
    items_per_page = 100

    while start_index < 10_000:
        payload = _request(
            f"/company/{cleaned_number}/filing-history",
            {
                "items_per_page": items_per_page,
                "start_index": start_index,
            },
        )
        items = payload.get("items") or []

        if not items:
            break

        for filing in items:
            filing_date = str(filing.get("date") or "")
            filing_year = int(filing_date[:4]) if filing_date[:4].isdigit() else 0

            if filing_year and filing_year < (date.today().year - years):
                continue

            transaction_id = str(filing.get("transaction_id") or "")
            document_url = ""

            if transaction_id:
                document_url = (
                    f"{COMPANIES_HOUSE_WEB}/company/{cleaned_number}/"
                    f"filing-history/{transaction_id}/document"
                )

            filings.append(
                {
                    "Registry": "UK Companies House",
                    "Company number": cleaned_number,
                    "Company": company_name,
                    "Category": str(filing.get("category") or "Other").title(),
                    "Type": str(filing.get("type") or ""),
                    "Title": _filing_title(filing),
                    "Filing date": filing_date,
                    "URL": document_url,
                }
            )

        total_count = int(payload.get("total_count") or 0)
        start_index += len(items)

        oldest_date = str(items[-1].get("date") or "")
        oldest_year = int(oldest_date[:4]) if oldest_date[:4].isdigit() else 0

        if start_index >= total_count or (
            oldest_year and oldest_year < (date.today().year - years)
        ):
            break

    filings.sort(key=lambda filing: filing["Filing date"], reverse=True)
    return company_name, filings
