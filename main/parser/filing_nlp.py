from typing import Dict, Set
import spacy
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Span, Doc, Token
from spacy import Language
from spacy.util import filter_spans
import logging
import string
import re
import  pandas as pd

from main.security_models.naiv_models import CommonShare, Securities

logger = logging.getLogger(__name__)

class MatchFormater:
    def money_string_to_int(self, money: str):
        digits = re.findall("[0-9]+", money)
        return int("".join(digits))

formater = MatchFormater()


def int_to_roman(input):
    """ Convert an integer to a Roman numeral. """

    if not isinstance(input, type(1)):
        raise TypeError(f"expected integer, got {type(input)}")
    if not (0 < input < 4000):
        print(input)
        raise ValueError("Argument must be between 1 and 3999")
    ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
    nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
    result = []
    for i in range(len(ints)):
        count = int(input / ints[i])
        result.append(nums[i] * count)
        input -= ints[i] * count
    return ''.join(result).lower()

def roman_list():
    return ["(" + int_to_roman(i)+")" for i in range(1, 50)]

def alphabetic_list():
    return ["(" + letter +")" for letter in list(string.ascii_lowercase)]

def numeric_list():
    return ["(" + str(number) + ")" for number in range(150)]

class FilingsSecurityLawRetokenizer:
    def __init__(self,  vocab):
        pass
    
    def __call__(self, doc):
        expressions = [
            # eg: 415(a)(4)
            re.compile(r'(\d\d?\d?\d?(?:\((?:(?:[a-zA-Z0-9])|(?:(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})))\)){1,})', re.I),
            re.compile(r"\s\((?:(?:[a-zA-Z0-9])|(?:(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})))\)\s", re.I),
            re.compile(r"(\s[a-z0-9]{1,2}\))|(^[a-z0-9]{1,2}\))", re.I | re.MULTILINE)
            ]
        match_spans = []
        for expression in expressions:
            for match in re.finditer(expression, doc.text):
                start, end = match.span()
                span = doc.char_span(start, end)
                if match is not None:
                    match_spans.append([span, start, end])
        # sorted_match_spans = sorted(match_spans, key=lambda x: x[1])
        longest_matches = filter_matches(match_spans)
        with doc.retokenize() as retokenizer:
            for span in longest_matches:
                span = span[0]
                if span is not None:
                    retokenizer.merge(span)
        return doc
        

class SecurityActMatcher:
    def __init__(self, vocab):
        Token.set_extension("sec_act", default=False)
        self.matcher = Matcher(vocab)
        self.add_sec_acts_to_matcher()
    
    def __call__(self, doc):
        matches = self.matcher(doc)
        spans = []  # Collect the matched spans here
        for match_id, start, end in matches:
            spans.append(doc[start:end])
        with doc.retokenize() as retokenizer:
            for span in spans:
                retokenizer.merge(span)
                for token in span:
                    token._.sec_act = True
        return doc 
    
    def add_sec_acts_to_matcher(self):
        romans = roman_list()
        numerals = numeric_list()
        letters = alphabetic_list()
        upper_letters = [a.upper() for a in letters]
        patterns = [
            [   
                {"ORTH": {"IN": ["Rule", "Section", "section"]}},
                {"LOWER": {
                    "REGEX": r'(\d\d?\d?\d?(?:\((?:(?:[a-z0-9])|(?:(?=[mdclxvi])m*(c[md]|d?C{0,3})(x[cl]|l?x{0,3})(i[xv]|v?i{0,3})))\)){0,})'
                        },
                "OP": "*"}
            ],
            [
                {"ORTH": {"IN": ["Section" + x for x in  list(string.ascii_uppercase)]}},
            ]
        ]
        self.matcher.add("sec_act", patterns, greedy="LONGEST")

def get_secuquantity(span):
    if span.label_ == "SECUQUANTITY":
        return formater.money_string_to_int(span.text)
    else:
        raise AttributeError("get_secuquantity can only be called on Spans with label: 'SECUQUANTITY'")

