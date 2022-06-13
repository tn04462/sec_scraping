from abc import ABC
import logging
from main.parser.filings_base import Filing, FilingValue
from datetime import datetime
import pandas as pd
import re
from spacy.matcher import Matcher
from .filing_nlp import SpacyFilingTextSearch

logger = logging.getLogger(__name__)


class AbstractFilingExtractor(ABC):
    def extract_filing_values(self, filing: Filing):
        """extracts values and returns them as a list[FilingValue] where dict has
        keys: cik, date_parsed, accession_number, field_name, field_values"""
        pass

class BaseExtractor():
    def create_filing_value(self, filing: Filing, field_name: str, field_values: dict, context:str=None, date_parsed: datetime=datetime.now()):
        '''create a FilingValue'''
        return FilingValue(
            cik=filing.cik,
            date_parsed=date_parsed,
            accession_number=filing.accession_number,
            form_type=filing.form_type,
            field_name=field_name,
            field_values=field_values,
            context=context
        )
    
    def create_filing_values(self, values_list: list[dict], filing: Filing, date_parsed: datetime=datetime.utcnow()):
        '''
        create a list of FilingValues from a values_list
        
        Args:
            values_list: list[dict] with dict of form: 
                        {field_name: {field_values}, "context": additional 
                        context for uploader or None}
            filing: instance of Filing or a sublcass thereof
            date_parsed: when the parsing happend, defaults to datetime.utcnow()
        
        Returns:
            list[FilingValue] or None
        '''
        if values_list == []:
            return None
        filing_values = []
        for value in values_list:
            for k, v in value.items():
                if k != "context":
                    filing_values.append(self.create_filing_value(filing, field_name=k, field_values=v, context=values_list["context"]  if "context" in value.keys() else None))
        return filing_values


class BaseHTMExtractor(BaseExtractor):
    def __init__(self):
        self.spacy_text_search = SpacyFilingTextSearch()

    def extract_outstanding_shares(self, filing: Filing):
        text = filing.get_text_only()
        if text is None:
            logger.debug(filing)
            return None
        values = self.spacy_text_search.match_outstanding_shares(text)
        return self.create_filing_values(values, filing)

class HTMS1Extractor(BaseHTMExtractor, AbstractFilingExtractor):
    def extract_filing_values(self, filing: Filing):
        return [self.extract_outstanding_shares(filing)]

class HTMS3Extractor(BaseHTMExtractor, AbstractFilingExtractor):


    # def classify_s3(self, filing: Filing):
    #     text = ""
    #     cover_page = filing.get_section(re.compile("cover page"))
    #     if isinstance(cover_page, list):
    #         raise AttributeError(f"couldnt get the cover page section; sections present: {[s.title for s in filing.sections]}")

    def _is_base_prospectus(self, doc): # import Doc from spacy for Type
        '''
        look for key phrases in the cover page to determine if this is a base prospectus.
        '''
        matcher = Matcher(self.spacy_text_search.nlp.vocab)
        pattern1 = [
            {"IS_SENT_START": True},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": "not"},
            {"LEMMA": "be"},
            {"LEMMA": "use"},
            {"ORTH": "to"},
            {"LEMMA": {"IN": ["offer", "consummate", "sell"]}},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": {"IN": ["any", "these"]}},
            {"LOWER": {"IN": ["securities", "security"]}},
            {"LOWER": "unless"},
            {"OP": "*", "IS_SENT_START": False},
            {"LEMMA": "accompany"},
            {"OP": "*", "IS_SENT_START": False},
            {"ORTH": "by"},
            {"ORTH": "a"},
            {"OP": "?", "IS_SENT_START": False},
            {"ORTH": {"IN": ["supplement", "supplements"]}}
            ]
        pattern2 = [
            {"LOWER": "each"},
            {"LOWER": "time"},
            {"OP": "?", "IS_SENT_START": False},
            {"LEMMA": {"IN": ["sell", "offer"]}},
            {"LOWER": {"IN": ["securities", "security"]}},
            {"OP": "*", "IS_SENT_START": False},
            {"LEMMA": "provide"},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": {"IN": ["supplement", "supplements"]}}
        ]
        pattern3 = [
            {"LOWER": "each"},
            {"LOWER": "time"},
            {"OP": "?", "IS_SENT_START": False},
            {"LOWER": {"IN": ["securities", "security"]}},
            {"LEMMA": "be"},
            {"LEMMA": {"IN": ["sell", "offer"]}},
            {"OP": "*", "IS_SENT_START": False},
            {"LEMMA": "provide"},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": {"IN": ["supplement", "supplements"]}}
        ]
        matcher.add("base_prospectus", [pattern1, pattern2, pattern3])
        possible_matches = matcher(doc, as_spans=True)
        logger.debug(f"possible matches for _is_base_prospectus: {[m for m in possible_matches]}")
        if len(possible_matches) > 0:
            return True
        return False

    def extract_shelf_capacity(self, filing: Filing):
        fp = filing.get_section("front page")
        if isinstance(fp, list):
            raise AttributeError(f"couldnt get the front page section; sections present: {[s.title for s in filing.sections]}")
        registration_table  = fp.get_tables(classification="registration_table", table_type="extracted")
        if registration_table is not None:
            if len(registration_table) == 1:
                registration_table = registration_table[0]["parsed_table"]
                print(registration_table)
                try:
                    if re.search(re.compile("^total.*", re.I | re.MULTILINE), registration_table[-1][0]):
                        registration_table[-1][0] = "total"
                except IndexError:
                    pass
                registration_df = pd.DataFrame(registration_table[1:], columns=["Title", "Amount", "Price Per Unit", "Price Aggregate", "Fee"])
                values = []
                print(registration_df)
                row = None
                if "total" in registration_df["Title"].values:
                    row = registration_df[registration_df["Title"] == "total"]
                elif len(registration_df["Title"].values) == 1:
                    row = registration_df.iloc[0]
                if row is None:
                    raise ValueError(f"couldnt determine correct row while extracting from registration table: {registration_df}")
                if row["Amount"].item() != "":
                    values.append({"total_shelf_capacity": {"amount": row["Amount"].item(), "unit": "shares"}})
                elif row["Price Aggregate"].item() != "":
                    values.append({"total_shelf_capacity": {"amount": row['Price Aggregate'].item(), "unit": "$"}})
                return self.create_filing_values(values, filing)
        return None
    
    



class HTMDEF14AExtractor(BaseHTMExtractor, AbstractFilingExtractor):
    def extract_filing_values(self, filing: Filing):
        return [self.extract_outstanding_shares(filing)]





class ExtractorFactory:
    def __init__(self, defaults: list[tuple]=[]):
        self.extractors = {}
        if len(defaults) > 0:
            for case in defaults:
                self.register_extractor(*case)

    def register_extractor(
        self, form_type: str, extension: str, extractor: AbstractFilingExtractor
    ):
        self.extractors[(form_type, extension)] = extractor

    def get_extractor(self, form_type: str, extension: str, **kwargs):
        extractor = self.extractors.get((form_type, extension))
        if extractor:
            return extractor(**kwargs)
        else:
            raise ValueError(
                f"no extractor for that form_type and extension combination({form_type}, {extension}) registered"
            )

extractor_factory_default = [
    ("S-1", ".htm", HTMS1Extractor),
    ("DEF 14A", ".htm", HTMDEF14AExtractor)
    # (None, ".htm", BaseHTMExtractor)
    ]

extractor_factory = ExtractorFactory(defaults=extractor_factory_default)


