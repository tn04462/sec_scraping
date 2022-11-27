from collections import defaultdict
from dataclasses import dataclass
from itertools import product
from typing import Any, Callable, Dict, Optional, Set
import spacy
from spacy.matcher import Matcher, DependencyMatcher
from spacy.tokens import Span, Doc, Token
from spacy import Language
import logging
import string
import re
import  pandas as pd
from pandas import Timestamp


from main.parser.filing_nlp_utils import MatchFormater
from main.parser.filing_nlp_patterns import (
    SECU_DATE_RELATION_PATTERNS_FROM_ROOT_VERB,
    SECU_SECUQUANTITY_PATTERNS,
    SECU_EXERCISE_PRICE_PATTERNS,
    SECU_EXPIRY_PATTERNS,
    SECU_ENT_REGULAR_PATTERNS,
    SECU_ENT_DEPOSITARY_PATTERNS,
    SECU_ENT_SPECIAL_PATTERNS,
    SECUQUANTITY_ENT_PATTERNS,
    SECU_DATE_RELATION_PATTERNS_FROM_ROOT_VERB,
    SECU_DATE_RELATION_FROM_ROOT_VERB_CONTEXT_PATTERNS,
    VERB_NEGATION_PATTERNS,
    ADJ_NEGATION_PATTERNS,
    SECU_GET_EXPIRY_DATE_LEMMA_COMBINATIONS,
    SECU_GET_EXERCISE_DATE_LEMMA_COMBINATIONS,


)
from main.parser.filing_nlp_constants import (
    PLURAL_SINGULAR_SECU_TAIL_MAP,
    SINGULAR_PLURAL_SECU_TAIL_MAP,
    SECUQUANTITY_UNITS,
    ATTRIBUTE_KEY_TO_STRINGKEY,
    DEPENDENCY_ATTRIBUTE_MATCHER_IS_OPTIONAL_FLAG,
)

logger = logging.getLogger(__name__)
formater = MatchFormater()


class UnclearInformationExtraction(Exception):
    pass


class DependencyNode:
    #TODO: review if I will ever use this, otherwise move to own project or delete
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


def add_anchor_pattern_to_patterns(anchor_pattern: list[dict], patterns: list[list[dict]]) -> list[list[dict]]:
    if not any([False if entry["RIGHT_ID"] != "anchor" else True for entry in anchor_pattern]):
        raise ValueError("Anchor pattern must contain an anchor token with RIGHT_ID = 'anchor'")
    finished_patterns = [None] * len(patterns)
    for idx, pattern in enumerate(patterns):
        finished_patterns[idx] = anchor_pattern + pattern
    return finished_patterns


class DependencyMatchHelper:
    def _convert_key_to_stringkey(self, key: str) -> str:
        return key.lower() + "_"       

    def _has_attributes(self, token: Token, attrs: dict) -> bool:
        # logger.debug(f"checking if token {token} has attributes {attrs}.")
        # logger.debug(f"{[(attr, getattr(token, ATTRIBUTE_KEY_TO_STRINGKEY[attr])) for attr in attrs]}")
        if not isinstance(attrs, dict):
            raise TypeError(f"expecting a dict, got: {type(attrs)}")
        if attrs == {}:
            return True
        for attr, value in attrs.items():
            attribute_name = ATTRIBUTE_KEY_TO_STRINGKEY[attr]
            if isinstance(value, dict):
                for modifier, values in value.items():
                    if modifier in ["IN", "NOT_IN"]:
                        if modifier == "IN":
                            if not getattr(token, attribute_name) in values:
                                return False
                            else:
                                pass
                        if modifier == "NOT_IN":
                            if getattr(token, attribute_name) in values:
                                return False
                            else:
                                pass
            else:
                if not getattr(token, attribute_name) == value:
                    return False
        return True

    def check_head(self, token: Token, attrs: dict) -> Token:
        result = []
        if not token.head:
            return result
        if self._has_attributes(token.head, attrs):
            result.append(token.head)
            return result
        else:
            return result

    def check_children(self, token: Token, attrs: dict) -> list[Token]:
        result = []
        if not token.children:
            return result

        for i in filter(lambda x: x is not None,
                    [child
                    if self._has_attributes(child, attrs)
                    else None
                    for child in token.children]
        ):
            result.append(i)
        return result

    def check_ancestors(self, token: Token, attrs: dict) -> list[Token]:
        result = []
        if not token.ancestors:
            return result
        for ancestor in token.ancestors:
            if self._has_attributes(ancestor, attrs):
                result.append(ancestor)
        return result

    def check_descendants(self, token: Token, attrs: dict) -> list[Token]:
        result = []
        if not token.subtree:
            return result
        for descendant in token.subtree:
            if token == descendant:
                continue
            if self._has_attributes(descendant, attrs):
                result.append(descendant)
        return result


class DependencyAttributeMatcher():
    '''
    Find a specific dependency from an origin token. 
    Currently not all of the standard operations of a SpaCy pattern dict 
    is covered, covered attributes and modifiers are:
        standard attributes:
            "POS"
            "LOWER"
            "TAG"
            "ORTH"
            "DEP"
            "ENT_TYPE"
            "LEMMA"
        set modifiers:
            "IN"
            "NOT_IN"
    
    additional entries to the pattern dict:
        "IS_OPTIONAL": bool (wether a match on this token is optional)

    example pattern dict with anchor:
        [
            {
                "RIGHT_ID": "anchor",
                "TOKEN": origin_token   
            },
            {
                "LEFT_ID": "anchor",
                "REL_OP": ">>",
                "RIGHT_ID": "aux_verb",
                "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}},
            }
        ]

    '''
    # need to resolve what happens if an optional token isnt found and what happens to its children
    dep_getter = DependencyMatchHelper()
    DEPENDENCY_OPS = {
        "<<": dep_getter.check_ancestors,
        "<": dep_getter.check_head,
        ">": dep_getter.check_children,
        ">>": dep_getter.check_descendants
    }

    def run_patterns_for_match(self, complete_patterns: list[list[dict]]) -> list[list]:
        matches = []
        for pattern in complete_patterns:
            matches += self.get_candidate_matches(pattern)
        return matches if matches != [] else None 

    def _get_tokens_with_tag_from_match_tuples(self, match: list[tuple[Token, str]], tag: str) -> Token|None:
        if not match:
            yield None
        if len(match) == 0:
            yield None
        for entry in match:
            token, right_id = entry
            if right_id == tag:
                yield token
        yield None

    def _get_anchor_pattern(self, anchor: Token):
        if not isinstance(anchor, Token):
            raise TypeError(f"anchor must be a Token to correctly match, got {type(anchor)}")
        return [{
            "RIGHT_ID": "anchor",
            "TOKEN": anchor
        }]

    def _get_matches(self, dependant: Token, attr: list[dict]):
        # logger.debug(f"getting matches for {dependant} and attr: {attr}")
        rel_op = attr["REL_OP"]
        matches = self.DEPENDENCY_OPS[rel_op](dependant, attr["RIGHT_ATTRS"])
        # logger.debug(f"got matches: {matches}; for (dependant: {dependant}; attr: {attr})")
        return matches


    def _get_attr_tree(self, attrs: list[dict]):
        right_id_to_idx = {}
        for idx, attr in enumerate(attrs):
            # logger.debug(f"currently working on attr: {attr}")
            # logger.debug(f"with idx: {idx}")
            right_id_to_idx[attr["RIGHT_ID"]] = idx
        tree = defaultdict(list)
        root = None
        for idx, attr in enumerate(attrs):
            if "REL_OP" in attr:
                tree[right_id_to_idx[attr["LEFT_ID"]]].append((attr["REL_OP"], idx))
            else:
                root = idx
        return tree, root
    
    def _conditions_optional(self, attr: dict):
        booleans = []
        for key, value in attr["RIGHT_ATTRS"].items():
            if key == "OP":
                if value == "?":
                    booleans.append(True)
            else:
                booleans.append(False)
        return any(booleans)
    
    def get_candidate_matches(self, attrs: list[dict]) -> list[list[tuple[Token, str]]]:
        tree, root = self._get_attr_tree(attrs)
        # logger.debug(f"tree: {tree}; root: {root}")
        candidates_cache = {k: [] for k, _ in enumerate(attrs)}
        root_attr = None
        candidates_cache[root].append((attrs[root]["TOKEN"], attrs[root]["RIGHT_ID"]))
        # logger.debug(f"inital candidates_cache: {candidates_cache}")
        def resolve_matching_from_node(node, candidates_cache, tree):
            if not tree.get(node):
                return 
            else:
                children = tree.get(node)
                # print(f"children: {children}")
                for child in children:
                    rel_op, child_idx = child
                    # print(f"\t rel_op, child_idx: {rel_op}, {child_idx}")
                    for parent, parent_right_id in candidates_cache[node]:
                        # print(f"\t\t parent, parent_right_id: {parent}, {parent_right_id}")
                        matches = self._get_matches(parent, attrs[child_idx])
                        # print("\t\t ",matches)
                        is_optional = attrs[child_idx].get("IS_OPTIONAL", None)
                        right_id = attrs[child_idx]["RIGHT_ID"]
                        if is_optional and not matches:
                            candidates_cache[child_idx].append((DEPENDENCY_ATTRIBUTE_MATCHER_IS_OPTIONAL_FLAG, right_id))
                        if matches:
                            for match in matches:
                                candidates_cache[child_idx].append((match, right_id))
                        else:
                            if is_optional:
                                continue 
                            # continue and add placeholder if matching this token is optional else return -1
                            # logger.debug(f"breaking out and returning -1")
                            return -1
                    # logger.debug(f"continuing with recursion.")
                    resolve_matching_from_node(child_idx, candidates_cache, tree)
        found_matches = resolve_matching_from_node(root, candidates_cache, tree)
        # logger.debug(f"final candidates_cache: {candidates_cache}")
        if found_matches == -1:
            return []
        else:
            def build_matches_from_candidates(candidates_cache, tree):
                unprocessed_matches = [i for i in product(*[candidates_cache[k] for k in candidates_cache])]
                processed_matches = []
                for unprocessed in unprocessed_matches:
                    processed_entry = []
                    for entry in unprocessed:
                        if isinstance(entry[0], type(DEPENDENCY_ATTRIBUTE_MATCHER_IS_OPTIONAL_FLAG)):
                            if entry[0] == DEPENDENCY_ATTRIBUTE_MATCHER_IS_OPTIONAL_FLAG:
                                pass
                        else:
                            processed_entry.append(entry)
                    processed_matches.append(processed_entry)
                return processed_matches
            return build_matches_from_candidates(candidates_cache, tree)


