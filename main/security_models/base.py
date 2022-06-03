from pydantic import validator, BaseModel, root_validator
from datetime import datetime
from typing import Callable


def _requires_fields(boolean_field: str, required_if_true: list[str]):
    def _get_and_check_switch_values(cls, values):
        switch = values.get(boolean_field)
        if switch is True:
            assert [values.get(k) is not None for k in required_if_true]
        if switch is False:
            assert [values.get(k) is None for k in list(values.keys()).remove(boolean_field)]
    return _get_and_check_switch_values

class Life(BaseModel):
    has_maturity: bool = False
    maturity_date: datetime = None

    _maturity_requires_field = root_validator(allow_reuse=True)(
        _requires_fields(
            "has_maturity",
            ["maturity_date"]
        )
    )


class ParValue(BaseModel):
    par_value: float = 0.001
    currency: str = "USD"

class VotingRight(BaseModel):
    voting_ratio: float = 1.0  #voting ratio in common shares
    has_voting_rights: bool = True
    

class CashFlowRight(BaseModel):
    has_cash_flow_right: bool = True

class DividendRight(BaseModel):
    has_dividend_rights: bool = True
    has_cumulative_rights: bool = False

class RedemptionRight(BaseModel):
    has_redemption_right: bool = False
    start_date: datetime = None
    end_date: datetime = None
    start_price: float = None
    end_price: float = None
    price_slope_description: str = None

    _redemption_requires_fields = root_validator(allow_reuse=True)(
        _requires_fields(
            "has_redemption",
            ["start_date", "end_date", "start_price", "end_price"]))
            
