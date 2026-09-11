"""Retrieve official United Kingdom filings from Companies House."""

import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import requests
from dotenv import load_dotenv


load_dotenv()

COMPANIES_HOUSE_API = "https://api.company-information.service.gov.uk"
COMPANIES_HOUSE_WEB = (
    "https://find-and-update.company-information.service.gov.uk"
)
COMPANIES_HOUSE_DOCUMENT_API = (
    "https://document-api.company-information.service.gov.uk"
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


def _document_request(
    path: str,
    accept: str = "application/json",
) -> requests.Response:
    """Request metadata or content from the Companies House Document API."""

    response = requests.get(
        f"{COMPANIES_HOUSE_DOCUMENT_API}{path}",
        auth=(_get_api_key(), ""),
        headers={"Accept": accept},
        timeout=45,
    )

    if response.status_code == 401:
        raise ValueError(
            "The Companies House API key was rejected by the Document API."
        )

    response.raise_for_status()
    return response


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
            document_link = str(
                (filing.get("links") or {}).get("document_metadata") or ""
            )
            document_id = document_link.rstrip("/").split("/")[-1]
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
                    "Document ID": document_id,
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


def _local_name(tag: str) -> str:
    """Return an XML tag name without its namespace."""

    return tag.rsplit("}", 1)[-1].lower()


def _normalise_concept(value: str) -> str:
    """Normalise an XBRL concept name for resilient matching."""

    return re.sub(r"[^a-z0-9]", "", value.split(":")[-1].lower())


def _parse_number(element: ElementTree.Element) -> float | None:
    """Parse an inline-XBRL numeric fact, including sign and scale."""

    if str(element.attrib.get("nil", "")).lower() == "true":
        return None

    text = "".join(element.itertext()).strip()
    text = text.replace(",", "").replace("£", "").replace(" ", "")
    if not text or text in {"-", "—"}:
        return None

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]

    try:
        value = Decimal(text)
        scale = int(element.attrib.get("scale", "0") or 0)
        value *= Decimal(10) ** scale
        if negative or element.attrib.get("sign") == "-":
            value = -abs(value)
        return float(value)
    except (InvalidOperation, ValueError):
        return None


def _context_periods(root: ElementTree.Element) -> dict[str, str]:
    """Map XBRL context identifiers to their reporting-period end date."""

    periods = {}
    for element in root.iter():
        if _local_name(element.tag) != "context":
            continue

        context_id = element.attrib.get("id", "")
        period_end = ""
        for child in element.iter():
            if _local_name(child.tag) in {"enddate", "instant"}:
                period_end = (child.text or "").strip()
                if period_end:
                    break

        if context_id and period_end:
            periods[context_id] = period_end

    return periods


def _extract_uk_xbrl_facts(content: bytes) -> dict[str, list[dict]]:
    """Extract supported model metrics from UK inline-XBRL/XML accounts."""

    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError(
            "The Companies House accounts document could not be parsed."
        ) from error

    concept_groups = {
        "Revenue": {
            "turnoverrevenue",
            "turnovergrossoperatingrevenue",
            "revenue",
        },
        "Cash": {
            "cashbankonhand",
            "cashandcashequivalents",
            "cashandcash equivalents",
        },
        "Long-Term Debt": {
            "creditorsamountsfallingdueaftermorethanoneyear",
            "longtermborrowings",
            "noncurrentborrowings",
            "bankborrowingsnoncurrent",
        },
    }
    concept_groups["Cash"] = {
        _normalise_concept(value) for value in concept_groups["Cash"]
    }
    periods = _context_periods(root)
    extracted = {metric: {} for metric in concept_groups}

    for element in root.iter():
        concept_name = (
            element.attrib.get("name")
            or element.attrib.get("concept")
            or _local_name(element.tag)
        )
        concept = _normalise_concept(concept_name)
        context_id = (
            element.attrib.get("contextRef")
            or element.attrib.get("contextref")
            or ""
        )
        period = periods.get(context_id, "")
        if not period:
            continue

        value = _parse_number(element)
        if value is None:
            continue

        for metric, supported_concepts in concept_groups.items():
            if concept in supported_concepts and period not in extracted[metric]:
                extracted[metric][period] = {
                    "Period": period,
                    "Value": value,
                    "Form": "Companies House accounts",
                    "Filed": "",
                    "Accession": "",
                }

    return {
        metric: sorted(records.values(), key=lambda item: item["Period"], reverse=True)
        for metric, records in extracted.items()
    }


def get_uk_financial_facts(company_number: str) -> dict:
    """Retrieve machine-readable Companies House accounts for model inputs."""

    cleaned_number = clean_uk_company_number(company_number)
    profile = _request(f"/company/{cleaned_number}")
    company_name = profile.get("company_name") or cleaned_number
    payload = _request(
        f"/company/{cleaned_number}/filing-history",
        {"category": "accounts", "items_per_page": 100},
    )

    for filing in payload.get("items") or []:
        document_link = str(
            (filing.get("links") or {}).get("document_metadata") or ""
        )
        document_id = document_link.rstrip("/").split("/")[-1]
        if not document_id:
            continue

        metadata = _document_request(f"/document/{document_id}").json()
        resources = metadata.get("resources") or {}
        available_types = [
            content_type
            for content_type in ("application/xhtml+xml", "application/xml")
            if content_type in resources
        ]
        if not available_types:
            continue

        content_type = available_types[0]
        document = _document_request(
            f"/document/{document_id}/content",
            accept=content_type,
        )
        financial_data = _extract_uk_xbrl_facts(document.content)

        if any(financial_data.values()):
            filed_date = str(filing.get("date") or "")
            for records in financial_data.values():
                for record in records:
                    record["Filed"] = filed_date

            return {
                "Company": company_name,
                "Company number": cleaned_number,
                "Currency": "GBP",
                "Financial Data": financial_data,
            }

    raise ValueError(
        "No machine-readable UK accounts with supported revenue, cash or "
        "long-term debt values were available for this company."
    )
