"""Generate free rule-based investment commentary."""

from typing import Any


def generate_rule_based_analysis(
    company_name: str,
    ticker: str,
    scenario: str,
    financial_summary: dict[str, Any],
) -> str:
    """Generate commentary without using a paid AI API."""

    revenue_growth = financial_summary["revenue_growth"]
    ebitda_margin = financial_summary["ebitda_margin"]
    final_revenue = financial_summary["final_revenue"]
    final_ebitda = financial_summary["final_ebitda"]
    final_fcf = financial_summary["final_fcf"]
    cash = financial_summary["cash"]
    debt = financial_summary["debt"]
    enterprise_value = financial_summary["enterprise_value"]
    implied_value = financial_summary["implied_value_per_share"]
    current_price = financial_summary.get("current_price")
    red_flags = financial_summary.get("red_flags", [])

    if revenue_growth >= 0.15:
        growth_view = (
            "The model assumes strong revenue growth, which is an important "
            "driver of the investment case."
        )
    elif revenue_growth >= 0.05:
        growth_view = (
            "The model assumes moderate revenue growth, suggesting a relatively "
            "balanced operating outlook."
        )
    elif revenue_growth >= 0:
        growth_view = (
            "Revenue growth is limited, so valuation depends more heavily on "
            "margin improvement and cash generation."
        )
    else:
        growth_view = (
            "Revenue is forecast to decline, creating a material risk to the "
            "investment case."
        )

    if ebitda_margin >= 0.25:
        margin_view = (
            "The forecast EBITDA margin is strong and indicates meaningful "
            "operating profitability."
        )
    elif ebitda_margin >= 0.10:
        margin_view = (
            "The EBITDA margin is positive but leaves room for operational "
            "improvement."
        )
    elif ebitda_margin >= 0:
        margin_view = (
            "The EBITDA margin is low, making the valuation sensitive to "
            "relatively small changes in costs."
        )
    else:
        margin_view = (
            "The forecast remains EBITDA-negative, and the path to "
            "profitability should be examined carefully."
        )

    if final_fcf > 0:
        cash_flow_view = (
            "The business produces positive free cash flow in the final "
            "forecast year."
        )
    else:
        cash_flow_view = (
            "Free cash flow remains negative in the final forecast year, "
            "which may create additional funding requirements."
        )

    if debt > cash * 2:
        balance_sheet_view = (
            "Debt is more than twice the cash balance, indicating elevated "
            "financial leverage."
        )
    elif cash >= debt:
        balance_sheet_view = (
            "Cash is sufficient to cover reported debt, providing balance-sheet "
            "flexibility."
        )
    else:
        balance_sheet_view = (
            "Debt exceeds cash, but the difference is not extreme under the "
            "current assumptions."
        )

    valuation_comparison = (
        "A market-price comparison is unavailable because no current price "
        "was loaded."
    )

    if current_price not in (None, 0):
        upside = implied_value / current_price - 1

        if upside >= 0.20:
            valuation_comparison = (
                f"The model indicates potential upside of {upside:.1%} "
                "relative to the current market price."
            )
        elif upside <= -0.20:
            valuation_comparison = (
                f"The model indicates potential downside of {abs(upside):.1%} "
                "relative to the current market price."
            )
        else:
            valuation_comparison = (
                f"The implied value is within approximately 20% of the "
                f"current price, with modelled upside of {upside:.1%}."
            )

    risks_text = "\n".join(
        f"- {flag}" for flag in red_flags
    )

    if not risks_text:
        risks_text = "- No rule-based financial red flags were identified."

    return f"""
## Investment thesis

Under the **{scenario} scenario**, {company_name} ({ticker}) is forecast to
reach final-year revenue of **{final_revenue:,.2f}** and EBITDA of
**{final_ebitda:,.2f}**.

{growth_view}

{margin_view}

## Cash flow and balance sheet

{cash_flow_view}

{balance_sheet_view}

The model uses cash of **{cash:,.2f}** and debt of **{debt:,.2f}**.

## Valuation

The calculated enterprise value is **{enterprise_value:,.2f}**, and the
implied value per share is **{implied_value:,.2f}**.

{valuation_comparison}

## Potential catalysts

- Revenue growth exceeding the current {revenue_growth:.1%} assumption
- EBITDA-margin improvement above {ebitda_margin:.1%}
- Stronger free-cash-flow conversion
- Reduced debt or improved liquidity
- Lower valuation discount rates

## Key risks and red flags

{risks_text}

## Bull case

The bull case would require faster revenue growth, margin expansion, stronger
cash conversion and a lower perceived risk profile.

## Bear case

The bear case would involve slower growth, margin pressure, weaker free cash
flow or a higher discount rate.

## Metrics to monitor

- Revenue growth
- EBITDA margin
- Free-cash-flow conversion
- Debt relative to cash
- Capital expenditure
- Working-capital requirements
- WACC and terminal-growth assumptions

*This commentary is generated from model calculations and is not investment
advice. It does not incorporate qualitative company developments unless they
are separately added to the model.*
"""