from abc import ABC
import logging
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Span
from spacy import language
from main.parser.filings_base import Filing, FilingValue
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class AbstractFilingExtractor(ABC):
    def extract_filing_values(self, filing: Filing):
        """extracts values and returns them as a list[FilingValue] where dict has
        keys: cik, date_parsed, accession_number, field_name, field_values"""
        pass

class BaseExtractor():
    def create_filing_value(self, filing: Filing, date_parsed: datetime, field_name: str, field_values: dict, context:str=None):
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
                    filing_values.append(self.create_filing_value(filing, date_parsed, field_name=k, field_values=v, context=values_list["context"]  if "context" in value.keys() else None))
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

class HTMDEF14AExtractor(BaseHTMExtractor, AbstractFilingExtractor):
    def extract_filing_values(self, filing: Filing):
        return [self.extract_outstanding_shares(filing)]



class SECUMatcher:
    _instance = None
    def __init__(self, vocab):
        self.matcher = Matcher(vocab)
        self.add_SECU_ent_to_matcher()
    
    def __call__(self, doc):
        self.matcher(doc)
        
    
    def add_SECU_ent_to_matcher(self):
        exclude = [
            "Agreement",
            "Agent",
            "indebenture"
            ]
        warrant_exclude = [
            "Shares",

        ]

        preferred_modifiers = [
            "Series",
        ]
        warrant_modifiers = [
            "Series",
            "Tranche"
        ]
        patterns = [
            # [{"LOWER": {"IN": preferred_modifiers}, "OP": "?"}, {"TEXT": {"REGEX": "[a-z0-9]{1,3}"}, "OP": "?"},{"LOWER": "preferred"}, {"LOWER": "stock"}],
            [{"LOWER": "common"}, {"LOWER": "stock"}],
            # [{"LOWER": "senior"}, {"LOWER": "debt"}, {"LOWER": "securities"}],
            # [{"LOWER": "subordinated"}, {"LOWER": "debt"}, {"LOWER": "securities"}],
            # [{"LOWER": "debt"}, {"LOWER": "securities"}, {"LOWER": {"NOT_IN": exclude}}],
            # [{"LOWER": {"IN": ["warrant", "warrants"]}}, {"LOWER": {"NOT_IN": exclude}}]
        ]
        self.matcher.add("SECU_ENT", patterns, on_match=_add_SECU_ent)
    
def _add_SECU_ent(matcher, doc, i, matches):
    # Get the current match and create tuple of entity label, start and end.
    # Append entity to the doc's entity. (Don't overwrite doc.ents!)
    match_id, start, end = matches[i]
    entity = Span(doc, start, end, label="SECU")
    doc.ents += (entity,)
    print(entity.text)

@language.factory("secu_matcher")
def create_secu_matcher(self, nlp, name):
    return SECUMatcher(nlp.vocab)

class SpacyFilingTextSearch:
    _instance = None
    # make this a singleton/get it from factory through cls._instance so we can avoid
    # the slow process of adding patterns (if we end up with a few 100)
    def __init__(self):
        pass


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpacyFilingTextSearch, cls).__new__(cls)
            cls._instance.nlp = spacy.load("en_core_web_sm")
            cls._instance.nlp.add_pipe("secu_matcher")
        return cls._instance


    def match_outstanding_shares(self, text):
        pattern1 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": "CARDINAL"},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["outstanding", "stockoutstanding"]}}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE"}, {"ENT_TYPE": "DATE", "OP": "*"}]
        pattern2 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": "CARDINAL"},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "outstanding"}, {"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"},{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE"}, {"ENT_TYPE": "DATE", "OP": "+"}]
        pattern3 = [{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE"}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "CARDINAL"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["issued", "outstanding"]}}]
        self.matcher.add("outstanding", [pattern1, pattern2])
        doc = self.nlp(text)
        possible_matches = self.matcher(doc, as_spans=False)
        if possible_matches == []:
            logger.debug("no matches for outstanding shares found")
            return []
        matches = self._convert_matches_to_spans(doc, self._take_longest_matches(possible_matches))
        values = []
        for match in matches:
            value = {"outstanding_shares": {}}
            for ent in match.ents:
                print(ent, ent.label_)
                if ent.label_ == "CARDINAL":
                    value["outstanding_shares"]["amount"] = int(str(ent).replace(",", ""))
                if ent.label_ == "DATE":
                    value["outstanding_shares"]["date"] = pd.to_datetime(str(ent))
            try:
                validate_filing_values(value, "outstanding_shares", ["date", "amount"])
            except AttributeError:
                pass
            else:
                values.append(value)
        return values
    
    def _take_longest_matches(self, matches):
            entries = []
            prev_m = None
            current_longest = None
            for m in matches:
                if prev_m is None:
                    prev_m = m
                    current_longest = m
                    continue
                if prev_m[1] == m[1]:
                    if prev_m[2] < m[2]:
                        current_longest = m
                else:
                    entries.append(current_longest)
                    current_longest = m
                    prev_m = m
                    continue
            if current_longest not in entries:
                entries.append(current_longest)
            return entries

    def _convert_matches_to_spans(self, doc, matches):
        m = []
        for match in matches:
            m.append(doc[match[1]:match[2]])
        return m

def validate_filing_values(values, field_name, attributes):
    '''validate a flat filing value'''
    if field_name not in values.keys():
        raise AttributeError
    for attr in attributes:
        if attr not in values[field_name].keys():
            raise AttributeError


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
spacy_text_search = SpacyFilingTextSearch()

