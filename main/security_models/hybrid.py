from datetime import datetime, timedelta
from glob import has_magic
from base import _requires_fields, Life
from pydantic import BaseModel, validator, root_validator
from derivatives import Warrant
from debt import DebtSecurity


class ResetFeature(BaseModel):
    '''resets feature to a certain value if certain conditions are met. eg: conversion price is adjusted if stock price is below x for y days'''
    has_feature: bool = False
    duration: timedelta 
    min_occurence: float # how many x of min_occurence_frequenzy should evaluate to true of the reset_clause/reset_feature and security_feature during duration 
    min_occurence_frequency: str 
    security: str #  security on which the reset_clause is checked over duration
    security_feature: str # feature of the security to be checked for reset_clause eg: VWAP, close, high, low
    reset_feature: str #  must be a field of the parent eg: conversion_price
    reset_clause: float # percent as float eg: 100% == 1.0
    reset_to: str # value to which the reset_feature is set if the reset_clause is valid over duration in the security_feature
    
    _validate_required_feature = root_validator(allow_reuse=True)(
        _requires_fields(
            boolean_feature="has_feature",
            required_if_true=["all"]
        )
    )


class CallFeature(BaseModel):
    '''issuer has option of early redemption if condition are met'''
    has_feature: bool = False
    duration: timedelta
    min_occurence: float
    min_occurence_frequency: str
    security: str
    security_feature: str
    call_feature: str
    call_clause: float

    _validate_required_feature = root_validator(allow_reuse=True)(
        _requires_fields(
            boolean_feature="has_feature",
            required_if_true=["all"]
        )
    )    
    

class PutFeature(BaseModel):
    '''holder has option of early repayment of all or part'''
    has_feature: bool = False
    start_date: datetime
    duration: timedelta
    frequency: timedelta
    other_conditions: str
    
    _validate_required_feature = root_validator(allow_reuse=True)(
        _requires_fields(
            boolean_feature="has_feature",
            required_if_true=["all"]
        )
    )


class ContigentConversionFeature(BaseModel):
    has_feature: bool = False
    duration: timedelta
    min_occurence: float
    min_occurence_frequency: str
    security: str
    security_feature: str
    conversion_feature: str
    conversion_clause: float
    
    _validate_required_feature = root_validator(allow_reuse=True)(
        _requires_fields(
            boolean_feature="has_feature",
            required_if_true=["all"]
        )
    )


class ConvertibleFeature(BaseModel):
    pass
    
