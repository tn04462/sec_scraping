from abc import ABC
import logging
import spacy
from spacy.matcher import Matcher, DependencyMatcher
from spacy.tokens import Span, Doc
from spacy import Language
from spacy.util import filter_spans
from main.parser.filings_base import Filing, FilingValue
from datetime import datetime
import pandas as pd
import re

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

class HTMS3Extractor(BaseExtractor, AbstractFilingExtractor):
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
    
    



class HTMDEF14AExtractor(BaseHTMExtractor, AbstractFilingExtractor):
    def extract_filing_values(self, filing: Filing):
        return [self.extract_outstanding_shares(filing)]



class SECUMatcher:
    _instance = None
    def __init__(self, vocab):
        self.matcher = Matcher(vocab)
        self.add_SECU_ent_to_matcher()
        self.add_SECUATTR_ent_to_matcher()
    
    def __call__(self, doc):
        self.matcher(doc)
        return doc 
    
    def add_SECUATTR_ent_to_matcher(self):
        patterns = [
            [
                {"LOWER": "exercise"},
                {"LOWER": "price"}
            ]
        ]
        self.matcher.add("SECUATTR_ENT", [*patterns], on_match=_add_SECUATTR_ent)
    

    
    def add_SECU_ent_to_matcher(self):
        # base_securities is just to keep track of the different bases we work with
        base_securities = [
            [{"LOWER": "common"}, {"LOWER": "stock"}], #
            [{"TEXT": "Ordinary"}, {"LOWER": "shares"}], #
            [{"LOWER": "warrants"}], #
            [{"LOWER": "preferred"}], #
            [{"LOWER": "debt"}, {"LOWER": "securities"}], #
            [{"TEXT": "Purchase"}], #
            [{"LOWER": "depository"}, {"LOWER": "shares"}], #
            [{"LOWER": "depositary"}, {"LOWER": "shares"}], #
            [{"LOWER": "subsciption"}, {"LOWER": "rights"}], #

        ]
        

        debt_securities_l1_modifiers = [
            "subordinated",
            "senior"
        ]

        general_pre_sec_modifiers = [
            "convertible",
            "non-convertible"
        ]
        general_affixes = [
            "series",
            "tranche",
            "class"
        ]
        purchase_affixes = [
            "stock",
            "shares"
        ]
        purchase_suffixes = [
            "rights",
            "contracts",
            "units"
        ]


        special_patterns = [
            [{"LOWER": "common"}, {"LOWER": "units"}, {"LOWER": "of"}, {"LOWER": "beneficial"}, {"LOWER": "interest"}],
            [{"TEXT": "Subsciption"}, {"TEXT": "Rights"}],

        ]
        # exclude particles, conjunctions from regex match 
        patterns = [
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "warrant", "warrants", "ordinary"]}},
                {"LOWER": {"IN": ["stock", "shares"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "warrant", "warrants", "ordinary"]}},
                {"LOWER": {"IN": ["stock", "shares"]}}
            ]
                ,
            
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "ordinary"]}, "OP": "?"},
                {"LOWER": {"IN": ["stock"]}},
                {"LOWER": {"IN": ["options", "option"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "ordinary"]}, "OP": "?"},
                {"LOWER": {"IN": ["stock"]}},
                {"LOWER": {"IN": ["options", "option"]}}
            ]

                ,
            
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["warrant", "warrants"]}},
                {"LOWER": {"IN": ["stock", "shares"]}, "OP": "?"}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["warrant", "warrants"]}},
                {"LOWER": {"IN": ["stock", "shares"]}, "OP": "?"}
            ]
                ,

            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": debt_securities_l1_modifiers}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": "debt"}, {"LOWER": "securities"}
            ]
                ,

            [   {"LOWER": {"IN": debt_securities_l1_modifiers}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": "debt"}, {"LOWER": "securities"}
            ]
                ,

            [   {"LOWER": {"IN": purchase_affixes}, "OP": "?"}, {"TEXT": "Purchase"}, {"LOWER": {"IN": purchase_suffixes}}
        ],
            
        ]
        self.matcher.add("SECU_ENT", [*patterns, *special_patterns], on_match=_add_SECU_ent)

