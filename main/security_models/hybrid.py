from datetime import timedelta
from base import Life
from pydantic import BaseModel, validator
from derivatives import Warrant
from debt import DebtSecurity

class ResetFeature(BaseModel):
    duration: timedelta
    min_occurence: float # how many x of min_occurence_frequenzy should evaluate to true of the reset_clause/reset_feature and security_feature during duration 
    min_occurence_frequenzy: str
    security: str #  security on which the reset_clause is checked over duration
    security_feature: str # feature of the security to be checked for reset_clause eg: VWAP, close, high, low
    reset_feature: str #  must be a field of the parent eg: conversion_price
    reset_clause: float # percent as float eg: 100% == 1.0
    reset_to: str # value to which the reset_feature is set if the reset_clause is valid over duration in the security_feature

class CallFeature(BaseModel):