def get_alias(doc: Doc, secu: Span):
    logger.debug(f"getting alias for: {secu}")
    if doc._.is_alias(secu) is True:
        return None
    else:
        secu_first_token = secu.__getitem__(0)
        secu_last_token = secu.__getitem__(-1)
        for sent in doc.sents:
            if secu_first_token in sent:
                # possible_alias = []
                for token in sent[secu_last_token.i+1:]:
                    alias = doc._.tokens_to_alias_map.get(token.i)
                    if token.ent_type_ == "SECU":
                        if alias is None:
                            return None
                    if alias:
                        if alias.similarity(secu) > 0.6:
                            return alias
                        else:
                            logger.debug(f"similarity score was to low for alias to be considered correct (< 0.6)")
                            logger.debug(f"similarity score: {alias.similarity(secu)} for base:{secu} and alias:{alias}")
                            return None
                    # if token.ent_type_ == "SECU":
                    #     possible_alias.append(token)
                    # else:
                    #     if possible_alias != []:
                    #         print(f"possible_alias: {possible_alias[0]}, {possible_alias[-1]}")
                    #         span = doc[possible_alias[0].i:possible_alias[-1].i+1]
                    #         print(f"span: {span}")
                    #         if doc._.is_alias(span):
                    #             alias.append(span)
                    #             print(span.similarity(secu), f"secu: {secu}, possible_alias: {span}")
                    #             possible_alias = []
                    #         else:
                    #             return alias

                    


                
'''
how to get the alias of secu?
1) create map of spans to token idx, so we can query from token idx to span
2) get sentence containing original secu
3) iter through tokens after original secu and see if we have an
alias before we encounter the next secu
'''


def is_alias(doc: Doc, secu: Span):
    if secu.text in doc._.alias_set:
        return True
    return False

