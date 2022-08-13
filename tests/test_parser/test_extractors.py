import main.parser.extractors as extractors
import pytest
import spacy
import pandas as pd
from pathlib import Path
import datetime
import re
from main.parser.parsers import filing_factory
from main.domain import model
from main.services import unit_of_work, messagebus

s3_shelf = r"test_resources\filings\0001035976\S-3\000143774918017591\fncb20180927_s3.htm"
s3_resale = r"test_resources\filings\0000908311\S-3\000110465919045626\a19-16974_2s3.htm"
s3_ATM = r"test_resources\filings\0000831547\S-3\000083154720000018\cleans-3.htm"
s3_resale_with_warrants = r"test_resources\filings\0001453593\S-3\000149315221008120\forms-3.htm"

def _get_absolute_path(rel_path):
    return str(Path(__file__).parent.parent / rel_path)

@pytest.fixture
def get_fake_messagebus():
    mb = messagebus.MessageBus(unit_of_work.FakeCompanyUnitOfWork, dict())
    yield mb
    del mb

@pytest.fixture
def get_base_extractor():
    base_extractor = extractors.BaseHTMExtractor()
    yield base_extractor
    del base_extractor

@pytest.fixture
def get_s3_extractor():
    base_extractor = extractors.HTMS3Extractor()
    yield base_extractor
    del base_extractor

def get_fake_company():
    return model.Company(
        **{   
            "cik": "0000000001",
            "sic": "9000",
            "symbol": "RAND",
            "name": "Rand Inc.",
            "description_": "Solely a test company meant for usage with pytest"
        }
    )

@pytest.fixture
def get_filing_s3_shelf():
    path = _get_absolute_path(s3_shelf)
    info = {
            "path": path,
            "filing_date": datetime.date(2018, 9, 28),
            "accession_number": Path(path).parents[0].name,
            "cik": Path(path).parents[2].name,
            "file_number": "1",
            "form_type": "S-3",
            "extension": ".htm"
            }
    filing = filing_factory.create_filing(**info)
    return filing

@pytest.fixture
def get_filing_s3_resale_with_warrants():
    path = _get_absolute_path(s3_resale_with_warrants)
    info = {
            "path": path,
            "filing_date": datetime.date(2018, 9, 28),
            "accession_number": Path(path).parents[0].name,
            "cik": Path(path).parents[2].name,
            "file_number": "1",
            "form_type": "S-3",
            "extension": ".htm"
            }
    filing = filing_factory.create_filing(**info)
    return filing

@pytest.fixture
def get_filing_s3_resale():
    path = _get_absolute_path(s3_resale)
    info = {
            "path": path,
            "filing_date": datetime.date(2018, 9, 28),
            "accession_number": Path(path).parents[0].name,
            "cik": Path(path).parents[2].name,
            "file_number": "2",
            "form_type": "S-3",
            "extension": ".htm"
            }
    filing = filing_factory.create_filing(**info)
    return filing

@pytest.fixture
def get_filing_s3_ATM():
    path = _get_absolute_path(s3_ATM)
    info = {
            "path": path,
            "filing_date": datetime.date(2018, 9, 28),
            "accession_number": Path(path).parents[0].name,
            "cik": Path(path).parents[2].name,
            "file_number": "1",
            "form_type": "S-3",
            "extension": ".htm"
            }
    filing = filing_factory.create_filing(**info)[1]
    return filing

# def test_s3_ATM_creation(get_s3_extractor, get_filing_s3_ATM):
#     extractor = get_s3_extractor
#     filing = get_filing_s3_ATM
#     print([s.title for s in filing.sections])
#     cover_page_doc = extractor.doc_from_section(filing.get_section(re.compile("cover page")))
#     offering_amount = extractor.extract_aggregate_offering_amount(cover_page_doc)
#     print(offering_amount, type(offering_amount))
#     assert 1 == 2

def test_s3_classification(get_s3_extractor, get_filing_s3_shelf, get_filing_s3_resale, get_filing_s3_ATM):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    shelf_filing = get_filing_s3_shelf
    assert extractor.classify_s3(shelf_filing) == "shelf"
    resale_filing = get_filing_s3_resale
    assert extractor.classify_s3(resale_filing) == "resale"
    atm_filing = get_filing_s3_ATM
    assert extractor.classify_s3(atm_filing) == "ATM"


