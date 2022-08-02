
from main.parser.filing_nlp import SpacyFilingTextSearch, MatchFormater
from spacy.tokens import Token, Span
import pytest

text_search = SpacyFilingTextSearch()
f = MatchFormater()

@pytest.mark.parametrize(["input", "expected"], [
    ("up to $75,000,000", 75000000),
    ("up to $7.5 million", 7500000),
    ("up to $7,5 million", 7500000),
    ("up to $0.0075 billion", 7500000)
    ])
def test_money_string_to_int(input, expected):
    assert f.money_string_to_int(input) == expected
