from pathlib import Path
import os
import pytest

from main.parser.parsers import filing_factory, HTMFilingParser
s3_rel_path = r"test_resources\filings\0001325879\S-3\000119312518218817\d439397ds3.htm"

def _get_absolute_path(rel_path):
    return str(Path(__file__).parent.parent / s3_rel_path)

# @pytest.mark.parser_splitting
def test_s3_splitting_by_toc_hrefs():
    s3_path = _get_absolute_path(s3_rel_path)
    parser = HTMFilingParser()
    doc = parser.get_doc(s3_path)
    sections = parser._split_by_table_of_contents_based_on_hrefs(parser.make_soup(doc))
    print(sections)
    assert 1 == 2

# @pytest.mark.parser_splitting
def test_s3_splitting_by_toc_headers():
    s3_path = _get_absolute_path(s3_rel_path)
    parser = HTMFilingParser()
    doc = parser.get_doc(s3_path)
    sections = parser._split_by_table_of_content_based_on_headers(parser.make_soup(doc))

def test_s3_filing_creation():
    s3_path = _get_absolute_path(s3_rel_path)
    s3_path_Path = Path(s3_path)
    info = {
            "path": s3_path,
            "filing_date": None,
            "accession_number": s3_path_Path.parents[0].name,
            "cik": s3_path_Path.parents[2].name,
            "file_number": None,
            "form_type": "S-3",
            "extension": ".htm"
            }
    required_sections = [
        "prospectus summary",
        "risk factors", 
        "cautionary note regarding forward-looking information",
        "use of proceeds",
        "price range of common stock",
        "dividend policy",
        "determination of offering price",
        "dilution",
        "plan of distribution",
        "description of securities",
        "material u.s federal tax consideration for non-u.s holders of common stock",
        "legal matters",
        "where you can find more information",
        "incorporation of certain documents by reference"
        ]
    filing = filing_factory.create_filing(**info)
    filing_titles = set(s.title for s in filing.sections)
    for rsec in required_sections:
        assert rsec in filing_titles
        assert len(filing.get_section(rsec).content) > 10

    # need to run tests on the splitting by toc table first to detect why we cant find close_to_toc

    
        