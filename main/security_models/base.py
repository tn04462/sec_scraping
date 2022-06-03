from pydantic import validator, BaseModel, root_validator
from datetime import datetime
from typing import Callable

def _validate_datetime(cls, v):
    if isinstance(v, datetime):
        return v.isoformat()


def _requires_fields(boolean_field: str, required_if_true: list[str]):
    def _get_and_check_switch_values(cls, values):
        switch = values.get(boolean_field)
        if switch is True:
            assert [values.get(k) is not None for k in required_if_true] is True
            return values
        if switch is False:
            keys_to_check = list(values.keys()).remove(boolean_field)
            if keys_to_check is None:
                return values
            else:
                assert [values.get(k) is None for k in keys_to_check] is True
                return values
    return _get_and_check_switch_values

class Life(BaseModel):
    has_maturity: bool = False
    maturity_date: datetime = None

    _validate_maturity = validator("maturity_date", allow_reuse=True)(_validate_datetime)

    # _maturity_requires_field = root_validator(allow_reuse=True)(
    #     _requires_fields(
    #         boolean_field="has_maturity",
    #         required_if_true=["maturity_date"]
    #     )
    # )


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
            
