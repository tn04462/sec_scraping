from dataclasses import dataclass
from functools import partial
from typing import Callable, Dict, Optional, Set
from attr import Attribute
import spacy
from spacy.matcher import Matcher, PhraseMatcher, DependencyMatcher
from spacy.tokens import Span, Doc, Token
from spacy import Language
from spacy.util import filter_spans
import logging
import string
import re
import  pandas as pd
from datetime import timedelta

logger = logging.getLogger(__name__)

PLURAL_SINGULAR_SECU_TAIL_MAP = {
    "warrants": "warrant"
}
SINGULAR_PLURAL_SECU_TAIL_MAP = {
    "warrant": "warrants"
}

class UnclearInformationExtraction(Exception):
    pass

class WordToNumberConverter():
    numbers_map = {
        "one": 1,
        "first": 1,
        "two": 2,
        "second": 2,
        "three": 3,
        "third": 3,
        "four": 4,
        "fourth": 4,
        "five": 5,
        "fifth": 5,
        "six": 6,
        "sixth": 6,
        "seven": 7,
        "seventh": 7,
        "eight": 8,
        "eighth": 8,
        "nine": 9,
        "ninth": 9,
        "ten": 10,
        "tenth": 10,
        "eleven": 11,
        "eleventh": 11,
        "twelve": 12,
        "twelfth": 12
    }
    timedelta_map = {
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30),
        "year": timedelta(days=365.25),
        "days": timedelta(days=1),
        "weeks": timedelta(weeks=1),
        "months": timedelta(days=30),
        "years": timedelta(days=365.25)
    }

    def convert_spacy_token(self, token: Token):
        if self.numbers_map.get(token.lower_):
            return self.numbers_map[token.lower_]
        if self.timedelta_map.get(token.lower_):
            return self.timedelta_map[token.lower_]
        return None

class MatchFormater:
    def __init__(self):
        self.w2n = WordToNumberConverter()

    def parse_number(self, text):
        '''from https://github.com/hayj/SystemTools/blob/master/systemtools/number.py'''
        try:
            # First we return None if we don't have something in the text:
            if text is None:
                return None
            if isinstance(text, int) or isinstance(text, float):
                return text
            text = text.strip()
            if text == "":
                return None
            # Next we get the first "[0-9,. ]+":
            n = re.search("-?[0-9]*([,. ]?[0-9]+)+", text).group(0)
            n = n.strip()
            if not re.match(".*[0-9]+.*", text):
                return None
            # Then we cut to keep only 2 symbols:
            while " " in n and "," in n and "." in n:
                index = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
                n = n[0:index]
            n = n.strip()
            # We count the number of symbols:
            symbolsCount = 0
            for current in [" ", ",", "."]:
                if current in n:
                    symbolsCount += 1
            # If we don't have any symbol, we do nothing:
            if symbolsCount == 0:
                pass
            # With one symbol:
            elif symbolsCount == 1:
                # If this is a space, we just remove all:
                if " " in n:
                    n = n.replace(" ", "")
                # Else we set it as a "." if one occurence, or remove it:
                else:
                    theSymbol = "," if "," in n else "."
                    if n.count(theSymbol) > 1:
                        n = n.replace(theSymbol, "")
                    else:
                        n = n.replace(theSymbol, ".")
            else:
                rightSymbolIndex = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
                rightSymbol = n[rightSymbolIndex:rightSymbolIndex+1]
                if rightSymbol == " ":
                    return self.parse_number(n.replace(" ", "_"))
                n = n.replace(rightSymbol, "R")
                leftSymbolIndex = max(n.rfind(','), n.rfind(' '), n.rfind('.'))
                leftSymbol = n[leftSymbolIndex:leftSymbolIndex+1]
                n = n.replace(leftSymbol, "L")
                n = n.replace("L", "")
                n = n.replace("R", ".")
            n = float(n)
            if n.is_integer():
                return int(n)
            else:
                return n
        except:
            pass
        return None

    def money_string_to_float(self, money: str):
        multiplier = 1
        digits = re.findall("[0-9.,]+", money)
        amount_float = self.parse_number("".join(digits))
        if re.search(re.compile("million(?:s)?", re.I), money):
            multiplier = 1000000
        if re.search(re.compile("billion(?:s)?", re.I), money):
            multiplier = 1000000000
        return float(amount_float*multiplier)
    
    def coerce_tokens_to_datetime(self, tokens: list[Token]|Span):
        try:
            date = pd.to_datetime("".join([i.text_with_ws for i in tokens]))
        except Exception as e:
            logger.debug(e, exc_info=True)
            return None
        else:
            return date

    
    def coerce_tokens_to_timedelta(self, tokens: list[Token]):
        multipliers = []
        timdelta_ = None
        current_idxs = []
        converted = []
        for idx, token in enumerate(tokens):
            w2n_conversion = self.w2n.convert_spacy_token(token)
            if w2n_conversion:
                if isinstance(w2n_conversion, timedelta):
                    timedelta_ = w2n_conversion
                    current_idxs.append(idx)
                    for prev_idx in range(idx-1, -1, -1):
                        prev_token = tokens[prev_idx]
                        if prev_token.is_punct:
                            continue
                        try:
                            current_idxs.append(prev_idx)
                            number = int(prev_token.lower_)
                            multipliers.append(number)
                        except ValueError:
                            number = self.w2n.convert_spacy_token(prev_token)
                            if isinstance(number, int):
                                multipliers.append(number)
                            else:
                                break
                    if multipliers != [] and timedelta_ is not None:
                        if len(multipliers) > 1:
                            raise NotImplementedError(f"multiple numbers before a timedelta token arent handled yet")
                        converted.append((multipliers[0]*timedelta_, current_idxs))
                timedelta_ = None
                multipliers = []
                current_idxs = []                    
        return converted if converted != [] else None

            

    

    def issuable_relation_no_primary_secu():
        pass

    def issuable_relation_with_primary_secu(self, doc: Doc, match: Span):
        # dict with keys: primary, base, action, price
        pass

    def issuable_relation_no_exercise_price_no_primary():
        pass

    def issuable_relation_no_exercise_price_no_primary():
        pass

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







class SpacyDependencyAttributeGetter:
    def _convert_key_to_stringkey(self, key: str) -> str:
        return key.lower() + "_"

    def _has_attributes(self, token: Token, attrs: dict) -> bool:
        if not isinstance(dict, attrs):
            raise TypeError(f"expecting a dict, got: {type(attrs)}")
        for attr, value in attrs.items():
            if not token.getattr(attr) == value:
                return False
        return True
    
    def check_head(self, token: Token, attrs: dict) -> Token:
        if not token.head:
            return None
        if self._has_attributes(token.head, attrs):
            return token.head
        else:
            return None
    
    def check_children(self, token: Token, attrs: dict) -> list[Token]:
        children = []
        if not token.children:
            return children
        
        for i in filter(lambda x: x is not None,
                    [child
                    if self._has_attributes(child, attrs)
                    else None
                    for child in token.children]
        ):
            children.append(i)
        return children
    
    def check_ancestors(self, token: Token, attrs: dict) -> list[Token]:
        ancestors = []
        if not token.ancestors:
            return ancestors
        for ancestor in token.ancestors:
            if self._has_attributes(ancestor, attrs):
                ancestors.append(ancestor)
        return ancestors
    
    def check_descendants(self, token: Token, attrs: dict) -> list[Token]:
        descendants = []
        if not token.subtree:
            return descendants
        for descendant in token.subtree:
            if token == descendant:
                continue
            if self._has_attributes(descendant, attrs):
                descendants.append(descendant)
        return descendants
            
          
    def _get_root_verb(self, attrs) -> list[Token]:
        valid_tokens = [i for i in self.check_ancestors(self.origin, attrs)]
        if valid_tokens != []:
            return valid_tokens
        else:
            return None
    
    def _wrap_results_in_dict(self, results: list[Token], key: str):
        if results is None or results == []:
            return None
        for r in results:
            yield {key: r}