def _is_match_followed_by(doc: Doc, start: int, end: int, exclude: list[str]):
    if doc[end].lower not in exclude:
        return False
    return True

def _is_match_preceeded_by(doc: Doc, start: int, end: int, exclude: list[str]):
    if (start == 0) or (exclude == []):
        return False
    if doc[start-1] not in exclude:
        return False
    return True
    
def _add_SECU_ent(matcher, doc: Doc, i, matches):
    _add_ent(doc, i, matches, "SECU", exclude_after=[
            "agreement"
            "agent",
            "indebenture",
            "rights"])

def _add_SECUATTR_ent(matcher, doc: Doc, i, matches):
    _add_ent(doc, i, matches, "SECUATTR")

def _add_ent(doc: Doc, i, matches, ent_label: str, exclude_after: list[str]=[], exclude_before: list[str]=[]):
    '''add a custom entity through an on_match callback.'''
    match_id, start, end = matches[i]
    # print(doc[start:end])
    # print(f"followed_by: {_is_match_followed_by(doc, start, end, exclude_after)}")
    # print(f"preceeded_by: {_is_match_preceeded_by(doc, start, end, exclude_before)}")
    if (not _is_match_followed_by(doc, start, end, exclude_after)) and (
        not _is_match_preceeded_by(doc, start, end, exclude_before)):
        entity = Span(doc, start, end, label=ent_label)
        try:
            doc.ents += (entity,)
        except ValueError as e:
            if "[E1010]" in str(e):
                # logger.debug(f"---NEW ENT--- {entity}")
                previous_ents = set(doc.ents)
                conflicting_ents = []
                for ent in doc.ents:                
                    covered_tokens = range(ent.start, ent.end)
                    if (start in covered_tokens) or (end in covered_tokens):
                        if (ent.end - ent.start) <= (end - start):
                            # logger.debug(covered_tokens)
                            # logger.debug(("ent: ", ent, ent.text, ent.label_, ent.start, ent.end))
                            # logger.debug(("entity which replaces ent: ",entity, entity.text, entity.label_, entity.start, entity.end))
                            conflicting_ents.append((ent.end - ent.start, ent))
                if [end-start > k[0] for k in conflicting_ents] is True:
                    [previous_ents.remove(k[1]) for k in conflicting_ents]
                    previous_ents.append(entity)
                doc.ents = previous_ents
                    
@Language.factory("secu_matcher")
def create_secu_matcher(nlp, name):
    return SECUMatcher(nlp.vocab)

