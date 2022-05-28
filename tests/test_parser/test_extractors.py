import main.parser.extractors as extractors
import pytest
import spacy



def test_match_outstanding_shares():
    phrases = (
        "As of May 4, 2021, 46,522,759 shares of our common stock were issued and outstanding.",
        "The number of shares and percent of class stated above are calculated based upon 399,794,291 total shares outstanding as of May 16, 2022",
        "based on 34,190,415 total outstanding shares of common stock of the Company as of January 17, 2020. ",
        "are based on 30,823,573 shares outstanding on April 11, 2022. ",
        "based on 70,067,147 shares of our Common Stockoutstanding as of October 18, 2021. ",
        "based on 41,959,545 shares of our Common Stock outstanding as of October 26, 2020. "
        )
    for sent in phrases:
        print(sent)
        res = extractors.spacy_text_search.match_outstanding_shares(sent)
        print(res)
    assert 1 == 2

    
    
    