class DatefulRelation:
    def _format_context_as_lemmas(self, context: dict[str, list[Token]]) -> dict[str, set[str]]:
        if context is None:
            return {}
        lemma_dict = defaultdict(set)
        for key, tokens in context.items():
            if tokens:
                for token in tokens:
                    lemma_dict[key].add(token.lemma_)
        return lemma_dict


class DatetimeRelation(DatefulRelation):
    def __init__(self, spacy_date: Span, timestamp: Timestamp, context: dict[str, list[Token]]):
        self.spacy_date = spacy_date
        self.timestamp = timestamp
        self.context = context
        self.lemmas = self._format_context_as_lemmas(context.get("formatted", None) if context != [] else None)
    
    def __repr__(self):
        return f"{self.spacy_date} - {self.context}"
    
    def __eq__(self, other):
        if isinstance(other, DatetimeRelation):
            if (
                (self.spacy_date == other.spacy_date) and 
                (self.timestamp == other.timestamp) and
                (self.lemmas == other.lemmas) and
                (self.context == other.context)
            ):
                return True
        return False

class SecurityDependencyAttributeMatcher(DependencyAttributeMatcher):
    def __init__(self):
        super().__init__()


    def _filter_negated(self, args):
        # TODO: can this be done as simple as checking ._.negated on the main verb/adj ?
        pass

    # TODO: is get_exercise_price and get_expiry_date in the correct location here, or should it be moved to either SECU or somewhere else?
    # eg in a class that handles the information of date_relation and quantities to form a definitv object (eg: exercise_price with date, expiry ect)
    def get_exercise_price(self, secu: Token):
        prices = self._get_exercise_price(secu)
        if not prices:
            return None
        if len(prices) > 1:
            # NOTE: handling price ranges in a security class "warrants have exercise prices between 10 and 20" ect. I mostlikely cant link it back to a specific security i will just ignore it for now
            logger.info("Multiple exercise prices found, current case only handles one. pretending we didnt find any.")
            logger.info(f"actual prices found were: {prices}")
        else:
            return (formater.money_string_to_float(prices[0][0].text), prices[0][1].text)
    
    def _get_exercise_price(self, secu: Token):
        anchor_pattern = self._get_anchor_pattern(secu)
        complete_pattern = add_anchor_pattern_to_patterns(anchor_pattern, SECU_EXERCISE_PRICE_PATTERNS)
        longest_match = []
        for pattern in complete_pattern:
            candidate_matches = self.get_candidate_matches(pattern)
            if candidate_matches:
                for match in candidate_matches:
                    if len(match) > len(longest_match):
                        longest_match = match
        result = []
        if len(longest_match) > 0:
            amount, symbol = None, None
            for currency_amount in self._get_tokens_with_tag_from_match_tuples(longest_match, "pobj_CD"):
                for currency_symbol in self._get_tokens_with_tag_from_match_tuples(longest_match, "currency_symbol"):
                    if currency_symbol is None:
                        break
                    symbol = currency_symbol
                if currency_amount is None:
                    break
                amount = currency_amount
            if amount is None or symbol is None:
                logger.debug(f"couldnt extract the amount:{amount} or the symbol:{symbol} from the match: {longest_match}")
            result.append((amount, symbol))
        return result

    def get_date_relation(self, token: Token) -> dict:
        unformatted_dates = []
        unformatted_dates += self._get_date_relation_through_root_verb(token)
        # TODO: think and write how i will need the timedelta part of this and how it could be used
        dates = {"datetime": [], "timedelta": []}
        contexts = []
        for unformatted in unformatted_dates:
            context = self._get_context_for_date_relation(unformatted.root)
            date = formater.coerce_tokens_to_datetime(unformatted)
            if date:
                relation = DatetimeRelation(unformatted, date, context)
                if relation not in dates["datetime"]:
                    dates["datetime"].append(relation)
            else:
                date = formater.coerce_tokens_to_timedelta(unformatted)
                if date:
                    dates["timedelta"].append({"date": date, "context": context})
        return dates
        # TODO: fix the implementation of date_relation in a SECU context since we should only have one date in a specific context, right?
        # we should only have one date in a quantity context otherwise we cant be certain how they relate ?
        # options: 1) create a set of the datetimerelations and check if len <= 1 when assigning to quantity

    def _get_context_for_date_relation(self, date_root_token: Token) -> dict:
        '''
        Returns:
            {"original": list[tuple], "formatted": dict[str, dict]}
        '''
        logger.debug(f"getting context for date relation with root token: {date_root_token}")
        date_root_pattern = self._get_anchor_pattern(date_root_token)
        complete_patterns = add_anchor_pattern_to_patterns(date_root_pattern, SECU_DATE_RELATION_FROM_ROOT_VERB_CONTEXT_PATTERNS)
        matches = self.run_patterns_for_match(complete_patterns)
        logger.debug(f"matches for date_relation context: {matches}")
        # TODO: Filter the context matches to eliminate duplicates (or a set that is fully contained within another)
        if not matches:
            return []
        merged_set = self._merge_wanted_tags_into_set(matches)
        formatted_tags = self._format_wanted_tags_from_set_as_dict(merged_set)
        return {"original": merged_set, "formatted": formatted_tags}
    
    def _merge_wanted_tags_into_set(
            self,
            matches: list[list[tuple]],
            wanted_tags: list[str]=["prep1", "prep2", "prep_end", "adj_to_aux", "adj_to_verb", "aux_verb", "verb"],
        ) -> list[tuple]:
        merged_set = set()
        print("matches: ", matches)
        for match in matches:
            for entry in match:
                if entry[1] in wanted_tags:
                    if entry not in merged_set:
                        merged_set.add(entry)
        return merged_set if len(merged_set) != 0 else None

    def _format_wanted_tags_from_set_as_dict(
            self,
            wanted_tags_set,
            default_groups: list[str]=[
                "prep",
                "aux_verb",
                "adj",
                "verb"
            ],
            group_mapping: dict[str, str]={
                "prep1": "prep",
                "prep2": "prep",
                "prep_end": "prep",
                "verb": "verb", 
                "aux_verb": "aux_verb",
                "adj_to_aux": "adj",
                "adj_to_verb": "adj"
            },
            sort_order: dict[str, list]={
                "prep": ["prep_end", "prep2", "prep1"]
            }
        ) -> dict[str, dict]:
        finished_grouping = {k: [] for k in default_groups}
        unsorted_grouping = defaultdict(list)
        # wanted_tags_set = self._merge_wanted_tags_into_set(matches)
        def _index_for_sort_group(element, sort_group):
            idx = -1
            try:
                idx = sort_group.index(element)
            except ValueError:
                return len(sort_group) + 1
            else:
                return idx
        for entry in wanted_tags_set:
            parent_tag = group_mapping.get(entry[1], None)
            if parent_tag:
                unsorted_grouping[parent_tag].append(entry)
        for key in unsorted_grouping.keys():
            if sort_order.get(key, None):
                finished_group = [i[0] for i in sorted(
                    unsorted_grouping[key],
                    key=lambda x: _index_for_sort_group(x[1],
                    sort_order.get(key))
                )]
                finished_grouping[key] = finished_group
            else:
                finished_grouping[key] = [i[0] for i in unsorted_grouping[key]]
        return finished_grouping
                
    def _get_date_relation_through_root_verb(self, token: Token) -> list[Span]:
        root_verb = self.get_root_verb(token)
        result = []
        if root_verb:
            anchor_pattern = self._get_anchor_pattern(root_verb)
            date_relation_root_verb_patterns = add_anchor_pattern_to_patterns(anchor_pattern, SECU_DATE_RELATION_PATTERNS_FROM_ROOT_VERB)
            for pattern in date_relation_root_verb_patterns:
                candidate_matches = self.get_candidate_matches(pattern)
                for match in candidate_matches:
                    for rel in self._get_tokens_with_tag_from_match_tuples(match, "date_start"):
                        if rel is None:
                            break
                        result.append(extend_token_ent_to_span(rel, rel.doc))
        return result

    def get_quantities(self, token: Token) -> list[Token]|None:
        anchor_pattern = self._get_anchor_pattern(token)
        patterns = add_anchor_pattern_to_patterns(anchor_pattern, SECU_SECUQUANTITY_PATTERNS)
        result = []
        for pattern in patterns:
            # logger.debug(f"currently working on pattern {pattern}")
            candidate_matches = self.get_candidate_matches(pattern)
            if len(candidate_matches) > 0:
                for match in candidate_matches:
                    source_secu = None
                    quant = None
                    for entry in match:
                        candidate_token, right_id = entry
                        if right_id == "secuquantity":
                            quant = candidate_token
                        if right_id == "source_secu":
                            source_secu = candidate_token
                    if quant is not None:
                        result.append({"quantity": quant, "source_secu": source_secu})
        return result if result != [] else None
    
    def get_aux_verbs(self, token: Token) -> list[Token]|None:
        '''get the child aux verbs of token.'''
        candidate_matches = self.get_candidate_matches(
            [
                {
                    "RIGHT_ID": "anchor",
                    "TOKEN": token    
                },
                {
                    "LEFT_ID": "anchor",
                    "REL_OP": ">>",
                    "RIGHT_ID": "aux_verb",
                    "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}},
                }
            ]
        )
        # logger.debug(f"canddiate_matches for aux_verb: {candidate_matches}")
        aux_verbs = []
        if candidate_matches != []:
            for match in candidate_matches:
                for aux in self._get_tokens_with_tag_from_match_tuples(match, "aux_verb"):
                    if aux is None:
                        break
                    aux_verbs.append(aux)
            return aux_verbs if aux_verbs != [] else None
        return None
    
    def get_parent_verb(self, token: Token) -> Token|None:
        '''get the closest parent verb in the dependency tree of token.'''
        candidate_matches = self.get_candidate_matches(
            [
                {
                    "RIGHT_ID": "anchor",
                    "TOKEN": token    
                },
                {
                    "LEFT_ID": "anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "parent_verb",
                    "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}},
                    "IS_OPTIONAL": False
                }
            ]
        )
        if candidate_matches != []:
            if len(candidate_matches) > 1:
                verbs = []
                for candidate_match in candidate_matches:
                    for entry in candidate_match:
                        candidate_token, right_id = entry
                        if right_id == "parent_verb":
                            verbs.append(candidate_token)
                dep_distances = [None] * len(verbs)
                for idx, verb in enumerate(verbs):
                    dep_distances[idx] = get_dep_distance_between(token, verb)
                min_idx =  dep_distances.index(min(dep_distances))
                return verbs[min_idx]
            else:
                for entry in candidate_matches[0]:
                    candidate_token, right_id = entry
                    if right_id == "parent_verb":
                        return candidate_token
        return None

    def get_root_verb(self, token: Token) -> Token|None:
        '''get the root parent verb of the dependency tree of token.'''
        candidate_matches = self.get_candidate_matches(
            [
                {
                    "RIGHT_ID": "anchor",
                    "TOKEN": token    
                },
                {
                    "LEFT_ID": "anchor",
                    "REL_OP": "<<",
                    "RIGHT_ID": "root_verb",
                    "RIGHT_ATTRS": {"POS": {"IN": ["VERB", "AUX"]}},
                    "IS_OPTIONAL": False
                }
            ]
        )
        # logger.debug(f"canddiate_matches for root_verb: {candidate_matches}")
        if candidate_matches != []:
            if len(candidate_matches) > 1:
                verbs = []
                for candidate_match in candidate_matches:
                    for entry in candidate_match:
                        candidate_token, right_id = entry
                        if right_id == "root_verb":
                            verbs.append(candidate_token)
                dep_distances = [None] * len(verbs)
                for idx, verb in enumerate(verbs):
                    dep_distances[idx] = get_dep_distance_between(token, verb)
                max_idx =  dep_distances.index(max(dep_distances))
                return verbs[max_idx]
            else:
                for entry in candidate_matches[0]:
                    candidate_token, right_id = entry
                    if right_id == "root_verb":
                        return candidate_token
        return None
    
