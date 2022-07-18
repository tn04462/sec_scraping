from abc import ABC
import logging
from typing import List

from pydantic import ValidationError
from datetime import datetime
import pandas as pd
import re
from spacy.matcher import Matcher
from spacy.tokens import Doc

from main.parser.filings_base import Filing, FilingSection
from main.domain import model,  commands
from main.domain.model import CommonShare, DebtSecurity, PreferredShare, Security, SecurityTypeFactory, Warrant, Option
from main.services.messagebus import Message, MessageBus
from main.services.unit_of_work import AbstractUnitOfWork
from .filing_nlp import SpacyFilingTextSearch

logger = logging.getLogger(__name__)
security_type_factory = SecurityTypeFactory()

class UnhandledClassificationError(Exception):
    pass



class AbstractFilingExtractor(ABC):
    def extract_form_values(self, filing: Filing, bus: MessageBus):
        """extracts values and issues commands.Command to MessageBus"""
        pass


class BaseHTMExtractor():
    def __init__(self):
        self.spacy_text_search = SpacyFilingTextSearch()
    
    def _normalize_SECU(self, security: str):
        return security.lower()
    
    def handle_commands(self, commands: List[commands.Command], bus: MessageBus):
        for command in commands:
            bus.handle(command)
    
    def get_mentioned_secus(self, doc: Doc):
        '''get all SECU entities'''
        secus = dict()
        for ent in doc.ents:
            if ent.label_ == "SECU":
                normalized_ent = self._normalize_SECU(ent.text)
                if normalized_ent in secus.keys():
                    secus[normalized_ent].append(ent)
                else:
                    secus[normalized_ent] = [ent]
        return secus
    
    def get_security_type(self, security_name: str):
        return security_type_factory.get_security_type(security_name)
    
    
    def merge_attributes(self, d1: dict, d2: dict):
        if d1.keys() == d2.keys():
            for d2key in d2.keys():
                try:
                    if (d1[d2key] is None) and (d2[d2key] is not None):
                        d1[d2key] = d2[d2key]
                except KeyError:
                    pass
            return d1 

    def get_security_attributes(self, doc: Doc, security_name: str, security_type: Security):  
        attributes = {}
        _kwargs = {"doc": doc, "security_name": security_name}
        if isinstance(security_type, CommonShare):
            attributes = {
                "name": security_name
                }
        elif isinstance(security_type, PreferredShare):
            attributes = {
                "name": security_name
                }
        elif isinstance(security_type, Warrant):
            attributes = {
                "name": security_name,
                "exercise_price": self.get_secu_exercise_price(**_kwargs),
                "expiry": self.get_secu_interest_rate(**_kwargs),
                "right": self.get_secu_right(**_kwargs),
                "multiplier": self.get_secu_multiplier(**_kwargs),
                "issue_date": self.get_secu_latest_issue_date(**_kwargs)
                }
        elif isinstance(security_type, Option):
            attributes = {
                "name": security_name,
                "strike_price": self.get_secu_exercise_price(**_kwargs),
                "expiry": self.get_secu_interest_rate(**_kwargs),
                "right": self.get_secu_right(**_kwargs),
                "multiplier": self.get_secu_multiplier(**_kwargs),
                "issue_date": self.get_secu_latest_issue_date(**_kwargs)
            }
        elif isinstance(security_type, DebtSecurity):
            attributes = {
                "name": security_name,
                "interest_rate": self.get_secu_interest_rate(**_kwargs),
                "maturity": self.get_secu_expiry(**_kwargs),
                "issue_date": self.get_secu_latest_issue_date(**_kwargs)
            }
        if attributes != {}:
            return attributes
        else:
            return None
            
    def get_secu_exercise_price(self, doc: Doc, security_name: str):
        pass
    
    def get_secu_expiry(self, doc: Doc, security_name: str):
        pass

    def get_secu_multiplier(self, doc: Doc, security_name: str):
        pass

    def get_secu_latest_issue_date(self, doc: Doc, security_name: str):
        pass

    def get_secu_interest_rate(self, doc: Doc, security_name: str):
        pass

    def get_secu_right(self, doc: Doc, security_name: str):
        pass

    def get_secu_conversion(self, doc: Doc, security_name: str):
        pass

    
    
    def get_issuable_relation(self, doc: Doc, security_name: str):
        # make patterns match on base secu explicitly
        # if part1[0] matches assume common stock?
        # then extract relation (and note span of SECU aswell)
        # normalize secu text to lower so we reduce amount of cases
        # write function to create secu from secu_type and optional kwargs
        primary_matches = self.spacy_text_search.match_issuable_secu_primary(doc)
        no_primary_matches = self.spacy_text_search.match_issuable_secu_no_primary(doc)
        #WIP


    # def _handle_issuable_no_primary_secu_match(self, match):
    #     converted_security = CommonShare()
    #     base_secu = 

    # def _handle_issuable_primary_secu_match(self, match):
    
    def doc_from_section(self, section: FilingSection):
        return self.spacy_text_search.nlp(section.text_only)

    def extract_outstanding_shares(self, filing: Filing):
        text = filing.get_text_only()
        if text is None:
            logger.debug(filing)
            return None
        values = self.spacy_text_search.match_outstanding_shares(text)
        return [model.SecurityOutstanding(v["amount"], v["date"]) for v in values]

class HTMS1Extractor(BaseHTMExtractor, AbstractFilingExtractor):
    def extract_form_values(self, filing: Filing):
        return [self.extract_outstanding_shares(filing)]

