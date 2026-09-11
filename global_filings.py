"""Shared schema and filtering helpers for global regulatory filings."""

from collections.abc import Iterable

import pandas as pd


GLOBAL_FILING_COLUMNS = [
    "Source",
    "Identifier",
    "Company",
    "Filing type",
    "Category",
    "Title",
    "Filing date",
    "Report date",
    "URL",
]


def _text(value: object) -> str:
    """Return a display-safe string without exposing missing values as None."""

    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalise_filings(
    filings: Iterable[dict],
    source: str,
    identifier: str = "",
    company_name: str = "",
) -> list[dict]:
    """Convert filings from SEC, NSE, BSE or Companies House to one schema."""

    normalised = []

    for filing in filings or []:
        filing_type = _text(
            filing.get("Form")
            or filing.get("Type")
            or filing.get("Category")
        )
        category = _text(filing.get("Category") or filing_type)
        title = _text(filing.get("Title") or filing_type or "Official filing")
        filing_identifier = _text(
            filing.get("Symbol")
            or filing.get("Scrip code")
            or filing.get("Company number")
            or identifier
        )

        normalised.append(
            {
                "Source": source,
                "Identifier": filing_identifier,
                "Company": _text(filing.get("Company") or company_name),
                "Filing type": filing_type,
                "Category": category,
                "Title": title,
                "Filing date": _text(filing.get("Filing date")),
                "Report date": _text(filing.get("Report date")),
                "URL": _text(filing.get("URL")),
            }
        )

    return normalised


def build_global_filings_table(sources: Iterable[dict]) -> pd.DataFrame:
    """Combine multiple filing collections into a date-sorted table."""

    rows = []
    for source in sources:
        rows.extend(
            normalise_filings(
                filings=source.get("filings", []),
                source=_text(source.get("source")),
                identifier=_text(source.get("identifier")),
                company_name=_text(source.get("company_name")),
            )
        )

    table = pd.DataFrame(rows, columns=GLOBAL_FILING_COLUMNS)
    if table.empty:
        return table

    parsed_dates = pd.to_datetime(table["Filing date"], errors="coerce")
    table = table.assign(_filing_date=parsed_dates)
    table = table.sort_values("_filing_date", ascending=False, na_position="last")
    return table.drop(columns="_filing_date").reset_index(drop=True)


def filter_global_filings(
    table: pd.DataFrame,
    sources: list[str] | None = None,
    year: int | None = None,
    search_text: str = "",
) -> pd.DataFrame:
    """Filter a unified filings table without changing the source data."""

    filtered = table.copy()

    if sources:
        filtered = filtered[filtered["Source"].isin(sources)]

    if year is not None:
        filing_years = pd.to_datetime(
            filtered["Filing date"], errors="coerce"
        ).dt.year
        filtered = filtered[filing_years == year]

    query = search_text.strip()
    if query:
        searchable_columns = [
            "Identifier",
            "Company",
            "Filing type",
            "Category",
            "Title",
        ]
        search_values = filtered[searchable_columns].fillna("").astype(str)
        matches = search_values.apply(
            lambda column: column.str.contains(
                query, case=False, regex=False, na=False
            )
        ).any(axis=1)
        filtered = filtered[matches]

    return filtered.reset_index(drop=True)