class Amount:
    def __init__(self, amount: float):
        self.amount = amount
    
    def __eq__(self, other):
        if isinstance(other, Amount):
            if self.amount == other.amount:
                return True
        return False
    
    def __repr__(self):
        return f"{self.amount}"
    
class Unit:
    def __init__(self, unit: str):
        self.unit = unit
    
    def __eq__(self, other):
        if isinstance(other, Unit):
            if self.unit == other.unit:
                return True
        return False
    
    def __repr__(self):
        return self.unit

class SecurityAmount:
    def __init__(self, amount, unit):
        self.amount = amount
        self.unit = unit
    
    def __eq__(self, other):
        if isinstance(other, SecurityAmount):
            if (
                (self.amount == other.amount) and
                (self.unit == other.unit)
            ):
                return True
        return False
    
    def __repr__(self):
        return f"{self.amount} {self.unit}"
    
    
class SECUQuantity:
    def __init__(self, original, attr_matcher: SecurityDependencyAttributeMatcher):
        self.original: Token|Span = original
        self._quantity = original._.secuquantity
        self._unit: str = original._.secuquantity_unit
        self.amount: SecurityAmount = SecurityAmount(self._quantity, self._unit)
        self.amods: list = original._.amods
        self.parent_verb = attr_matcher.get_parent_verb(self.original)
        self._date_relations = attr_matcher.get_date_relation(self.original)
        self.datetime_relation: DatetimeRelation = self._get_datetime_relation()
    
    def _get_datetime_relation(self):
        if self._date_relations:
            if len(self._date_relations["datetime"]) == 0:
                return None
            elif len(self._date_relations["datetime"]) == 1:
                return self._date_relations["datetime"][0]
            elif len(self._date_relations) > 1:
                raise ValueError(f"More than one datetime relation present for {self.original}, failed to determine a certain context -> failed to create the SECUQuantity object.")
        else:
            return None
        
    def __repr__(self):
        return f"SECUQuantity({self.amount} -\
    \t {self.amods} - \
    \t {self.datetime_relation})"   

    def __eq__(self, other):
        if isinstance(other, SECUQuantity):
            has_same_timestamp = False
            if isinstance(self.datetime_relation, DatetimeRelation) and isinstance(other.datetime_relation, DatetimeRelation):
                if self.datetime_relation.timestamp == other.datetime_relation.timestamp:
                    has_same_timestamp = True
            if (
                (self.amount == other.amount) and
                (self.datetime_relation == other.datetime_relation or has_same_timestamp)
            ):
                return True
        return False


@dataclass
class QuantityRelation:
    quantity: SECUQuantity
    main_secu: Any
    rel_type: str = "quantity"
    
    def __repr__(self):
        return f"QuantityRelation(\
 {self.quantity}\
\t {self.main_secu.original})"

    def __eq__(self, other):
        if (
            (self.quantity == other.quantity)
            and
            (self.main_secu == other.main_secu)
        ):
            return True
        return False


class SourceQuantityRelation(QuantityRelation):
    def __init__(self, *args, source, **kwargs):
        super().__init__(*args, **kwargs)
        self.source: SECU = source
        self.rel_type = "source_quantity"

    def __repr__(self):
        return f"SourceQuantityRelation({self.quantity},\
\t {self.source.original})"


