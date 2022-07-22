import main.parser.extractors as extractors
import pytest
import spacy
import pandas as pd

@pytest.fixture
def get_base_extractor():
    base_extractor = extractors.BaseHTMExtractor()
    yield base_extractor
    del base_extractor

def test_match_outstanding_shares(get_base_extractor):
    base_extractor = get_base_extractor
    phrases = (
        "As of May 4, 2021, 46,522,759 shares of our common stock were issued and outstanding.",
        "The number of shares and percent of class stated above are calculated based upon 399,794,291 total shares outstanding as of May 16, 2022",
        "based on 34,190,415 total outstanding shares of common stock of the Company as of January 17, 2020. ",
        "are based on 30,823,573 shares outstanding on April 11, 2022. ",
        "based on 70,067,147 shares of our Common Stockoutstanding as of October 18, 2021. ",
        "based on 41,959,545 shares of our Common Stock outstanding as of October 26, 2020. "
        )
    expected = [
        {"date": pd.to_datetime("May 4, 2021"),"amount": 46522759},
        {"date": pd.to_datetime("May 16, 2022"),"amount": 399794291},
        {"date": pd.to_datetime("January  17, 2020"),"amount": 34190415},
        {"date": pd.to_datetime("April 11, 2022"),"amount": 30823573},
        {"date": pd.to_datetime("October 18, 2021"),"amount": 70067147},
        {"date": pd.to_datetime("October 26, 2020"),"amount": 41959545},
    ]
    for sent, ex in zip(phrases, expected):
        res = base_extractor.spacy_text_search.match_outstanding_shares(sent)
        assert res[0] == ex

    
    

    