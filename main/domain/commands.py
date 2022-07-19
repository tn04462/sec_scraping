from datetime import date
from typing import Optional
from dataclasses import dataclass
import datetime

import model



class Command:
    pass

@dataclass
class CompanyCommand(Command):
    cik: str

@dataclass
class SecuritiesCommand(CompanyCommand):
    name: str

@dataclass
class AddCompany(Command):
    company: model.Company

@dataclass
class AddOutstanding(SecuritiesCommand):
    outstanding: list[model.SecurityOutstanding]

@dataclass
class AddSecurities(CompanyCommand):
    securities: list[model.Security]

# this commmand and others like it should be events instead eg: AddedShelfRegistration 
# @dataclass
# class AddShelfRegistration(CompanyCommand):