class SECU:
    def __init__(self, original, attr_matcher: SecurityDependencyAttributeMatcher):
        self.original: Token = self._set_original(original)
        self.attr_matcher: SecurityDependencyAttributeMatcher = attr_matcher
        self.secu_key: str = original._.secu_key
        self.amods = original._.amods
        self.other_relations: list = list()
        self.quantity_relations: list[QuantityRelation|SourceQuantityRelation] = list()
        self._set_quantity_relations()
        self.root_verb: Token|None = attr_matcher.get_root_verb(self.original)
        self.parent_verb: Token|None = attr_matcher.get_parent_verb(self.original)
        self.aux_verbs: list = attr_matcher.get_aux_verbs(self.original)
        self.date_relations: list[dict] = attr_matcher.get_date_relation(self.original)
        self.exercise_price: tuple|None = attr_matcher.get_exercise_price(self.original)
        self.expiry_date = self._get_expiry_datetime_relation()
        self.exercise_date = self._get_exercise_datetime_relation()
    
    def _date_relation_attr_with_subset_of_pattern(self, valid_patterns: list[dict[str, set]], attr: str="lemmas"):
        '''
        valid_patterns:
        [
            {
                "prep": set(["as", "of", "on"]),
                "adj": set(["exercisable"]),
            },
            ...
        ]
        '''
        matches = set()
        for date_relation in self.date_relations["datetime"]:
            if not getattr(date_relation, attr): continue
            for pattern in valid_patterns:
                keys_to_check = pattern.keys()
                attrs = getattr(date_relation, attr, None)
                if not attrs:
                    continue
                if not all([k in attrs.keys() for k in keys_to_check]):
                    logger.debug(f"SECU. _date_relation_attr_has_subset_of_pattern(): not all required keys found. Missing:{[k if k not in attrs.keys() else None for k in keys_to_check]} ")
                    continue
                if all([attrs[key].issubset(pattern[key]) for key in keys_to_check]):
                    if date_relation not in matches:
                        matches.add(date_relation)
        return matches
    

    def _get_exercise_datetime_relation(self):
        if (self.date_relations is None) or (len(self.date_relations["datetime"]) == 0):
            return None
        valid_patterns = SECU_GET_EXERCISE_DATE_LEMMA_COMBINATIONS
        matches = self._date_relation_attr_with_subset_of_pattern(
            valid_patterns,
            attr="lemmas")
        return list(matches)[0] if len(matches) == 1 else None

    
    def _get_expiry_datetime_relation(self):
        #TODO: implement this for the timedelta case (when i have a grip on issuance dates)
        if (self.date_relations is None) or (len(self.date_relations["datetime"]) == 0):
            return None
        valid_patterns = SECU_GET_EXPIRY_DATE_LEMMA_COMBINATIONS
        matches = self._date_relation_attr_with_subset_of_pattern(valid_patterns, "lemmas")
        if len(matches) > 1:
            raise ValueError(f"SECU._get_expiry_datetime_relation() found more than one expiry for a specific security, case not handled. dates found: {matches}, secu: {self}")
        return list(matches)[0] if len(matches) == 1 else None
        
    

    def _set_quantity_relations(self):
        quants = self.attr_matcher.get_quantities(self.original)
        if not quants:
            # logger.debug(f"no quantities found for secu: {self.original}")
            return
        for quant in quants:
            quant_obj = SECUQuantity(quant["quantity"], self.attr_matcher)
            if getattr(quant_obj.original, "source_secu", None) is not None:
                source = quant["source_secu"]
                rel = SourceQuantityRelation(quant_obj, self, source)
                self._add_quantity_relation(rel)
            else:
                rel = QuantityRelation(quant_obj, self)
                self._add_quantity_relation(rel)


    def _set_original(self, original: Token|Span) -> None:
        if isinstance(original, Token):
            return original
        elif isinstance(original, Span):
            if len(original) == 1:
                return original[0]
            else:
                raise NotImplementedError("Span with more than one token for use as original argument is not supported yet.")
    
    def _add_quantity_relation(self, relation: QuantityRelation|SourceQuantityRelation):
        if relation not in self.quantity_relations:
            self.quantity_relations.append(relation)
        else:
            logger.debug(f"quantity_relation {relation} already present in {self}")

    def _add_relation(self, relation):
        if relation not in self.other_relations:
            self.other_relations.append(relation)
        else:
            logger.debug(f"relation {relation} already in relations of {self}")

    def __repr__(self):
        rels = ""
        for x in range(len(self.other_relations)):
            rels += f"\n\t {x}) {self.other_relations[x]}"
        return f"SECU({self.original}\
\t secu_key: {self.secu_key}\
\t amods: {self.amods}\
\n\t relations: {rels})"
    
    def __eq__(self, other):
        if not isinstance(other, SECU):
            logger.debug(f"comparing {self} to {other} which is not of type SECU, but of: {type(other)}")
            return False
        return (
            self.secu_key == other.secu_key
            and
            self.original == other.original
        )


    


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

def get_span_secuquantity_float(span: Span):
    if not isinstance(span, Span):
        raise TypeError("span must be of type spacy.tokens.span.Span, got: {}".format(type(span)))
    if span.label_ == "SECUQUANTITY":
        return formater.money_string_to_float(span.text)
    else:
        raise AttributeError("get_secuquantity can only be called on Spans with label: 'SECUQUANTITY'")

def get_token_secuquantity_float(token: Token):
    if not isinstance(token, Token):
        raise TypeError("token must be of type spacy.tokens.token.Token, got: {}".format(type(token)))
    if token.ent_type_ == "SECUQUANTITY":
        return formater.money_string_to_float(token.text)
    else:
        raise AttributeError("get_secuquantity can only be called on Spans with label: 'SECUQUANTITY'")

def retokenize_SECU(doc: Doc):
    # this needs to decouple the source/premerge tokens so 
    # we dont have problem with a shift of token positions
    # after the merge
    with doc.retokenize() as retokenizer:
        for ent in doc.ents:
            if ent.label_ == "SECU":
                source_doc_slice = ent.as_doc(copy_user_data=True)
                # handle previously merged tokens to retain 
                # original/first source_span_unmerged
                if not ent.has_extension("was_merged"):
                    source_tokens = tuple([t for t in source_doc_slice])
                else:
                    if ent._.was_merged:
                        source_tokens = ent._.premerge_tokens
                    else:
                        source_tokens = tuple([t for t in source_doc_slice])
                attrs = {
                            "tag": ent.root.tag,
                            "dep": ent.root.dep,
                            "ent_type": ent.label,
                            "_": {
                                "source_span_unmerged": source_tokens, 
                                "was_merged": True
                            }
                }
                ent._.was_merged = True
                retokenizer.merge(ent, attrs=attrs)
    return doc

def get_span_to_span_similarity_map(secu: list[Token]|Span, alias: list[Token]|Span, threshold: float = 0.65):
    similarity_map = {}
    for secu_token in secu:
        for alias_token in alias:
            similarity = secu_token.similarity(alias_token)
            similarity_map[(secu_token, alias_token)] = similarity
    return similarity_map
            # if  similarity > 0.65:
            #     similarity_map_entry["very_similar"].append((secu_token, alias_token, secu_token.similarity(alias_token)))
            #     very_similar_count += 1

                # compare token to token2 and check if we have a token that is very similar >.65
                # count the very similar tokens
                # take the alias with the highest count ?
                # bootstrap a statistical model to predict the alias?

def BFS_non_recursive(origin, target) -> list:
    '''
    Breadth First Search algorithm

    Returns:
        list: list of nodes in the path from origin to target
        None: if no path is found
    '''
    path = []
    queue = [[origin]]
    node = origin
    visited = set()
    while queue:
        path = queue.pop(0)
        node = path[-1]
        if node == target:
            return path
        visited.add(node)
        adjacents = (list(node.children) if node.children else []) + (list(node.ancestors) if node.ancestors else [])
        for adjacent in adjacents:
            if adjacent in visited:
                continue
            new_path = list(path)
            new_path.append(adjacent)
            queue.append(new_path)

def get_dep_distance_between(origin, target) -> int:
    '''
    get the distance between two tokens in a spaCy dependency tree.

    Returns:
        int: distance between origin and target
        None: if origin and target arent part of the same tree
    '''
    is_in_same_tree = False
    if origin.is_ancestor(target):
        is_in_same_tree = True
        start = origin
        end = target
    if target.is_ancestor(origin):
        is_in_same_tree = True
        start = target
        end = origin
    if is_in_same_tree:
        path = BFS_non_recursive(start, end)
        return len(path)
    else:
        return None

def get_dep_distance_between_spans(origin, target) -> int:
    '''
    get the distance between two spans (counting from their root) in a spaCy dependency tree.

    Returns:
        int: distance between origin and target
        None: if origin and target arent part of the same tree
    '''
    distance = get_dep_distance_between(origin.root, target.root)
    return distance

def get_span_distance(secu, alias: list[Token]|Span) -> int:
    if secu[0].i > alias[0].i:
        first = alias
        second = secu
    else:
        first = secu
        second = alias
    mean_distance = ((second[0].i - first[-1].i) + (second[-1].i - first[0].i))/2
    return mean_distance

