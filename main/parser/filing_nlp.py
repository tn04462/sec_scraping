import spacy
from spacy.matcher import Matcher, DependencyMatcher
from spacy.tokens import Span, Doc
from spacy import Language
from spacy.util import filter_spans
import logging

logger = logging.getLogger(__name__)

def int_to_roman(input):
    """ Convert an integer to a Roman numeral. """

    if not isinstance(input, type(1)):
        raise TypeError, "expected integer, got %s" % type(input)
    if not 0 < input < 4000:
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
    return ["(" + int_to_roman(i)+")" for i in range(50)]

def alphabetic_list():
    return ["(" + letter +")" for letter in list(str.ascii_lowercase)]

def numeric_list():
    return ["(" + number + ")" for number in range(150)]

class SecurityActMatcher:
    _instance = None

    def __init__(self, vocab):
        self.matcher = Matcher(vocab)
        self.add_1933_to_matcher()
    
    def __call__(self, doc):
        self.matcher(doc)
        return doc 
    
    def add_1933_act_to_matcher(self):
        romans = roman_list()
        numerals = numeric_list()
        letters = alphabetic_list()
        upper_letters = [a.upper() for a in letters]
        patters = [
            {"LOWER": {"IN": sum([romans, numerals, letters, upper_letters], [])}, "OP": "*"}

        ]


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