class HTMS3Extractor(BaseHTMExtractor, AbstractFilingExtractor):
    def extract_form_values(self, filing: Filing, bus: AbstractUnitOfWork):
        form_case = self.classify_s3(filing)
        securities = self.extract_securities(filing)

    
    def extract_securities(self, filing: Filing, uow: AbstractUnitOfWork):
        '''extract securities and their relation and return a modified Company repository.'''
        securities = []
        cover_page = filing.get_section(re.compile("cover page"))
        cover_page_doc = self.doc_from_section(cover_page)
        raw_secus = self.get_mentioned_secus(cover_page_doc)
        description_sections = filing.get_sections(re.compile("description\s*of", re.I))
        description_docs = [self.doc_from_section(x) for x in description_sections]
        for secu, _ in raw_secus.items():
            security_type = self.get_security_type(secu)
            security_attributes = {}
            for doc in description_docs:
                security_attributes = self.merge_attributes(
                    security_attributes,
                    self.get_security_attributes(doc, secu, security_type))
            securities.append({"seucrity_type": security_type, "securitiy_attributes": security_attributes})
        for security in securities:
            for doc in description_docs:
                conversion_attr = self.get_secu_conversion(doc, security.name)
                if conversion_attr:
                    # add conversion attribute to Securities
                    pass # need to write get_secu_conversion first
        return securities

                


            # iter through sections and get attributes then merge attributes
            # stop as soon as attributes have all None values

        # look in descrption of capital stock and cover page
        # 
        #WIP

    def classify_s3(self, filing: Filing):
        cover_page = filing.get_section(re.compile("cover page"))
        distribution = filing.get_section(re.compile("distribution", re.I))
        summary = filing.get_section(re.compile("summary", re.I))
        about = filing.get_section(re.compile("about\s*this"), re.I)
        if cover_page == []:
            raise AttributeError(f"couldnt get the cover page section; sections present: {[s.title for s in filing.sections]}")
        cover_page_doc = self.doc_from_section(cover_page)
        distribution_doc = self.doc_from_section(distribution) if distribution != [] else []
        summary_doc = self.doc_from_section(summary) if summary != [] else []
        about_doc = self.doc_from_section(about) if about != [] else []
        if self._is_resale_prospectus(cover_page_doc):
            return "resale"
        if self._is_at_the_market_prospectus(cover_page_doc) or self._is_at_the_market_prospectus(distribution_doc):
            return "ATM"
        if True in [self._is_shelf_prospectus(x) if x != [] else False for x in [cover_page_doc, about_doc, summary_doc]]:
            return "shelf"
        raise UnhandledClassificationError

    def _is_resale_prospectus(self, doc: Doc) -> bool:
        '''
        determine if this is a resale of securities by anyone other than the registrar,
        by checking for key phrases in the "cover page".'''
        matcher = Matcher(self.spacy_text_search.nlp.vocab)
        # action_verbs = ["sell", "offer", "resell", "disposition"]
        pattern1 = [
            {"LOWER": "prospectus"},
            {"LEMMA": "relate"},
            {"LOWER": "to"},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": "by"},
            {"LOWER": "the"},
            {"LOWER": "selling"},
            {"LOWER": {"IN": ["stockholder", "stockholders"]}}
        ]
        matcher.add("ATM", [pattern1])
        possible_matches = matcher(doc, as_spans=True)
        logger.debug(f"possible matches for _is_resale_prospectus: {[m for m in possible_matches]}")
        if len(possible_matches) > 0:
            return True
        return False


    def _is_at_the_market_prospectus(self, doc: Doc) -> bool:
        '''
        Determine if this is an "at-the-market" offering, rule 415(a)(4) Act 1933,
        by checking for key phrase in the "cover page" and "plan of distribution".
        
        '''
        matcher = Matcher(self.spacy_text_search.nlp.vocab)
        at_the_market_cases = [
            ["at", "-", "the", "-", "market"],
            ["at", "the", "market", "offering"],
            ["at", "the", "market", "offerings"],
            ["at", "the", "market"]
        ]
        pattern1 = [
            [
            {"LEMMA": {"IN": ["sale", "Sale", "sell"]}},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": "under"},
            {"LOWER": "this"},
            {"LOWER": "prospectus"},
            {"OP": "*", "IS_SENT_START": False},
            {"LEMMA": "be"},
            {"LEMMA": "make"},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": "deemed"},
            {"LOWER": "to"},
            {"LOWER": "be"},
            {"IS_PUNCT": True, "IS_SENT_START": False},
            at_the_market_case,
            {"IS_PUNCT": True, "IS_SENT_START": False},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": "as"},
            {"LEMMA": "define"},
            {"LOWER": "in"},
            {"_": {"sec_act": True}, "TEXT": {"REGEX": "415"}}]
            for at_the_market_case in at_the_market_cases
            # need to add label LAW or SECACT for rules from 1933/1934
            # add rule 415 cases then create dicts from at_the-market_case list

        ]
        matcher.add("ATM", [pattern1])
        possible_matches = matcher(doc, as_spans=True)
        logger.debug(f"possible matches for _is_at_the_market_prospectus: {[m for m in possible_matches]}")
        if len(possible_matches) > 0:
            return True
        return False


    def _is_shelf_prospectus(self, doc: Doc) -> bool:
        '''
        Determine if this is a base prospectus
        by checking for key phrases in the "cover page", "about this" or "summary".
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
    def extract_form_values(self, filing: Filing):
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


