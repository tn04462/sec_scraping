import pytest
import spacy
from spacy.tokens import Span, Token, Doc
from spacy.matcher import Matcher
from main.parser.filing_nlp import SpacyFilingTextSearch

@pytest.fixture
def get_search():
    search = SpacyFilingTextSearch()
    yield search
    del search

# @pytest.fixture
# def get_empty_matcher(get_search):
#     search = get_search
#     matcher = Matcher(search.nlp.vocab)
#     yield matcher
#     del matcher

@pytest.mark.parametrize(["text", "expected", "secu_idx"], [
    (
        "Warrants to purchase 33,334 shares of common stock at any time on or prior to September 26, 2022 at an initial exercise price of $3.00 per share.",
        "Warrants to purchase 33,334 shares of common stock at any time on or prior to September 26, 2022 at an initial exercise price of $3.00 per share.",
        (0, 1)),
    (
        "The Series A Warrants have an exercise price of $11.50 per share",
        "Series A Warrants have an exercise price of $11.50 per share",
        (1, 4)),
    ])
def test_match_exercise_price(text, expected, secu_idx, get_search):
    search: SpacyFilingTextSearch = get_search
    doc = search.nlp(text)
    # print([ent.text for ent in doc.ents])
    # print([token.text for token in doc])
    secu = doc[secu_idx[0]:secu_idx[1]]
    matches = search.match_secu_exercise_price(doc, secu)
    # print(matches, type(matches[0]))
    assert expected == matches[0].text

