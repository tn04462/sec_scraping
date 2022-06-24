from typing import Union
from pydantic import validator, BaseModel, root_validator
from datetime import datetime, timedelta


# implement an __eq__ for each security

# class Security(BaseModel):
#     name: str

class CommonShare(BaseModel):
    name: str
    par_value: float = 0.001

class PreferredShare(BaseModel):
    name: str
    par_value: float = 0.001

class Option(BaseModel):
    name: str
    right: str
    strike_price: float
    issue_date: datetime
    lifetime: timedelta
    multiplier: float = 100

class Warrant(BaseModel):
    name: str
    exercise_price: float
    issue_date: datetime = ...
    right: str = "Call"
    lifetime: timedelta = timedelta(days=1825)
    multiplier: float = 1.0

class DebtSecurity(BaseModel):
    name: str
    interest_rate: float
    issue_date: datetime = ...
    lifetime: timedelta = ...

class ConvertibleAttribute(BaseModel):
    base_secu: Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity]
    converted_secu: Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity]
    conversion_ratio: float = 1.0

class SecurityCompletedOffering(BaseModel):
    secu: Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity]
    amount: int
    source_secu: Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity]

class SecurityRegistration(BaseModel):
    secu: Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity]
    unit: str 
    amount: int
    conversion_attribute: ConvertibleAttribute = ...

class FormValues:
    def __init__(self):
        self._secus: set[Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity]] = set()
        self._conversion_attributes = set()
        self._registrations = set()
        self._completed_offerings = set()
        self._filing_values = list()

        

    


if __name__ == "__main__":
    debt_secu = DebtSecurity(name="debt_secu", interest_rate=0.5, issue_date=datetime(2020, 2, 1), lifetime=timedelta(days=1825))
