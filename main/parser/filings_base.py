
from dataclasses import dataclass
from datetime import datetime
from os import PathLike
from pathlib import Path

@dataclass
class Filing:
    path: str
    filing_date: str
    accession_number: str
    cik: str
    file_number: str
    form_type: str
    extension: str = None

    def __post_init__(self):
        if self.extension is None:
            self.extension = self._get_extension(self.path)

    def _get_extension(self, path):
        string_path = ""
        if isinstance(path, PathLike):
            string_path = str(path)
            self.extension = Path(string_path).suffix
        elif isinstance(path, str):
            self.extension = Path(path).suffix
        else:
            raise TypeError(f"couldnt get extension from given path. expecting pathlib.Path or str, got: {type(self.path)}")



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