def calculate_similarity_score(alias: list[Token]|Span, similarity_map, dep_distance: int, span_distance: int, very_similar_threshold: float, dep_distance_weight: float, span_distance_weight: float) -> float:
    very_similar = sum([v > very_similar_threshold for v in similarity_map.values()])
    very_similar_score = very_similar / len(alias) if very_similar != 0 else 0
    dep_distance_score = dep_distance_weight * (1/dep_distance)
    span_distance_score = span_distance_weight * (10/span_distance)
    total_score = dep_distance_score + span_distance_score + very_similar_score
    return total_score

def get_span_similarity_score(
        span1: list[Token]|Span,
        span2: list[Token]|Span,
        dep_distance_weight: float = 0.7,
        span_distance_weight: float = 0.3,
        very_similar_threshold: float=0.65
    ) -> float:
    premerge_tokens = span1._.premerge_tokens if span1.has_extension("premerge_tokens") else span1
    similarity_map = get_span_to_span_similarity_map(premerge_tokens, span2)
    dep_distance = get_dep_distance_between_spans(span1, span2)
    span_distance = get_span_distance(span1, span2)
    if dep_distance and span_distance and similarity_map:
        score = calculate_similarity_score(
            span2,
            similarity_map,
            dep_distance,
            span_distance,
            very_similar_threshold=very_similar_threshold,
            dep_distance_weight=dep_distance_weight,
            span_distance_weight=span_distance_weight
            )
        return score


def get_alias(doc: Doc, secu: Span):
    # logger.debug(f"getting alias for: {secu}")
    if doc._.is_alias(secu) is True:
        return None
    else:
        secu_first_token = secu[0]
        secu_last_token = secu[-1]
        similarity_score_store = []
        checked_combination = set()
        #TODO: optimize this
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
                        if (secu, alias) in checked_combination:
                            continue
                        score = get_span_similarity_score(secu, alias)
                        checked_combination.add((secu, alias))
                        if score:
                            similarity_score_store.append((secu, alias, sent[0].i, score))
        # logger.debug(f"similarity_score_map: {similarity_score_store}")
        if similarity_score_store != []:
            highest_similarity = sorted(similarity_score_store, key=lambda x: x[3])[-1]
            return highest_similarity[1]
        else:
            return None             

def _get_SECU_in_doc(doc: Doc) -> list[Span]:
    secu_spans = []
    for ent in doc.ents:
        if ent.label_ == "SECU":
            secu_spans.append(ent)
    return secu_spans

def _set_single_secu_alias_map(doc: Doc) -> dict:
        if (doc.spans.get("SECU") is None) or (doc.spans.get("alias") is None):
            raise AttributeError(f"Didnt set spans correctly missing one or more keys of (SECU, alias). keys found: {doc.spans.keys()}")
        single_secu_alias = dict()
        secu_ents = doc._.secus
        # logger.debug(f"working from ._.secus: {secu_ents}")
        for secu in secu_ents:
            if doc._.is_alias(secu):
                continue
            secu_key = get_secu_key(secu)
            # logger.debug(f"got secu_key: {secu_key} -> from secu -> {secu}")
            if secu_key not in single_secu_alias.keys():
                single_secu_alias[secu_key] = {"base": [secu], "alias": []}
            else:
                single_secu_alias[secu_key]["base"].append(secu)
            alias = doc._.get_alias(secu)
            if alias:
                single_secu_alias[secu_key]["alias"].append(alias)
        # logger.debug(f"got single_secu_alias map: {single_secu_alias}")
        doc._.single_secu_alias = single_secu_alias

def _set_single_secu_alias_map_as_tuples(doc: Doc) -> dict:
        if (doc.spans.get("SECU") is None) or (doc.spans.get("alias") is None):
            # print(doc.spans.get("SECU"), doc.spans.get("alias"))
            raise AttributeError(f"Didnt set spans correctly missing one or more keys of (SECU, alias). keys found: {doc.spans.keys()}")
        single_secu_alias_tuples = dict()
        secu_ents = doc._.secus
        for secu in secu_ents:
            if doc._.is_alias(secu):
                continue
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

                

def is_alias(doc: Doc, secu: Span) -> bool:
    if secu.text in doc._.alias_set:
        return True
    return False

def get_secu_key(secu: Span|Token) -> str:
    premerge_tokens = secu._.premerge_tokens if secu.has_extension("premerge_tokens") else None
    # logger.debug(f"premerge_tokens while getting secu_key: {premerge_tokens}")
    if premerge_tokens:
        secu = premerge_tokens
    core_tokens = secu if secu[-1].text.lower() not in ["shares"] else secu[:-1] 
    body = [token.text_with_ws.lower() for token in core_tokens[:-1]]
    try:
        current_tail = core_tokens[-1].lemma_.lower()
        if current_tail in PLURAL_SINGULAR_SECU_TAIL_MAP.keys():
            tail = PLURAL_SINGULAR_SECU_TAIL_MAP[current_tail]
        else:
            tail = current_tail
        body.append(tail)
    except IndexError:
        logger.debug("IndexError when accessing tail information of secu_key -> no tail -> pass")
        pass
    result = "".join(body) 
    # logger.debug(f"get_secu_key() returning key: {result} from secu: {secu}")
    return result

def get_secu_key_extension(target: Span|Token) -> str:
    if isinstance(target, Span):
        return _get_secu_key_extension_for_span(target)
    elif isinstance(target, Token):
        return _get_secu_key_extension_for_token(target)
    else:
        raise TypeError(f"target must be of type Span or Token, got {type(target)}")

def _get_secu_key_extension_for_span(span: Span):
    if span.label_ != "SECU":
        raise AttributeError(f"Can only get secu_key for SECU spans, span is not a SECU span. received span.label_: {span.label_}")
    return get_secu_key(span)

def _get_secu_key_extension_for_token(token: Token):
    if token.ent_type_ != "SECU":
        raise AttributeError(f"Can only get secu_key for SECU tokens, token is not a SECU token. received token.ent_type_: {token.ent_type_}")
    return get_secu_key(token)

def get_premerge_tokens_for_span(span: Span) -> tuple|None:
    premerge_tokens = []
    source_spans_seen = set()
    # logger.debug(f"getting premerge_tokens for span: {span}")
    for token in span:
        # logger.debug(f"checking token: {token}")
        if token.has_extension("was_merged"):
            if token._.was_merged is True:
                # logger.debug(f"token._.source_span_unmerged: {token._.source_span_unmerged}")
                if token._.source_span_unmerged not in source_spans_seen:
                    premerge_tokens.append([i for i in token._.source_span_unmerged])
                    source_spans_seen.add(token._.source_span_unmerged)
    # flatten
    premerge_tokens = sum(premerge_tokens, [])
    if premerge_tokens != []:
        return tuple(premerge_tokens)
    else:
        return None

def get_premerge_tokens_for_token(token: Token) -> tuple|None:
    if not isinstance(token, Token):
        raise TypeError(f"get_premerge_tokens_for_token() expects a Token object, received: {type(token)}")
    if token.has_extension("was_merged"):
        if token._.was_merged is True:
            return tuple([i for i in token._.source_span_unmerged])
    return None

