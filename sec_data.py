import requests


SEC_HEADERS = {
    "User-Agent": "Financial Analysis Platform muskaankarnawat12@gmail.com"
}


def get_sec_company_filings(cik):
    clean_cik = str(cik).strip().lstrip("0").zfill(10)

    url = f"https://data.sec.gov/submissions/CIK{clean_cik}.json"

    response = requests.get(
        url,
        headers=SEC_HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    recent = data["filings"]["recent"]

    filings = []

    for index, form in enumerate(recent["form"]):
        if form in ["10-K", "10-Q", "8-K"]:
            accession = recent["accessionNumber"][index]
            document = recent["primaryDocument"][index]

            filing_url = (
                "https://www.sec.gov/Archives/edgar/data/"
                f"{clean_cik.lstrip('0')}/"
                f"{accession.replace('-', '')}/"
                f"{document}"
            )

            filings.append(
                {
                    "Form": form,
                    "Filing date": recent["filingDate"][index],
                    "Report date": recent["reportDate"][index],
                    "URL": filing_url,
                }
            )

    return data.get("name", "Unknown company"), filings