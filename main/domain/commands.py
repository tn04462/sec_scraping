from datetime import date
from typing import Optional
from dataclasses import dataclass


class Command:
    pass

@dataclass
class SecurityOutstanding(Command):
    