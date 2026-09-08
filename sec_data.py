import requests


SEC_HEADERS = {
    "User-Agent": "Financial Analysis Platform muskaankarnawat12@gmail.com"
}


def get_sec_cik_from_ticker(ticker):
    """Find a company's SEC CIK using its US stock ticker."""

    url = "https://www.sec.gov/files/company_tickers.json"

    response = requests.get(
        url,
        headers=SEC_HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    companies = response.json()
    clean_ticker = ticker.strip().upper()

    for company in companies.values():
        if company["ticker"].upper() == clean_ticker:
            return str(company["cik_str"]).zfill(10)

    raise ValueError(
        f"No SEC CIK was found for ticker {clean_ticker}."
    )


def get_sec_company_filings(cik):
    """Retrieve recent and historical SEC filings for a company."""

    clean_cik = str(cik).strip().lstrip("0").zfill(10)
    cik_without_zeros = clean_cik.lstrip("0")

    company_url = (
        f"https://data.sec.gov/submissions/CIK{clean_cik}.json"
    )

    response = requests.get(
        company_url,
        headers=SEC_HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    company_data = response.json()
    filings = []

    def add_filings(filing_data):
        forms = filing_data.get("form", [])
        accession_numbers = filing_data.get("accessionNumber", [])
        filing_dates = filing_data.get("filingDate", [])
        report_dates = filing_data.get("reportDate", [])
        primary_documents = filing_data.get("primaryDocument", [])

        for index, form in enumerate(forms):
            accession = accession_numbers[index]
            document = primary_documents[index]

            if not accession or not document:
                continue

            filing_url = (
                "https://www.sec.gov/Archives/edgar/data/"
                f"{cik_without_zeros}/"
                f"{accession.replace('-', '')}/"
                f"{document}"
            )

            report_date = ""
            if index < len(report_dates):
                report_date = report_dates[index]

            filings.append(
                {
                    "Form": form,
                    "Filing date": filing_dates[index],
                    "Report date": report_date,
                    "URL": filing_url,
                }
            )

    # Add the company's recent filings.
    add_filings(company_data["filings"]["recent"])

    # Add older filings stored in the SEC archive files.
    historical_files = company_data["filings"].get("files", [])

    for historical_file in historical_files:
        historical_url = (
            "https://data.sec.gov/submissions/"
            f"{historical_file['name']}"
        )

        historical_response = requests.get(
            historical_url,
            headers=SEC_HEADERS,
            timeout=30,
        )
        historical_response.raise_for_status()

        historical_data = historical_response.json()
        add_filings(historical_data)

    filings.sort(
        key=lambda filing: filing["Filing date"],
        reverse=True,
    )

    company_name = company_data.get(
        "name",
        "Unknown company",
    )

    return company_name, filings