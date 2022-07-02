from types import NoneType
from typing import Optional, TypeAlias, TypeVar, Union
from pydantic import ValidationError, validator, BaseModel, root_validator
from datetime import date, datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CommonShare(BaseModel):
    name: str = "Common Stock"
    par_value: float = 0.001

class PreferredShare(BaseModel):
    name: str
    par_value: float = 0.001

class Option(BaseModel):
    name: str
    strike_price: float
    expiry: datetime
    right: str
    multiplier: float = 100
    issue_date: Optional[datetime] = None

class Warrant(BaseModel):
    name: str
    exercise_price: float
    expiry: datetime
    right: str = "Call" 
    multiplier: float = 1.0
    issue_date: Optional[datetime] = None

class DebtSecurity(BaseModel):
    name: str
    interest_rate: float
    maturity: datetime
    issue_date: Optional[datetime] = None
    

SecurityType: TypeAlias =  Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity, NoneType]

class SecurityTypeFactory:
    '''get the correct Security Type from a string'''
    def __init__(self):
        self.builders = {
            "common": CommonShare,
            "preferred": PreferredShare,
            "option": Option,
            "warrant": Warrant,
            "note": DebtSecurity
        }
        self.keywords = list(self.builders.keys())
        self.fallback = DebtSecurity

    def register_builders(self, keywords: list, security_type: SecurityType):
        for kw in keywords:
            if kw in self.keywords:
                raise AttributeError(f"keyword is already associated with a different Security Type: {kw} associated with {self.builders[kw]}")
            else:
                self.builders[kw] = security_type
                self.keywords.append(kw)
                self.keywords.sort(key=lambda x: len(x))
    
    def get_security_type(self, name: str):
        for kw in self.keywords:
            if kw in name:
                return self.builders[kw]
        return self.fallback

class Security:
    def __init__(self, secu_type: str, secu_attributes: SecurityType, name: str=None, underlying_name: str=None):
        self.name = secu_attributes.name if name is None else name
        self.underlying_name = underlying_name
        self.security_attributes = secu_attributes.json()
    
    def __repr__(self):
        return str(self.security_attributes)

@dataclass
class SecurityOutstanding:
    amount_outstanding: int
    instant: date

@dataclass
class ShelfOffering:
    offering_type: str
    anticipated_offering_amount: float
    commencment_date: datetime
    end_date: datetime
    final_offering_amount_usd: float = None

    
    def __repr__(self):
        return str(self)

class Offering:
    def __init__(self, designation: str):
        self.designation = designation
        self.amounts = list()
    
    def __repr__(self):
        return self.designation

class Company:
    def __init__(self, _name: str, securities: set[SecurityType], offerings: set[Offering]):
        self._name = _name
        self.securities = securities
        self.offerings = offerings
    
    def change_name(self, new_name):
        self._name = new_name
    
    def add_security(self, security_type):
        self.securities.add(SecurityType(security_type=security_type))