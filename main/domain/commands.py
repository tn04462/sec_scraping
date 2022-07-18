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
class SecuritiesOutstanding(CompanyCommand):
    outstanding: list[model.SecurityOutstanding]

sec = SecuritiesOutstanding("891219229", [model.SecurityOutstanding(1999, datetime.date(2022, 1, 1))])