class SECUMatcher:
    _instance = None
    def __init__(self, vocab):
        self.matcher = Matcher(vocab)
        self.second_matcher = Matcher(vocab)

        Span.set_extension("secuquantity", getter=get_secuquantity)
        Span.set_extension("secuquantity_unit", default=None)
        Doc.set_extension("get_alias", method=get_alias)
        Doc.set_extension("alias_set", default=set())
        Doc.set_extension("tokens_to_alias_map", default=dict())
        '''
        0) add SECU ent to doc.spans["SECU"] list
        1) populate alias to tokens map
        1.5) for each secu get
        2) to get alias:
            *) look for tokens after subject
            *) get next alias in same sent
            *) ?
        '''
        Doc.set_extension("is_alias", method=is_alias)
        Doc.set_extension("base_alias_map", default=dict())
        # need a:
        #   get alias method on doc which takes the Span of origin as arg
        
        self.add_SECU_ent_to_matcher()
        self.add_SECUATTR_ent_to_matcher()
        self.add_SECUQUANTITY_ent_to_matcher(self.second_matcher)
    

    def __call__(self, doc: Doc):
        self.chars_to_token_map = self.get_chars_to_tokens_map(doc)
        self.matcher(doc)
        self.second_matcher(doc)
        self.add_possible_alias_spans(doc)
        self.add_tokens_to_alias_map(doc)
        return doc
    
    def get_chars_to_tokens_map(self, doc: Doc):
        chars_to_tokens = {}
        for token in doc:
            for i in range(token.idx, token.idx + len(token.text)):
                chars_to_tokens[i] = token.i
        return chars_to_tokens
    
    def get_tokens_to_alias_map(self, doc: Doc, alias_spans: list[Span]):
        tokens_to_alias_map = {}
        for span in alias_spans:
            for token in span:
                tokens_to_alias_map[token.i] = span
        return tokens_to_alias_map
    
    def get_possible_alias_spans(self, doc: Doc, chars_to_tokens: Dict):
        spans = []
        parenthesis_pattern = re.compile(r"\([^(]*\)")
        possible_alias_pattern = re.compile(
            r'(?:\"|“)[a-zA-Z\s-]*(?:\"|”)'
        )
        for match in re.finditer(parenthesis_pattern, doc.text):
            if match:
                start_idx = match.start()
                for possible_alias in re.finditer(possible_alias_pattern, match.group()):
                    if possible_alias:
                        start_token = chars_to_tokens.get(start_idx + possible_alias.start())
                        end_token = chars_to_tokens.get(start_idx + possible_alias.end()-1)
                        if (start_token is not None) and (end_token is not None):
                            spans.append(doc[start_token+1:end_token])
                        else:
                            logger.debug(f"couldnt find start/end token for alias: {possible_alias}; start/end token: {start_token}/{end_token}")
        return spans
    
    # def mark_possible_alias_spans(self, doc: Doc, spans: list[Span]):
    #     for span in spans:
    #         span._.is_alias = True
    #     return spans
    
    def set_possible_alias_spans(self, doc: Doc, spans: list[Span]):
        doc.spans["alias"] = spans
        
    def add_possible_alias_spans(self, doc: Doc):
        self.set_possible_alias_spans(
            doc,
            self.get_possible_alias_spans(doc, self.chars_to_token_map)
        )
        logger.debug(f"set alias spans: {doc.spans['alias']}")
        for span in doc.spans["alias"]:
            doc._.alias_set.add(span.text)
        logger.debug(f"alias_set extension on doc: {doc._.alias_set}")
    
    def add_tokens_to_alias_map(self, doc: Doc):
        doc._.tokens_to_alias_map = self.get_tokens_to_alias_map(doc, doc.spans["alias"])
        


    
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
            "convertible"
        ]
        general_pre_sec_compound_modifiers = [
            [
                {"LOWER": "non"},
                {"LOWER": "-"},
                {"LOWER": "convertible"}
            ],
            [
                {"LOWER": "pre"},
                {"LOWER": "-"},
                {"LOWER": "funded"}
            ],
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
            *[  
                [
                    *general_pre_sec_compound_modifier,
                    {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "warrant", "warrants", "ordinary"]}},
                    {"LOWER": {"IN": ["stock", "shares"]}, "OP": "?"}
                ] for general_pre_sec_compound_modifier in general_pre_sec_compound_modifiers
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

    def add_SECUQUANTITY_ent_to_matcher(self, matcher: Matcher):
        regular_patterns = [
            [
                {"ENT_TYPE": "CARDINAL"},
                {"LOWER": {"IN": ["authorized", "outstanding"]}, "OP": "?"},
                {"LOWER": {"IN": ["share", "shares", "warrant shares"]}}
            ],
            [   
                {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
                {"LOWER": "of", "OP": "?"},
                {"ENT_TYPE": "SECU"}
                # # {"ENT_TYPE": "SECU", "OP": "*"},
            ]
        ]
        each_pattern = [
                [
                    {"LOWER": {"IN": ["each", "every"]}},
                    {"LOWER": {"IN": ["share", "shares", "warrant shares"]}}
                ]
            ]
        matcher.add("SECUQUANTITY_ENT", [*regular_patterns, *each_pattern], on_match=_add_SECUQUANTITY_ent_regular_case)


def _is_match_followed_by(doc: Doc, start: int, end: int, exclude: list[str]):
    if end == len(doc):
        end -= 1
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

            

def _add_SECUQUANTITY_ent_regular_case(matcher, doc: Doc, i, matches):
    logger.debug(f"Adding ent_label: SECUQUANTITY")
    _, match_start, match_end = matches[i]
    match_id, start, _ = matches[i]
    end = start + 1
    entity = Span(doc, start, end, label="SECUQUANTITY")
    match_tokens = [t for t in doc[match_start:match_end]]
    if "MONEY" in [t.ent_type_ for t in match_tokens]:
        entity._.secuquantity_unit = "MONEY"
    elif ("each" in entity.text) or ("every" in entity.text):
        entity._.secuquantity_unit = "ALL"
    else:
        entity._.secuquantity_unit = "COUNT"
    print(entity._.secuquantity_unit)
    try:
        doc.ents += (entity,)
    except ValueError as e:
        if "[E1010]" in str(e):
            previous_ents = set(doc.ents)
            conflicting_ents = []
            for ent in doc.ents:                
                covered_tokens = range(ent.start, ent.end)
                if (start in covered_tokens) or (end in covered_tokens):
                    if (ent.end - ent.start) <= (end - start):
                        conflicting_ents.append((ent.end - ent.start, ent))
            if False not in [end-start >= k[0] for k in conflicting_ents]:
                [previous_ents.remove(k[1]) for k in conflicting_ents]
                previous_ents.add(entity)
            doc.ents = previous_ents

def _add_ent(doc: Doc, i, matches, ent_label: str, exclude_after: list[str]=[], exclude_before: list[str]=[]):
    '''add a custom entity through an on_match callback.'''
    logger.debug(f"Adding ent_label: {ent_label}")
    match_id, start, end = matches[i]
    # print(doc[start:end])
    # print(f"followed_by: {_is_match_followed_by(doc, start, end, exclude_after)}")
    # print(f"preceeded_by: {_is_match_preceeded_by(doc, start, end, exclude_before)}")
    if (not _is_match_followed_by(doc, start, end, exclude_after)) and (
        not _is_match_preceeded_by(doc, start, end, exclude_before)):
        entity = Span(doc, start, end, label=ent_label)
        # logger.debug(f"entity: {entity}")
        try:
            doc.ents += (entity,)
        except ValueError as e:
            if "[E1010]" in str(e):
                # logger.debug(f"---NEW ENT--- {entity}")
                previous_ents = set(doc.ents)
                conflicting_ents = []
                for ent in doc.ents:                
                    covered_tokens = range(ent.start, ent.end + 1)
                    # print([x for x in covered_tokens], (ent.start, start), (ent.end, end))
                    if (start in covered_tokens) or (end in covered_tokens):
                        print(start, end)
                        if (ent.end - ent.start) <= (end - start):
                            print(start, end)
                            # logger.debug(covered_tokens)
                            # logger.debug(("ent: ", ent, ent.text, ent.label_, ent.start, ent.end))
                            # logger.debug(("entity which replaces ent: ",entity, entity.text, entity.label_, entity.start, entity.end))
                            conflicting_ents.append((ent.end - ent.start, ent))
                # logger.debug(f"conflicting_ents: {conflicting_ents}")
                if (False not in [end-start >= k[0] for k in conflicting_ents]) and (conflicting_ents != []):
                    [previous_ents.remove(k[1]) for k in conflicting_ents]
                    # logger.debug(f"removed conflicting_ents: {[k[1] for k in conflicting_ents]}")
                    # logger.debug(f"Added entity: {entity}")
                    previous_ents.add(entity)
                    
                # logger.debug(f"new_ents: {previous_ents}")
                doc.ents = previous_ents
                    
@Language.factory("secu_matcher")
def create_secu_matcher(nlp, name):
    return SECUMatcher(nlp.vocab)

@Language.factory("secu_act_matcher")
def create_secu_act_matcher(nlp, name):
    return SecurityActMatcher(nlp.vocab)

@Language.factory("security_law_retokenizer")
def create_regex_retokenizer(nlp, name):
    return FilingsSecurityLawRetokenizer(nlp.vocab)

class SpacyFilingTextSearch:
    _instance = None
    # make this a singleton/get it from factory through cls._instance so we can avoid
    # the slow process of adding patterns (if we end up with a few 100)
    def __init__(self):
        pass


    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpacyFilingTextSearch, cls).__new__(cls)
            cls._instance.nlp = spacy.load("en_core_web_lg")
            cls._instance.nlp.add_pipe("security_law_retokenizer")
            cls._instance.nlp.add_pipe("secu_matcher")
            cls._instance.nlp.add_pipe("secu_act_matcher")
        return cls._instance
    
    def match_prospectus_relates_to(self, text):
        pattern = [
            # This prospectus relates to
            {"LOWER": "prospectus"},
            {"LEMMA": "relate"},
            {"LOWER": "to"},
            {"OP": "*", "IS_SENT_START": False}
        ]
        matcher = Matcher(self.nlp.vocab)
        matcher.add("relates_to", [pattern])
        doc = self.nlp(text)
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
        return matches if matches is not None else []
    
    def match_aggregate_offering_amount(self, doc: Doc):
        pattern = [
            {"LOWER": "aggregate"},
            {"LOWER": "offering"},
            {"OP": "?"},
            {"OP": "?"},
            {"LOWER": "up"},
            {"LOWER": "to"},
            {"ENT_TYPE": "MONEY", "OP": "+"}
        ]
        matcher = Matcher(self.nlp.vocab)
        matcher.add("offering_amount", [pattern])
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
        return matches if matches is not None else []
    
    def get_secus_and_secuquantity(self,  doc: Doc):
        found = []
        for ent in doc.ents:
            print(ent.text, ent.label_)
            if ent.label_ == "SECUQUANTITY":
                found.append({"amount": ent.text})
            if ent.label_ == "SECU":
                found.append({"security": ent})
        return found

    def match_outstanding_shares(self, text):
        pattern1 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": "CARDINAL"},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["outstanding", "stockoutstanding"]}}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "DATE", "OP": "?"}, {"OP": "?"}, {"ENT_TYPE": "DATE", "OP": "*"}]
        pattern2 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": "CARDINAL"},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "outstanding"}, {"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"},{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "DATE", "OP": "?"}, {"OP": "?"}, {"ENT_TYPE": "DATE", "OP": "*"}]
        pattern3 = [{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "DATE", "OP": "?"}, {"OP": "?"}, {"ENT_TYPE": "DATE", "OP": "*"}, {"OP": "?"}, {"ENT_TYPE": "CARDINAL"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["issued", "outstanding"]}}]
        matcher = Matcher(self.nlp.vocab)
        matcher.add("outstanding", [pattern1, pattern2, pattern3])
        doc = self.nlp(text)
        possible_matches = matcher(doc, as_spans=False)
        if possible_matches == []:
            logger.debug("no matches for outstanding shares found")
            return []
        matches = _convert_matches_to_spans(doc, filter_matches(possible_matches))
        values = []
        for match in matches:
            value = {"date": ""}
            for ent in match.ents:
                print(ent, ent.label_)
                if ent.label_ == "CARDINAL":
                    value["amount"] = int(str(ent).replace(",", ""))
                if ent.label_ == "DATE":
                    value["date"] = " ".join([value["date"], ent.text])
            value["date"] = pd.to_datetime(value["date"])
            try:
                validate_filing_values(value, ["date", "amount"])
            except AttributeError:
                pass
            else:
                values.append(value)
        return values
    
    def match_issuable_secu_primary(self, doc: Doc):
        secu_transformative_actions = ["exercise", "conversion"]
        part1 = [
            [
                {"ENT_TYPE": "CARDINAL"},
                {"LOWER": "shares"},
                {"LOWER": "of"},
                {"LOWER": "our", "OP": "?"},
                {"ENT_TYPE": "SECU", "OP": "+"},
                {"LOWER": "issuable"},
                {"LOWER": "upon"},
                {"LOWER": "the", "OP": "?"}
            ]
        ]
        part2 = [
            [
                {"LOWER": {"IN": ["exercise", "conversion"]}},
                {"LOWER": "price"},
                {"LOWER": "of"},
                {"OP": "?", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"ENT_TYPE": "MONEY"},
                {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}}
            ],
            [
                {"LOWER": {"IN": ["exercise", "conversion"]}},
                {"LOWER": {"IN": ["price", "prices"]}},
                {"LOWER": "ranging"},
                {"LOWER": "from"},
                {"OP": "?", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"ENT_TYPE": "MONEY"},
                {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"LOWER": "to"},
                {"OP": "?", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"ENT_TYPE": "MONEY"},
                {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}}
            ]
        ]
        primary_secu_pattern = []
        for transformative_action in secu_transformative_actions:
            p1 = part1[1]
            for p2 in part2:
                pattern = [
                            *p1,
                            {"LOWER": transformative_action},
                            {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                            *p2,
                            {"LOWER": "of"},
                            {"ENT_TYPE": "SECU", "OP": "+"}
                            ]
                primary_secu_pattern.append(pattern)
        pattern2 = [
            [
            {"ENT_TYPE": "CARDINAL"},
            {"LOWER": "shares"},
            {"LOWER": "of"},
            {"LOWER": "our", "OP": "?"},
            {"ENT_TYPE": "SECU", "OP": "+"},
            {"LOWER": "issuable"},
            {"LOWER": "upon"},
            {"LOWER": "the", "OP": "?"},
            {"LOWER": transformative_action},
            {"LOWER": "of"},
            {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
            {"ENT_TYPE": "SECU", "OP": "+"}
            ]
            for transformative_action in secu_transformative_actions
        ]
        [primary_secu_pattern.append(x) for x in pattern2]
        matcher = Matcher(self.nlp.vocab)
        matcher.add("primary_secu", [*primary_secu_pattern])
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
    
    def match_issuable_secu_no_primary(self, doc: Doc):
        secu_transformative_actions = ["exercise", "conversion"]
        part1 = [
            [
                {"ENT_TYPE": "CARDINAL"},
                {"LOWER": "shares"},
                {"LOWER": "issuable"},
                {"LOWER": "upon"}
            ]
        ]
        part2 = [
            [
                {"LOWER": {"IN": ["exercise", "conversion"]}},
                {"LOWER": "price"},
                {"LOWER": "of"},
                {"OP": "?", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"ENT_TYPE": "MONEY"},
                {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}}
            ],
            [
                {"LOWER": {"IN": ["exercise", "conversion"]}},
                {"LOWER": {"IN": ["price", "prices"]}},
                {"LOWER": "ranging"},
                {"LOWER": "from"},
                {"OP": "?", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"ENT_TYPE": "MONEY"},
                {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"LOWER": "to"},
                {"OP": "?", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                {"ENT_TYPE": "MONEY"},
                {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}}
            ]
        ]
        no_primary_secu_pattern = []
        for transformative_action in secu_transformative_actions:
            for p2 in part2:
                pattern = [
                            *part1,
                            {"LOWER": transformative_action},
                            {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                            *p2,
                            {"LOWER": "of"},
                            {"ENT_TYPE": "SECU", "OP": "+"}
                            ]
                no_primary_secu_pattern.append(pattern)
        matcher = Matcher(self.nlp.vocab)
        matcher.add("no_primary_secu", [*no_primary_secu_pattern])
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
        return matches
    
    
def filter_matches(matches):
    '''works as spacy.util.filter_spans but for matches'''
    if len(matches) <= 1:
        return matches
    logger.debug(f"pre filter matches: {[m for m in matches]}")
    get_sort_key = lambda match: (match[2] - match[1], -match[1])
    sorted_matches = sorted(matches, key=get_sort_key, reverse=True)
    result = []
    seen_tokens: Set[int] = set()
    for match in sorted_matches:
        # Check for end - 1 here because boundaries are inclusive
        if match[1] not in seen_tokens and match[2] - 1 not in seen_tokens:
            result.append(match)
            seen_tokens.update(range(match[1], match[2]))
    result = sorted(result, key=lambda match: match[1])
    return result  

    
# def _take_longest_matches(matches):
#         entries = []
#         prev_m = None
#         current_longest = None
#         sorted_matches = sorted(matches, key=lambda x: x[1])
#         if sorted_matches == []:
#             return []
#         for m in sorted_matches:
#             if prev_m is None:
#                 prev_m = m
#                 current_longest = m
#                 continue
#             if prev_m[1] == m[1]:
#                 if prev_m[2] < m[2]:
#                     current_longest = m
#             else:
#                 entries.append(current_longest)
#                 current_longest = m
#                 prev_m = m
#                 continue
#         if current_longest not in entries:
#             entries.append(current_longest)
#         return entries

def _convert_matches_to_spans(doc, matches):
    m = []
    for match in matches:
        m.append(doc[match[1]:match[2]])
    return m

def validate_filing_values(values, attributes):
    '''validate a flat filing value'''
    for attr in attributes:
        if attr not in values.keys():
            raise AttributeError
