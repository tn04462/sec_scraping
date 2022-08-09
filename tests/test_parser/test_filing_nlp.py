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
        3,
        (0, 1)
    ),
    (
        "The Series A Warrants have an exercise price of $11.50 per share",
        11.5,
        (1, 4)
    ),
    (
        "Warrants to purchase 96,668 shares of common stock and remain outstanding at any time on or prior to December 31, 2022 at an initial exercise price of $3.00 per share.",
        3,
        (0, 1)
    ),
    ])
def test_match_exercise_price(text, expected, secu_idx, get_search):
    search: SpacyFilingTextSearch = get_search
    doc = search.nlp(text)
    # print([ent.text for ent in doc.ents])
    # print([token.text for token in doc])
    secu = doc[secu_idx[0]:secu_idx[1]]
    matches = search.match_secu_exercise_price(doc, secu)
    # print(matches, type(matches[0]))
    assert expected == matches[0]

def test_secu_alias_map(get_search):
    search = get_search
    text = "On February 22, 2021, we entered into the Securities Purchase Agreement (the “Securities Purchase Agreement”), pursuant to which we agreed to issue the investor named therein (the “Investor”) 8,888,890 shares (the “Shares”) of our common stock, par value $0.000001 per share, at a purchase price of $2.25 per share, and a warrant to purchase up to 6,666,668 shares of our common stock (the “Investor Warrant”) in a private placement (the “Private Placement”). The closing of the Private Placement occurred on February 24, 2021."
    # text = "On February 22, 2021, we entered into the Securities Purchase Agreement (the “Securities Purchase Agreement”), pursuant to which we agreed to issue the investor named therein (the “Investor”) 8,888,890 shares (the “Shares”) of our common stock, par value $0.000001 per share, at a purchase price of $2.25 per share, and a warrant (the “Investor Warrant”) to purchase up to 6,666,668 shares of our common stock in a private placement (the “Private Placement”). The closing of the Private Placement occurred on February 24, 2021."
    doc = search.nlp(text)
    print(doc._.single_secu_alias_tuples)
    print(doc._.single_secu_alias)
    for k, v in doc._.single_secu_alias_tuples.items():
        for value in v:
            base = value[0]
            alias = value[1]
            print(base[0].i, base[-1].i)
            if alias is not None:
                print(alias[0].i, alias[-1].i)
    assert 1 == 2