def set_SECUMatcher_extensions():
    token_extensions = [
        {"name": "source_span_unmerged", "kwargs": {"default": None}},
        {"name": "was_merged", "kwargs": {"default": False}},
        {"name": "secuquantity", "kwargs": {"getter": get_token_secuquantity_float}},
        {"name": "secuquantity_unit", "kwargs": {"default": None}},
        {"name": "amods", "kwargs": {"getter": token_amods_getter}},
        {"name": "nsubjpass", "kwargs": {"getter": token_nsubjpass_getter}},
        {"name": "adj", "kwargs": {"getter": token_adj_getter}},
        {"name": "premerge_tokens", "kwargs": {"getter": get_premerge_tokens_for_token}},
        {"name": "secu_key", "kwargs": {"getter": get_secu_key_extension}},
        {"name": "negated", "kwargs": {"default": False}}
    ]
    span_extensions = [
        {"name": "secuquantity", "kwargs": {"getter": get_span_secuquantity_float}},
        {"name": "secuquantity_unit", "kwargs": {"default": None}},
        {"name": "secu_key", "kwargs": {"getter": get_secu_key_extension}},
        {"name": "amods", "kwargs": {"getter": span_amods_getter}},
        {"name": "premerge_tokens", "kwargs": {"getter": get_premerge_tokens_for_span}},
        {"name": "was_merged", "kwargs": {"default": False}},
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
    for each in token_extensions:
        _set_extension(Token, each["name"], each["kwargs"])


class SECUMatcher:
    def __init__(self, vocab):
        self.vocab = vocab
        self.matcher_SECU = Matcher(vocab)
        self.matcher_SECUREF = Matcher(vocab)
        self.matcher_SECUATTR = Matcher(vocab)
        self.matcher_SECUQUANTITY = Matcher(vocab)

        set_SECUMatcher_extensions()
        
        self.add_SECU_ent_to_matcher(self.matcher_SECU)
        self.add_SECUREF_ent_to_matcher(self.matcher_SECUREF)
        self.add_SECUATTR_ent_to_matcher(self.matcher_SECUATTR)
        self.add_SECUQUANTITY_ent_to_matcher(self.matcher_SECUQUANTITY)
    

    def __call__(self, doc: Doc):
        self._init_span_labels(doc)
        self.chars_to_token_map = self.get_chars_to_tokens_map(doc)
        self.set_possible_alias_spans(doc)
        self.set_tokens_to_alias_map(doc)
        self.matcher_SECU(doc)
        update_doc_secus_spans(doc)
        self.matcher_SECUREF(doc)
        doc = self.handle_retokenize_SECU(doc)
        self.handle_SECU_special_cases(doc)
        doc = self.handle_retokenize_SECU(doc)
        self.matcher_SECUATTR(doc)
        self.matcher_SECUQUANTITY(doc)
        return doc
    
    def handle_retokenize_SECU(self, doc: Doc):
        doc = retokenize_SECU(doc)
        update_doc_secus_spans(doc)
        self.chars_to_token_map = self.get_chars_to_tokens_map(doc)
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
        special_patterns = []
        for secu_key, values in doc._.single_secu_alias_tuples.items():
            # logger.info(f"current key: {secu_key}")
            alias_tuples = doc._.single_secu_alias_tuples[secu_key]["alias"]
            # logger.info(f"current alias_tuples: {alias_tuples}")
            if alias_tuples and alias_tuples != []:
                for entry in alias_tuples:
                    # base_span = entry[0]
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
        matcher.add(
            "SECU_ENT",
            [
                *SECU_ENT_REGULAR_PATTERNS,
                *SECU_ENT_DEPOSITARY_PATTERNS,
                *SECU_ENT_SPECIAL_PATTERNS
            ],
            on_match=_add_SECU_ent
        )

    def add_SECUQUANTITY_ent_to_matcher(self, matcher: Matcher):
        matcher.add(
            "SECUQUANTITY_ENT",
            [
                *SECUQUANTITY_ENT_PATTERNS
            ],
            on_match=_add_SECUQUANTITY_ent_regular_case
        )
        logger.debug("added SECUQUANTITY patterns to matcher")

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

def update_doc_secus_spans(doc: Doc):
    doc._.secus = []
    # logger.debug(f"updating doc._.secus")
    for ent in doc.ents:
        if ent.label_ == "SECU":
            # logger.debug(f"found SECU ent in doc.ents: {ent}")
            if doc._.is_alias(ent):
                continue
            # logger.debug(f"ent was not an alias, adding it.")
            doc._.secus.append(ent)

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
    # logger.debug(f"adding SECU ent: {matches[i]}")
    _add_ent(doc, i, matches, "SECU", exclude_after=[
            "agreement",
            "agent",
            "indebenture",
            # "rights",
            "shares"],
            ent_callback=None,
            always_overwrite=["ORG", "WORK_OF_ART", "LAW"]
            )

def _add_SECUATTR_ent(matcher, doc: Doc, i: int, matches):
    _add_ent(doc, i, matches, "SECUATTR")

def _add_CONTRACT_ent(matcher, doc: Doc, i: int, matches):
    _add_ent(doc, i, matches, "CONTRACT", adjust_ent_before_add_callback=adjust_CONTRACT_ent_before_add)

def adjust_CONTRACT_ent_before_add(entity: Span):
    logger.debug(f"adjust_contract_ent_before_add entity before adjust: {entity}")
    doc = entity.doc
    root = entity.root
    start = entity.start
    if start != 0:
        for i in range(entity.start-1, 0, -1):
            if doc[i].dep_ == "compound" and root.is_ancestor(doc[i]):
                start = i
            else:
                break
    end = entity.end
    for i in range(entity.end, len(doc), 1):
        if doc[i].dep_ == "compound" and root.is_ancestor(doc[i]):
            end = i
        else:
            break
    entity = Span(doc, start, end, label="CONTRACT")
    logger.debug(f"adjust_contract_ent_before_add entity after adjust: {entity}")
    return entity
    
def _add_SECUQUANTITY_ent_regular_case(matcher, doc: Doc, i, matches):
    _, match_start, match_end = matches[i]
    match_tokens = [t for t in doc[match_start:match_end]]
    # logger.debug(f"handling SECUQUANTITY for match: {match_tokens}")
    match_id, start, _ = matches[i]
    end = None
    wanted_tokens = []
    for token in match_tokens:
        # logger.debug(f"token: {token}, ent_type: {token.ent_type_}")
        if (token.ent_type_ in ["MONEY", "CARDINAL", "SECUQUANTITY"]) or (token.dep_ == "nummod" and token.pos_ == "NUM"):
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
    unit = "COUNT"
    if "MONEY" in [t.ent_type_ for t in match_tokens]:
        unit = "MONEY"
    span._.secuquantity_unit = unit
    for token in span:
        token._.secuquantity_unit = unit

def _add_ent(doc: Doc, i, matches, ent_label: str, exclude_after: list[str]=[], exclude_before: list[str]=[], adjust_ent_before_add_callback: Optional[Callable]=None, ent_callback: Optional[Callable]=None, ent_exclude_condition: Optional[Callable]=None, always_overwrite: Optional[list[str]]=None):
    '''add a custom entity through an on_match callback.
    
    Args:
        adjust_ent_before_add_callback:
            a callback that can be used to adjust the entity before
            it is added to the doc.ents. Takes the entity (Span) as single argument
            and should return a Span (the adjusted entity to be added)
        ent_callback: function which will be called, if entity was added, with the entity and doc as args.
        ent_exclude_condition: callable which returns bool and takes entity and doc as args.'''
    match_id, start, end = matches[i]
    if (not _is_match_followed_by(doc, start, end, exclude_after)) and (
        not _is_match_preceeded_by(doc, start, end, exclude_before)):
        entity = Span(doc, start, end, label=ent_label)
        if adjust_ent_before_add_callback is not None:
            entity = adjust_ent_before_add_callback(entity)
            if not isinstance(entity, Span):
                raise TypeError(f"entity should be a Span, got: {entity}")
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
    # logger.debug(f"new ent covering tokens: {[i for i in covered_tokens]}")
    for ent in doc.ents:
        # if ent.end == ent.start-1:
        #     covered_tokens = [ent.start]
        # else:               
        # covered_tokens = range(ent.start, ent.end)
        # logger.debug(f"potentital conflicting ent: {ent}; with tokens: {[i for i in range(ent.start, ent.end)]}; and label: {ent.label_}")
        possible_conflicting_tokens_covered = [i for i in range(ent.start, ent.end-1)]
        # check if we have a new longer ent or a new shorter ent with a required overwrite label
        if ((ent.start in covered_tokens) or (ent.end-1 in covered_tokens)) or (any([i in covered_tokens for i in possible_conflicting_tokens_covered])):
            if conflicting_ents == []:
                seen_conflicting_ents.append(ent)
            if ((ent.end - ent.start) <= (end - start)) or (ent.label_ in overwrite_labels if overwrite_labels else False) is True:
                if conflicting_ents == []:
                    conflicting_ents = seen_conflicting_ents
                else:
                    conflicting_ents.append(ent)
            # else:
                # logger.debug(f"{ent} shouldnt be conflicting")
                
    return conflicting_ents

def _get_singular_or_plural_of_SECU_token(token):
    singular = PLURAL_SINGULAR_SECU_TAIL_MAP.get(token.lower_)
    plural = SINGULAR_PLURAL_SECU_TAIL_MAP.get(token.lower_)
    if singular is None:
        return plural
    else:
        return singular

class AgreementMatcher:
    '''
    What do i want to tag?
        1) contractual agreements between two parties CONTRACT
        2) placements (private placement), public offerings -> specifiers for a CONTRACT or standing alone in text
        how else could the context of origin be present in a filing?
    '''
    # change the name to something more fitting, also adjust the Language.factory for name
    def __init__(self, vocab):
        self.vocab = vocab
        self.matcher = Matcher(vocab)
        self.add_CONTRACT_ent_to_matcher()
    
    def add_CONTRACT_ent_to_matcher(self):
        patterns = [
            [{"LOWER": "agreement"}],
        ]
        self.matcher.add("contract", patterns, on_match=_add_CONTRACT_ent)
    
    def add_PLACEMENT_ent_to_matcher(self):
        pass
    
    def __call__(self, doc: Doc):
        self.matcher(doc)
        return doc
    
    # def agreement_callback()


class NegationSetter:
    '''
    sets negation for ADJ and VERBS with the token extension ._.negated.
    '''
    def __init__(self, vocab):
        self.vocab = vocab
        self.matcher = Matcher(vocab)
        self.add_negation_ent_to_matcher()
    
    def add_negation_ent_to_matcher(self):
        self.matcher.add("negation", [*VERB_NEGATION_PATTERNS, *ADJ_NEGATION_PATTERNS], on_match=_set_negation_extension)
        

    def __call__(self, doc: Doc):
        self.matcher(doc)
        return doc


    
def _set_negation_extension(matcher: Matcher, doc: Doc, i: int, matches: list):
    '''
    sets the negation extension for the matched tokens
    '''
    match_id, start, end = matches[i]
    for token in doc[start:end]:
        if token.dep_ not in ["neg", "aux", "auxpass"]:
            token._.negated = True

                    
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

@Language.factory("agreement_matcher")
def create_agreement_matcher(nlp, name):
    return AgreementMatcher(nlp.vocab)

@Language.factory("negation_setter")
def create_negation_setter(nlp, name):
    if not Token.has_extension("negated"):
        Token.set_extension("negated", default=False)
    return NegationSetter(nlp.vocab)


class SpacyFilingTextSearch:
    _instance = None
    # make this a singleton/get it from factory through cls._instance so we can avoid
    # the slow process of adding patterns (if we end up with a few 100)
    def __init__(self):
        self.secu_attr_getter = SecurityDependencyAttributeMatcher()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpacyFilingTextSearch, cls).__new__(cls)
            cls._instance.nlp = spacy.load("en_core_web_lg")
            cls._instance.nlp.add_pipe("secu_act_matcher", first=True)
            cls._instance.nlp.add_pipe("security_law_retokenizer", after="secu_act_matcher")
            cls._instance.nlp.add_pipe("common_financial_retokenizer", after="security_law_retokenizer")
            cls._instance.nlp.add_pipe("negation_setter")
            cls._instance.nlp.add_pipe("secu_matcher")
            cls._instance.nlp.add_pipe("agreement_matcher")
            # cls._instance.nlp.add_pipe("coreferee")
        return cls._instance
        
    def get_SECU_objects(self, doc: Doc) -> dict[str, list[SECU]]:
        if not self.nlp.has_pipe("secu_matcher"):
            raise AttributeError("SECUMatcher not added to pipeline. Please add it with nlp.add_pipe('secu_matcher')")
        secus = defaultdict(list)
        for secu in doc._.secus:
            if len(secu)==1:
                secu = secu[0]
            secu_obj = SECU(secu, self.secu_attr_getter)
            secus[secu_obj.secu_key].append(secu_obj)
            # # state = secu._.amods
            # # print(f"state: {state}")
            # secu_obj.date_relations = self.secu_attr_getter.get_date_relation(secu)
            # quants = self.secu_attr_getter.get_quantities(secu)
            # # quants = self.get_secuquantities(doc, secu)
            # if not quants:
            #     logger.debug(f"no quantities found for secu: {secu}")
            #     continue
            # for quant in quants:
            #     quant_obj = SECUQuantity(quant["quantity"])
            #     if getattr(quant_obj.original, "source_secu", None) is not None:
            #         source = quant["source_secu"]
            #         rel = SourceQuantityRelation(quant_obj, secu_obj, source)
            #         secu_obj._add_relation(rel)
            #     else:
            #         rel = QuantityRelation(quant_obj, secu_obj)
            #         secu_obj._add_relation(rel)
        return secus
    
    def handle_match_formatting(self, match: tuple[str, list[Token]], formatting_dict: Dict[str, Callable], doc: Doc, *args, **kwargs) -> tuple[str, dict]:
        try:
            # match_id = doc.vocab.strings[match[0]]
            match_id = match[0]
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
        anchor_pattern = [{
                    "RIGHT_ID": "anchor",
                    "RIGHT_ATTRS": {"ENT_TYPE": "SECU", "LOWER": secu.root.lower_},
                }]
        incomplete_patterns = [
            [
                {
                    "LEFT_ID": "anchor",
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
        patterns = add_anchor_pattern_to_patterns(anchor_pattern, incomplete_patterns)
        dep_matcher.add("secu_cd", patterns)
        matches = dep_matcher(doc)
        if matches:
            matches = _convert_dep_matches_to_spans(doc, matches)
            return [match[1] for match in matches]
        return []
    
    def get_queryable_similar_spans_from_lower(self, doc: Doc, span: Span):
        '''
        look for similar spans by matching through regex on the
        combined .text_with_ws of the tokens of span with re.I flag
        (checking for last token singular or plural aslong as it is registered
        in PLURAL_SINGULAR_SECU_TAIL_MAP and SINGULAR_PLURAL_SECU_TAIL_MAP.
        '''
        #adjusted for merged SECUs
        matcher = Matcher(self.nlp.vocab)
        tokens = []
        to_check = []
        if (span._.was_merged if span.has_extension("was_merged") else False):
            tokens = list(span._.premerge_tokens)
        else:
            tokens = [i for i in span]
        # add base case to check for later
        to_check.append(tokens)
        # see if we find an additional plural or singular case based on the last token
        tail_lower = _get_singular_or_plural_of_SECU_token(tokens[-1])
        if tail_lower:
            additional_case = tokens.copy()
            additional_case.pop()
            additional_case.append(tail_lower)
            to_check.append(additional_case)
        re_patterns = []
        # convert to string
        for entry in to_check:
            re_patterns.append(
                re.compile(
                    "".join([x.text_with_ws if isinstance(x, (Span, Token)) else x for x in entry]),
                    re.I
                    )
                )
        found_spans = set()
        for re_pattern in re_patterns:
            logger.debug(f"checking with re_pattern: {re_pattern}")
            for result in self._find_full_text_spans(re_pattern, doc):
                logger.debug(f"found a match: {result}")
                if result not in found_spans and result != span:
                    found_spans.add(result)
        matcher_patterns = []
        for entry in to_check:
            matcher_patterns.append([{"LOWER": x.lower_ if isinstance(x, (Span, Token)) else x} for x in entry])
        logger.debug(f"working with matcher_patterns: {matcher_patterns}")
        matcher.add("similar_spans", matcher_patterns)
        matches = matcher(doc)
        match_results = _convert_matches_to_spans(doc, filter_matches(matches))
        logger.debug(f"matcher converted matches: {match_results}")
        if match_results is not None:
            for match in match_results:
                if match not in found_spans and match != span:
                    found_spans.add(match)
        logger.info(f"Found {len(found_spans)} similar spans for {span}")
        logger.debug(f"similar spans: {found_spans}")
        return list(found_spans) if len(found_spans) != 0 else None
    
    def _find_full_text_spans(self, re_term: re.Pattern, doc: Doc):
        for match in re.finditer(re_term, doc.text):
            start, end = match.span()
            result = doc.char_span(start, end)
            if result:
                yield result
    
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

    def _create_span_dependency_matcher_dict_lower(self, secu: Span) -> dict:
        '''
        create a list of dicts for dependency match patterns.
        the root token will have RIGHT_ID of 'anchor'
        '''
        secu_root_token = secu.root
        if secu_root_token is None:
            return None
        root_pattern = [
            {
                "RIGHT_ID": "anchor",
                "RIGHT_ATTRS": {"ENT_TYPE": secu_root_token.ent_type_, "LOWER": secu_root_token.lower_}
            }
        ]
        if secu_root_token.children:
            for idx, token in enumerate(secu_root_token.children):
                if token in secu:
                    root_pattern.append(
                        {
                            "LEFT_ID": "anchor",
                            "REL_OP": ">",
                            "RIGHT_ID": token.lower_ + "__" + str(idx),
                            "RIGHT_ATTRS": {"LOWER": token.lower_}
                        }
                    )
        return root_pattern
    
    def match_secu_expiry(self, doc: Doc, secu: Span):
        secu_root_pattern = self._create_span_dependency_matcher_dict_lower(secu)
        if secu_root_pattern is None:
            logger.warning(f"couldnt get secu_root_pattern for secu: {secu}")
            return
        dep_matcher = DependencyMatcher(self.nlp.vocab, validate=True)
        patterns = add_anchor_pattern_to_patterns(secu_root_pattern, SECU_EXPIRY_PATTERNS)
        dep_matcher.add("expiry", patterns)
        matches = dep_matcher(doc)
        logger.debug(f"raw expiry matches: {matches}")
        for i in doc:
            print(i, i.lemma_)
        if matches:
            matches = _convert_dep_matches_to_spans(doc, matches)
            logger.info(f"matches: {matches}")
            formatted_matches = []
            for match in matches:
                formatted_matches.append(self._format_expiry_match(match[1]))
            return formatted_matches
        logger.debug("no matches for epxiry found in this sentence")
    
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
        logger.debug("match_secu_exercise_price:")
        logger.debug(f"     secu: {secu}")
        
        '''
        acl   (SECU) <- VERB (purchase) -> 					 prep (of | at) -> [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (have)  	->				     			       [dobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (purchase) -> 					 prep (at) ->      [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (purchase) -> conj (remain)  -> prep (at) ->      [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
		nsubj (SECU) <- VERB (purchase) -> 					 prep (at) ->      [pobj (price) -> compound (exercise)] -> prep (of) -> pobj CD
        
        relcl (SECU) <- VERB (purchase) >> prep(at) -> 
        '''
        secu_root_dict = self._create_span_dependency_matcher_dict_lower(secu)
        if secu_root_dict is None:
            return None
        patterns = add_anchor_pattern_to_patterns(secu_root_dict, SECU_EXERCISE_PRICE_PATTERNS)
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
        # INVESTIGATIVE
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
        # INVESTIGATIVE
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


    def match_outstanding_shares(self, text):
        # WILL BE REPLACED
        pattern1 = [
            {"LEMMA": "base"},
            {"LEMMA": {"IN": ["on", "upon"]}},
            {"ENT_TYPE": {"IN": ["CARDINAL", "SECUQUANTITY"]}},
            {"IS_PUNCT":False, "OP": "*"},
            {"LOWER": "shares"},
            {"IS_PUNCT":False, "OP": "*"},
            {"LOWER": {"IN": ["outstanding", "stockoutstanding"]}},
            {"IS_PUNCT":False, "OP": "*"},
            {"LOWER": {"IN": ["of", "on"]}},
            {"ENT_TYPE": "DATE", "OP": "+"},
            {"ENT_TYPE": "DATE", "OP": "?"},
            {"OP": "?"},
            {"ENT_TYPE": "DATE", "OP": "*"}
        ]
        pattern2 = [
            {"LEMMA": "base"},
            {"LEMMA": {"IN": ["on", "upon"]}},
            {"ENT_TYPE": {"IN": ["CARDINAL", "SECUQUANTITY"]}},
            {"IS_PUNCT":False, "OP": "*"},
            {"LOWER": "outstanding"},
            {"LOWER": "shares"},
            {"IS_PUNCT":False, "OP": "*"},
            {"LOWER": {"IN": ["of", "on"]}},
            {"ENT_TYPE": "DATE", "OP": "+"},
            {"ENT_TYPE": "DATE", "OP": "?"},
            {"OP": "?"},
            {"ENT_TYPE": "DATE", "OP": "*"}
        ]
        pattern3 = [
            {"LOWER": {"IN": ["of", "on"]}},
            {"ENT_TYPE": "DATE", "OP": "+"},
            {"ENT_TYPE": "DATE", "OP": "?"},
            {"OP": "?"},
            {"ENT_TYPE": "DATE", "OP": "*"},
            {"OP": "?"},
            {"ENT_TYPE": {"IN": ["CARDINAL", "SECUQUANTITY"]}},
            {"IS_PUNCT":False, "OP": "*"},
            {"LOWER": {"IN": ["issued", "outstanding"]}}
        ]
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
        # WILL BE REPLACED
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
        # WILL BE REPLACED
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
        # WILL BE REPLACED
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

def token_adj_getter(target: Token):
    if not isinstance(target, Token):
        raise TypeError("target must be a Token, got {}".format(type(target)))
    if target.ent_type_ == "SECUQUANTITY":
        return _secuquantity_adj_getter(target)
    if target.ent_type_ == "SECU":
        return _secu_adj_getter(target)
    return _regular_adj_getter(target)

def _regular_adj_getter(target: Token):
    adjs = []
    if target.children:
        for child in target.children:
            if child.pos_ == "ADJ":
                adjs.append(child)
    return adjs

def _secu_adj_getter(target: Token):
    if not isinstance(target, Token):
        raise TypeError("target must be a Token, got {}".format(type(target)))
    if target.ent_type_ != "SECU":
        raise ValueError("target must be a SECU, got {}".format(target.ent_type_))
    # only check in direct children
    adjs = []
    if target.children:
        for child in target.children:
            if child.pos_ == "ADJ":
                adjs.append(child)
    return adjs

def _secuquantity_adj_getter(target: Token):
    if not isinstance(target, Token):
        raise TypeError("target must be a Token")
    if not target.ent_type_ == "SECUQUANTITY":
        raise ValueError("target must be of ent_type_ 'SECUQUANTITY'")
    adjs = []
    amods = token_amods_getter(target)
    if amods:
        adjs += amods
    if target.head:
        if target.head.dep_ == "nummod":
            if target.head.lower_ in SECUQUANTITY_UNITS:
                nsubjpass = token_nsubjpass_getter(target.head)
                if nsubjpass:
                    if nsubjpass.get("adj", None):
                        adjs += nsubjpass["adj"]
    return adjs if adjs != [] else None                        
    
def token_nsubjpass_getter(target: Token):
    if not isinstance(target, Token):
        raise TypeError("target must be a Token. got {}".format(type(target)))
    if target.dep_ == "nsubjpass":
        nsubjpass = {}
        head = target.head
        if head.pos_ == "VERB":
            nsubjpass["verb"] = head
            nsubjpass["adj"] = []
            for child in head.children:
                if child.pos_ == "ADJ":
                    nsubjpass["adj"].append(child)
            if nsubjpass["adj"] == []:
                nsubjpass["adj"] = None
            return nsubjpass
        else:
            nsubjpass = [target] + [i for i in target.children]
            logger.info(f"found following nsubjpass with a different head than a verb, head -> {head, head.pos_, head.dep_}, whole -> {nsubjpass}")
    return None

def span_amods_getter(target: Span):
    if not isinstance(target, Span):
        raise TypeError("target must be a Span, got: type {}".format(type(target)))
    # logger.debug(f"getting amods for: {target, target.label_}")
    if target.label_ == "SECUQUANTITY":
        seen_tokens = set([i for i in target])
        heads_with_dep = []
        for token in target:
            logger.debug(f"token: {token, token.dep_}")
            if token.dep_ == "nummod":
                if token.head:
                    head = token.head
                    if head in seen_tokens:
                        continue
                    else:
                        # always nouns?
                        heads_with_dep.append(head)
                        seen_tokens.add(head)
        amods = []
        if len(heads_with_dep) > 0:
            for head in heads_with_dep:
                if head.lower_ in SECUQUANTITY_UNITS:
                    amods += _get_amods_of_target(head)
        amods += _get_amods_of_target(target)
        return amods if amods != [] else None
    else:
        amods = _get_amods_of_target(target)
        return amods if amods != [] else None

def token_amods_getter(target: Token):
    if not isinstance(target, Token):
        raise TypeError("target must be a Token, got: type {}".format(type(target)))
    # logger.debug(f"getting amods for: {target, target.ent_type_}")
    amods = []
    if target.ent_type_ == "SECUQUANTITY":
        if target.dep_ == "nummod":
            # also get the amods of certain heads
            if target.head:
                if target.head.lower_ in SECUQUANTITY_UNITS:
                    amods += _get_amods_of_target(target.head)
    amods += _get_amods_of_target(target)
    return amods if amods != [] else None

def _get_amods_of_target(target: Span|Token) -> list:
    if isinstance(target, Span):
        return _get_amods_of_target_span(target)
    elif isinstance(target, Token):
        return _get_amods_of_target_token(target)
    else:
        raise TypeError("target must be a Span or Token")


def _get_amods_of_target_span(target: Span):
    '''get amods of first order of target. Needs to have dep_ set.'''
    amods = []
    amods_to_ignore = set([token if token.dep_ == "amod" else None for token in target])
    for token in target:
        pool = [i for i in token.children] + [token.head]
        for possible_match in pool:
            if possible_match.dep_ == "amod" and possible_match not in amods_to_ignore:
                if possible_match not in amods:
                    amods.append(possible_match)
    return amods

def _get_amods_of_target_token(target: Token):
    amods = []
    pool = [i for i in target.children] + [target.head]
    for possible_match in pool:
        if possible_match.dep_ == "amod":
            if possible_match not in amods:
                amods.append(possible_match)
    return amods

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

def filter_dep_matches(matches):
    '''take the longest of the dep matches with same start token, discard rest'''
    if len(matches) <= 1:
        return matches
    len_map = {}
    result_map = {}
    # logger.debug(f"filtering dep matches: {matches}")
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

def _convert_matches_to_spans(doc, matches):
    m = []
    for match in matches:
        m.append(doc[match[1]:match[2]])
    return m

def _convert_dep_matches_to_spans(doc, matches) -> list[tuple[str, list[Token]]]:
    m = []
    for match in matches:
        print(f"match: {match}")
        m.append((match[0], [doc[f] for f in match[1]]))
    return m

def validate_filing_values(values, attributes):
    '''validate a flat filing value'''
    for attr in attributes:
        if attr not in values.keys():
            raise AttributeError