def test_security_extraction_s3_shelf(get_s3_extractor, get_fake_messagebus, get_filing_s3_shelf):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    bus = get_fake_messagebus
    filing = get_filing_s3_shelf
    company = get_fake_company()
    cover_page = filing.get_section(re.compile("cover page"))
    cover_page_doc = extractor.doc_from_section(cover_page)
    securities = extractor.extract_securities(filing, company, bus, cover_page_doc)
    expected_securities = [
        model.Security(model.CommonShare(name="common stock", par_value=0.001)),
        model.Security(model.PreferredShare(name="preferred stock", par_value=0.001))
        ]
    assert securities == expected_securities

def test_security_extraction_s3_warrant(get_s3_extractor, get_fake_messagebus, get_filing_s3_resale_with_warrants):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    bus = get_fake_messagebus
    filing = get_filing_s3_resale_with_warrants
    company = get_fake_company()
    cover_page = filing.get_section(re.compile("cover page"))
    # cover_page_doc = extractor.doc_from_section(cover_page)
    filing_text = filing.get_text_only()
    filing_text_doc = extractor.spacy_text_search.nlp(filing_text)
    print(f"single_secu_alias_tuples: {filing_text_doc._.single_secu_alias_tuples}")
    securities = extractor.extract_securities(filing, company, bus, filing_text_doc)
    print(securities)
    assert 1 == 2

def test_security_extraction_s3_ATM(get_s3_extractor, get_fake_messagebus, get_filing_s3_ATM):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    bus = get_fake_messagebus
    filing = get_filing_s3_ATM
    company = get_fake_company()
    cover_page = filing.get_section(re.compile("cover page"))
    cover_page_doc = extractor.doc_from_section(cover_page)
    securities = extractor.spacy_text_search.get_secus_and_secuquantity(cover_page_doc)
    print(securities)
    assert 1 == 2


def test_extract_shelf_s3(get_s3_extractor, get_fake_messagebus, get_filing_s3_shelf):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    bus = get_fake_messagebus
    filing = get_filing_s3_shelf
    company = get_fake_company()
    company = extractor.extract_form_values(filing, company, bus)
    expected_shelf = model.ShelfRegistration("000143774918017591", "1", "S-3", 75000000, datetime.date(2018, 9, 28))
    assert expected_shelf == list(company.shelfs)[0]

def test_extract_resale_s3(get_s3_extractor, get_fake_messagebus, get_filing_s3_resale):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    bus = get_fake_messagebus
    filing = get_filing_s3_resale
    company = get_fake_company()
    company = extractor.extract_form_values(filing, company, bus)
    print(company.resales)
    resale = company.get_resale(filing.accession_number)
    expected_resale = model.ResaleRegistration(**{
        "accn": filing.accession_number,
        "form_type": filing.form_type,
        "file_number": filing.file_number,
        "filing_date": filing.filing_date
    })
    assert resale == expected_resale

def test_extract_ATM_s3(get_s3_extractor, get_fake_messagebus, get_filing_s3_ATM, get_filing_s3_shelf):
    extractor: extractors.HTMS3Extractor = get_s3_extractor
    bus = get_fake_messagebus
    company = get_fake_company()
    shelf_filing = get_filing_s3_shelf
    company = extractor.extract_form_values(shelf_filing, company, bus)
    atm_filing = get_filing_s3_ATM
    company = extractor.extract_form_values(atm_filing, company, bus)
    shelf = company.get_shelf(shelf_filing.file_number)
    offering = shelf.get_offering_by_accn(atm_filing.accession_number)
    expected_offering = model.ShelfOffering(**{
        "offering_type": "ATM",
        "accn": atm_filing.accession_number,
        "anticipated_offering_amount": 75000000,
        "commencment_date": datetime.date(2018, 9, 28),
        "end_date": datetime.date(2021, 9, 27)
    })
    assert offering == expected_offering
    cover_page_doc = extractor.doc_from_section(atm_filing.get_section(re.compile("cover page")))
    aggregate_offering = extractor.extract_aggregate_offering_amount(cover_page_doc)
    expected_aggregate_offering = {'SECU': ['common stock'], 'amount': 75000000}
    assert aggregate_offering == expected_aggregate_offering
    

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

    
    

    