class DependencyNode:
    def __init__(self, data, children=None):
        self.children: list[DependencyNode] = children if children is not None else list()
        self.data = data
    
    def __repr__(self):
        return str(self.data)
    
    def get_leaf_paths(self, node=None, current_path: list=list()):
        '''
        Get the paths from node->leaf of tree this node is a part of.
        Recursive function.

        Args:
            node: a DependencyNode, defaults to the Node this is called from.
            current_path: The already traveresed path should be left at the default value.

        '''
        if node is None:
            node = self
        if current_path == []:
            current_path = [node]
        if node.children == []:
            yield current_path
        else:
            for child in node.children:
                new_path = current_path.copy()
                new_path.append(child)
                yield from [arr for arr in self.get_leaf_paths(child, new_path)]         



class SpacySECUDependencyAttributeMatcher():
    dep_getter = SpacyDependencyAttributeGetter()
    DEPENDENCY_OPS = {
        "<<": dep_getter.check_ancestors,
        "<": dep_getter.check_head,
        ">": dep_getter.check_children,
        ">>": dep_getter.check_descendants
    }
    def __init__(self): pass
        # self,
        # secu: Token,
        # doc: Doc):
        # self.secu: Token = secu
        # self.doc = doc
        # self.unit: Optional[Token] = None
        # self.quantity: Optional[Token] = None
        # self.source_secu: Optional[SpacySECUInstance] = None
        # self.root_verb: Optional[Token] = None
        # self.root_verb_noun: Optional[Token] = None
        # self.state: Optional[list[Token]] = list() #either make this a dict with the different states available or make attributes for each state ? 

    '''
    flow of attributes:
    secu -> quantity -> unit
    secu -> root_verb -> source_secu
    secu -> root_verb -> root_verb_noun
    secu -> state
    '''
    def get_matches(self, dependant, attrs):
        rel_op = attrs["REL_OP"]
        return self.DEPENDENCY_OPS[rel_op](dependant, **attrs["RIGHT_ATTRS"])
    
    def chain_match(self, origin, attrs) -> list[DependencyNode]:
        match_tree = DependencyNode(None, origin)
        for idx, attr in enumerate(attrs):
            if idx == 0:
                matches = self.get_matches(origin, attr)
                for match in matches:
                    match_tree.children.append(DependencyNode(data=match))

            
        
        # first create list[dict[parent, list[child]]] then convert to DependencyNodes

            




    
    # def get_root_verbs(self):
    #     root_verbs = self._get_root_verb(
    #         self.secu,
    #         {"POS": "VERB"}
    #         )
    #     return self._wrap_results_in_dict(root_verbs, "root_verb")
            
    # def get_root_verb_noun(self, root_verb):
    #     possible_preps = [i for i in self.check_children(root_verb, {"DEP": "prep"})]
    #     if possible_preps != []:
    #         for prep in possible_preps:
    #             nouns = self.check_children(prep, {"POS": "NOUN"})
    #             if nouns and nouns != []:
    #                 return nouns
        


class CommonFinancialRetokenizer:
    def __init__(self,  vocab):
        pass
    
    def __call__(self, doc):
        expressions = [
            re.compile(r'par\svalue', re.I),
            ]
        match_spans = []
        for expression in expressions:
            for match in re.finditer(expression, doc.text):
                start, end = match.span()
                span = doc.char_span(start, end)
                if match is not None:
                    match_spans.append([span, start, end])
        with doc.retokenize() as retokenizer:
            for span in match_spans:
                span = span[0]
                if span is not None:
                    retokenizer.merge(span, attrs={"POS": "NOUN", "TAG": "NN"})
        return doc


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
        return formater.money_string_to_float(span.text)
    else:
        raise AttributeError("get_secuquantity can only be called on Spans with label: 'SECUQUANTITY'")

def retokenize_SECU(doc: Doc):
    with doc.retokenize() as retokenizer:
        for ent in doc.ents:
            if ent.label_ == "SECU":
                attrs = {"tag": ent.root.tag, "dep": ent.root.dep, "ent_type": ent.label}
                retokenizer.merge(ent, attrs=attrs)
    return doc


def get_alias(doc: Doc, secu: Span):
    # logger.debug(f"getting alias for: {secu}")
    if doc._.is_alias(secu) is True:
        return None
    else:
        secu_first_token = secu[0]
        secu_last_token = secu[-1]
        for sent in doc.sents:
            if secu_first_token in sent:
                secu_counter = 0
                token_idx_offset = sent[0].i
                for token in sent[secu_last_token.i-token_idx_offset+1:]:
                    alias = doc._.tokens_to_alias_map.get(token.i)
                    if token.ent_type_ == "SECU":
                        secu_counter += 1
                        if alias is None and secu_counter > 2: 
                            return None
                    if alias:
                        if alias.similarity(secu) > 0.7:
                            return alias
                        else:
                            logger.debug(f"similarity score was to low for alias to be considered correct (<= 0.7)")
                            logger.debug(f"similarity score: {alias.similarity(secu)} for base:{secu} and alias:{alias}")
                            return None

def _get_SECU_in_doc(doc: Doc):
    secu_spans = []
    for ent in doc.ents:
        if ent.label_ == "SECU":
            secu_spans.append(ent)
    return secu_spans

def _set_single_secu_alias_map(doc: Doc):
        if (doc.spans.get("SECU") is None) or (doc.spans.get("alias") is None):
            raise AttributeError(f"Didnt set spans correctly missing one or more keys of (SECU, alias). keys found: {doc.spans.keys()}")
        single_secu_alias = dict()
        secu_ents = doc._.secus
        for secu in secu_ents:
            secu_key = get_secu_key(secu)
            if secu_key not in single_secu_alias.keys():
                single_secu_alias[secu_key] = {"base": [secu], "alias": []}
            else:
                single_secu_alias[secu_key]["base"].append(secu)
            alias = doc._.get_alias(secu)
            if alias:
                single_secu_alias[secu_key]["alias"].append(alias)
        logger.debug(f"got single_secu_alias map: {single_secu_alias}")
        doc._.single_secu_alias = single_secu_alias

def _set_single_secu_alias_map_as_tuples(doc: Doc):
        if (doc.spans.get("SECU") is None) or (doc.spans.get("alias") is None):
            # print(doc.spans.get("SECU"), doc.spans.get("alias"))
            raise AttributeError(f"Didnt set spans correctly missing one or more keys of (SECU, alias). keys found: {doc.spans.keys()}")
        single_secu_alias_tuples = dict()
        secu_ents = doc._.secus
        for secu in secu_ents:
            # if doc._.is_alias(secu):
            #     continue
            secu_key = get_secu_key(secu)
            if secu_key not in single_secu_alias_tuples.keys():
                single_secu_alias_tuples[secu_key] = {"alias": [], "no_alias": []}
            alias = doc._.get_alias(secu)
            if alias:
                single_secu_alias_tuples[secu_key]["alias"].append((secu, alias))
            else:
                single_secu_alias_tuples[secu_key]["no_alias"].append(secu)
        logger.info(f"single_secu_alias_tuples: {single_secu_alias_tuples}")
        doc._.single_secu_alias_tuples = single_secu_alias_tuples

                

def is_alias(doc: Doc, secu: Span):
    if secu.text in doc._.alias_set:
        return True
    return False

def get_secu_key(secu: Span|str):
    core_tokens = secu if secu[-1].text.lower() not in ["shares"] else secu[:-1] 
    body = [token.text_with_ws.lower() for token in core_tokens[:-1]]
    try:
        tail = core_tokens[-1].lemma_.lower()
        if tail == "warrants":
            tail = "warrant"
        body.append(tail)
    except IndexError:
        logger.debug("IndexError when accessing tail information of secu_key -> no tail -> pass")
        pass
    result = "".join(body) 
    # logger.debug(f"get_secu_key() returning key: {result} from secu: {secu}")
    return result

