from types import NoneType
from typing import Optional, TypeAlias, TypeVar, Union
from pydantic import ValidationError, validator, BaseModel, root_validator
from datetime import datetime, timedelta
import logging

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


class ResetFeature(BaseModel):
    '''resets feature to a certain value if certain conditions are met. eg: conversion price is adjusted if stock price is below x for y days'''
    duration: timedelta 
    min_occurence: float # how many x of min_occurence_frequenzy should evaluate to true of the reset_clause/reset_feature and security_feature during duration 
    min_occurence_frequency: str 
    security: str #  security on which the reset_clause is checked over duration
    security_feature: str # feature of the security to be checked for reset_clause eg: VWAP, close, high, low
    reset_feature: str #  must be a field of the parent eg: conversion_price
    reset_clause: float # percent as float eg: 100% == 1.0
    reset_to: str # value to which the reset_feature is set if the reset_clause is valid over duration in the security_feature
    

class CallFeature(BaseModel):
    '''issuer has option of early redemption if condition are met'''
    duration: timedelta
    min_occurence: float
    min_occurence_frequency: str
    security: str
    security_feature: str
    call_feature: str
    call_clause: float
   
    
class PutFeature(BaseModel):
    '''holder has option of early repayment of all or part'''
    start_date: datetime
    duration: timedelta
    frequency: timedelta
    other_conditions: str


class ContigentConversionFeature(BaseModel):
    duration: timedelta
    min_occurence: float
    min_occurence_frequency: str
    security: str
    security_feature: str
    conversion_feature: str
    conversion_clause: float
    

class ConvertibleFeature(BaseModel):
    conversion_ratio: float
    contigent_conversion_features: list[ContigentConversionFeature] = []
    call_features: list[CallFeature] = []
    put_features: list[PutFeature] = []
    reset_features: list[ResetFeature] = []
    

Security: TypeAlias =  Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity, NoneType]

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
    
    def register_builders(self, keywords: list, security_type: Security):
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


class ConvertibleAttribute(BaseModel):
    base_secu: str
    converted_secu: str
    conversion_ratio: float = 1.0

class SecurityCompletedOffering(BaseModel):
    secu: str
    amount: int
    source_secu: Union[CommonShare, PreferredShare, Option, Warrant, DebtSecurity, NoneType]

class SecurityRegistration(BaseModel):
    secu: str
    amount: int
    unit: str 
    source_secu: str



class Securities:
    def __init__(self):
        self._secus: set[Security] = set()
        self._completed_offerings: set[SecurityCompletedOffering] = set()
        self._registrations: set[SecurityRegistration] = set()
        self._convertible_attr: set[ConvertibleAttribute] = set()
        self._secus_values = dict[Security] = dict() #unused
    
    @property
    def secus(self):
        return self._secus

    def get_secu(self, secu_type, **kwargs):
        secus_found = []
        for s in self._secus.keys():
            if isinstance(s, secu_type):
                for key, value in kwargs.items():
                    if s.get(key) != value:
                        continue
                secus_found.append(s)
        if len(secus_found) > 1:
            raise ValueError(f"found more than one security matching the kwargs: {kwargs}, securities found: {secus_found}")
        elif len(secus_found) == 1:
            return secus_found[0]
        elif secus_found == []:
            return None
    
    def add_secu(self, secu_type: Security, kwargs: dict):
        try:
            security = secu_type(**kwargs)
        except ValidationError as e:
            logger.debug(f"ValidationError in get_security: {e}. passed secu_type: {secu_type}; kwargs: {kwargs}", exc_info=True)
            return None
        self._secus.add(security)
        return security
    
    def _assert_secu_in_secus(self, secu: Security):
        if secu is None:
            raise TypeError("cant add NoneType to _secus")
        if secu not in self._secus:
                self._secus.add(secu)
        
    
    def add_conversion_attribute(self, base_secu: str, converted_secu: str, conversion_ratio: float):
        for s in [base_secu, converted_secu]:
            self._assert_secu_in_secus(s)
        self._convertible_attr.add(
            ConvertibleAttribute(
                base_secu=base_secu,
                converted_secu=converted_secu,
                conversion_ratio=conversion_ratio)
        )
    
    def add_completed_offering(self, secu: str, amount: int, source_secu: str=None):
        self._assert_secu_in_secus(secu)
        if source_secu is not None:
            self._assert_secu_in_secus(source_secu)
        self._completed_offerings.add(
            SecurityCompletedOffering(
                secu=secu,
                amount=amount,
                source_secu=source_secu))
    
    def add_registration(self, secu: str, amount: int, unit: str="shares", source_secu: str=None):
        self._assert_secu_in_secus(secu)
        self._registrations.add(
            SecurityRegistration(
                secu=secu,
                unit=unit,
                amount=amount,
                source_secu=source_secu)
        )
    
    
class FormValues:
    def __init__(self, cik: str, accn: str, form_type: str):
        self.cik = cik
        self.accession_number = accn
        self.form_type: str = form_type
        self._form_case: str = None
        # self._filing_values: list[FilingValue] = list()
        self._securities = Securities()
    
    @property
    def form_case(self):
        return self._form_case
    
    @form_case.setter
    def form_case(self, new_case):
        self._form_case = new_case
    
    @property
    def securities(self):
        return self._securities
    
    def add_secu(self, secu_type, **kwargs):
        return self.securities.add_secu(secu_type=secu_type, **kwargs)
    
    def get_secu(self, secu_type, **kwargs):
        return self.securities.get_secu(secu_type=secu_type, **kwargs)
    
    def add_completed_offering(self, secu: Security, amount: int, source_secu: Security=None):
        return self.securities.add_completed_offering(secu=secu, amount=amount, source_secu=source_secu)
    
    def add_registration(self, secu: Security, amount: int, unit: str="shares", source_secu: Security=None):
        return self.securities.add_registration(secu=secu, amount=amount, source_secu=source_secu)
    
    def add_conversion_attribute(self, base_secu: Security, converted_secu: Security, conversion_ratio: float):
        return self.securities.add_conversion_attribute(base_secu=base_secu, converted_secu=converted_secu, conversion_ratio=conversion_ratio)
    

        

                    


    

 

        

    


if __name__ == "__main__":
    debt_secu = DebtSecurity(interest_rate=0.5, maturity=datetime(2020, 2, 1))