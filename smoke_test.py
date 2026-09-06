"""Basic tests for the financial analysis platform."""

from exports import create_excel_model
from financial_model import (
    calculate_dcf,
    create_sensitivity_table,
    forecast_financials,
    identify_financial_red_flags,
)


def run_tests() -> None:
    """Run basic calculation and export tests."""

    print("1. Testing financial forecast...")

    forecast = forecast_financials(
        starting_revenue=1000,
        revenue_growth=0.10,
        ebitda_margin=0.20,
        depreciation_percent=0.03,
        tax_rate=0.25,
        capex_percent=0.05,
        nwc_percent=0.02,
        forecast_years=5,
        first_forecast_year=2027,
    )

    assert not forecast.empty
    assert len(forecast) == 5
    assert forecast.iloc[0]["Revenue"] == 1100
    assert forecast.iloc[-1]["Revenue"] > forecast.iloc[0]["Revenue"]

    print("   Forecast test passed.")

    print("2. Testing DCF valuation...")

    valuation = calculate_dcf(
        forecast=forecast,
        wacc=0.10,
        terminal_growth=0.03,
        cash=100,
        debt=50,
        diluted_shares=100,
    )

    assert valuation["Enterprise Value"] > 0
    assert valuation["Equity Value"] > 0
    assert valuation["Implied Value Per Share"] > 0

    print("   DCF test passed.")

    print("3. Testing sensitivity analysis...")

    sensitivity = create_sensitivity_table(
        forecast=forecast,
        cash=100,
        debt=50,
        diluted_shares=100,
    )

    assert not sensitivity.empty
    assert sensitivity.shape == (5, 5)

    print("   Sensitivity test passed.")

    print("4. Testing financial red flags...")

    red_flags = identify_financial_red_flags(
        forecast=forecast,
        debt=50,
        cash=100,
    )

    assert isinstance(red_flags, list)
    assert len(red_flags) > 0

    print("   Red-flag test passed.")

    print("5. Testing Excel export...")

    assumptions = {
        "Starting revenue": 1000,
        "Revenue growth": 0.10,
        "EBITDA margin": 0.20,
        "Tax rate": 0.25,
        "WACC": 0.10,
        "Terminal growth": 0.03,
    }

    excel_file = create_excel_model(
        company_name="Test Company",
        ticker="TEST",
        scenario="Base",
        currency="USD",
        units="millions",
        assumptions=assumptions,
        forecast=forecast,
        valuation=valuation,
        sensitivity=sensitivity,
    )

    assert isinstance(excel_file, bytes)
    assert len(excel_file) > 1000

    # XLSX files are ZIP-based and begin with these bytes.
    assert excel_file[:2] == b"PK"

    print("   Excel-export test passed.")

    print("\nAll core tests passed successfully.")


if __name__ == "__main__":
    run_tests()