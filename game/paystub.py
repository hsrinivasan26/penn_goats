"""Phase 1: Income -- the gross->net paystub, the game's signature teaching moment."""

from .formulas import paystub


def phase_income(state) -> dict:
    """Add this month's net pay to cash, track year-to-date totals, return the paystub for display."""
    if not state.employed:
        state._paystub = paystub(0)
        return state._paystub
    stub = paystub(state.gross_month)
    state.cash += stub["net"]
    state.withheld_income_tax_ytd += stub["federal"] + stub["state"]
    state.annual_gross_ytd += stub["gross"]
    state._paystub = stub
    return stub
