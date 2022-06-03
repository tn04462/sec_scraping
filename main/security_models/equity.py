from types import NoneType
from typing import Callable
from pydantic import BaseModel
from datetime import datetime

from base import Life, ParValue, VotingRight, CashFlowRight, RedemptionRight


class CommonShares(BaseModel):
    life: Life = Life(has_maturity=False, maturity_date=None)
    par_value: ParValue = ParValue()
    voting_right: VotingRight = VotingRight(has_voting_rights=True, voting_ratio=1.0)
    cash_flow_right: CashFlowRight = CashFlowRight(has_cash_flow_rights=True, has_cumulative_rights=False)

class PreferredShares(BaseModel):
    voting_right: VotingRight
    cash_flow_right: CashFlowRight
    redemption_right: RedemptionRight
    life: Life = Life(has_maturity=False, maturity_date=None)
    par_value: ParValue = ParValue()
    
if __name__ == "__main__":
    # life = Life()
    cs = CommonShares()
    print(cs.json())