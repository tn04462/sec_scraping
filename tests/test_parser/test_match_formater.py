
from main.parser.filing_nlp import SpacyFilingTextSearch, MatchFormater
from spacy.tokens import Token, Span
import pytest
from datetime import timedelta
import datetime

text_search = SpacyFilingTextSearch()
f = MatchFormater()

@pytest.mark.parametrize(["input", "expected"], [
    ("up to $75,000,000", 75000000),
    ("up to $7.5 million", 7500000),
    ("up to $7,5 million", 7500000),
    ("up to $0.0075 billion", 7500000),
    ("11.5", 11.5)
    ])
def test_money_string_to_float(input, expected):
    assert f.money_string_to_float(input) == expected

def test_timedelta_conversion_with_numeric_tokens():
    tokens = [t for t in text_search.nlp("3 weeks")]
    assert f.coerce_tokens_to_timedelta(tokens)[0][0] == timedelta(weeks=3)

def test_timedelta_conversion_with_numbers_as_words_tokens():
    tokens = [t for t in text_search.nlp("three weeks")]
    assert f.coerce_tokens_to_timedelta(tokens)[0][0] == timedelta(weeks=3)

def test_timedelta_conversion_with_garbage_tokens():
    tokens = [t for t in text_search.nlp("starting on the 3 weeks anniversary after the date which is the issuance date")]
    assert f.coerce_tokens_to_timedelta(tokens)[0][0] == timedelta(weeks=3)

def test_timedelta_conversion_with_multiple_timedeltas():
    tokens = [t for t in text_search.nlp("after 3 weeks and after five weeks")]
    result = f.coerce_tokens_to_timedelta(tokens)
    assert result[0][0] == timedelta(weeks=3)
    assert result[1][0] == timedelta(weeks=5)

@pytest.mark.parametrize(["input", "expected"],
    [
        (
            "April 14th 2020", datetime.datetime(2020, 4, 14)
        ),
        (
            "April 14, 2020", datetime.datetime(2020, 4, 14)
        ),
        (
            "14th April 2020", datetime.datetime(2020, 4, 14)
        ),
        (
            "14 of April 2020", datetime.datetime(2020, 4, 14)
        )
    ]
)
def test_date_conversion_from_tokens(input, expected):
    tokens = [t for t in text_search.nlp(input)]
    assert f.coerce_tokens_to_datetime(tokens) == expected
