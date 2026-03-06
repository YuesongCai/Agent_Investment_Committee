"""Input validation for ticker data bundles."""

from __future__ import annotations

import json
from pathlib import Path

from config.settings import LOW_DATA_QUALITY_THRESHOLD
from schemas import TickerInput


class InputValidationError(Exception):
    pass


def load_ticker_input(path: str | Path) -> TickerInput:
    """Load and validate a ticker input JSON file."""
    path = Path(path)
    if not path.exists():
        raise InputValidationError(f"Input file not found: {path}")
    if not path.suffix == ".json":
        raise InputValidationError(f"Input file must be JSON: {path}")

    with open(path) as f:
        data = json.load(f)

    return validate_ticker_input(data)


def validate_ticker_input(data: dict) -> TickerInput:
    """Validate a ticker input dict and return a TickerInput model."""
    required_fields = ["ticker", "company_name", "data_date"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise InputValidationError(f"Missing required fields: {missing}")

    ticker_input = TickerInput(**data)

    # Check data quality
    warnings = check_data_quality(ticker_input)
    if warnings:
        for w in warnings:
            print(f"  WARNING: {w}")

    return ticker_input


def check_data_quality(ticker_input: TickerInput) -> list[str]:
    """Check for missing or potentially stale data. Returns list of warnings."""
    warnings = []

    # Check financials completeness
    fin = ticker_input.financials
    fin_fields = [
        fin.revenue_ttm, fin.net_income_ttm, fin.ebitda_ttm,
        fin.free_cash_flow_ttm, fin.market_cap, fin.pe_ratio,
        fin.revenue_growth_yoy, fin.gross_margin, fin.operating_margin,
    ]
    non_null = sum(1 for f in fin_fields if f is not None)
    if non_null < LOW_DATA_QUALITY_THRESHOLD:
        warnings.append(
            f"Low financial data quality: only {non_null} of {len(fin_fields)} "
            f"key fields populated (minimum: {LOW_DATA_QUALITY_THRESHOLD})"
        )

    # Check price data
    price = ticker_input.price
    if price.current_price is None:
        warnings.append("Missing current price")

    # Check for missing earnings transcript
    if not ticker_input.earnings_transcript_summary:
        warnings.append("No earnings transcript summary provided")

    # Check macro data
    macro = ticker_input.macro
    if not macro.sector:
        warnings.append("Missing sector classification")

    return warnings
