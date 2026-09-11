# AI Financial Analysis Platform

An interactive financial modelling and valuation dashboard for public-company analysis. The platform combines market data, regulatory filings, editable forecasts, valuation tools and exportable analyst outputs in one Streamlit application.

## Live Application

[Open the Financial Analysis Platform](https://financial-analysis-platform-dqjnb4jvhnv8c3dwgeuues.streamlit.app/)

## Core Features

- Search and analyse listed companies using ticker symbols
- Display company market and operating information
- Retrieve market data and financial statements through Yahoo Finance
- Access recent and historical SEC filings for US-listed companies
- Retrieve structured SEC financial facts and apply reported actuals as model inputs
- Access official NSE and BSE corporate filings for Indian-listed companies
- Present historical income statement, balance sheet, cash-flow and ratio analysis
- Build editable, driver-based financial forecasts
- Compare Base, Upside and Downside valuation scenarios
- Calculate EBITDA, EBIT, NOPAT and free cash flow
- Perform DCF valuation and calculate implied value per share
- Run WACC and terminal-growth sensitivity analysis
- Analyse comparable companies using trading multiples
- Identify rule-based financial risks and generate investment commentary
- Export the financial model to Excel and the investment report to PDF

## Example Tickers

| Market | Examples |
| --- | --- |
| United States | `AAPL`, `MSFT`, `GOOGL`, `AMZN` |
| India - NSE | `RELIANCE.NS`, `TCS.NS`, `INFY.NS`, `HDFCBANK.NS` |
| India - BSE | Use the supported BSE company identifier in the filings section |

## Analysis Workflow

1. Enter a company ticker and retrieve public market information.
2. Review the company snapshot and historical financial performance.
3. Inspect primary-source filings from the SEC, NSE or BSE where available.
4. Populate or edit the forecast assumptions.
5. Generate Base, Upside and Downside forecasts.
6. Review DCF valuation, sensitivity analysis and comparable-company benchmarks.
7. Analyse financial risks and investment commentary.
8. Export the results to Excel or PDF.

## Data Sources

- Yahoo Finance through `yfinance` for market data, company information and financial statements
- US Securities and Exchange Commission EDGAR APIs for US filings and structured company facts
- National Stock Exchange of India for official NSE corporate announcements
- BSE India for official BSE corporate announcements

Data availability and naming conventions vary by issuer, exchange and reporting period. Missing values are displayed as unavailable rather than treated as zero.

## Technology

- Python
- Streamlit
- pandas and NumPy
- Plotly
- yfinance and Requests
- XlsxWriter and openpyxl
- ReportLab

## Project Structure

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit interface and application workflow |
| `financial_model.py` | Forecasting, DCF, sensitivity and historical-analysis calculations |
| `data_sources.py` | Company information and comparable-company data |
| `sec_data.py` | SEC ticker mapping, filings and structured financial facts |
| `india_data.py` | NSE and BSE filing integrations |
| `ai_analysis.py` | Rule-based investment commentary |
| `exports.py` | Excel and PDF report generation |
| `smoke_test.py` | Core forecast, valuation and export checks |

## Running Locally

Clone the repository and enter the project directory:

```bash
git clone https://github.com/muskaankarnawat12-hash/financial-analysis-platform.git
cd financial-analysis-platform
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, activate it with:

```powershell
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and replace the example SEC contact with your own application name and contact email. The SEC requests an identifiable `User-Agent` for automated requests.

```bash
cp .env.example .env
```

Run the dashboard:

```bash
streamlit run app.py
```

## Testing

Run the core smoke test:

```bash
python3 smoke_test.py
```

Run a syntax check:

```bash
python3 -m py_compile app.py ai_analysis.py data_sources.py exports.py financial_model.py india_data.py sec_data.py smoke_test.py
```

## Important Notice

This project is intended for analytical, educational and demonstration purposes. It is not investment advice. Public-source information can be delayed, incomplete or restated, so users should verify material figures against the issuer's original filings before making financial decisions.
