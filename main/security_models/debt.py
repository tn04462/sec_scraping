from pydantic import BaseModel, root_validator, validator
from base import Life, ParValue, VotingRight, CashFlowRight, RedemptionRight, DividendRight, _requires_fields
from datetime import timedelta, datetime

class BondProvision(BaseModel):
    has_provision: bool = True
    start_date: datetime
    end_date: datetime
    right: str #call or put
    price: float

    _provision_requires_field = root_validator(allow_reuse=True)(
        _requires_fields(
            "has_provision",
            ["start_date", "end_date", "right", "price"]
        )
    )


class InterestRate(BaseModel):
    has_interest_rate: bool = True
    base_payout_rate: float
    floating_payout_base: str
    payout_frequenzy: timedelta

    _provision_requires_field = root_validator(allow_reuse=True)(
        _requires_fields(
            "has_interest_rate",
            ["base_payout_rate", "payout_frequenzy"]
        )
    )
    
    
class DebtSecurity(BaseModel):
    life: Life
    interest_rate: InterestRate
    redemption_right: RedemptionRight
    provision: BondProvision = BondProvision(has_provision=False, provision_start=None, provision_end=None, right=None, price=None)
    voting_right: VotingRight = VotingRight(voting_ratio=None, has_voting_rights=False)
    cash_flow_right: CashFlowRight = CashFlowRight(has_cash_flow_right=True)
    dividend_right: DividendRight = DividendRight(has_dividend_right=False, has_cumulative_right=False)



