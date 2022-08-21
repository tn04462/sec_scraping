import pytest
import spacy
from spacy.tokens import Span, Token, Doc
from spacy.matcher import Matcher
from main.parser.filing_nlp import SpacyFilingTextSearch, SECUMatcher
from pandas import to_datetime
import datetime

@pytest.fixture
def get_en_core_web_lg_nlp():
    nlp = spacy.load("en_core_web_lg")
    yield nlp
    del nlp

@pytest.fixture
def get_search():
    search = SpacyFilingTextSearch()
    yield search
    del search

@pytest.fixture
def get_secumatcher(get_en_core_web_lg_nlp):
    nlp = get_en_core_web_lg_nlp
    secu_matcher = SECUMatcher(nlp.vocab)
    yield secu_matcher
    del secu_matcher

@pytest.mark.parametrize(["input", "expected"], [
    (
        "This prospectus covers the sale of an aggregate of 2,388,050 shares (the “shares”) of our common stock , $0.001 par value per share (the “ common stock ”), by the selling stockholders identified in this prospectus (collectively with any of the holder’s transferees, pledgees, donees or successors, the “selling stockholders”). The shares are issuable upon the exercise of warrants (the “ warrants ”) purchased by the selling stockholders in a private placement transaction exempt from registration under Section 4(a)(2) of the Securities Act of 1933, as amended (the “Securities Act”), pursuant to a Securities Purchase Agreement dated April 9, 2021 (the “Purchase Agreement”).",
        ["2,388,050"]
    ),
    (
        "This prospectus relates to an aggregate of up to 9,497,051 shares of common stock , par value $0.01 per share, of Basic Energy Services, Inc. (“Basic”) that may be resold from time to time by the selling stockholders named on page 5 of this prospectus for their own account.",
        ["up", "to", "9,497,051"]
    )
])
def test_matcher_SECUQUANTITY(input, expected, get_secumatcher, get_en_core_web_lg_nlp):
    sm =  get_secumatcher
    nlp = get_en_core_web_lg_nlp
    doc = nlp(input)
    sm.matcher_SECUQUANTITY(doc)
    secuquantities = [i.text for i in filter(lambda x: x.ent_type_ == "SECUQUANTITY", doc)]
    assert expected == secuquantities


def test_matcher_SECU(get_secumatcher, get_en_core_web_lg_nlp):
    sm = get_secumatcher
    nlp = get_en_core_web_lg_nlp
    doc = nlp("The Common stock, Series A Preferred stock and the Series C Warrants of company xyz is fairly valued.")
    sm.matcher_SECU(doc)
    secus = [i.text for i in filter(lambda x: x.ent_type_ == "SECU", doc)]
    assert secus == ['Common', 'stock', 'Series', 'A', 'Preferred', 'stock', 'Series', 'C', 'Warrants']

def test__create_secu_span_dependency_matcher_dict(get_search):
    search = get_search
    text = "The Series A Warrants have an exercise price of $11.50 per share"
    doc = search.nlp(text)
    secu = doc[1:4]
    dep_dict = search._create_secu_span_dependency_matcher_dict(secu)
    assert dep_dict == [
        {
            'RIGHT_ID': 'secu_anchor',
            'RIGHT_ATTRS': {'ENT_TYPE': 'SECU', 'LOWER': 'warrants'}
        },
        {
            'LEFT_ID': 'secu_anchor',
            'REL_OP': '>',
            'RIGHT_ID': 'series__1',
            'RIGHT_ATTRS': {'LOWER': 'Series'}
        },
        {
            'LEFT_ID': 'secu_anchor',
            'REL_OP': '>',
            'RIGHT_ID': 'a__2',
            'RIGHT_ATTRS': {'LOWER': 'A'}
        }
        ]
    

@pytest.mark.parametrize(["text", "expected"], [
    (
        "Warrant Shares",
        "Shares"
    ),
    (
        "Placement Agent Warrant",
        "Warrant"
    ),
    (
        "Warrant",
        "Warrant"
    )
])
def test__get_compound_SECU_root(text, expected, get_search):
    search = get_search
    doc = search.nlp(text)
    secu = doc[0:]
    root_token = search._get_compound_SECU_root(secu)
    assert isinstance(root_token, Token) is True
    assert root_token.text == expected
    

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
    secu = doc[secu_idx[0]:secu_idx[1]]
    matches = search.match_secu_exercise_price(doc, secu)
    assert expected == matches[0]



