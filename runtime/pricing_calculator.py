"""Strategic pricing calculator for freelancers and agencies.

Pure-math helpers that derive recommended bill rates from a freelancer's
income goal, yearly expenses, tax rate, platform fees, and utilization.

Inspired by the value-based pricing sections of the freelance marketing
report (2.7.7). No network calls; raises ``ValidationError`` on bad input.
"""

from __future__ import annotations

from runtime.schemas import ValidationError


def recommended_rate(
    income_goal: float,
    weeks_per_year: int = 48,
    billable_hours_per_week: float = 0.0,
    expenses_yearly: float = 0.0,
    tax_rate: float = 0.0,
    platform_fee_rate: float = 0.0,
    utilization: float = 0.7,
) -> dict[str, float]:
    """Compute recommended bill rates from business inputs.

    Args:
        income_goal: Net (after-tax) income the freelancer wants per year.
        weeks_per_year: Working weeks per year (default 48, leaving 4 for rest).
        billable_hours_per_week: Target billable hours per week at full capacity.
        expenses_yearly: Yearly business expenses (hosting, software, etc.).
        tax_rate: Effective tax rate as a fraction (0.2 = 20%).
        platform_fee_rate: Platform cut as a fraction (0.2 = 20% on Upwork).
        utilization: Fraction of capacity actually billable (default 0.7).

    Returns:
        Dict with ``hourly``, ``day`` (8h), ``project`` (a 40h project),
        and ``retainer`` (monthly, 4 weeks) recommended rates before tax
        but inclusive of expenses, tax, and platform fees.

    Raises:
        ValidationError: on non-positive goals or out-of-range ratios.
    """
    if income_goal <= 0:
        raise ValidationError(
            "income_goal must be positive",
            context={"income_goal": income_goal},
        )
    if weeks_per_year <= 0:
        raise ValidationError(
            "weeks_per_year must be positive",
            context={"weeks_per_year": weeks_per_year},
        )
    if billable_hours_per_week <= 0:
        raise ValidationError(
            "billable_hours_per_week must be positive",
            context={"billable_hours_per_week": billable_hours_per_week},
        )
    if not 0.0 <= tax_rate < 1.0:
        raise ValidationError(
            "tax_rate must be in [0, 1)", context={"tax_rate": tax_rate}
        )
    if not 0.0 <= platform_fee_rate < 1.0:
        raise ValidationError(
            "platform_fee_rate must be in [0, 1)",
            context={"platform_fee_rate": platform_fee_rate},
        )
    if not 0.0 < utilization <= 1.0:
        raise ValidationError(
            "utilization must be in (0, 1]", context={"utilization": utilization}
        )

    gross_needed = (income_goal + expenses_yearly) / (1.0 - tax_rate)
    effective_hourly_capacity = billable_hours_per_week * utilization * weeks_per_year
    if effective_hourly_capacity <= 0:
        raise ValidationError("computed billable capacity is non-positive")

    hourly = gross_needed / effective_hourly_capacity / (1.0 - platform_fee_rate)
    day_rate = hourly * 8.0
    project_rate = hourly * 40.0
    retainer_rate = hourly * billable_hours_per_week * 4.0

    return {
        "hourly": round(hourly, 2),
        "day": round(day_rate, 2),
        "project": round(project_rate, 2),
        "retainer": round(retainer_rate, 2),
    }
