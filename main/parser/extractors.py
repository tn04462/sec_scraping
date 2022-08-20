from abc import ABC
from functools import reduce
import logging
from types import NotImplementedType
from typing import Dict, List, Optional

from pydantic import ValidationError
from datetime import datetime, timedelta
import pandas as pd
import re
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Span, Token

from main.parser.filings_base import Filing, FilingSection
from main.domain import model,  commands
from main.domain.model import CommonShare, DebtSecurity, PreferredShare, Security, SecurityTypeFactory, Warrant, Option
from main.services.messagebus import Message, MessageBus
from main.services.unit_of_work import AbstractUnitOfWork
from .filing_nlp import SpacyFilingTextSearch, MatchFormater, get_secu_key

logger = logging.getLogger(__name__)
security_type_factory = SecurityTypeFactory()

class UnhandledClassificationError(Exception):
    pass

class UnclearInformationExtraction(Exception):
    pass



class AbstractFilingExtractor(ABC):
    def extract_form_values(self, filing: Filing, bus: MessageBus):
        """extracts values and issues commands.Command to MessageBus"""
        pass


class BaseHTMExtractor():
    # maybe add get_doc(text_search) to FilingSection with a doc instance variable, so i dont make a doc more than once during extraction? 
    def __init__(self):
        self.spacy_text_search = SpacyFilingTextSearch()
        self.formater = MatchFormater()
    
    def get_secu_key(self, security: Span|str):
        if isinstance(security, str):
            doc = self.spacy_text_search.nlp(security)
            security = doc[0:]
        if isinstance(security, Span):
            return get_secu_key(security)
        else:
            raise TypeError(f"BaseHTMExtractor.get_secu_key is expecting type:Span got:{type(security)}")
    
    def get_mentioned_secus(self, doc: Doc, secus: Optional[Dict]=None):
        if secus is None:
            secus = dict()
        single_secu_alias_tuples = doc._.single_secu_alias_tuples
        for key in single_secu_alias_tuples.keys():
            if key not in secus.keys():
                secus[key] = []
            secus[key] += single_secu_alias_tuples[key]["no_alias"]
            for alias in single_secu_alias_tuples[key]["alias"]:
                alias_span = alias[1]
                alias_key = get_secu_key(alias_span)
                if alias_key:
                    if alias_key not in secus.keys():
                        secus[alias_key] = []
                    similar_spans = self.spacy_text_search.get_queryable_similar_spans_from_lower(doc, alias_span)
                    if similar_spans:
                        secus[alias_key] += similar_spans
        return secus
    
    # def get_mentioned_secus(self, doc: Doc, secus:Optional[Dict]=None):
    #     '''get all SECU entities. 
        
    #     Returns:
    #         {secu_name: [spacy entities]}
    #     '''
    #     if secus is None:
    #         secus = dict()
    #     for key in doc._.single_secu_alias.keys():
    #         print(f"get_mentioned_secus working on key. {key}")
    #         if key not in secus.keys():
    #             secus[key] = doc._.single_secu_alias[key]
    #         else:
    #             secus[key]["base"] += doc._.single_secu_alias[key]["base"]
    #             secus[key]["alias"] += doc._.single_secu_alias[key]["alias"]
    #     return secus
    
    def get_security_type(self, security_name: str):
        return security_type_factory.get_security_type(security_name)
    
    def merge_attributes(self, d1: dict, d2: dict):
        print(d1, d2)
        if (d2 is None) or (d2 == {}):
            return d1
        for d2key in d2.keys():
            try:
                if (d1[d2key] is None) and (d2[d2key] is not None):
                    d1[d2key] = d2[d2key]
            except KeyError:
                d1[d2key] = d2[d2key]
        return d1 

    def get_security_attributes(self, doc: Doc, security_name: str, security_type: Security, security_spans):  
        attributes = {}
        _kwargs = {"doc": doc, "security_name": security_name, "security_spans": security_spans}
        if security_type == CommonShare:
            attributes = {
                "name": security_name
                }
        elif security_type == PreferredShare:
            attributes = {
                "name": security_name
                }
        elif security_type == Warrant:
            attributes = {
                "name": security_name,
                "exercise_price": self.get_secu_exercise_price(**_kwargs),
                "expiry": self.get_secu_expiry(**_kwargs),
                "right": self.get_secu_right(**_kwargs),
                "multiplier": self.get_secu_multiplier(**_kwargs),
                "issue_date": self.get_secu_latest_issue_date(**_kwargs)
                }
        elif security_type == Option:
            attributes = {
                "name": security_name,
                "strike_price": self.get_secu_exercise_price(**_kwargs),
                "expiry": self.get_secu_expiry(**_kwargs),
                "right": self.get_secu_right(**_kwargs),
                "multiplier": self.get_secu_multiplier(**_kwargs),
                "issue_date": self.get_secu_latest_issue_date(**_kwargs)
            }
        elif security_type == DebtSecurity:
            attributes = {
                "name": security_name,
                "interest_rate": self.get_secu_interest_rate(**_kwargs),
                "maturity": self.get_secu_expiry(**_kwargs),
                "issue_date": self.get_secu_latest_issue_date(**_kwargs)
            }
        logger.info(f"attributes: {attributes} of security: {security_name} with type: {security_type}")
        return attributes
    
    def get_securities_from_docs(self, docs: List[Doc]) -> List[model.Security]:
        securities = []
        mentioned_secus = {}
        for doc in docs:
            mentioned_secus = self.get_mentioned_secus(doc, mentioned_secus)
        logger.debug(f"finished collecting mentioned_secus: {mentioned_secus}")
        for secu, secu_spans in mentioned_secus.items():
            security_type = self.get_security_type(secu)
            logger.debug(f"getting security_attributes for {secu} with type: {security_type}")
            security_attributes = {}
            for doc in docs:
                security_attributes = self.merge_attributes(
                    security_attributes,
                    self.get_security_attributes(doc, secu, security_type, secu_spans))
            try:
                security = model.Security(security_type(**security_attributes))
            except ValidationError:
                logger.debug(f"Failed to construct model.Security from args: security_type={security_type}, security_attributes={security_attributes}")
            else:
                securities.append(security)
        return securities

    def get_queryable_secu_spans_from_key(self, doc: Doc, security_key: str):
        # POSSIBLE WASTE CODE
        # print("security_key when getting queryable_secu_spans: ", security_key)
        single_secu_alias = doc._.single_secu_alias.get(security_key)
        # print(f"working with single_secu_alias map: {doc._.single_secu_alias}")
        # print(f"got single_secu_alias: {single_secu_alias}")
        if single_secu_alias:
            base = single_secu_alias.get("base")
            alias = single_secu_alias.get("alias")
            return base + alias
            # need to think how i handle bases that arent unique -> only return alias? or only search until we encounter next sentence containing a base span?
            # maybe apply a flag when creating the alias map
        return None
        # now build queries which take the span as arg to search for features

    def get_secu_exercise_price(self, doc: Doc, security_name: str, security_spans: List[Span]):
        exercise_prices_seen = set()
        exercise_prices = []
        logger.debug("get_secu_exercise_price:")
        logger.debug(f" getting exercise_price for:")
        logger.debug(f"     security_name  - {security_name}")
        logger.debug(f"     security_spans - {security_spans}")
        for secu in security_spans:
            for sent in doc.sents:
                if self._is_span_in_sent(sent, secu):
                    temp_doc = doc[sent.start:sent.end]
                    exercies_price = self.spacy_text_search.match_secu_exercise_price(temp_doc, secu)
                    if exercies_price:
                        for price in exercies_price:
                            if price not in exercise_prices_seen:
                                exercise_prices_seen.add(price)
                                exercise_prices.append(price)
                                logger.debug(f"     exercise price found: {price}")
                                logger.debug(f"     sentence: {temp_doc}")
        return exercise_prices
    
    def _is_span_in_sent(self, sent: Span, span: Span|Token):
        token_idx_offset = sent[0].i
        if isinstance(span, Span):
            span_length = len(span)
            first_token = span[0]
            for token in sent:
                if token == first_token:
                    first_idx = token.i - token_idx_offset
                    # logger.info(f"sent: {sent}")
                    # logger.info(f"first_idx|end_idx: {first_idx, first_idx+span_length}")
                    # logger.info(f"is this valid_span?: {sent[first_idx:first_idx+span_length]}")
                    try:
                        if sent[first_idx:first_idx+span_length] == span:
                            if self._span_neighbors_arent_SECU(sent, span):
                                # logger.info("valid span")
                                return True
                    except IndexError:
                        logger.debug("excepted IndexError in _assert_any_secu_span_is_in_match; passing.")
                        pass
        if isinstance(span, Token):
            if self._is_single_token_SECU_in_sent(sent, span):
                return True
        return False
                
    
    def _is_single_token_SECU_in_sent(self, sent: Span, token: Token):
        if token in sent:
            if self._span_neighbors_arent_SECU(sent, token):
                return True
        return False
    
    def _span_neighbors_arent_SECU(self, sent: Span, span: Span|Token):
        token_idx_offset = sent[0].i
        if isinstance(span, Token):
            start = span.i
            end = start
        else:
            start = span[0].i
            end = span[-1].i
        start = start - token_idx_offset
        end = end - token_idx_offset
        if start != 0 and end != sent[-1].i:
            if sent[start-1].ent_type_ != "SECU" and sent[end+1].ent_type_ != "SECU":
                return True
        else:
            if start != 0:
                if sent[start-1].ent_type_ != "SECU":
                    return True
            else:
                if sent[end+1].ent_type_ != "SECU":
                    return True
        return False
    
    def get_secu_expiry(self, doc: Doc, security_name: str, security_spans: List[Span]):
        expiries_seen = set()
        expiries = []
        logger.debug("get_secu_expiry:")
        logger.debug(f" getting expiry for:")
        logger.debug(f"     security_name  - {security_name}")
        logger.debug(f"     security_spans - {security_spans}")
        for secu in security_spans:
            for sent in doc.sents:
                if self._is_span_in_sent(sent, secu):
                    temp_doc = doc[sent.start:sent.end]
                    expiry = self.spacy_text_search.match_secu_expiry(temp_doc, secu)
                    if expiry:
                        logger.info(expiry)
                        if expiry not in expiries_seen:
                            expiries_seen.add(expiry)
                            expiries.append(expiry)
        if len(expiries) > 1:
            raise UnclearInformationExtraction(f"Couldnt get a definitive match for the expiry, got multiple: {expiries}")
        else:
            return expiries if expiries != [] else None

    def get_secu_multiplier(self, doc: Doc, security_name: str, security_spans: List[Span]):
        logger.debug("get_secu_multiplier returning dummy value: 1")
        return 1

    def get_secu_latest_issue_date(self, doc: Doc, security_name: str, security_spans: List[Span]):
        logger.debug("get_secu_latest_issue_date returning dummy value: None")
        return None

    def get_secu_interest_rate(self, doc: Doc, security_name: str, security_spans: List[Span]):
        logger.debug("get_secu_interest_rate returning dummy value: 0.05")
        return 0.05

    def get_secu_right(self, doc: Doc, security_name: str, security_spans: List[Span]):
        logger.debug("get_secu_right returning dummy value: 'Call'")
        return "Call"

    def get_secu_conversion(self, doc: Doc, security_name: str, security_spans: List[Span]):
        pass
    
    def get_issuable_relation(self, doc: Doc, security_name: str):
        # make patterns match on base secu explicitly
        # if part1[0] matches assume common stock?
        # then extract relation (and note span of SECU aswell)
        # normalize secu text to lower so we reduce amount of cases
        # write function to create secu from secu_type and optional kwargs
        primary_matches = self.spacy_text_search.match_issuable_secu_primary(doc)
        print(f"primary_matches: {primary_matches}")
        no_primary_matches = self.spacy_text_search.match_issuable_secu_no_primary(doc)
        print(f"no_primary_matches: {no_primary_matches}")
        no_exercise_price = self.spacy_text_search.match_issuable_secu_no_exercise_price(doc)
        print(f"no_exercise_price_matches: {no_exercise_price}")
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
    def extract_form_values(self, filing: Filing, company: model.Company, bus: MessageBus):
        complete_doc = self.spacy_text_search.nlp(filing.get_text_only())
        form_case = self.classify_s3(filing)
        cover_page_doc = self.doc_from_section(filing.get_section(re.compile("cover page")))
        # self.extract_securities(filing, company, bus, cover_page_doc)
        self.extract_securities(filing, company, bus, complete_doc)
        form_classifications = form_case["classifications"]
        if "shelf" in form_classifications:
            logger.info(f"Handling classification case: 'shelf' in form_case: {form_case}")
            # add shelf_registration
            self.handle_shelf(filing, company, bus, is_preliminary=form_case["is_preliminary"])
        if "resale" in form_classifications:
            logger.info(f"Handling classification case: 'resale' in form_case: {form_case}")
            # add resale_registration
            self.handle_resale(filing, company, bus, is_preliminary=form_case["is_preliminary"])
        if "ATM" in form_classifications:
            logger.info(f"Handling classification case: 'ATM' in form_case: {form_case}")
            # add ShelfOffering to BaseProspectus
            # check if we have ShelfRegistration added
            self.handle_ATM(filing, company, bus, cover_page_doc, is_preliminary=form_case["is_preliminary"])
        return company

    def handle_ATM(self, filing: Filing, company: model.Company, bus: MessageBus, cover_page_doc: Doc, is_preliminary: bool=False):
        shelf: model.ShelfRegistration = company.get_shelf(file_number=filing.file_number)
        print(f"found base registration 'shelf': {shelf}")
        if shelf:
            commencment_date = filing.filing_date #write function for this, for now assume filing_date
            kwargs = {
                    "offering_type": "ATM",
                    "accn": filing.accession_number,
                    "anticipated_offering_amount": self.extract_aggregate_offering_amount(cover_page_doc).get("amount"),
                    "commencment_date": commencment_date,
                    "end_date": commencment_date + timedelta(days=1095)
                }
            offering = model.ShelfOffering(**kwargs)
            shelf.add_offering(offering)
            logger.info("Added ShelfOffering")
            bus.handle(commands.AddShelfOffering(company.cik, offering))
            self.handle_ATM_security_registrations(filing, company, bus, cover_page_doc)

    def handle_ATM_security_registrations(self, filing: Filing, company: model.Company, bus: MessageBus, cover_page_doc: Doc):
        security_registrations = self.get_ATM_security_registrations(filing, company, cover_page_doc)
        for security_registration in security_registrations:
            self.handle_shelf_security_registration(
                    filing=filing,
                    company=company,
                    bus=bus,
                    security_registration=security_registration)
                
            

    def handle_resale(self, filing: Filing, company: model.Company, bus: MessageBus, is_preliminary: bool=False):
        kwargs =  {
                "accn": filing.accession_number,
                "form_type": filing.form_type,
                "file_number": filing.file_number,
                "filing_date": filing.filing_date
            }
        resale = model.ResaleRegistration(**kwargs)
        company.add_resale(resale)
        bus.handle(commands.AddResaleRegistration(filing.cik, resale))
        self.handle_resale_security_registrations(filing, company, bus)
    
    def handle_resale_security_registrations(self, filing: Filing, company: model.Company, bus: MessageBus):
        security_registrations = self.get_resale_security_registrations(filing, company)
    
    def get_resale_security_registrations(self, filing: Filing, company: model.Company):
        pass


    def handle_shelf(self, filing: Filing, company: model.Company, bus: MessageBus, is_preliminary: bool=False):
        kwargs = {
                "accn": filing.accession_number,
                "form_type": filing.form_type,
                "file_number": filing.file_number,
                "capacity": self.format_total_shelf_capacity(self.extract_shelf_capacity(filing)),
                "filing_date": filing.filing_date
            }
        shelf = model.ShelfRegistration(**kwargs)
        company.add_shelf(shelf)
        bus.handle(commands.AddShelfRegistration(filing.cik, shelf))
                # if no registrations can be found add whole dollar amount as common
                # add ShelfOffering
                # get underwriters, registrations and completed then modify
                # previously added ShelfOffering
    
    def handle_shelf_security_registration(self, filing: Filing, company: model.Company, bus: MessageBus, security_registration: model.ShelfSecurityRegistration):
        offering = company.get_shelf_offering(filing.accession_number)
        offering.add_registration(security_registration)
        cmd = commands.AddShelfSecurityRegistration(filing.cik, filing.accession_number, security_registration=security_registration)
        bus.handle(cmd)
    
    def get_ATM_security_registrations(self, filing: Filing, company: model.Company, cover_page: Doc):
        registrations = []
        aggregate_offering_amount = self.extract_aggregate_offering_amount(cover_page)
        if aggregate_offering_amount:
            if len(aggregate_offering_amount["SECU"]) == 1:
                secu = company.get_security_by_name(aggregate_offering_amount["SECU"][0])
                amount = aggregate_offering_amount["amount"]
                registrations.append(model.ShelfSecurityRegistration(secu, amount, None, None))
        return registrations if registrations != [] else None


    def extract_securities(self, filing: Filing, company: model.Company, bus: MessageBus, security_doc: Doc) -> List[model.Security]:
        '''extract securities from cover_page and descriptions of securities.'''
        # raw_secus = self.get_mentioned_secus(security_doc)
        # description_sections = filing.get_sections(re.compile("description\s*of", re.I))
        # description_docs = [self.doc_from_section(x) for x in description_sections]
        # security_relevant_docs = [
        #     self.doc_from_section(x) for x in filing.get_sections(
        #         re.compile("(description)|(summary)|(about)|(selling)", re.I))]
        # logger.info(f"security_relevant_docs_found: {[s.title if s is not None else None for s in filing.get_sections(re.compile('(description)|(summary)|(about)|(selling)', re.I))]}")
        # securities = self.get_securities_from_docs(security_relevant_docs)

        securities = self.get_securities_from_docs([security_doc])

        for security in securities:
            company.add_security(security)
        bus.handle(commands.AddSecurities(company.cik, securities))
        return securities
    
    def extract_aggregate_offering_amount(self, cover_page: Doc) -> dict:
        matches = self.spacy_text_search.match_aggregate_offering_amount(cover_page)
        # check how well this works
        if len(matches) > 1:
            logger.debug(f"Unhandled case for extract_offering_amount: more than one match. matches: {matches}")
            raise NotImplementedError
        else:
            offering_data = {"SECU": [], "amount": None}
            for ent in matches[0].ents:
                if ent.label_ == "SECU":
                    offering_data["SECU"].append(get_secu_key(ent))
                if ent.label_ == "MONEY":
                    offering_data["amount"] = self.formater.money_string_to_float(ent.text)
            return offering_data if (offering_data["amount"] is not None) else None
 
    def extract_securities_conversion_attributes(self, filing: Filing, company: model.Company, bus: MessageBus) -> List[model.SecurityConversion]:
        description_sections = filing.get_sections(re.compile("description\s*of", re.I))
        description_docs = [self.doc_from_section(x) for x in description_sections]
        conversions = []
        for security in company.securities:
            for doc in description_docs:
                conversion_attr = self.get_secu_conversion(doc, security.name)
                if conversion_attr:
                    # add conversion attribute to Securities
                    pass # need to write get_secu_conversion first
        return conversions

                


            # iter through sections and get attributes then merge attributes
            # stop as soon as attributes have all None values

        # look in descrption of capital stock and cover page
        # 
        #WIP

    def classify_s3(self, filing: Filing):
        front_page = filing.get_section(re.compile("front page"))
        cover_page = filing.get_section(re.compile("cover page"))
        distribution = filing.get_section(re.compile("distribution", re.I))
        summary = filing.get_section(re.compile("summary", re.I))
        about = filing.get_section(re.compile("about\s*this", re.I))
        if cover_page == []:
            raise AttributeError(f"couldnt get the cover page section; sections present: {[s.title for s in filing.sections]}")
        cover_page_doc = self.doc_from_section(cover_page)
        distribution_doc = self.doc_from_section(distribution) if distribution != [] else []
        summary_doc = self.doc_from_section(summary) if summary != [] else []
        about_doc = self.doc_from_section(about) if about != [] else []
        form_case = {"is_preliminary": False, "is_combination_form_case": False, "classifications": set()}
        if front_page:
            front_page_doc = self.doc_from_section(front_page)
            if self._is_preliminary_prospectus(front_page_doc):
                form_case["is_preliminary"] = True
        if self._is_resale_prospectus(cover_page_doc):
            form_case["classifications"].add("resale")
        if self._is_at_the_market_prospectus(cover_page_doc) or self._is_at_the_market_prospectus(distribution_doc):
            form_case["classifications"].add("ATM")
        if True in [self._is_shelf_prospectus(x) if x != [] else False for x in [cover_page_doc, about_doc, summary_doc]]:
            form_case["classifications"].add("shelf")
        if len(form_case["classifications"]) > 1:
            form_case["is_combination_form_case"] = True
        if form_case["classifications"] == []:
            raise UnhandledClassificationError
        return form_case
    
    def _is_preliminary_prospectus(self, doc: Doc):
        phrase_matcher = PhraseMatcher(self.spacy_text_search.nlp.vocab, attr="LOWER")
        pm_patterns = [self.spacy_text_search.nlp.make_doc(term) for term in [
            "SUBJECT TO COMPLETION,",
            "The information in this prospectus is not complete and may be changed.",
            "The information set forth in this preliminary prospectus is not complete and may be changed.",
            "The information set forth in this prospectus is not complete and may be changed."
        ]]
        phrase_matcher.add("is_preliminary_prospectus", pm_patterns)
        if len(phrase_matcher(doc)) > 0:
            return True
        else:
            return False

    def _is_resale_prospectus(self, doc: Doc) -> bool:
        '''
        determine if this is a resale of securities by anyone other than the registrar,
        by checking for key phrases in the "cover page".'''
        matcher = Matcher(self.spacy_text_search.nlp.vocab)
        phrase_matcher = PhraseMatcher(self.spacy_text_search.nlp.vocab, attr="LOWER")
        # action_verbs = ["sell", "offer", "resell", "disposition"]
        m_pattern1 = [
            {"LOWER": "prospectus"},
            {"LEMMA": "relate"},
            {"LOWER": "to"},
            {"OP": "*", "IS_SENT_START": False},
            {"LOWER": "by"},
            {"LOWER": "the"},
            {"LOWER": "selling"},
            {"LOWER": {"IN": ["stockholder", "stockholders"]}}
        ]
        pm_patterns = [self.spacy_text_search.nlp.make_doc(term) for term in [
            "“Selling Stockholder”",
            "“Selling Stockholders”",
            "Selling Stockholder will receive all of the net proceeds"
            "Selling Stockholders will receive all of the net proceeds"
        ]]
        phrase_matcher.add("selling_stockholder", pm_patterns)
        matcher.add("ATM", [m_pattern1])
        possible_phrase_matches = phrase_matcher(doc, as_spans=True)
        possible_matches = matcher(doc, as_spans=True)
        if len(possible_matches) > 0:
            logger.debug(f"This is a 'resale' Prospectus, determined by matches: {possible_matches}")
            return True
        if len(possible_phrase_matches) > 0:
            logger.debug(f"This is a 'resale' Prospectus, determined by phrase_matches: {possible_phrase_matches}")
            return True
        return False


    def _is_at_the_market_prospectus(self, doc: Doc) -> bool:
        if not isinstance(doc, Doc):
            logger.debug(f"_is_at_the_market_prospectus failed; Expecting type: Doc got type: {type(doc), doc}")
            return False
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
            {"LOWER": {"IN": ["an", "a"]}, "OP": "?"},
            {"IS_PUNCT": True, "IS_SENT_START": False},
            *[{"LOWER": x} for x in at_the_market_case],
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
        matcher.add("ATM", [*pattern1])
        possible_matches = matcher(doc, as_spans=True)
        if len(possible_matches) > 0:
            logger.debug(f"This is an 'ATM' (at-the-market) Prospectus, determined by matches: {possible_matches}")
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
        if len(possible_matches) > 0:
            logger.debug(f"This is a 'shelf' Prospectus, determined by matches: {possible_matches}")
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
                # values = []
                logger.debug(f"registration_df: {registration_df}")
                row = None
                if "total" in registration_df["Title"].values:
                    row = registration_df[registration_df["Title"] == "total"]
                elif len(registration_df["Title"].values) == 1:
                    row = registration_df.iloc[0]
                if row is None:
                    raise ValueError(f"couldnt determine correct row while extracting from registration table: {registration_df}")
                if row["Amount"].item() != "":
                    return {"total_shelf_capacity": {"amount": row["Amount"].item(), "unit": "shares"}}
                elif row["Price Aggregate"].item() != "":
                    return {"total_shelf_capacity": {"amount": row['Price Aggregate'].item(), "unit": "$"}}
        return None
    
    def format_total_shelf_capacity(self, capacity_dict: Dict):
        if "total_shelf_capacity" not in capacity_dict.keys():
            return None
        capacity = capacity_dict["total_shelf_capacity"]
        if capacity["unit"] == "$":
            return self.formater.money_string_to_float(capacity["amount"])
        if capacity["unit"] == "shares":
            return str(self.formater.money_string_to_float(capacity["amount"])) + " shares"
    
    



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


