
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Filing:
    path: str
    filing_date: str
    accession_number: str
    cik: str
    file_number: str
    form_type: str


@dataclass
class FilingSection:
    title: str
    content: str

@dataclass
class FilingValue:
    cik: str
    date_parsed: datetime
    accession_number: str
    form_type: str
    field_name: str
    field_values: dict
    context: str = None