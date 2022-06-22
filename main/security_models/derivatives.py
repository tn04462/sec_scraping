from base import Life
from pydantic import BaseModel, validator


class BaseDerivative(BaseModel):
    life: Life
    underlying: str
    strike_price: float
    settlement: str = "cash"
    multiplier: float

    @validator("settlement")
    def _is_physical_or_cash(cls, v):
        if v not in ["physical", "cash"]:
            raise ValueError("settlement: must be either 'physical' or 'cash'")
        return v

class Option(BaseDerivative):
    excercise_type: str = "american"
    right: str

    @validator("right")
    def _is_call_or_put(cls, v):
        if v not in ["call", "put"]:
            raise ValueError("right: must be either 'call' or 'put'")
        return v

    @validator("exercise_type")
    def _is_american_or_european(cls, v):
        if v not in ["american", "european"]:
            raise ValueError("exercise_type: must be either 'american' or 'european'")
        return v

class Warrant(BaseDerivative):
    warrant_type: str = "equity"

    @validator("warrant_type")
    def _validate_warrant_type(cls, v):
        if v not in ["equity", "covered", "basket", "index", "wedding", "detachable", "naked"]:
            raise ValueError("warrant_type: must be one of ['equity', 'covered', 'basket', 'index', 'wedding', 'detachable', 'naked']")
        return v
