from main.parser.extractors import MatchFormater
from main.parser.filing_nlp import SpacyFilingTextSearch
from spacy.tokens import Token, Span

text_search = SpacyFilingTextSearch()
f = MatchFormater()


def test_money_string_to_int():
    text = "up to $75,000,000"
    doc = text_search.nlp(text)
    span = doc[0:4]
    assert f.money_string_to_int(span.text) == 75000000
