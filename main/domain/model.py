from types import NoneType
from typing import Optional, Set, TypeAlias, TypeVar, Union
from typing_extensions import Self
from pydantic import AnyUrl, Json, ValidationError, validator, BaseModel, root_validator
from datetime import date, datetime, timedelta
import logging
from dataclasses import dataclass, fields

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
@dataclass
class Underwriter:
    name: str

@dataclass
class OfferingStatus:
    status_name: str

@dataclass
class SecurityCusip:
    cusip_number: str
    security_name: str

class Security:
    def __init__(self, secu_type: str, secu_attributes: SecurityType, name: str=None, underlying: Optional[Self]=None):
        self.name = secu_attributes.name if name is None else name
        self.security_attributes = secu_attributes.json()
        self.underlying = underlying
    
    def __repr__(self):
        return str(self.security_attributes)

@dataclass
class SecurityConversionAttributes:
    conversion_attributes: Json

'''
Notes:
    build test case to relate source_name to source_id
    in a sibling model class or find alternatives.
'''
@dataclass
class SecurityOutstanding:
    amount: int
    instant: date

@dataclass
class SecurityAuthorized:
    security_type: str
    amount: int
    instant: date

@dataclass
class ShelfSecurityRegistration:
    security: Security
    amount: int
    source_security: Optional[Security] = fields(default=None)

@dataclass
class ShelfSecurityComplete:
    security: Security
    amount: int
    source_security: Optional[Security] = fields(default=None)


@dataclass
class ShelfOffering:
    offering_type: str
    anticipated_offering_amount: float
    commencment_date: datetime
    end_date: datetime
    final_offering_amount_usd: float = 0.0
    underwriters: Set[Underwriter] = fields(default_factory=set)
    registrations: Set[ShelfSecurityRegistration] = fields(default_factory=set)
    completed: Set[ShelfSecurityComplete] = fields(default_factory=set)

    def __repr__(self):
        return f"{self}: offering_type:{self.offering_type};anticipated_amount:{self.anticipated_offering_amount}"

@dataclass
class ShelfRegistration:
    accn: str
    form_type: str
    capacity: int
    filing_date: date
    effect_date: Optional[date] = fields(default=None)
    last_update: Optional[date] = fields(default=None)
    expiry: Optional[date] = fields(default=None)
    total_amount_raised: Optional[int] = fields(default=None)
    total_amount_raised_unit: Optional[str] = fields(default="USD")
    offerings: Set[ShelfOffering] = fields(default_factory=set)

@dataclass
class ResaleSecurityRegistration:
    security: Security
    amount: int
    source_security: Optional[Security] = fields(default=None)

@dataclass
class ResaleSecurityComplete:
    security: Security
    amount: int
    source_security: Optional[Security] = fields(default=None)

@dataclass
class ResaleRegistration:
    accn: str
    form_type: str
    filing_date: date
    effect_date: Optional[date] = fields(default=None)
    last_update: Optional[date] = fields(default=None)
    expiry: Optional[date] = fields(default=None)
    registrations: Set[ResaleSecurityRegistration] = fields(default_fatory=set)
    completed: Set[ResaleSecurityComplete] = fields(default_fatory=set)



@dataclass
class Sic:
    sector: str
    industry: str
    division: str

@dataclass
class FilingParseHistoryEntry:
    accession_number: str
    date_parsed: date

@dataclass
class FilingLink:
    filing_html: AnyUrl
    form_type: str
    filing_date: date
    description_: str
    file_number: str

@dataclass
class CashOperating:
    from_date: date
    to_date: date
    amount: int

@dataclass
class CashFinancing:
    from_date: date
    to_date: date
    amount: int

@dataclass
class CashInvesting:
    from_date: date
    to_date: date
    amount: int

@dataclass
class NetCashAndEquivalents:
    instant: date
    amount: int


class Company:
    def __init__(self, _name: str, securities: set[Security]=None, shelfs: set[ShelfRegistration]=None, resales: set[ResaleRegistration]=None, filing_parse_history: set[FilingParseHistoryEntry]=None):
        self._name = _name
        self.securities = set() if securities is None else securities
        self.shelfs = set() if shelfs is None else shelfs
        self.resales = set() if resales is None else resales
        self.filing_parse_history = set() if filing_parse_history is None else filing_parse_history
        self.filing_links = set()
        self.cash_operating = set()
        self.cash_finacing = set()
        self.cash_investing = set()
        self.net_cash_and_equivalents = set()


    def change_name(self, new_name):
        self._name = new_name
    
    def add_security(self, security_type: SecurityType, name: str, kwargs: dict):
        self.securities.add(security_type(name=name, **kwargs))

# make company an aggregate and do all the work from there ?