@pytest.mark.parametrize(["text", "expected", "secu_idx"], [
        (
            "The Warrants expires on August 6, 2025.",
            datetime.datetime(2025, 8, 6),
            (1, 2),

        ),
        (
            "The Warrants are exercisable at an exercise price of $2.00 per share and expire on the fourth year anniversary of December 14, 2021, the initial issuance date of the Warrants",
            datetime.datetime(2021, 12, 14) + 4*datetime.timedelta(365.25),
            (1, 2),

        ),
        (
            "The Warrants have an exercise price of $11.50 per share will be exercisable beginning on the calendar day following the six month anniversary of the date of issuance, will expire on March 17, 2026.",
            datetime.datetime(2026, 3, 17),
            (1, 2),

        ),
    ])
def test_match_expiry(text, expected, secu_idx, get_search):
    search: SpacyFilingTextSearch = get_search
    doc = search.nlp(text)
    secu = doc[secu_idx[0]:secu_idx[1]]
    matches = search.match_secu_expiry(doc, secu)
    print(matches)
    assert expected == matches[0]


def test_secu_alias_map(get_search):
    search = get_search
    text = "On February 22, 2021, we entered into the Securities Purchase Agreement (the “Securities Purchase Agreement”), pursuant to which we agreed to issue the investor named therein (the “Investor”) 8,888,890 shares (the “Shares”) of our common stock, par value $0.000001 per share, at a purchase price of $2.25 per share, and a warrant to purchase up to 6,666,668 shares of our common stock (the “Investor Warrant”) in a private placement (the “Private Placement”). The closing of the Private Placement occurred on February 24, 2021."
    # text = "On February 22, 2021, we entered into the Securities Purchase Agreement (the “Securities Purchase Agreement”), pursuant to which we agreed to issue the investor named therein (the “Investor”) 8,888,890 shares (the “Shares”) of our common stock, par value $0.000001 per share, at a purchase price of $2.25 per share, and a warrant (the “Investor Warrant”) to purchase up to 6,666,668 shares of our common stock in a private placement (the “Private Placement”). The closing of the Private Placement occurred on February 24, 2021."
    doc = search.nlp(text)
    # print(doc._.single_secu_alias_tuples)
    # print(doc._.single_secu_alias)
    expected_bases = ["common stock", "common stock", "warrant"]
    expected_alias = ["Investor Warrant"]
    alias_map = doc._.single_secu_alias
    received_bases = sum([alias_map[k]["base"] for k, v in alias_map.items()], [])
    received_alias = sum([alias_map[k]["alias"] for k, v in alias_map.items()], [])
    assert len(expected_bases) == len(received_bases)
    assert len(expected_alias) == len(received_alias)
    for expected, received in zip(expected_bases, received_bases):
        assert expected == received.text
    for expected, received in zip(expected_alias, received_alias):
        assert expected == received.text

def test_match_outstanding_shares(get_search):
    search = get_search
    phrases = (
        "As of May 4, 2021, 46,522,759 shares of our common stock were issued and outstanding.",
        "The number of shares and percent of class stated above are calculated based upon 399,794,291 total shares outstanding as of May 16, 2022",
        "based on 34,190,415 total outstanding shares of common stock of the Company as of January 17, 2020. ",
        "are based on 30,823,573 shares outstanding on April 11, 2022. ",
        "based on 70,067,147 shares of our Common Stockoutstanding as of October 18, 2021. ",
        "based on 41,959,545 shares of our Common Stock outstanding as of October 26, 2020. "
        )
    expected = [
        {"date": to_datetime("May 4, 2021"),"amount": 46522759},
        {"date": to_datetime("May 16, 2022"),"amount": 399794291},
        {"date": to_datetime("January  17, 2020"),"amount": 34190415},
        {"date": to_datetime("April 11, 2022"),"amount": 30823573},
        {"date": to_datetime("October 18, 2021"),"amount": 70067147},
        {"date": to_datetime("October 26, 2020"),"amount": 41959545},
    ]
    for sent, ex in zip(phrases, expected):
        res = search.match_outstanding_shares(sent)
        assert res[0] == ex