def set_SECUMatcher_extensions():
    span_extensions = [
        {"name": "secuquantity", "kwargs": {"getter": get_secuquantity}},
        {"name": "secuquantity_unit", "kwargs": {"default": None}}
    ]
    doc_extensions = [
        {"name": "alias_set", "kwargs": {"default": set()}},
        {"name": "tokens_to_alias_map", "kwargs": {"default": dict()}},
        {"name": "single_secu_alias", "kwargs": {"default": dict()}},
        {"name": "single_secu_alias_tuples", "kwargs": {"default": dict()}},
        {"name": "is_alias", "kwargs": {"method": is_alias}},
        {"name": "get_alias", "kwargs": {"method": get_alias}},
        {"name": "secus", "kwargs": {"getter": _get_SECU_in_doc}},
    ]
    def _set_extension(cls, name, kwargs):
        if not cls.has_extension(name):
            cls.set_extension(name, **kwargs)
    for each in span_extensions:
        _set_extension(Span, each["name"], each["kwargs"])
    for each in doc_extensions:
        _set_extension(Doc, each["name"], each["kwargs"])

class SECUMatcher:
    def __init__(self, vocab):
        self.vocab = vocab
        self.matcher_SECU = Matcher(vocab)
        self.matcher_SECUREF = Matcher(vocab)
        self.matcher_SECUATTR = Matcher(vocab)
        self.matcher_SECUQUANTITY = Matcher(vocab)

        set_SECUMatcher_extensions()

        # Span.set_extension("secuquantity", getter=get_secuquantity)
        # Span.set_extension("secuquantity_unit", default=None)
        # Doc.set_extension("get_alias", method=get_alias)
        # Doc.set_extension("alias_set", default=set())
        # Doc.set_extension("tokens_to_alias_map", default=dict())

        # Doc.set_extension("is_alias", method=is_alias)
        # Doc.set_extension("single_secu_alias", default=dict())
        # Doc.set_extension("single_secu_alias_tuples", default=dict())
        # Doc.set_extension("secus", getter=_get_SECU_in_doc)
    
        
        self.add_SECU_ent_to_matcher(self.matcher_SECU)
        self.add_SECUREF_ent_to_matcher(self.matcher_SECUREF)
        self.add_SECUATTR_ent_to_matcher(self.matcher_SECUATTR)
        self.add_SECUQUANTITY_ent_to_matcher(self.matcher_SECUQUANTITY)
    

    def __call__(self, doc: Doc):
        # logger.warning(f"__call__ executed")
        self._init_span_labels(doc)
        self.chars_to_token_map = self.get_chars_to_tokens_map(doc)
        self.set_possible_alias_spans(doc)
        self.set_tokens_to_alias_map(doc)
        self.matcher_SECU(doc)
        self.matcher_SECUREF(doc)
        doc = self.handle_retokenize_SECU(doc)
        self.handle_SECU_special_cases(doc)
        doc = self.handle_retokenize_SECU(doc)
        self.matcher_SECUATTR(doc)
        self.matcher_SECUQUANTITY(doc)
        return doc
    
    def handle_retokenize_SECU(self, doc: Doc):
        doc = retokenize_SECU(doc)
        self.set_possible_alias_spans(doc)
        self.set_tokens_to_alias_map(doc)
        _set_single_secu_alias_map(doc)
        _set_single_secu_alias_map_as_tuples(doc)
        return doc
    
    def _init_span_labels(self, doc: Doc):
        doc.spans["SECU"] = []
        doc.spans["alias"] = []
    
    def handle_SECU_special_cases(self, doc: Doc):
        special_case_matcher = Matcher(self.vocab)
        self.add_alias_SECU_cases_to_matcher(doc, special_case_matcher)
        special_case_matcher(doc)


    def add_alias_SECU_cases_to_matcher(self, doc, matcher):
        # duplicate spans
        # overlapping spans ?
        # side effects of rerunning matcher ? 
        special_patterns = []
        for secu_key, values in doc._.single_secu_alias_tuples.items():
            # logger.info(f"current key: {secu_key}")
            alias_tuples = doc._.single_secu_alias_tuples[secu_key]["alias"]
            # logger.info(f"current alias_tuples: {alias_tuples}")
            if alias_tuples and alias_tuples != []:
                for entry in alias_tuples:
                    base_span = entry[0]
                    alias_span = entry[1]
                    special_patterns.append(
                        [{"LOWER": x.lower_} for x in alias_span]
                    )
                    if len(alias_span) > 1:
                        special_patterns.append(
                            [*[{"LOWER": x.lower_} for x in alias_span[:-1]], {"LEMMA": alias_span[-1].lemma_}]
                        )
        logger.debug(f"adding special alias_SECU patterns to matcher: {special_patterns}")
        matcher.add("alias_special_cases", special_patterns, on_match=_add_SECU_ent)
                    

            
    def get_chars_to_tokens_map(self, doc: Doc):
        chars_to_tokens = {}
        for token in doc:
            for i in range(token.idx, token.idx + len(token.text)):
                chars_to_tokens[i] = token.i
        return chars_to_tokens
    
    def get_tokens_to_alias_map(self, doc: Doc):
        tokens_to_alias_map = {}
        alias_spans = doc.spans["alias"]
        for span in alias_spans:
            for token in span:
                tokens_to_alias_map[token.i] = span
        return tokens_to_alias_map
    
    def get_possible_alias_spans(self, doc: Doc, chars_to_tokens: Dict):
        secu_alias_exclusions = set([
            "we",
            "us",
            "our"
        ])
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
                            alias_span = doc[start_token+1:end_token]
                            if alias_span.text in secu_alias_exclusions:
                                logger.debug(f"Was in secu_alias_exclusions -> discarded alias span: {alias_span}")
                                continue
                            spans.append(alias_span)
                        else:
                            logger.debug(f"couldnt find start/end token for alias: {possible_alias}; start/end token: {start_token}/{end_token}")
        return spans

    def _set_possible_alias_spans(self, doc: Doc, spans: list[Span]):
        doc.spans["alias"] = spans
        
    def set_possible_alias_spans(self, doc: Doc):
        self._set_possible_alias_spans(
            doc,
            self.get_possible_alias_spans(doc, self.chars_to_token_map)
        )
        logger.debug(f"set alias spans: {doc.spans['alias']}")
        for span in doc.spans["alias"]:
            doc._.alias_set.add(span.text)
        logger.debug(f"set alias_set extension: {doc._.alias_set}")
    
    def set_tokens_to_alias_map(self, doc: Doc):
        doc._.tokens_to_alias_map = self.get_tokens_to_alias_map(doc)
        
    
    def add_SECUATTR_ent_to_matcher(self, matcher):
        patterns = [
            [
                {"LOWER": "exercise"},
                {"LOWER": "price"}
            ]
        ]
        matcher.add("SECUATTR_ENT", [*patterns], on_match=_add_SECUATTR_ent)
    
    def add_SECUREF_ent_to_matcher(self, matcher):
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
        # exclude particles, conjunctions from regex match 
        patterns = [
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "warrant", "warrants", "ordinary"]}},
                {"LOWER": {"IN": ["shares"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "warrant", "warrants", "ordinary"]}},
                {"LOWER": {"IN": ["shares"]}}
            ]
                ,
            *[  
                [
                    *general_pre_sec_compound_modifier,
                    {"LOWER": {"IN": ["preferred", "common", "warrant", "warrants", "ordinary"]}},
                    {"LOWER": {"IN": ["shares"]}}
                ] for general_pre_sec_compound_modifier in general_pre_sec_compound_modifiers
            ]
                ,

            
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["warrant", "warrants"]}},
                {"LOWER": {"IN": ["shares"]}}
            ]
  
        ]

        matcher.add("SECUREF_ENT", [*patterns], on_match=_add_SECUREF_ent)

    
    def add_SECU_ent_to_matcher(self, matcher):
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
        depositary_patterns = [
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["depository", "depositary"]}},
                {"LOWER": {"IN": ["shares"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "depository", "depositary", "ordinary"]}},
                {"LOWER": {"IN": ["shares"]}}
            ]
                ,
            *[  
                [
                    *general_pre_sec_compound_modifier,
                    {"LOWER": {"IN": ["depository", "depositary"]}},
                    {"LOWER": {"IN": ["shares"]}, "OP": "?"}
                ] for general_pre_sec_compound_modifier in general_pre_sec_compound_modifiers
            ]
                ,
            
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["depository", "depositary"]}, "OP": "?"},
                {"LOWER": {"IN": ["shares", "stock"]}},
                {"LOWER": {"IN": ["options", "option"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["depository", "depositary"]}, "OP": "?"},
                {"LOWER": {"IN": ["shares", "stock"]}},
                {"LOWER": {"IN": ["options", "option"]}}
            ]

        ]
        patterns = [
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "ordinary"]}},
                {"LOWER": {"IN": ["stock"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "ordinary"]}},
                {"LOWER": {"IN": ["stock"]}}
            ]
                ,
            *[  
                [
                    *general_pre_sec_compound_modifier,
                    {"LOWER": {"IN": ["preferred", "common", "warrant", "warrants", "ordinary"]}},
                    {"LOWER": {"IN": ["stock"]}, "OP": "?"}
                ] for general_pre_sec_compound_modifier in general_pre_sec_compound_modifiers
            ]
                ,
            
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "ordinary"]}, "OP": "?"},
                {"LOWER": {"IN": ["stock"]}},
                {"LOWER": {"IN": ["options", "option"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["preferred", "common", "ordinary"]}, "OP": "?"},
                {"LOWER": {"IN": ["stock"]}},
                {"LOWER": {"IN": ["options", "option"]}}
            ]

                ,
            
            [   {"LOWER": {"IN": general_affixes}}, {"TEXT": {"REGEX": "[a-zA-Z0-9]{1,3}", "NOT_IN": ["of"]}, "OP": "?"},
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["warrant", "warrants"]}}
            ]
                ,
            [
                {"LOWER": {"IN": general_pre_sec_modifiers}, "OP": "?"},
                {"LOWER": {"IN": ["warrant", "warrants"]}},
                {"LOWER": {"IN": ["stock"]}, "OP": "?"}
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
            ]
                ,            
        ]

        matcher.add("SECU_ENT", [*patterns, *depositary_patterns, *special_patterns], on_match=_add_SECU_ent)

    def add_SECUQUANTITY_ent_to_matcher(self, matcher: Matcher):
        
        regular_patterns = [
            [
                {"ENT_TYPE": "CARDINAL", "OP": "+"},
                {"LOWER": {"IN": ["authorized", "outstanding"]}, "OP": "?"},
                {"LOWER": {"IN": ["share", "shares", "warrant shares"]}}
            ],
            
            [   
                {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
                {"LOWER": "of", "OP": "?"},
                {"LOWER": "our", "OP": "?"},
                {"ENT_TYPE": {"IN": ["SECU", "SECUREF"]}}
            ],
            [
                {"ENT_TYPE": {"IN": ["CARDINAL", "MONEY"]}, "OP": "+"},
                {"LOWER": "shares"},
                {"OP": "*", "IS_SENT_START": False, "POS": {"NOT_IN": ["VERB"]}, "ENT_TYPE": {"NOT_IN": ["SECU", "SECUQUANTITY"]}},
                {"LOWER": "of", "OP": "?"},
                {"LOWER": "our", "OP": "?"},
                {"ENT_TYPE": {"IN": ["SECU"]}}
            ]

        ]

        matcher.add("SECUQUANTITY_ENT", [*regular_patterns], on_match=_add_SECUQUANTITY_ent_regular_case)
        logger.info("added SECUQUANTITY patterns to matcher")

def _is_match_followed_by(doc: Doc, start: int, end: int, exclude: list[str]):
    if end == len(doc):
        end -= 1
    if doc[end].lower_ not in exclude:
        return False
    return True

def _is_match_preceeded_by(doc: Doc, start: int, end: int, exclude: list[str]):
    if (start == 0) or (exclude == []):
        return False
    if doc[start-1].lower_ not in exclude:
        return False
    return True

def add_SECU_to_spans(doc: Doc, entity: Span):
    if doc._.is_alias(entity):
        return
    else:
        # logger.debug(f"adding to SECU spans: {entity}")
        add_entity_to_spans(doc, entity, "SECU")

def add_entity_to_spans(doc: Doc, entity: Span, span_label: str):
    if not doc.spans.get(span_label):
        doc.spans[span_label] = []
    doc.spans[span_label].append(entity)

def _add_SECUREF_ent(matcher, doc: Doc, i: int, matches):
    _add_ent(doc, i, matches, "SECUREF", exclude_after=[
            "agreement",
            "agent",
            "indebenture",
            "rights"
            ])


    
def _add_SECU_ent(matcher, doc: Doc, i: int, matches):
    _add_ent(doc, i, matches, "SECU", exclude_after=[
            "agreement",
            "agent",
            "indebenture",
            # "rights",
            "shares"],
            ent_callback=add_SECU_to_spans,
            always_overwrite=["ORG"]
            )

def _add_SECUATTR_ent(matcher, doc: Doc, i: int, matches):
    _add_ent(doc, i, matches, "SECUATTR")

            

def _add_SECUQUANTITY_ent_regular_case(matcher, doc: Doc, i, matches):
    _, match_start, match_end = matches[i]
    match_tokens = [t for t in doc[match_start:match_end]]
    # logger.debug(f"handling SECUQUANTITY for match: {match_tokens}")
    match_id, start, _ = matches[i]
    end = None
    wanted_tokens = []
    for token in match_tokens:
        # logger.debug(f"token: {token}, ent_type: {token.ent_type_}")
        if token.ent_type_ in ["MONEY", "CARDINAL", "SECUQUANTITY"]:
            # end = token.i-1
            wanted_tokens.append(token.i)
    end = sorted(wanted_tokens)[-1]+1 if wanted_tokens != [] else None
    # print(end, wanted_tokens)
    if end is None:
        raise AttributeError(f"_add_SECUQUANTITY_ent_regular_case couldnt determine the end token of the entity, match_tokens: {match_tokens}")
    entity = Span(doc, start, end, label="SECUQUANTITY")
    # logger.debug(f"Adding ent_label: SECUQUANTITY. Entity: {entity} [{start}-{end}], original_match:{doc[match_start:match_end]} [{match_start}-{match_end}]")
    _set_secuquantity_unit_on_span(match_tokens, entity)
    try:
        doc.ents += (entity,)
    except ValueError as e:
        if "[E1010]" in str(e):
            # logger.debug("handling overlapping ents")
            handle_overlapping_ents(doc, start, end, entity)

def _set_secuquantity_unit_on_span(match_tokens: Span, span: Span):
    if span.label_ != "SECUQUANTITY":
        raise TypeError(f"can only set secuquantity_unit on spans of label: SECUQUANTITY. got span: {span}")
    if "MONEY" in [t.ent_type_ for t in match_tokens]:
        span._.secuquantity_unit = "MONEY"
    else:
        span._.secuquantity_unit = "COUNT"

def _add_ent(doc: Doc, i, matches, ent_label: str, exclude_after: list[str]=[], exclude_before: list[str]=[], ent_callback: Callable=None, ent_exclude_condition: Callable=None, always_overwrite: Optional[list[str]]=None):
    '''add a custom entity through an on_match callback.
    
    Args:
        ent_callback: function which will be called if entity was added with the entity and doc as args.
        ent_exclude_condition: function which returns bool and takes entity and doc as args.'''
    match_id, start, end = matches[i]
    if (not _is_match_followed_by(doc, start, end, exclude_after)) and (
        not _is_match_preceeded_by(doc, start, end, exclude_before)):
        entity = Span(doc, start, end, label=ent_label)
        if ent_exclude_condition is not None:
            if ent_exclude_condition(doc, entity) is True:
                logger.debug(f"ent_exclude_condition: {ent_exclude_condition} was True; not adding: {entity}")
                return
        # logger.debug(f"entity: {entity}")
        try:
            doc.ents += (entity,)
            # logger.debug(f"Added entity: {entity} with label: {ent_label}")
        except ValueError as e:
            if "[E1010]" in str(e):
                # logger.debug(f"handling overlapping entities for entity: {entity}")
                handle_overlapping_ents(doc, start, end, entity, overwrite_labels=always_overwrite)
        if (ent_callback) and (entity in doc.ents):
            ent_callback(doc, entity)

def handle_overlapping_ents(doc: Doc, start: int, end: int, entity: Span, overwrite_labels: Optional[list[str]]=None):
    previous_ents = set(doc.ents)
    conflicting_ents = get_conflicting_ents(doc, start, end, overwrite_labels=overwrite_labels)
    # logger.debug(f"conflicting_ents: {conflicting_ents}")
    # if (False not in [end-start >= k[0] for k in conflicting_ents]) and (conflicting_ents != []):
    if conflicting_ents != []:
        [previous_ents.remove(k) for k in conflicting_ents]
        # logger.debug(f"removed conflicting ents: {[k for k in conflicting_ents]}")
        previous_ents.add(entity)
        try:
            doc.ents = previous_ents
        except ValueError as e:
            if "E1010" in str(e):
                token_idx = int(sorted(re.findall(r"token \d*", str(e)), key=lambda x: len(x))[0][6:])
                token_conflicting = doc[token_idx]
                logger.debug(f"token conflicting: {token_conflicting} with idx: {token_idx}")
                logger.debug(f"sent: {token_conflicting.sent}")
                conflicting_entity = []
                for i in range(token_idx, 0, -1):
                    if doc[i].ent_type_ == token_conflicting.ent_type_:
                        conflicting_entity.insert(0, doc[i])
                    else:
                        break
                for i in range(token_idx+1, 10000000, 1):
                    if doc[i].ent_type_ == token_conflicting.ent_type_:
                        conflicting_entity.append(doc[i])
                    else:
                        break

                logger.debug(f"conflicting with entity: {conflicting_entity}")
                raise e
        # logger.debug(f"Added entity: {entity} with label: {entity.label_}")

def get_conflicting_ents(doc: Doc, start: int, end: int, overwrite_labels: Optional[list[str]]=None):
    conflicting_ents = []
    seen_conflicting_ents = []
    covered_tokens = range(start, end)
    for ent in doc.ents:
        # if ent.end == ent.start-1:
        #     covered_tokens = [ent.start]
        # else:               
        # covered_tokens = range(ent.start, ent.end)
        if (ent.start in covered_tokens) or (ent.end-1 in covered_tokens):
            if conflicting_ents == []:
                seen_conflicting_ents.append(ent)
            if ((ent.end - ent.start) <= (end - start)) or (ent.label_ in overwrite_labels if overwrite_labels else False) is True:
                if conflicting_ents == []:
                    conflicting_ents = seen_conflicting_ents
                else:
                    conflicting_ents.append(ent)
    return conflicting_ents

def _get_singular_or_plural_of_SECU_token(token):
    singular = PLURAL_SINGULAR_SECU_TAIL_MAP.get(token.lower_)
    plural = SINGULAR_PLURAL_SECU_TAIL_MAP.get(token.lower_)
    if singular is None:
        return plural
    else:
        return singular
                    
@Language.factory("secu_matcher")
def create_secu_matcher(nlp, name):
    return SECUMatcher(nlp.vocab)

@Language.factory("secu_act_matcher")
def create_secu_act_matcher(nlp, name):
    return SecurityActMatcher(nlp.vocab)

@Language.factory("security_law_retokenizer")
def create_regex_retokenizer(nlp, name):
    return FilingsSecurityLawRetokenizer(nlp.vocab)

@Language.factory("common_financial_retokenizer")
def create_common_financial_retokenizer(nlp, name):
    return CommonFinancialRetokenizer(nlp.vocab)


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
            cls._instance.nlp.add_pipe("secu_act_matcher", first=True)
            cls._instance.nlp.add_pipe("security_law_retokenizer", after="secu_act_matcher")
            cls._instance.nlp.add_pipe("common_financial_retokenizer", after="security_law_retokenizer")
            cls._instance.nlp.add_pipe("secu_matcher")
            # cls._instance.nlp.add_pipe("coreferee")
        return cls._instance
    
    def handle_match_formatting(self, match: tuple[str, list[Token]], formatting_dict: Dict[str, Callable], doc: Doc, *args, **kwargs) -> tuple[str, dict]:
        try:
            match_id = doc.vocab.strings[match[0]]
            logger.debug(f"string_id of match: {match_id}")
        except KeyError:
            raise AttributeError(f"No string_id found for this match_id in the doc: {match_id}")
        tokens = match[1]
        try:
            formatting_func = formatting_dict[match_id]
        except KeyError:
            raise AttributeError(f"No formatting function associated with this match_id: {match_id}")
        else:
            return (match_id, formatting_func(tokens, doc, *args, **kwargs))

    def match_secu_with_dollar_CD(self, doc: Doc, secu: Span):
        dep_matcher = DependencyMatcher(self.nlp.vocab, validate=True)
        secu_root_token = secu.root
        patterns = [
            [
                {
                    "RIGHT_ID": "secu_anchor",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECU", "LOWER": secu_root_token.lower_},
                },
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"IN": ["purchase", "have"]}}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">>",
                    "RIGHT_ID": "CD_",
                    "RIGHT_ATTRS": {"TAG": "CD"}, 
                },
                {
                    "LEFT_ID": "CD_",
                    "REL_OP": ">",
                    "RIGHT_ID": "nmod",
                    "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}, 
                },

            ]
        ]
        dep_matcher.add("secu_cd", patterns)
        matches = dep_matcher(doc)
        if matches:
            matches = _convert_dep_matches_to_spans(doc, matches)
            return [match[1] for match in matches]
        return []
    
    def get_queryable_similar_spans_from_lower(self, doc: Doc, span: Span):
        matcher = Matcher(self.nlp.vocab)
        pattern = [
            [{"LOWER": x.lower_} for x in span]
        ]
        if len(span) > 1:
            tail_lower = _get_singular_or_plural_of_SECU_token(span[-1])
            if tail_lower:
                pattern.append(
                    [*[{"LOWER": x.lower_} for x in span[:-1]], {"LOWER": tail_lower}]
                )
        matcher.add("similar_spans", pattern)
        logger.debug(f"similar_spans_from_lower match patterns: {pattern}")
        matches = matcher(doc)
        return _convert_matches_to_spans(doc, filter_matches(matches)) if matches else None
    
    def get_prep_phrases(self, doc: Doc):
        phrases = []
        seen = set()
        for token in doc:
            if token.dep_ == "prep":
                subtree = [i for i in token.subtree]
                new = True
                for t in subtree:
                    if t in seen:
                        new = False
                if new is True:
                    phrases.append(doc[subtree[0].i:subtree[-1].i])
                    for t in subtree:
                        if t not in seen:
                            seen.add(t)
        return phrases
    
    def get_verbal_phrases(self, doc: Doc):
        phrases = []
        for token in doc:
            if token.pos_ == "VERB":
                subtree = [i for i in token.subtree]
                phrases.append(doc[subtree[0].i:subtree[-1].i])
        return phrases

    def _create_secu_span_dependency_matcher_dict(self, secu: Span) -> dict:
        '''
        create a list of dicts for dependency match patterns.
        the root token will have RIGHT_ID of 'secu_anchor'
        '''
        secu_root_token = secu.root
        if secu_root_token is None:
            return None
        root_pattern = [
            {
                "RIGHT_ID": "secu_anchor",
                "RIGHT_ATTRS": {"ENT_TYPE": secu_root_token.ent_type_, "LOWER": secu_root_token.lower_}
            }
        ]
        if secu_root_token.children:
            for idx, token in enumerate(secu_root_token.children):
                if token in secu:
                    root_pattern.append(
                        {
                            "LEFT_ID": "secu_anchor",
                            "REL_OP": ">",
                            "RIGHT_ID": token.lower_ + "__" + str(idx),
                            "RIGHT_ATTRS": {"LOWER": token.lower_}
                        }
                    )
        return root_pattern
    
    def match_secu_expiry(self, doc: Doc, secu: Span):
        secu_root_pattern = self._create_secu_span_dependency_matcher_dict(secu)
        if secu_root_pattern is None:
            logger.warning(f"couldnt get secu_root_pattern for secu: {secu}")
            return
        dep_matcher = DependencyMatcher(self.nlp.vocab, validate=True)
        patterns = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "expire"}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj1",
                    "RIGHT_ATTRS": {"DEP": "pobj"}, 
                },
            ],
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">>",
                    "RIGHT_ID": "verb2",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "expire"}, 
                },
                {
                    "LEFT_ID": "verb2",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj1",
                    "RIGHT_ATTRS": {"DEP": "pobj"}, 
                },
            ],
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb2",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "exercise"}, 
                },
                {
                    "LEFT_ID": "verb2",
                    "REL_OP": ">>",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "up"}, 
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep2",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "to"}, 
                },
                {
                    "LEFT_ID": "prep2",
                    "REL_OP": ".*",
                    "RIGHT_ID": "prep3",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "on"}, 
                },
                {
                    "LEFT_ID": "prep3",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj1",
                    "RIGHT_ATTRS": {"DEP": "pobj", "LEMMA": "date"}, 
                },
                {
                    "LEFT_ID": "pobj1",
                    "REL_OP": ">",
                    "RIGHT_ID": "verb3",
                    "RIGHT_ATTRS": {"LEMMA": "be"}, 
                },
                {
                    "LEFT_ID": "verb3",
                    "REL_OP": ">",
                    "RIGHT_ID": "attr1",
                    "RIGHT_ATTRS": {"DEP": "attr"}, 
                },
                {
                    "LEFT_ID": "attr1",
                    "REL_OP": ">>",
                    "RIGHT_ID": "issuance1",
                    "RIGHT_ATTRS": {"ENT_TYPE": {"IN": ["ORDINAL", "CARDINAL"]}}, 
                },
            ]
        ]
        dep_matcher.add("expiry", patterns)
        matches = dep_matcher(doc)
        logger.debug(f"raw expiry matches: {matches}")
        if matches:
            matches = _convert_dep_matches_to_spans(doc, matches)
            logger.info(f"matches: {matches}")
            formatted_matches = []
            for match in matches:
                formatted_matches.append(self._format_expiry_match(match[1]))
            return formatted_matches
    
    def _format_expiry_match(self, match):
        # print([(i.ent_type_, i.text) for i in match])
        logger.debug("_format_expiry_match:")
        if match[-1].ent_type_ == "ORDINAL":
            match = match[:-1]
        if match[-1].lower_ != "anniversary":
            try:
                date = "".join([i.text_with_ws for i in match[-1].subtree])
                logger.debug(f"     date tokens joined: {date}")
                date = pd.to_datetime(date)
            except Exception as e:
                logger.debug(f"     failed to format expiry match: {match}")
            else:
                return date
        else:
            date_tokens = [i for i in match[-1].subtree]
            # print(date_tokens, [i.dep_ for i in date_tokens])
            date_spans = []
            date = []
            for token in date_tokens:
                if token.dep_ != "prep":
                    date.append(token)
                else:
                    date_spans.append(date)
                    date = []
            if date != []:
                date_spans.append(date)
            logger.debug(f"     date_spans: {date_spans}")
            dates = []
            deltas = []
            if len(date_spans) > 0:
                #handle anniversary with issuance date
                for date in date_spans:
                    possible_date = formater.coerce_tokens_to_datetime(date)
                    # print(f"possible_date: {possible_date}")
                    if possible_date:
                        dates.append(possible_date)
                    else:
                        possible_delta = formater.coerce_tokens_to_timedelta(date)
                        # print(f"possible_delta: {possible_delta}")
                        if possible_delta:
                            for delta in possible_delta:
                                deltas.append(delta[0])
                if len(dates) == 1:
                    if len(deltas) == 1:
                        return dates[0] + deltas[0]
                    if len(delta) == 0:
                        return dates[0]
                if len(dates) > 1:
                    raise UnclearInformationExtraction(f"unhandled case of extraction found more than one date for the expiry: {dates}")
                if len(deltas) == 1:
                    return deltas[0]
                elif len(deltas) > 1:
                    raise UnclearInformationExtraction(f"unhandled case of extraction found more than one timedelta for the expiry: {deltas}")
            return None
            
    
    def match_secu_exercise_price(self, doc: Doc, secu: Span):
        dep_matcher = DependencyMatcher(self.nlp.vocab, validate=True)
        # secu_root_token = self._get_compound_SECU_root(secu)
        logger.debug("match_secu_exercise_price:")
        logger.debug(f"     secu: {secu}")
        # logger.debug(f"     secu_root_token: ", secu_root_token)
        
        '''
        acl   (SECU) <- VERB (purchase) -> 					 prep (of | at) -> [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (have)  	->				     			       [dobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (purchase) -> 					 prep (at) ->      [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (purchase) -> conj (remain)  -> prep (at) ->      [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (purchase) -> 					 prep (at) ->      [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
        
        relcl (SECU) <- VERB (purchase) >> prep(at) -> 
        '''
        secu_root_dict = self._create_secu_span_dependency_matcher_dict(secu)
        if secu_root_dict is None:
            return None
        patterns = [
            [
                *secu_root_dict,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": ">",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">>",
                    "RIGHT_ID": "prepverb1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
                },
                {
                    "LEFT_ID": "prepverb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "price",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "compound",
                    "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj_CD",
                    "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
                },
                {
                    "LEFT_ID": "pobj_CD",
                    "REL_OP": ">",
                    "RIGHT_ID": "dollar",
                    "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
                } 
            ],
            [
                *secu_root_dict,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "conj",
                    "RIGHT_ATTRS": {"DEP": "conj", "LEMMA": {"IN": ["remain"]}},
                },
                {
                    "LEFT_ID": "conj",
                    "REL_OP": ">",
                    "RIGHT_ID": "prepverb1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
                },
                {
                    "LEFT_ID": "prepverb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "price",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "compound",
                    "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj_CD",
                    "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
                },
                {
                    "LEFT_ID": "pobj_CD",
                    "REL_OP": ">",
                    "RIGHT_ID": "dollar",
                    "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
                } 
            ],
            [
                *secu_root_dict,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": ">",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "prepverb1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
                },
                {
                    "LEFT_ID": "prepverb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "price",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "compound",
                    "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj_CD",
                    "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
                },
                {
                    "LEFT_ID": "pobj_CD",
                    "REL_OP": ">",
                    "RIGHT_ID": "dollar",
                    "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
                } 
            ],
            [
                *secu_root_dict,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LOWER": "purchase"}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "prepverb1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": {"IN": ["of", "at"]}}, 
                },
                {
                    "LEFT_ID": "prepverb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "price",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "compound",
                    "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj_CD",
                    "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
                },
                {
                    "LEFT_ID": "pobj_CD",
                    "REL_OP": ">",
                    "RIGHT_ID": "dollar",
                    "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
                } 
            ],
            [
                *secu_root_dict,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": "have"}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "price",
                    "RIGHT_ATTRS": {"DEP": {"IN": ["nobj", "pobj", "dobj"]}, "LOWER": "price"}, 
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "compound",
                    "RIGHT_ATTRS": {"DEP": "compound", "LOWER": "exercise"}
                },
                {
                    "LEFT_ID": "price",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep1",
                    "RIGHT_ATTRS": {"DEP": "prep", "LOWER": "of"}
                },
                {
                    "LEFT_ID": "prep1",
                    "REL_OP": ">",
                    "RIGHT_ID": "pobj_CD",
                    "RIGHT_ATTRS": {"DEP": "pobj", "TAG": "CD"}
                },
                {
                    "LEFT_ID": "pobj_CD",
                    "REL_OP": ">",
                    "RIGHT_ID": "dollar",
                    "RIGHT_ATTRS": {"DEP": "nmod", "TAG": "$"}
                }  
            ]
        ]
        dep_matcher.add("exercise_price", patterns)
        matches = dep_matcher(doc)
        logger.debug(f"raw exercise_price matches: {matches}")
        if matches:
            matches = _convert_dep_matches_to_spans(doc, matches)
            logger.info(f"matches: {matches}")
            secu_dollar_CD = self.match_secu_with_dollar_CD(doc, secu)
            if len(secu_dollar_CD) > 1:
                logger.info(f"unhandled ambigious case of exercise_price match: matches: {matches}; secu_dollar_CD: {secu_dollar_CD}")
                return None
            def _get_CD_object_from_match(match):
                for token in match:
                    if token.tag_ == "CD":
                        return formater.money_string_to_float(token.text)
            return [_get_CD_object_from_match(match[1]) for match in matches]


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
            {"ENT_TYPE": "SECU", "OP":"*"},
            {"IS_SENT_START": False, "OP": "*"},
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
    
    def get_secuquantities(self, doc: Doc, secu: Span):
        ''''match secuquantity and source_secu, secu, close verbs'''
        dep_matcher = DependencyMatcher(self.nlp.vocab, validate=True)
        secu_root_pattern = self._create_secu_span_dependency_matcher_dict(secu)
        # have dict of conversion functions to match_id
        # have a handle_match_formatting function
        # so we can convert each match to a sensible dictionary
        # dict should include direct verbs, direct adjectives, source_secu
        secuquantity_shares_no_verb = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"DEP": "prep"}
                },
                {
                    "LEFT_ID": "prep",
                    "REL_OP": "<",
                    "RIGHT_ID": "noun",
                    "RIGHT_ATTRS": {"POS": "NOUN", "LOWER": {"IN": ["shares"]}}
                },
                {
                    "LEFT_ID": "noun",
                    "REL_OP": ">",
                    "RIGHT_ID": "secuquantity",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
                }

            ]
        ]
        secuquantity_no_verb = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": ">",
                    "RIGHT_ID": "secuquantity",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
                }

            ]
        ]
        secuquantity_verb_second_order_noun_no_source_secu = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"IN": ["relate"]}}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"DEP": "prep"}, 
                },
                {
                    "LEFT_ID": "prep",
                    "REL_OP": ">",
                    "RIGHT_ID": "noun_relation",
                    "RIGHT_ATTRS": {"POS": "NOUN"}, 
                },
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "any",
                    "RIGHT_ATTRS": {"POS": "NOUN"}
                },
                {
                    "LEFT_ID": "any",
                    "REL_OP": ">",
                    "RIGHT_ID": "secuquantity",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
                }
            ]
        ]
        secuquantity_verb_second_order_noun_source_secu = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"IN": ["relate"]}}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"DEP": "prep"}, 
                },
                {
                    "LEFT_ID": "prep",
                    "REL_OP": ">",
                    "RIGHT_ID": "noun_relation",
                    "RIGHT_ATTRS": {"POS": "NOUN"}, 
                },
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "any",
                    "RIGHT_ATTRS": {"POS": "NOUN"}
                },
                {
                    "LEFT_ID": "any",
                    "REL_OP": ">",
                    "RIGHT_ID": "secuquantity",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": "<",
                    "RIGHT_ID": "source_secu",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECU"}, 
                }
            ]
        ]
        secuquantity_verb_patterns = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB", "LEMMA": {"NOT_IN": ["purchase", "acquire"]}}, 
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": ">>",
                    "RIGHT_ID": "secuquantity",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
                }
            ]
        ]
        secuquantity_verb_source_secu_patterns = [
            [
                *secu_root_pattern,
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "verb1",
                    "RIGHT_ATTRS": {"POS": "VERB"}
                },
                {
                    "LEFT_ID": "secu_anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "any",
                    "RIGHT_ATTRS": {}
                },
                {
                    "LEFT_ID": "any",
                    "REL_OP": ">",
                    "RIGHT_ID": "secuquantity",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECUQUANTITY"}
                },
                {
                    "LEFT_ID": "verb1",
                    "REL_OP": "<",
                    "RIGHT_ID": "source_secu",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECU"}, 
                },

            ]
        ]
        def format_match_secuquantity_shares_no_verb(match, doc: Doc, root_pattern_len: int):
            secu = match[:root_pattern_len]
            rest = match[root_pattern_len:]
            unit = rest[1]
            quantity = rest[2]
            return {
                "main_secu": secu,
                "unit": unit,
                "quantity": quantity
            }

        def format_match_secuquantity_no_verb(match, doc: Doc, root_pattern_len: int):
            secu = match[:root_pattern_len]
            rest = match[root_pattern_len:]
            quantity = rest[0]
            return {
                "main_secu": secu,
                "unit": None,
                "quantity": quantity
            }

        def format_match_secuquantity_verb_second_order_noun_no_source_secu(match, doc: Doc, root_pattern_len: int):
            secu = match[:root_pattern_len]
            rest = match[root_pattern_len:]
            preceding_root_verb = rest[0]
            noun_to_verb = rest[2]
            quantity = rest[4]
            return {
                "main_secu": secu,
                "root_verb": preceding_root_verb,
                "root_noun": noun_to_verb,
                "quantity": quantity,
                "source_secu": None,
            }

        def format_match_secuquantity_verb_second_order_noun_source_secu(match, doc: Doc, root_pattern_len: int):
            secu = match[:root_pattern_len]
            rest = match[root_pattern_len:]
            preceding_root_verb = rest[0]
            noun_to_verb = rest[2]
            quantity = rest[4]
            source_secu_token = rest[5]
            source_secu_span = extend_token_ent_to_span(source_secu_token, doc)
            return {
                "main_secu": secu,
                "root_verb": preceding_root_verb,
                "root_noun": noun_to_verb,
                "quantity": quantity,
                "source_secu": source_secu_span,
            }

        def format_match_secuquantity_verb_source_secu(match, doc: Doc, root_pattern_len: int):
            secu = match[:root_pattern_len]
            rest = match[root_pattern_len:]
            preceding_root_verb = rest[0]
            quantity = rest[2]
            source_secu_token = rest[3]
            source_secu_span = extend_token_ent_to_span(source_secu_token, doc)
            return {
                "main_secu": secu,
                "root_verb": preceding_root_verb,
                "root_noun": None,
                "quantity": quantity,
                "source_secu": source_secu_span,
            }
            # get full secu span from source_secu_token
            # return dict

        def format_match_secuquantity_verb(match, doc: Doc, root_pattern_len: int):
            secu = match[:root_pattern_len]
            rest = match[root_pattern_len:]
            preceding_root_verb = rest[0]
            quantity = rest[1]
            return {
                "main_secu": secu,
                "root_verb": preceding_root_verb,
                "root_noun": None,
                "quantity": quantity,
                "source_secu": None,
            }
        
        formatting_dict = {
            "secuquantity_shares_no_verb": format_match_secuquantity_shares_no_verb,
            "secuquantity_no_verb": format_match_secuquantity_no_verb,
            "secuquantity_verb": format_match_secuquantity_verb,
            "secuquantity_verb_source_secu": format_match_secuquantity_verb_source_secu,
            "secuquantity_verb_second_order_noun": format_match_secuquantity_verb_second_order_noun_no_source_secu,
            "secuquantity_verb_second_order_noun_source_secu": format_match_secuquantity_verb_second_order_noun_source_secu,
        }
            

        dep_matcher.add("secuquantity_shares_no_verb", secuquantity_shares_no_verb)
        dep_matcher.add("secuquantity_no_verb", secuquantity_no_verb)
        dep_matcher.add("secuquantity_verb", secuquantity_verb_patterns)
        dep_matcher.add("secuquantity_verb_source_secu", secuquantity_verb_source_secu_patterns)
        dep_matcher.add("secuquantity_verb_second_order_noun", secuquantity_verb_second_order_noun_no_source_secu)
        dep_matcher.add("secuquantity_verb_second_order_noun_source_secu", secuquantity_verb_second_order_noun_source_secu)

        matches = dep_matcher(doc)

        def _filter_dep_matches(matches):
            '''take the longest of the dep matches with same start token, discard rest'''
            if len(matches) <= 1:
                return matches
            len_map = {}
            result_map = {}
            for match in matches:
                if match[1][0] not in len_map.keys():
                    len_map[match[1][0]] = len(match[1])
                    result_map[match[1][0]] = match
                else:
                    current_len = len(match[1])
                    if current_len <= len_map[match[1][0]]:
                        pass
                    else:
                        len_map[match[1][0]] = len(match[1])
                        result_map[match[1][0]] = match
            return [v for _, v in result_map.items()]


        if matches:
            matches = _filter_dep_matches(matches)
            matches = _convert_dep_matches_to_spans(doc, matches)
            # logger.debug(f"raw but converted matches: {matches}")
            root_pattern_len = len(secu_root_pattern)
            formatted_matches = [self.handle_match_formatting(match, formatting_dict, doc, root_pattern_len) for match in matches]
            logger.debug(f"formatted matches: {formatted_matches}")
            return formatted_matches
        else:
            logger.debug(f"no secu_and_secuquantity matches found")
            return None
    
    def get_head_verbs(self, token: Token):
        # DEBUG CODE
        verbs = []
        for t in [i for i in token.ancestors] + [i for i  in token.children]:
            if t.pos_ == "VERB":
                verbs.append(t)
        return verbs
    
    def get_SECU_subtree_adjectives(self, token: Token):
        # DEBUG CODE
        adj = []
        for t in [i for i in token.subtree]:
            if (t.tag_ == "JJ") and (t.ent_type_ != "SECU"):
                adj.append(t)
        return adj


    def match_outstanding_shares(self, text):
        pattern1 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": {"IN": ["CARDINAL", "SECUQUANTITY"]}},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["outstanding", "stockoutstanding"]}}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "DATE", "OP": "?"}, {"OP": "?"}, {"ENT_TYPE": "DATE", "OP": "*"}]
        pattern2 = [{"LEMMA": "base"},{"LEMMA": {"IN": ["on", "upon"]}},{"ENT_TYPE": {"IN": ["CARDINAL", "SECUQUANTITY"]}},{"IS_PUNCT":False, "OP": "*"},{"LOWER": "outstanding"}, {"LOWER": "shares"}, {"IS_PUNCT":False, "OP": "*"},{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "DATE", "OP": "?"}, {"OP": "?"}, {"ENT_TYPE": "DATE", "OP": "*"}]
        pattern3 = [{"LOWER": {"IN": ["of", "on"]}}, {"ENT_TYPE": "DATE", "OP": "+"}, {"ENT_TYPE": "DATE", "OP": "?"}, {"OP": "?"}, {"ENT_TYPE": "DATE", "OP": "*"}, {"OP": "?"}, {"ENT_TYPE": {"IN": ["CARDINAL", "SECUQUANTITY"]}}, {"IS_PUNCT":False, "OP": "*"}, {"LOWER": {"IN": ["issued", "outstanding"]}}]
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
                if ent.label_ in ["CARDINAL", "SECUQUANTITY"]:
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
    
    # def match_issuabel_secu_primary(self, doc: Doc, primary_secu: Span)
    
    def match_issuable_secu_primary(self, doc: Doc):
        secu_transformative_actions = ["exercise", "conversion", "redemption"]
        part1 = [
            [
                {"ENT_TYPE": "SECUQUANTITY", "OP": "+"},
                {"OP": "?"},
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
            p1 = part1[0]
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
            {"ENT_TYPE": "SECUQUANTITY", "OP": "+"},
            {"OP": "?"},
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
        matcher.add("secu_issuabel_relation_primary_secu", [*primary_secu_pattern])
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
    
    def match_issuable_secu_no_primary(self, doc: Doc):
        secu_transformative_actions = ["exercise", "conversion", "redemption"]
        part1 = [
            [
                {"ENT_TYPE": "SECUQUANTITY", "OP": "+"},
                {"OP": "?"},
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
                            *part1[0],
                            {"LOWER": transformative_action},
                            {"OP": "*", "IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}},
                            *p2,
                            {"LOWER": "of"},
                            {"ENT_TYPE": "SECU", "OP": "+"}
                            ]
                no_primary_secu_pattern.append(pattern)
        matcher = Matcher(self.nlp.vocab)
        matcher.add("secu_issuable_relation_no_primary_secu", [*no_primary_secu_pattern])
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
        return matches
    
    def match_issuable_secu_no_exercise_price(self, doc: Doc):
        secu_transformative_actions = ["exercise", "conversion", "redemption"]
        part1 = [
            [
                {"ENT_TYPE": "SECUQUANTITY", "OP": "+"},
                {"OP": "?"},
                {"LOWER": "issuable"},
                {"LOWER": "upon"}
            ],
            [
                {"ENT_TYPE": "SECUQUANTITY", "OP": "+"},
                {"OP": "?"},
                {"LOWER": "of"},
                {"LOWER": "our", "OP": "?"},
                {"ENT_TYPE": "SECU", "OP": "+"},
                {"LOWER": "issuable"},
                {"LOWER": "upon"},
                {"LOWER": "the", "OP": "?"}
            ]
        ]
        patterns = []
        for transformative_action in secu_transformative_actions:
            for p1 in part1:
                pattern = [
                            *p1,
                            {"LOWER": transformative_action},
                            {"IS_SENT_START": False, "LOWER": {"NOT_IN": [";", "."]}, "ENT_TYPE": {"NOT_IN": ["SECUATTR"]}, "OP": "*"},
                            {"LOWER": "of"},
                            {"ENT_TYPE": "SECU", "OP": "+"}
                            ]
                patterns.append(pattern)
        matcher = Matcher(self.nlp.vocab)
        matcher.add("secu_issuable_relation_no_exercise_price", [*patterns])
        matches = _convert_matches_to_spans(doc, filter_matches(matcher(doc, as_spans=False)))
        return matches

def extend_token_ent_to_span(token: Token, doc: Doc) -> list[Token]:
    span_tokens = [token]
    logger.debug(f"extending ent span to surrounding for origin token: {token, token.i}")
    for i in range(token.i-1, 0, -1):
        if doc[i].ent_type_ == token.ent_type_:
            span_tokens.insert(0, doc[i])
            logger.debug(f"found preceding token matching ent: {doc[i]}")
        else:
            break
    for i in range(token.i+1, 10000000, 1):
        if doc[i].ent_type_ == token.ent_type_:
            span_tokens.append(doc[i])
            logger.debug(f"found following token matching ent: {doc[i]}")
        else:
            break
    logger.debug(f"making tokens to span: {span_tokens}")
    if len(span_tokens) <= 1:
        span = Span(doc, token.i, token.i+1, label=token.ent_type_)
        logger.debug(f"returning span: {span, span.text}")
        return span
    span = Span(doc, span_tokens[0].i, span_tokens[-1].i+1, label=token.ent_type_)
    logger.debug(f"span: {span, span.text}")
    return span

    
def filter_matches(matches):
    '''works as spacy.util.filter_spans but for matches'''
    if len(matches) <= 1:
        return matches
    # logger.debug(f"pre filter matches: {[m for m in matches]}")
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


def _convert_matches_to_spans(doc, matches):
    m = []
    for match in matches:
        m.append(doc[match[1]:match[2]])
    return m

def _convert_dep_matches_to_spans(doc, matches) -> list[tuple[str, list[Token]]]:
    m = []
    for match in matches:
        m.append((match[0], [doc[f] for f in match[1]]))
    return m

def validate_filing_values(values, attributes):
    '''validate a flat filing value'''
    for attr in attributes:
        if attr not in values.keys():
            raise AttributeError
