# Financial Analysis Platform

A publicly accessible financial modelling application that retrieves company data, creates editable financial forecasts, performs DCF valuation and generates investment commentary.

## Live Application

[Open the Financial Analysis Platform](https://financial-analysis-platform-dqjnb4jvhnv8c3dwgeuues.streamlit.app/)

## Features

- Search listed companies using ticker symbols
- Retrieve company information and reported financial data
- Display historical revenue trends
- Create editable financial forecasts
- Model Base, Upside and Downside scenarios
- Calculate EBITDA, EBIT, NOPAT and free cash flow
- Perform DCF valuation
- Calculate implied equity value and value per share
- Run WACC and terminal-growth sensitivity analysis
- Identify rule-based financial red flags
- Generate automated investment commentary
- Export the financial model to Excel

## Example Tickers

### United States

- AAPL
- MSFT
- GOOGL
- AMZN

### India

- RELIANCE.NS
- TCS.NS
- INFY.NS
- HDFCBANK.NS

## Model Structure

The application follows this process:

1. Retrieve company data
2. Standardise key financial metrics
3. Populate historical information
4. Apply editable forecast assumptions
5. Calculate free cash flow
6. Perform DCF valuation
7. Run sensitivity analysis
8. Generate investment commentary
9. Export the results to Excel

## Technology

- Python
- Streamlit
- pandas
- NumPy
- Plotly
- yfinance
- XlsxWriter

## Running Locally

Clone the repository:

```bash
git clone https://github.com/muskaankarnawat12-hash/financial-analysis-platform.git
cd financial-analysis-platform