class SpacyFilingTextSearch:
    _instance = None
    # make this a singleton/get it from factory through cls._instance so we can avoid
    # the slow process of adding patterns (if we end up with a few 100)
    def __init__(self):
        # self.dep_matcher = DependencyMatcher(self.nlp.vocab)
        # self._add_excercise_dependency()
        pass


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpacyFilingTextSearch, cls).__new__(cls)
            cls._instance.nlp = spacy.load("en_core_web_lg")
            cls._instance.nlp.add_pipe("secu_matcher")
        return cls._instance


    def match_outstanding_shares(self, text):
        pattern1 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": "CARDINAL"},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["outstanding", "stockoutstanding"]}}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE"}, {"ENT_TYPE": "DATE", "OP": "*"}]
        pattern2 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": "CARDINAL"},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "outstanding"}, {"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"},{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE"}, {"ENT_TYPE": "DATE", "OP": "+"}]
        pattern3 = [{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE"}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "CARDINAL"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["issued", "outstanding"]}}]
        matcher = Matcher(self.nlp.vocab)
        matcher.add("outstanding", [pattern1, pattern2])
        doc = self.nlp(text)
        possible_matches = matcher(doc, as_spans=False)
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
    
    # def _add_excercise_dependency(self):
    #     pattern1 = [
    #         {
    #             "RIGHT_ID": "anchor_issuable",
    #             "RIGHT_ATTRS": {"ORTH": "issuable"}
    #         },
    #         {
    #             "LEFT_ID": "anchor_issuable",
    #             "REL_OP": "<",
    #             "RIGHT_ID": "noun_dep",
    #             "RIGHT_ATTRS": {"POS": "NOUN"}
    #         },
            # {
            #     "LEFT_ID": "noun_dep",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "quant_num",
            #     "RIGHT_ATTRS": {"POS": "NUM"}
            # },
            # {
            #     "LEFT_ID": "anchor_issuable",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "adp",
            #     "RIGHT_ATTRS": {"POS": "ADP"}
            # },
            # {
            #     "LEFT_ID": "adp",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "price",
            #     "RIGHT_ATTRS": {"ORTH": "price"}
            # },
            # {
            #     "LEFT_ID": "price",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "excercise",
            #     "RIGHT_ATTRS": {"ORTH": "exercise"}
            # },
            # {
            #     "LEFT_ID": "price",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "adp_of2",
            #     "RIGHT_ATTRS": {"POS": "ADP", "ORTH": "of"}
            # },
            # {
            #     "LEFT_ID": "adp_of2",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "num",
            #     "RIGHT_ATTRS": {"POS": "NUM"}
            # },
            # {
            #     "LEFT_ID": "num",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "per",
            #     "RIGHT_ATTRS": {"ORTH": "per"}
            # },
            # {
            #     "LEFT_ID": "per",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "noun_dep2",
            #     "RIGHT_ATTRS": {"POS": "NOUN"}
            # }
        # ]
        # pattern2 = [
        #     {
        #         "RIGHT_ID": "anchor_issuable",
        #         "RIGHT_ATTRS": {"ORTH": "issuable"}
        #     },
        #     {
        #         "LEFT_ID": "anchor_issuable",
        #         "REL_OP": "<",
        #         "RIGHT_ID": "adp_of0",
        #         "RIGHT_ATTRS": {"POS": "ADP", "ORTH": "of"}
            # },
            # {
            #     "LEFT_ID": "adp_of0",
            #     "REL_OP": "<",
            #     "RIGHT_ID": "noun_dep",
            #     "RIGHT_ATTRS": {"POS": "NOUN"}
            # },
            # {
            #     "LEFT_ID": "noun_dep",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "quant_num",
            #     "RIGHT_ATTRS": {"POS": "NUM"}
            # },
            # {
            #     "LEFT_ID": "anchor_issuable",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "adp",
            #     "RIGHT_ATTRS": {"POS": "ADP"}
            # },
            # {
            #     "LEFT_ID": "adp",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "price",
            #     "RIGHT_ATTRS": {"ORTH": "price"}
            # },
            # {
            #     "LEFT_ID": "price",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "excercise",
            #     "RIGHT_ATTRS": {"ORTH": "exercise"}
            # },
            # {
            #     "LEFT_ID": "price",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "adp_of2",
            #     "RIGHT_ATTRS": {"POS": "ADP", "ORTH": "of"}
            # },
            # {
            #     "LEFT_ID": "adp_of2",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "num",
            #     "RIGHT_ATTRS": {"POS": "NUM"}
            # },
            # {
            #     "LEFT_ID": "num",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "per",
            #     "RIGHT_ATTRS": {"ORTH": "per"}
            # },
            # {
            #     "LEFT_ID": "per",
            #     "REL_OP": ">",
            #     "RIGHT_ID": "noun_dep2",
            #     "RIGHT_ATTRS": {"POS": "NOUN"}
            # }
        # ]
        # self.dep_matcher.add("EXCERCISE_PRICE", [pattern1, pattern2])
    
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

