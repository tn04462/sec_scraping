import re
import json
import logging
from pathlib import Path
from types import NoneType
from attr import Attribute
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup, NavigableString, element
import re
from pyparsing import Each
from dataclasses import dataclass
from abc import ABC


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()



DATE_OF_REPORT_PATTERN = r'(?:(?:(?:Date(?:.?|\n?)of(?:.?|\n?)report(?:[^\d]){0,40})((?:(?:(?:(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December))|(?:(?:Jan(?:(?:\D){0,4}))|(?:Feb(?:(?:\D){0,5}))|(?:Mar(?:(?:\D){0,2}))|(?:Apr(?:(?:\D){0,2}))|(?:May)|(?:Jun(?:(?:\D){0,1}))|(?:Jul(?:(?:\D){0,1}))|(?:Aug(?:(?:\D){0,4}))|(?:Sep(?:(?:\D){0,6}))|(?:Oct(?:(?:\D){0,4}))|(?:Nov(?:(?:\D){0,5}))|(?:Dec(?:(?:\D){0,6}))))(?:(?:[^\d]){0,5}\d.(?:[^\d]){0,6}\d\d\d\d))|(?:(?:(?:\d\d)|(?:[^\d]\d))(?:.){0,2}(?:(?:(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December))|(?:(?:Jan(?:(?:\D){0,4}))|(?:Feb(?:(?:\D){0,5}))|(?:Mar(?:(?:\D){0,2}))|(?:Apr(?:(?:\D){0,2}))|(?:May)|(?:Jun(?:(?:\D){0,1}))|(?:Jul(?:(?:\D){0,1}))|(?:Aug(?:(?:\D){0,4}))|(?:Sep(?:(?:\D){0,6}))|(?:Oct(?:(?:\D){0,4}))|(?:Nov(?:(?:\D){0,5}))|(?:Dec(?:(?:\D){0,6}))))(?:(?:[^\d]){0,5}\d.(?:[^\d]){0,6}\d\d\d\d))))|(?:((?:(?:(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December))|(?:(?:Jan(?:(?:\D){0,4}))|(?:Feb(?:(?:\D){0,5}))|(?:Mar(?:(?:\D){0,2}))|(?:Apr(?:(?:\D){0,2}))|(?:May)|(?:Jun(?:(?:\D){0,1}))|(?:Jul(?:(?:\D){0,1}))|(?:Aug(?:(?:\D){0,4}))|(?:Sep(?:(?:\D){0,6}))|(?:Oct(?:(?:\D){0,4}))|(?:Nov(?:(?:\D){0,5}))|(?:Dec(?:(?:\D){0,6}))))(?:[^\d]){0,5}\d.(?:[^\d]){0,6}\d\d\d\d(?:\n{0,3}))(?:.){0,10}(?:date(?:.){0,3}of(?:.){0,3}report)))|(?:(?:(?:Date(?:[^\d]){0,5}of(?:[^\d]){0,20}report(?:[^\d]){0,40})(?:((?:(?:(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December))|(?:(?:Jan(?:(?:\D){0,4}))|(?:Feb(?:(?:\D){0,5}))|(?:Mar(?:(?:\D){0,2}))|(?:Apr(?:(?:\D){0,2}))|(?:May)|(?:Jun(?:(?:\D){0,1}))|(?:Jul(?:(?:\D){0,1}))|(?:Aug(?:(?:\D){0,4}))|(?:Sep(?:(?:\D){0,6}))|(?:Oct(?:(?:\D){0,4}))|(?:Nov(?:(?:\D){0,5}))|(?:Dec(?:(?:\D){0,6}))))(?:(?:[^\d]){0,5}\d.(?:[^\d]){0,6}\d\d\d\d))|((?:(?:\d\d)|(?:[^\d]\d))(?:.){0,2}(?:(?:(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December))|(?:(?:Jan(?:(?:\D){0,4}))|(?:Feb(?:(?:\D){0,5}))|(?:Mar(?:(?:\D){0,2}))|(?:Apr(?:(?:\D){0,2}))|(?:May)|(?:Jun(?:(?:\D){0,1}))|(?:Jul(?:(?:\D){0,1}))|(?:Aug(?:(?:\D){0,4}))|(?:Sep(?:(?:\D){0,6}))|(?:Oct(?:(?:\D){0,4}))|(?:Nov(?:(?:\D){0,5}))|(?:Dec(?:(?:\D){0,6}))))(?:(?:[^\d]){0,5}\d.(?:[^\d]){0,6}\d\d\d\d)))|(?:(?:(?:(?:(?:January)|(?:February)|(?:March)|(?:April)|(?:May)|(?:June)|(?:July)|(?:August)|(?:September)|(?:October)|(?:November)|(?:December))|(?:(?:Jan(?:(?:\D){0,4}))|(?:Feb(?:(?:\D){0,5}))|(?:Mar(?:(?:\D){0,2}))|(?:Apr(?:(?:\D){0,2}))|(?:May)|(?:Jun(?:(?:\D){0,1}))|(?:Jul(?:(?:\D){0,1}))|(?:Aug(?:(?:\D){0,4}))|(?:Sep(?:(?:\D){0,6}))|(?:Oct(?:(?:\D){0,4}))|(?:Nov(?:(?:\D){0,5}))|(?:Dec(?:(?:\D){0,6}))))(?:[^\d]){0,5}\d.(?:[^\d]){0,6}\d\d\d\d(?:\n{0,3}))(?:.){0,5}(?:Date(?:[^\d]){0,5}of(?:[^\d]){0,20}report))))'
COMPILED_DATE_OF_REPORT_PATTERN = re.compile(DATE_OF_REPORT_PATTERN, re.I | re.MULTILINE | re.X | re.DOTALL)
ITEMS_8K = {
"Item1.01":"Item(?:.){0,2}1\.01(?:.){0,2}Entry(?:.){0,2}into(?:.){0,2}a(?:.){0,2}Material(?:.){0,2}Definitive(?:.){0,2}Agreement",
"Item1.02":"Item(?:.){0,2}1\.02(?:.){0,2}Termination(?:.){0,2}of(?:.){0,2}a(?:.){0,2}Material(?:.){0,2}Definitive(?:.){0,2}Agreement",
"Item1.03":"Item(?:.){0,2}1\.03(?:.){0,2}Bankruptcy(?:.){0,2}or(?:.){0,2}Receivership",
"Item1.04":"Item(?:.){0,2}1\.04(?:.){0,2}Mine(?:.){0,2}Safety",
"Item2.01":"Item(?:.){0,2}2\.01(?:.){0,2}Completion(?:.){0,2}of(?:.){0,2}Acquisition(?:.){0,2}or(?:.){0,2}Disposition(?:.){0,2}of(?:.){0,2}Assets",
"Item2.02":"Item(?:.){0,2}2\.02(?:.){0,2}Results(?:.){0,2}of(?:.){0,2}Operations(?:.){0,2}and(?:.){0,2}Financial(?:.){0,2}Condition",
"Item2.03":"Item(?:.){0,2}2\.03(?:.){0,2}Creation(?:.){0,2}of(?:.){0,2}a(?:.){0,2}Direct(?:.){0,2}Financial(?:.){0,2}Obligation(?:.){0,2}or(?:.){0,2}an(?:.){0,2}Obligation(?:.){0,2}under(?:.){0,2}an(?:.){0,2}Off-Balance(?:.){0,2}Sheet(?:.){0,2}Arrangement(?:.){0,2}of(?:.){0,2}a(?:.){0,2}Registrant",
"Item2.04":"Item(?:.){0,2}2\.04(?:.){0,2}Triggering(?:.){0,2}Events(?:.){0,2}That(?:.){0,2}Accelerate(?:.){0,2}or(?:.){0,2}Increase(?:.){0,2}a(?:.){0,2}Direct(?:.){0,2}Financial(?:.){0,2}Obligation(?:.){0,2}or(?:.){0,2}an(?:.){0,2}Obligation(?:.){0,2}under(?:.){0,2}an(?:.){0,2}Off-Balance(?:.){0,2}Sheet(?:.){0,2}Arrangement",
"Item2.05":"Item(?:.){0,2}2\.05(?:.){0,2}Costs(?:.){0,2}Associated(?:.){0,2}with(?:.){0,2}Exit(?:.){0,2}or(?:.){0,2}Disposal(?:.){0,2}Activities",
"Item2.06":"Item(?:.){0,2}2\.06(?:.){0,2}Material(?:.){0,2}Impairments",
"Item3.01":"Item(?:.){0,2}3\.01(?:.){0,2}Notice(?:.){0,2}of(?:.){0,2}Delisting(?:.){0,2}or(?:.){0,2}Failure(?:.){0,2}to(?:.){0,2}Satisfy(?:.){0,2}a(?:.){0,2}Continued(?:.){0,2}Listing(?:.){0,2}Rule(?:.){0,2}or(?:.){0,2}Standard;(?:.){0,2}Transfer(?:.){0,2}of(?:.){0,2}Listing",
"Item3.02":"Item(?:.){0,2}3\.02(?:.){0,2}Unregistered(?:.){0,2}Sales(?:.){0,2}of(?:.){0,2}Equity(?:.){0,2}Securities",
"Item3.03":"Item(?:.){0,2}3\.03(?:.){0,2}Material(?:.){0,2}Modification(?:.){0,2}to(?:.){0,2}Rights(?:.){0,2}of(?:.){0,2}Security(?:.){0,2}Holders",
"Item4.01":"Item(?:.){0,2}4\.01(?:.){0,2}Changes(?:.){0,2}in(?:.){0,2}Registrant's(?:.){0,2}Certifying(?:.){0,2}Accountant",
"Item4.02":"Item(?:.){0,2}4\.02(?:.){0,2}Non-Reliance(?:.){0,2}on(?:.){0,2}Previously(?:.){0,2}Issued(?:(?:.){0,2} | \.)((Financial(?:.){0,2}Statements)|(Related(?:.){0,2}Audit(?:.){0,2}Report)|(Completed(?:.){0,2}Interim(?:.){0,2}Review))",
"Item5.01":"Item(?:.){0,2}5\.01(?:.){0,2}Changes(?:.){0,2}in(?:.){0,2}Control(?:.){0,2}of(?:.){0,2}Registrant",
"Item5.02":"Item(?:.){0,2}5\.02(?:.){0,2}(?:(Departure(?:.){0,2}of(?:.){0,2}Directors(?:.){0,2}or(?:.){0,2}Certain(?:.){0,2}Officers)|(.Election(?:.){0,2}of(?:.){0,2}Directors)|(.Appointment(?:.){0,2}of(?:.){0,2}Certain(?:.){0,2}Officers)|(.Compensatory(?:.){0,2}Arrangements(?:.){0,2}of(?:.){0,2}Certain(?:.){0,2}Officers))",
"Item5.03":"Item(?:.){0,2}5\.03(?:.){0,2}Amendments(?:.){0,2}to(?:.){0,2}Articles(?:.){0,2}of(?:.){0,2}Incorporation(?:.){0,2}or(?:.){0,2}Bylaws;(?:.){0,2}Change(?:.){0,2}in(?:.){0,2}Fiscal(?:.){0,2}Year",
"Item5.04":"Item(?:.){0,2}5\.04(?:.){0,2}Temporary(?:.){0,2}Suspension(?:.){0,2}of(?:.){0,2}Trading(?:.){0,2}Under(?:.){0,2}Registrant's(?:.){0,2}Employee(?:.){0,2}Benefit(?:.){0,2}Plans",
"Item5.05":"Item(?:.){0,2}5\.05(?:.){0,2}Amendment(?:.){0,2}to(?:.){0,2}Registrant's(?:.){0,2}Code(?:.){0,2}of(?:.){0,2}Ethics,(?:.){0,2}or(?:.){0,2}Waiver(?:.){0,2}of(?:.){0,2}a(?:.){0,2}Provision(?:.){0,2}of(?:.){0,2}the(?:.){0,2}Code(?:.){0,2}of(?:.){0,2}Ethics",
"Item5.06":"Item(?:.){0,2}5\.06(?:.){0,2}Change(?:.){0,2}in(?:.){0,2}Shell(?:.){0,2}Company(?:.){0,2}Status",
"Item5.07":"Item(?:.){0,2}5\.07(?:.){0,2}Submission(?:.){0,2}of(?:.){0,2}Matters(?:.){0,2}to(?:.){0,2}a(?:.){0,2}Vote(?:.){0,2}of(?:.){0,2}Security(?:.){0,2}Holders",
"Item5.08":"Item(?:.){0,2}5\.08(?:.){0,2}Shareholder(?:.){0,2}Director(?:.){0,2}Nominations",
"Item6.01":"Item(?:.){0,2}6\.01(?:.){0,2}ABS(?:.){0,2}Informational(?:.){0,2}and(?:.){0,2}Computational(?:.){0,2}Material",
"Item6.02":"Item(?:.){0,2}6\.02(?:.){0,2}Change(?:.){0,2}of(?:.){0,2}Servicer(?:.){0,2}or(?:.){0,2}Trustee",
"Item6.03":"Item(?:.){0,2}6\.03(?:.){0,2}Change(?:.){0,2}in(?:.){0,2}Credit(?:.){0,2}Enhancement(?:.){0,2}or(?:.){0,2}Other(?:.){0,2}External(?:.){0,2}Support",
"Item6.04":"Item(?:.){0,2}6\.04(?:.){0,2}Failure(?:.){0,2}to(?:.){0,2}Make(?:.){0,2}a(?:.){0,2}Required(?:.){0,2}Distribution",
"Item6.05":"Item(?:.){0,2}6\.05(?:.){0,2}Securities(?:.){0,2}Act(?:.){0,2}Updating(?:.){0,2}Disclosure",
"Item7.01":"Item(?:.){0,2}7\.01(?:.){0,2}Regulation(?:.){0,2}FD(?:.){0,2}Disclosure",
"Item8.01":"Item(?:.){0,2}8\.01(?:.){0,2}Other(?:.){0,2}Events",
"Item9.01":"Item(?:.){0,2}9\.01(?:.){0,2}Financial(?:.){0,2}Statements(?:.){0,2}and(?:.){0,2}Exhibits"
}

TOC_ALTERNATIVES = {
    "principal stockholders": ["SECURITY OWNERSHIP OF CERTAIN BENEFICIAL OWNERS AND MANAGEMENT"],
    "index to financial statements": ["INDEX TO CONSOLIDATED FINANCIAL STATEMENTS"]
}

IGNORE_HEADERS_BASED_ON_STYLE = set("TABLE OF CONTENTS")
HEADERS_TO_DISCARD = ["(unaudited)"]

RE_COMPILED = {
    "two_newlines_or_more": re.compile("(\n){2,}", re.MULTILINE),
    "one_newline": re.compile("(\n)", re.MULTILINE),
    "two_spaces_or_more": re.compile("(\s){2,}", re.MULTILINE)
}


@dataclass
class Filing:
    path: str
    filing_date: str
    accession_number: str
    cik: str
    file_number: str
    form_type: str


@dataclass
class FilingSection:
    title: str
    content: str


class HTMFilingSection(FilingSection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.parser = HtmlFilingParser()
        self.soup: BeautifulSoup = self.parser.make_soup(self.content)
        self.tables: dict = self.extract_tables()
        self.text_only = self.parser.get_text_content(self.soup, exclude=["table", "script", "title", "head"])

    
    def extract_tables(self, reintegrate=["ul_bullet_points"]):
        '''extract the tables, parse them and return them as a dict of nested lists.

        side effect: modifies the soup attribute if reintegrate isnt an empty list
        
        Args:
            reintegrate: which tables to reintegrate as text. if this is an empty list
                         all tables will be returned in the "extracted" section of the dict
                         and the "reintegrated" section will be an empty list
        Returns:
            a dict of form: {
                "reintegrated": [
                        {
                        "classification": classification,
                        "reintegrated_as": new elements that were added to the original doc
                        "table_element": the original <table> element,
                        "parsed_table": parsed representation of the table before reintegration
                        }
                    ],
                "extracted": [
                        {
                        "classification": classification,
                        "table_element": the original <table> element,
                        "parsed_table": parsed representation of table,
                        }
                    ]
                }
        '''
        # pt = self.parser.preprocess_text(self.content)
        unparsed_tables = self.parser.get_unparsed_tables(self.soup)
        tables = {"reintegrated": [], "extracted": []}
        for t in unparsed_tables:
            parsed_table = None
            if self.parser.table_has_header(t):
                parsed_table = self.parser.parse_htmltable_with_header(t)
            else:
                parsed_table = self.parser.primitive_htmltable_parse(t)
                
            cleaned_table = self.parser._clean_parsed_table(
                self.parser._preprocess_table(parsed_table))
            classification = self.parser.classify_table(cleaned_table)
            # print()
            # print(cleaned_table, "\t", classification)
            # print()
            if classification in reintegrate:
                reintegrate_html = self.parser._make_reintegrate_html_of_table(
                    classification, cleaned_table)
                t.replace_with(reintegrate_html)
                tables["reintegrated"].append(
                    {"classification": classification,
                     "reintegrated_as": reintegrate_html,
                     "table_element": t,
                     "parsed_table": cleaned_table}
                )
            else:
                # further reformat the table
                tables["extracted"].append(
                    {"classification": classification,
                     "table_element": t,
                     "parsed_table": cleaned_table}
                )
        return tables


        #     parsed_tables.append(self.parser.clean_parsed_table(parsed_table))
        # return parsed_tables
            # print()
            
            # print(pd.DataFrame(parsed_table))
    
    


class HTMFiling(Filing):
    def __init__(self, doc: str, path: str=None, filing_date: str=None, accession_number: str=None, cik: str=None, file_number: str=None, form_type: str=None):
        super().__init__(
                path=path,
                filing_date=filing_date,
                accession_number=accession_number,
                cik=cik,
                file_number=file_number,
                form_type=form_type)
        self.parser: HtmlFilingParser = HtmlFilingParser()
        self.doc: str = doc
        self.soup: BeautifulSoup = self.parser.make_soup(doc)
        self.sections: list[HTMFilingSection] = self.parser.split_into_sections(self.soup)
    
    def get_preprocessed_text_content(self) -> str:
        '''get all the text content of the Filing'''
        return self.parser.preprocess_text(self.doc)

    def get_preprocessed_section(self, identifier: str|int):
        section = self.get_section(identifier=identifier)
        if section != []:
            return self.preprocess_section(section)
        else:
            return []
    
    def get_section(self, identifier: str|int):
        if not isinstance(identifier, (str, int)):
            raise ValueError
        if self.sections == []:
            return []
        if isinstance(identifier, int):
            try:
                self.sections[identifier]
            except IndexError:
                logger.info("no section with that identifier found")
                return []
        else:
            for sec in self.sections:
                if sec.title == identifier:
                    return sec
            return []
    
    def preprocess_section(self, section: HTMFilingSection):
        text_content = self.parser.make_soup(section.content).getText()
        return self.parser.preprocess_section_content(text_content)
    


class AbstractFilingParser(ABC):
    def split_into_sections(self, doc: BeautifulSoup):
        '''
        Must be implemented by the subclass.
        Should split the filing into logical sections.

        Returns:
            list[FilingSection]'''
        pass
    
    def preprocess_section(self, section: FilingSection):
        '''
        Must be implemented by the subclass.
        Should preprocess the content of the section for
        further processing.

        Returns:
            str
        '''
    
    


    
    


class Parser8K:
    '''
    process and parse 8-k filing.
    
    Usage:
        1) open file
        2) read() file with utf-8 and in "r"
        3) pass to preprocess_filing
        4) extract something: for example with parse_items
    '''
    def __init__(self):
        self.soup = None
        self.first_match_group = self._create_match_group()

    def _create_match_group(self):
        reg_items = "("
        for key, val in ITEMS_8K.items():
            reg_items = reg_items + "("+val+")|"
        reg_items = reg_items[:-2] + "))"
        return re.compile(reg_items, re.I | re.DOTALL)
            

    def make_soup(self, doc):
        self.soup = BeautifulSoup(doc, "html.parser")

    
    def split_into_items(self, path, get_cik=True):
        '''split the 8k into the individual items'''
        _path = path
        with open(path, "r", encoding="utf-8") as f:
            if get_cik is True:
                if isinstance(path, str):
                    _path = Path(path)
                cik = _path.parent.name.split("-")[0]
            else:
                cik = None
            file = f.read()
            filing = self.preprocess_filing(file)
            try:
                items = self.parse_items(filing)
            except AttributeError as e:
                logger.info((e, path, filing), exc_info=True)
                return None
            except IndexError as e:
                logger.info((e, path, filing), exc_info=True)
                return None
            try:
                date = self.get_date_of_report_matches(filing)
            except AttributeError as e:
                logger.info((e, path, filing), exc_info=True)
                return None
            except ValueError as e:
                logger.info((e, filing), exc_info=True)
                return None
            date_group = date.groups()
            valid_dates = []
            for d in date_group:
                if d is not None:
                    valid_dates.append(d)
            if len(valid_dates) > 1:
                logger.error(f"valid_dates found: {valid_dates}, filing: {filing}")
                raise AttributeError("more than one valid date of report for this 8k found")
            else:
                try:
                    valid_date = self.parse_date_of_report(valid_dates[0])
                except Exception as e:
                    logging.info(f"couldnt parse date of filing: {valid_dates}, filing: {filing}")
                    return None 
            return {"cik": str(cik), "file_date": valid_date, "items": items}
            
    
    def get_text_content(self, doc: BeautifulSoup=None, exclude=["table", "script"]):
        '''extract the unstructured language'''
        doc_copy = doc.__copy__()
        if exclude != [] or exclude is not None:
            [s.extract() for s in doc_copy(exclude)]
        return doc_copy.getText()

    def get_item_matches(self, filing: str):
        '''get matches for the 8-k items.
        
        Args:
            filing: should be a cleaned 8-k filing (only text content, no html ect)'''
        matches = []
        for match in re.finditer(self.first_match_group, filing):
            matches.append([match.start(), match.end(), match.group(0)])
        return matches
    
    def get_signature_matches(self, filing: str):
        '''get matches for the signatures'''
        signature_matches = []
        for smatch in re.finditer(re.compile("(signatures|signature)", re.I), filing):
            signature_matches.append([smatch.start(), smatch.end(), smatch.start() - smatch.end()])
        return signature_matches

    def get_date_of_report_matches(self, filing: str):
        date = re.search(COMPILED_DATE_OF_REPORT_PATTERN, filing)
        if date is None:
            raise ValueError
        return date
    
    def parse_date_of_report(self, fdate):
        try:
            date = pd.to_datetime(fdate.replace(",", ", "))
        except Exception as e:
            logging.info(f"couldnt parse date of filing; date found: {fdate}")
            raise e
        return date

    def parse_items(self, filing: str):
        '''extract the items from the filing and their associated paragraph
        '''
        # first get items and signatures
        extracted_items = []
        items = self.get_item_matches(filing)
        signatures = self.get_signature_matches(filing)
        # ensure that there is one signature which comes after all the items
        # otherwise discard the signature
        last_idx = len(items)-1
        for idx, sig in enumerate(signatures):
            # logger.debug(sig)
            for item in items:
                if sig[1] < item[1]:
                    try:
                        signatures.pop(idx)
                    except IndexError as e:
                        raise e
                    except TypeError as e:
                        logger.debug((f"unhandled case of TypeError: ", sig, signatures, e), exc_info=True)
            if len(signatures) == 0:
                continue
        for idx, item in enumerate(items):
            # last item
            if idx == last_idx:
                try:
                    body = filing[item[1]:signatures[0][0]]
                except Exception as e:
                    # logger.debug(f"filing{filing}, item: {item}, signatures: {signatures}")
                    if len(signatures) == 0:
                        # didnt find a signature so just assume content is until EOF
                        body = filing[item[1]:]
                #normalize item
                normalized_item = item[2].lower().replace(" ", "").replace(".", "").replace("\xa0", " ")
                extracted_items.append({normalized_item: body})
            else:
                body = filing[item[1]:items[idx+1][0]]
                normalized_item = item[2].lower().replace(" ", "").replace(".", "").replace("\xa0", " ")
                extracted_items.append({normalized_item: body})
        return extracted_items


    def preprocess_filing(self, filing: str):
        '''cleanes filing and returns only text'''
        if isinstance(filing, BeautifulSoup):
            soup = filing
        else:
            soup = self.make_soup(filing)
        filing = self.get_text_content(soup, exclude=[])
        # replace unwanted unicode characters
        filing.replace("\xa04", "")
        filing.replace("\xa0", " ")
        filing.replace("\u200b", " ")
        # fold multiple empty newline rows into one
        filing = re.sub(re.compile("(\n){2,}", re.MULTILINE), "\n", filing)
        filing = re.sub(re.compile("(\n)", re.MULTILINE), " ", filing)
        # fold multiple spaces into one
        filing = re.sub(re.compile("(\s){2,}", re.MULTILINE), " ", filing)
        return filing



    
class HtmlFilingParser():
    '''
    Baseclass for parsing HtmlFilings.

    Usage:
        from text_parser import HtmlFilingParser
        from bs4 import Beautifulsoup
        parser = HtmlFilingParser() 
        with open(path_to/filing.htm, "r") as f:
            soup = parser.make_soup(f.read())
            
            sections = parser.split_by_table_of_contents(soup)
            # get all the text of the sections
            for name, content in sections:
                # let bs4 make malformed html whole again
                html_content =  Beautifulsoup(content)
                # maybe you want to parse tables from here or just extract all tables
                # and use only the pure text content or not

                # not extracting anything and only replacing common unicode characters
                text = html_content.get_text()
                cleaned_text = parser.preprocess_text(text)

    '''
    def __init__(self):
        pass
    
    def get_text_content(self, doc: BeautifulSoup=None, exclude=["table", "script"]):
        '''extract the unstructured language'''
        doc_copy = doc.__copy__()
        if exclude != [] or exclude is not None:
            [s.extract() for s in doc_copy(exclude)]
        return doc_copy.getText()
    
    

    def get_span_of_element(self, doc: str, ele: element.Tag, pos: int=None):
        '''gets the span (start, end) of the element ele in doc
        
        Args:
            doc: html string'''
        exp = re.compile(re.escape(
                str(ele)))
        span = exp.search(
            doc,
            pos=0 if pos is None else pos).span()
        if not span:
            raise ValueError("span of element couldnt be found")
        else:
            return span
    
    def find_next_by_position(self, doc: str, start_ele: element.Tag, filter):
        if not isinstance(filter, (bool, NoneType)) and not callable(filter):
            raise ValueError("please pass a function, bool, or None for the filter arg to find_next_by_position")
        after_pos = self.get_span_of_element(doc, start_ele)[1]
        for ele in start_ele.next_elements:
            ele_pos = self.get_span_of_element(doc, ele)[0]
            if after_pos < ele_pos:
                if filter is True:
                    return ele
                if filter is None:
                    return ele
                if isinstance(filter, function):
                    if filter(ele) is True:
                        return ele
        return None
    
    
    
    def split_into_sections(self, doc: BeautifulSoup):
            sections_by_toc = self.split_by_table_of_contents(doc)
            if sections_by_toc:
                return sections_by_toc
            else:
                raise NotImplementedError("no way to split into sections is implemented for this case")
 
    def split_by_table_of_contents(self, doc: BeautifulSoup):
        '''split a filing with a TOC into sections base on the TOC.
        
        Args:
            doc: html parsed with bs4

        Returns:
            {section_title: section_content} Where section_content is malformed html and section_title a string
        '''
        # try and split by document by hrefs of the toc
        try:
            sections = self._split_by_table_of_contents_based_on_hrefs(doc)
        except AttributeError as e:
            # couldnt find toc
            logger.info(("Split_by_table_of_content: Filing doesnt have a TOC or it couldnt be determined", e), exc_info=True)
            return None
        except ValueError as e:
            # couldnt find hrefs in the toc so lets continue with different strategy
            logger.info(e, exc_info=True)
            pass
        else:
            return sections
        try:
            sections = self._split_by_table_of_content_based_on_headers(doc)
        except AttributeError as e:
            logger.info(("_Split_by_table_of_content_based_on_headers: Filing doesnt have a TOC or it couldnt be determined", e), exc_info=True)
            return None
        except Exception as e:
            #debug
            logger.info(e, exc_info=True)
        return sections
    
    def preprocess_text(self, text):
        '''removes common unicode and folds multi spaces/newlines into one'''
        text.replace("\xa04", ""
            ).replace("\xa0", " "
            ).replace("\u200b", " "
            )
        # fold multiple empty newline rows into one
        text = re.sub(RE_COMPILED["two_newlines_or_more"], "\n", text)
        text = re.sub(RE_COMPILED["one_newline"], " ", text)
        # fold multiple spaces into one
        text = re.sub(RE_COMPILED["two_spaces_or_more"], " ", text)
        return text
    
    def make_soup(self, doc):
        '''creates a BeautifulSoup from string html'''
        soup = BeautifulSoup(doc, features="html5lib")
        return soup

    def get_unparsed_tables(self, soup: BeautifulSoup):
        '''return all table tags in soup'''
        unparsed_tables = soup.find_all("table")
        return unparsed_tables
    
    
    def classify_table(self, table: list[list]):
        ''''classify a table into subcategories so they can
        be processed further. 
        
        Args:
            table: should be a list of lists cleaned with clean_parsed_table.
        '''
        # assume header
        table_shape = (len(table), len(table[0]))
        logger.debug(f"table shape is: {table_shape}")
        # could be a bullet point table
        if table_shape[1] == 2:
            if self._is_bullet_point_table(table) is True:
                return "ul_bullet_points"
            else:
                return "unclassified"
        return "unclassified"
    
    def _preprocess_table(self, table: list[list]):
        '''preprocess the strings in the table, removing multiple whitespaces and newlines
        Returns:
            a new (preprocessed) table with the same dimensions as the original
        '''
        t = table.copy()
        for ridx, _ in enumerate(t):
            for cidx, _ in enumerate(t[ridx]):
                field_content = t[ridx][cidx]
                if isinstance(field_content, str):
                    t[ridx][cidx] = self.preprocess_text(field_content)
        return t
    
    def _clean_parsed_table(self, table: list[list], remove_identifier: list = ["", "None", None, " "]):
        '''clean a parsed table of shape m,n by removing all columns whose row values are a combination of remove_identifier'''
        tablec = table.copy()
        nr_rows = len(tablec)
        nr_cols = len(tablec[0])
        boolean_matrix = [[True]*nr_cols for n in range(nr_rows)]
        for row in range(nr_rows):
            for col in range(nr_cols):
                if tablec[row][col] in remove_identifier:
                    boolean_matrix[row][col] = False
        cols_to_remove = []
        for col in range(nr_cols):
            all_empty = True
            for row in range(nr_rows):
                if boolean_matrix[row][col] is True:
                    all_empty = False
            if all_empty is True:
                cols_to_remove.insert(0, col)
        for rmv in cols_to_remove:
            for row in range(nr_rows):
                tablec[row].pop(rmv)
        return tablec
    
    def _is_bullet_point_table(self, table: list[list]):
        table_shape = (len(table), len(table[0]))
        if table_shape[1] != 2:
            return False
        bullet = "●"
        cols_unicode = [True]*table_shape[1]
        for col in range(table_shape[1]):
            for row in range(table_shape[0]):
                if table[row][col] not in  ["●", '● ●', "●●", '', ""]:
                    # print(table[row][col], row, col)
                    cols_unicode[col] = False
        if cols_unicode[0] is True:
            return True
        else:
            return False

   
    def _make_reintegrate_html_of_table(self, classification, table: list[list]):
        empty_soup = BeautifulSoup("", features="html5lib")
        base_element =  empty_soup.new_tag("p")
        if classification == "ul_bullet_points":
            for idx, row in enumerate(table):
                ele = empty_soup.new_tag("span")
                ele.string = " ".join(row) + "\n"
                base_element.insert(idx+2, ele)
        return  base_element
        
    
    def get_element_text_content(self, ele):
        '''gets the cleaned text content of a single element.Tag'''
        content = " ".join([s.strip().replace("\n", " ") for s in ele.strings]).strip()
        return content
    
    def primitive_htmltable_parse(self, htmltable):
        '''parse simple html tables without col or rowspan'''
        rows = htmltable.find_all("tr")
        amount_rows = len(rows)
        amount_columns = 0
        table = None
        for row in rows:
            nr_columns = len(row.find_all("td"))
            if nr_columns > amount_columns:
                amount_columns = nr_columns
        # create empty table 
        table = [[None] * amount_columns for each in range(amount_rows)]
        # write each row
        for row_idx, row in enumerate(rows):
            for field_idx, field in enumerate(row.find_all("td")):
                content = self.get_element_text_content(field)
                # adjust row_idx for header
                table[row_idx][field_idx] = content
        return table

    def parse_htmltable_with_header(self, htmltable, colspan_mode="separate", merge_delimiter=" "):
        # parse the header
        header, colspans, body = self.parse_htmltable_header(htmltable)
        # get number of rows (assuming rowspan=1 for each row)
        rows = htmltable.find_all("tr")
        amount_rows = len(rows)
        amount_columns = None
        table = None

        # mode to write duplicate column names for colspan > 1
        if colspan_mode == "separate":
            # get total number columns including colspan
            amount_columns = sum([col for col in colspans])
            # create empty table 
            table = [[None] * amount_columns for each in range(amount_rows)]
            # parse, write each row (ommiting the header)
            for row_idx, row in enumerate(rows[1:]):
                for field_idx, field in enumerate(row.find_all("td")):
                    content = self.get_element_text_content(field)
                    # adjust row_idx for header
                    table[row_idx+1][field_idx] = content

        # mode to merge content of a colspan column under one unique column
        # splitting field content by the merge_delimiter
        elif colspan_mode == "merge":
            #get number of columns ignoring colspan
            amount_columns = sum([1 for col in colspans])
            #create empty table
            table = [[None] * amount_columns for each in range(amount_rows)]

            # parse, merge and write each row excluding header
            for row_idx, row in enumerate(rows[1:]):
                # get list of content in row
                unmerged_row_content = [self.get_element_text_content(td) for td in row.find_all("td")]
                merged_row_content = [None] * amount_columns
                # what we need to shift by to adjust for total of colspan > 1
                colspan_offset = 0
                for idx, colspan in enumerate(colspans):
                    unmerged_idx = idx + colspan_offset
                    merged_row_content[idx] = merge_delimiter.join(unmerged_row_content[unmerged_idx:(unmerged_idx+colspan)])
                    colspan_offset += colspan - 1
                # write merged rows to table
                for r in range(amount_columns):
                    # adjust row_idx for header
                    table[row_idx+1][r] = merged_row_content[r]

            # change colspans to reflect the merge and write header correctly
            colspans = [1] * len(colspans)


        # write header
        cspan_offset = 0
        for idx, h in enumerate(header):
            colspan = colspans[idx]
            if colspan > 1:
                for r in range(colspan-1):
                    table[0][idx + cspan_offset] = h
                    cspan_offset = cspan_offset + 1

            else:
                table[0][idx + cspan_offset] = h

        return table
             
    def parse_htmltable_header(self, htmltable):
        parsed_header = []
        unparsed_header = []
        body = []
        colspans = []
        # first case with actual table header tag <th>
        if htmltable.find_all("th") != (None or []):
            for th in htmltable.find_all("th"):
                colspan = 1
                if "colspan" in th.attrs:
                    colspan = int(th["colspan"])
                parsed_header.append(self.get_element_text_content(th))
                colspans.append(colspan)
            body = [row for row in htmltable.find_all("tr")]
        # second case where first <tr> is header 
        else:
            unparsed_header = htmltable.find("tr")
            for td in unparsed_header.find_all("td"):
                colspan = 1
                if "colspan" in td.attrs:
                    colspan = int(td["colspan"])
                parsed_header.append(self.get_element_text_content(td))
                colspans.append(colspan)
            body = [row for row in htmltable.find_all("tr")][1:]
        return parsed_header, colspans, body

    def preprocess_section_content(self, section_content: str):
        '''cleanes section_content and returns only text'''
        if isinstance(section_content, BeautifulSoup):
            soup = section_content
        else:
            soup = self.make_soup(section_content)
        section_content = soup.getText()
        # replace unwanted unicode characters
        section_content.replace("\xa04", "")
        section_content.replace("\xa0", " ")
        section_content.replace("\u200b", " ")
        # fold multiple empty newline rows into one
        section_content = re.sub(re.compile("(\n){2,}", re.MULTILINE), "\n", section_content)
        section_content = re.sub(re.compile("(\n)", re.MULTILINE), " ", section_content)
        # fold multiple spaces into one
        section_content = re.sub(re.compile("(\s){2,}", re.MULTILINE), " ", section_content)
        return section_content

    def table_has_header(self, htmltable):
        has_header = False
        #has header if it has <th> tags in table
        if htmltable.find("th"):
            has_header = True
            return has_header
        else:
            # finding first <tr> element to check if it is empty
            # otherwise consider it a header
            possible_header = htmltable.find("tr")
            header_fields = [self.get_element_text_content(td) for td in possible_header.find_all("td")]
            for h in header_fields:
                if (h != "") and (h != []):
                    has_header = True
                    break
        return has_header

    def _get_possible_headers_based_on_style(self, doc: BeautifulSoup, start_ele: element.Tag|BeautifulSoup=None, max_distance_multiline: int=400, ignore_toc: bool=True):
        '''look for possible headers based on styling of the elements.

        Ignores elements in the TOC table if found.
        
        approach:
            1) filter all common types of styles the headers could be in
            2) sort into mainheader(all caps) and subheader(not all caps)
            3) if we dont have a lot of mainheaders try and sort by font-size/size
               mostlikely need to check if parents have that property
            4) assign subheaders based on position relative to mainheaders
               eg: subheaders between two mainheaders are assigned to the earlier
               mainheader

        Args:
            start_ele: what element to select from [optional] if not selected start_ele will be doc
        
        Raises:
            ValueError: if the position of an element couldnt be determined
        '''
        str_doc = str(doc)
        # weird start end of conesecutive elements (50k vs 800k ect)? why?
        toc_start_end = None
        if start_ele is None:
            start_ele = doc
        if ignore_toc is True:
            try:
                close_to_toc = doc.find(string=re.compile("(toc|table.of.contents)", re.I | re.DOTALL))
                if isinstance(close_to_toc, NavigableString):
                    close_to_toc = close_to_toc.parent
                if "href" in close_to_toc.attrs:
                    name_or_id = close_to_toc["href"][-1]
                    close_to_toc = doc.find(name=name_or_id)
                    if close_to_toc is None:
                        close_to_toc = doc.find(id=name_or_id)       
                toc_table = close_to_toc.find_next("table")
                found_toc = False
                while found_toc is False:
                    dirty_toc = self.parse_htmltable_with_header(toc_table)
                    if len(dirty_toc) < 10:
                        toc_table = toc_table.find_next("table")
                        if not toc_table:
                            print("couldnt find a toc")
                            after_toc = start_ele
                    else:
                        toc_start_end = self.get_span_of_element(str_doc, toc_table)
                        found_toc = True

                after_toc = self.find_next_by_position(str_doc, toc_table, True)
                logger.debug(f"toc_table span: {self.get_span_of_element(str_doc, toc_table)}")
                logger.debug(f"after_toc span: {self.get_span_of_element(str_doc, after_toc)}")
                # ignore_before = re.search(re.escape(str(after_toc)), str_doc).span()[1]

            except Exception as e:
                logger.debug("handle the following exception in the ignore_toc=True block of _get_possible_headers_based_on_style")
                raise e 

        
        # use i in css selector for case insensitive match
        style_textalign = ["[style*='text-align: center' i]", "[style*='text-align:center' i]"]
        style_weight = ["[style*='font-weight: bold' i]", "[style*='font-weight:bold' i]"]
        style_font = ["[style*='font: bold' i]", "[style*='font:bold' i]"]
        attr_align = "[align='center' i]"
        # add a total count and thresholds for different selector groups
        # eg: we dont find enough textcenter_b and textcenter_eigth candidates go to next group
        selectors = {
            "center_b": [" ".join([attr_align, "b"])],
            "textcenter_strong": [" ".join([s, "> strong"]) for s in style_textalign],
            "textcenter_b": [" ".join([s, " b"]) for s in style_textalign],
            "textcenter_weight": sum([[" ".join([s, ">", w]) for s in style_textalign] for w in style_weight], []),
            "td_textcenter_font_b": [" ".join(["td"+s, "> font > b"]) for s in style_textalign],
            "td_textcenter_font_weigth": sum([[" ".join(["td"+s, "> font"+w]) for s in style_textalign] for w in style_weight], []),
            "b_u": ["b > u"],
            "font_bold_text_align_center_parent": sum([[" ".join([a+f, "font"]) for a in style_textalign] for f in style_font], [])
        }

        matches = {}
        entry_to_ignore = set()
        multiline_matches = 0
        for name, selector in selectors.items():
            if isinstance(selector, list):
                match = {"main": [], "sub":[]}
                for s in selector:
                    last_entry = None
                    ele_group = []
                    # group together elements that are within close range of each other (how many chars?)
                    # -> multiline headers

                    # try this
                    selected_elements = start_ele.select(selector=s)
                    elements = []
                    for idx, e in enumerate(selected_elements):
                        if idx > 0:
                            start_pos = elements[idx-1][1][1]
                        else:
                            start_pos = 0
                        span = self.get_span_of_element(str_doc, e, pos=start_pos)
                        elements.append((e, span))
                    elements_sorted = sorted(elements, key=lambda x: x[1][1])

                    for entry in elements_sorted:
                        ele = entry[0]
                        if entry in entry_to_ignore:
                            continue
                        else:
                            entry_to_ignore.add(entry)
                        if toc_start_end is not None:
                            if self._ele_is_between(str_doc, ele, toc_start_end[0], toc_start_end[1]):
                            # if (0 <= entry[1][0] <= toc_start_end[1]):
                                continue
                        text_content = (ele.string if ele.string 
                                       else " ".join([s for s in ele.strings]))
                        t_is_upper = (text_content.isupper() if len(text_content.split()) < 2 else " ".join(text_content.split()[:1]).isupper()) 
                        if t_is_upper:                            
                            if last_entry is None:
                                last_entry = entry
                            else:
                                if (entry[1][0] - last_entry[1][1]) <= max_distance_multiline:
                                    if ele_group == []:
                                        ele_group.append(last_entry)
                                        entry_to_ignore.add(entry)
                                    if entry != last_entry:
                                        ele_group.append(entry)
                                    last_entry = entry
                                    continue
                                else:
                                    # finished possible multline title
                                    if ele_group != []:
                                        if len(ele_group) > 1:
                                            match["main"].append([e for e in ele_group])
                                            multiline_matches += 1
                                        else:
                                            match["main"].append(ele_group[0])
                                        ele_group = []
                                    else:
                                        match["main"].append(last_entry)
                                    last_entry = None
                                    continue
                            last_entry = entry      
                        else:
                            match["sub"].append(entry)
                            if ele_group != []:
                                match["main"].append([e for e in ele_group])
                                ele_group = []
                            if last_entry is not None:
                                match["main"].append(last_entry)
                                last_entry = None
                    if ele_group == []:
                        if last_entry is not None:
                            match["main"].append(last_entry)
                    else:
                        # append ele group
                        match["main"].append([e for e in ele_group])
                        multiline_matches += 1
                matches[name] = match
            else:
                raise TypeError(f"selectors should be wrapped in a list: got {type(selector)}")
            logger.debug(f"found {multiline_matches} multiline matches")
        return matches
    
    def _format_matches_based_on_style(self, matches, header_style="main"):
        formatted_matches = []
        for k, v in matches.items():
            for i in v[header_style]:
                if i:
                    if isinstance(i, list):
                        pos = i[0][1]
                        full_text = self._normalize_toc_title(
                            " ".join(
                                sum(
                                    [[i[idx][0].string if i[idx][0].string else " ".join([s for s in i[idx][0].strings]) for idx in range(len(i))]], [])))
                        formatted_matches.append({"elements": [f[0] for f in i], "start_pos": pos[0], "end_pos": pos[1], "selector": k, "full_norm_text": full_text})
                    else:
                        pos = i[1]
                        text = i[0].string if i[0].string else " ".join([s for s in i[0].strings])
                        text = self._normalize_toc_title(text)
                        # make this dict with start_ele, end_ele, first_ele_text_norm, full_text_norm, pos_start, pos_end
                        formatted_matches.append({"elements": [i[0]], "start_pos": pos[0], "end_pos": pos[1], "selector": k, "full_norm_text": text})
        return formatted_matches
    
    def _get_toc_list(self, doc: BeautifulSoup, start_table: element.Tag=None):
        '''gets the elements of the TOC as a list.
        
        currently doesnt account for multi table TOC.
        Returns:
            list of [description, page_number]
        '''
        if start_table is None:
            try:
                close_to_toc = doc.find(string=re.compile("(table.?.?of.?.?contents)", re.I|re.DOTALL), recursive=True) 
                if isinstance(close_to_toc, NavigableString):
                    close_to_toc = close_to_toc.parent
                if "href" in close_to_toc.attrs:
                    name_or_id = close_to_toc["href"][-1]
                    close_to_toc = doc.find(name=name_or_id)
                    if close_to_toc is None:
                        close_to_toc = doc.find(id=name_or_id)
                toc_table = close_to_toc.find_next("table")
            except AttributeError as e:
                logger.info(e, exc_info=True)
                logger.info("This filing mostlikely doesnt have a TOC. Couldnt find TOC from close_to_toc tag")
                return None
        else:
            toc_table = start_table
        if toc_table is None:
            logger.info("couldnt find TOC from close_to_toc tag")
        dirty_toc = self.parse_htmltable_with_header(toc_table, colspan_mode="separate")
        if dirty_toc is None:
            logger.info("couldnt get toc from toc_table") 
            return None 
        if len(dirty_toc) < 10:
            #assume we missed the toc
            try:
                toc_table = toc_table.find_next("table")
                toc = self._get_toc_list(doc, toc_table)
                return toc
            except AttributeError:
                return None
        toc = []
        for row in dirty_toc:
            offset = 0
            for idx in range(len(row)):
                field = row[idx-offset]
                if (field is None) or (field == ""):
                    row.pop(idx-offset)
                    offset += 1
            
            if row != []:
                if len(row) == 1:
                    row.append("None")
                toc.append(row)
        return toc
        # toc_table2 = toc_table.find_next("table")
        # toc2 = self.parse_htmltable_with_header(toc_table2, colspan_mode="separate")
        # if toc2 is not None:
        #     try:
        #         if (len(toc2[0][-1]) == (2 or 3)) and (len(toc2[0]) == len(dirty_toc[0])):
        #             [dirty_toc.append(t) for t in toc2]
        #             logger.info("doc had a multipage toc!")
        #     except TypeError:
        #         pass
        # toc = []
        
        # for row in dirty_toc:
        #     print(row)

        

    def _look_for_toc_matches_after(self, start_ele: element.Tag, re_toc_titles: list[(re.Pattern, int)], min_distance: int=5):
            '''
            looks for regex matches in the string of the tags of the element tree.
            
            Avoids matches that are descendants of the last match and matches that are too close
            together.
            
            Args:
                re_toc_titles: should be a list of tuples consisting of (the regex pattern, the max length to match for)
                max length to match for should be equal to the  length + some whitespace margin of the toc_title string 
            '''
            title_matches = []
            min_distance_count = 0
            matched_ele = None
            for ele in start_ele.next_elements:
                if matched_ele == ele.previous_element:
                    if min_distance_count >= min_distance:
                        matched_ele = None
                        min_distance_count = 0
                    else:
                        matched_ele = ele
                        min_distance_count += 1
                        continue
                if ele.string:
                    content = ele.string
                    for re_term, term_length in re_toc_titles:
                        if re.search(re_term, content):
                            content_length = len(ele) if isinstance(ele, (NavigableString, str)) else len(ele.string) 
                            if isinstance(ele, str):
                                ele = ele.parent
                            if content_length < term_length:
                                title_matches.append(ele)
                                # print(re_term, ele)
                                matched_ele = ele
                                break
            return title_matches
    
    def _search_toc_match_in_list_of_tags(self, tags, re_toc_titles):
            '''
            looks for regex matches in the string of the tags and their descendants.
        
            Avoids matches that are descendants of the last match.
            '''
            matches = []
            for tag in tags:
                matched = False
                if tag.string:
                    content = tag.string
                    if content == "":
                        pass
                    else:
                        for re_term, _ in re_toc_titles:
                            if re.search(re_term, content):
                                matches.append(tag)
                                matched = True
                                break
                if matched is False:
                    try:
                        for child in tag.descendants:
                            if child.string:
                                content = child.string
                                if content is not (None or ""):
                                    for re_term, _ in re_toc_titles:
                                        if re.search(re_term, content):
                                            matches.append(child)
                                            break
                    except AttributeError as e:
                        raise e
            return matches
    
    def _ele_is_between(self, doc: str, ele: element.Tag, x1, x2):
        '''check if ele is between x1 and x2 in the document (by regex span)'''
        ele_span = self.get_span_of_element(doc, ele)
        if (x1 > ele_span[0]) and (x2 < ele_span[1]):
            return True
        else:
            return False
    
    def _normalize_toc_title(self, title):
        return re.sub("\s{1,}", " ", re.sub("\n{1,}", " ", title)).lower().strip()
    
    def _create_toc_re(self, search_term, max_length=None):
        if max_length is None:
            max_length = len(search_term) + 4
        else:
            pass
        return (re.compile("^\s*"+re.sub("(\s){1,}", "(?:.){0,4}", search_term)+"\s*$", re.I | re.DOTALL | re.MULTILINE), max_length)
    
    def _split_into_sections_by_tags(self, doc: BeautifulSoup, section_start_elements: dict):
        '''
        splits html doc into malformed html strings by section_start_elements.
        Args:
            section_start_elements: {"section_title": section_title, "ele": element.Tag}
        '''
        sections = []
        for section_nr, start_element in enumerate(section_start_elements):
            
            ele = start_element["ele"]
            
                # ele.insert_before("-START_SECTION_TITLE_REST_OF_DOC")
                # while ele:
                #     previous_ele = ele
                #     ele = ele.find_next()
                # previous_ele.insert_after("-STOP_SECTION_TITLE_REST_OF_DOC")
                # break
            
            ele.insert_before("-START_SECTION_TITLE_"+start_element["section_title"])
            if len(section_start_elements)-1 == section_nr:
                continue
            while (ele != section_start_elements[section_nr + 1]["ele"]):
                ele = ele.next_element
            ele.insert_before("-STOP_SECTION_TITLE_"+start_element["section_title"])
        
        text = str(doc)
        for idx, sec in enumerate(section_start_elements):
            start = re.search(re.compile("-START_SECTION_TITLE_"+re.escape(sec["section_title"]), re.MULTILINE), text)
            if len(section_start_elements)-1 == idx:
                pass
            else:
                end = re.search(re.compile("-STOP_SECTION_TITLE_"+re.escape(sec["section_title"]), re.MULTILINE), text)
            try:
                if len(section_start_elements)-1 == idx:
                    sections.append(HTMFilingSection(
                        title=sec["section_title"],
                        content=text[start.span()[1]:]))
                else:
                    sections.append(HTMFilingSection(
                        title=sec["section_title"],
                        content=text[start.span()[1]:end.span()[0]]))
            except Exception as e:
                print("FAILURE TO SPLIT SECTION BECAUSE:")
                print(f"start: {start}, end: {end}, section_title: {sec['section_title']}, section_idx/total: {idx}/{len(section_start_elements)-1}")
                print(e)
                print("----------------")
        return sections
    
    def _split_by_table_of_content_based_on_headers(self, doc: BeautifulSoup):
        '''split the filing by the element strings of the TOC'''
        close_to_toc = doc.find(string=re.compile("(table.?.?of.?.?contents)", re.I|re.DOTALL), recursive=True) 
        toc_table = close_to_toc.find_next("table")
        # still need to account for multi table TOC, while close_to_toc -> check if toc table
        if toc_table is None:
            logger.info("couldnt find TOC table from close_to_toc tag")
        toc = self.parse_htmltable_with_header(toc_table, colspan_mode="separate")
        # check if we have desc, page header or not and remove it if so
        possible_header = toc[0]
        for head in possible_header:
            if re.search(re.compile("(descript.*)|(page)", re.I), head):
                toc.pop(0)
                break
        toc_titles = []
        for entry in toc:
            if entry[0] != "":
                toc_titles.append(entry[0])

        re_toc_titles = [(re.compile("^\s*"+re.sub("(\s|\n)", "(?:.){0,4}", t)+"\s*$", re.I | re.DOTALL | re.MULTILINE), len(t) + 3) for t in toc_titles]
        ele_after_toc = toc_table.next_sibling
        title_matches = self._look_for_toc_matches_after(
            ele_after_toc,
            re_toc_titles,
            min_distance=5)    
        stil_missing_toc_titles = [
            s for s in toc_titles if self._normalize_toc_title(s) not in 
                [self._normalize_toc_title(f.string
                ) if f.string else self._normalize_toc_title(" ".join([t for t in f.strings])
                ) for f in title_matches]
                ]
            # assume that the still missing toc titles are multi tag titles or malformed after the 4th word
            # so lets take take the first 4 words of the title and look for those
        norm_four_word_titles = [" ".join(self._normalize_toc_title(title).split(" ")[:4]) for title in stil_missing_toc_titles]
        re_four_word_titles = [self._create_toc_re(t, max_length=len(t)+10) for t in norm_four_word_titles]
        four_word_matches = self._look_for_toc_matches_after(ele_after_toc, re_four_word_titles)
        [title_matches.append(m) for m in four_word_matches]
        norm_title_matches = [self._normalize_toc_title(t.string if t.string else " ".join([s for s in t.strings])) for t in title_matches]
        unique_toc_titles = set([self._normalize_toc_title(t) for t in toc_titles])
        unique_match_titles = set(norm_title_matches)
        
        # print("TITLES FOUND:")
        # print(f"found/intersect/total: {len(unique_match_titles)}/{len(unique_match_titles & unique_toc_titles)}/{len(toc_titles)}")
        # print("MISSING TOC MATCHES:")
        # print(unique_toc_titles - unique_match_titles) 
        # print("FOUND BUT NOT IN TOC TITLES")
        # print(unique_match_titles - unique_toc_titles)
        alternative_matches = []
        for failure in (unique_toc_titles - unique_match_titles):
            if failure in TOC_ALTERNATIVES.keys():
                alternative_options = TOC_ALTERNATIVES[failure]
                for option in alternative_options:
                    matches = self._look_for_toc_matches_after(ele_after_toc, [self._create_toc_re(option)])
                    if matches:
                        alternative_matches.append(matches)
                        break
        for match in alternative_matches:
            if len(match) > 1:
                print(alternative_matches)
                print("--------->>>!! address this now !!<<<-------------")
            else:
                title_matches.append(match[0])
        section_start_elements = []
        headers_based_on_style = self._format_matches_based_on_style(self._get_possible_headers_based_on_style(doc, doc), header_style="main")
        # print()
        # print("ALL MATCHES BASED ON HEADERS")
        # print(title_matches, headers_based_on_style)
        replace_headers = []
        add_headers = []
        for idx, headers in enumerate(headers_based_on_style):
            for tm_idx, tm in enumerate(title_matches):
                if isinstance(tm, list):
                    ele = tm[0]
                else:
                    ele = tm
                if ele in headers["elements"]:
                    replace_headers.append((tm_idx, headers["elements"]))
                else:
                    if headers["elements"] not in add_headers:
                        add_headers.append(headers["elements"])
        for idx, replace_header in replace_headers:
            title_matches[idx] = replace_header
        for add_header in add_headers:
            # print(add_header)
            title_matches.append(add_header)
        for tm_idx, tm in enumerate(title_matches):
            if not isinstance(tm, list):
                title_matches[tm_idx] = [tm]
        
        title_matches.sort(key= lambda x: x[0].sourceline)

        offset = 0
        copy_title_matches = title_matches.copy()
        for idx, tm in enumerate(copy_title_matches):
            if idx < (len(title_matches) - 1):
                next_item_sourcelines = [t.sourceline for t in copy_title_matches[idx + 1]]
                current_sourcelines = [t.sourceline for t in tm]
                # print(tm, "\t" ,copy_title_matches[idx + 1])
                for csourceline in current_sourcelines:
                    if csourceline in next_item_sourcelines:
                        if len(tm) == len(copy_title_matches[idx + 1]):
                            title_matches.pop(idx + 1 - offset)
                            offset += 1
                        else:
                            if len(tm) > len(copy_title_matches[idx + 1]):
                                title_matches.pop(idx + 1 - offset)
                            else:
                                title_matches.pop(idx - offset)
                            offset += 1
                            break

        for match in title_matches:
            _title = " ".join(
                        sum(
                            [[match[idx].string if match[idx].string else " ".join([s for s in match[idx].strings]) for idx in range(len(match))]], []))
            section_title = self._normalize_toc_title(_title)
            if section_title not in HEADERS_TO_DISCARD:
                # print({"section_title": section_title, "ele": match[0]})
                section_start_elements.append({"section_title": section_title, "ele": match[0]})
            else:
                logger.info(f"_split_by_table_of_content_based_on_headers: \t Discarded section: {section_title} because it was in HEADERS_TO_DISCARD")
        
        return self._split_into_sections_by_tags(doc, section_start_elements=section_start_elements)
  
    def _split_by_table_of_contents_based_on_hrefs(self, doc: BeautifulSoup):
        '''split the filing based on the hrefs, linking to different parts of the filing, from the TOC.'''
        #
        #!
        #!
        #  ADD HEADERS BASED ON STYLE TO THIS FUNCTION TO MAKE IT MORE EQUIVALENT TO SPLITTING BY HEADERS
        #!
        #!
        #

        # get close to TOC
        try:
            close_to_toc = doc.find(string=re.compile("(toc|table.of.contents)", re.I | re.DOTALL))
            if isinstance(close_to_toc, NavigableString):
                    close_to_toc = close_to_toc.parent
            if "href" in close_to_toc.attrs:
                name_or_id = close_to_toc["href"][-1]
                close_to_toc = doc.find(name=name_or_id)
                if close_to_toc is None:
                    close_to_toc = doc.find(id=name_or_id)       
            toc_table = close_to_toc.find_next("table")
            hrefs = toc_table.findChildren("a", href=True)
            first_ids = [h["href"] for h in hrefs]
            n = 0
            if first_ids == []:
                while (first_ids == []) or (n < 5):
                    close_to_toc = close_to_toc.find_next(string=re.compile("(toc|table.of.contents)", re.I | re.DOTALL))       
                    toc_table = close_to_toc.find_next("table")
                    hrefs = toc_table.findChildren("a", href=True)
                    first_ids = [h["href"] for h in hrefs]
                    n += 1
        except AttributeError as e:   
            logger.info(e, exc_info=True)  
            return None                
        
        # determine first section so we can check if toc is multiple pages
        id = first_ids[0]
        id_match = doc.find(id=id[1:])
        if id_match is None:
            name_match = doc.find(attrs={"name":id[1:]})
            first_toc_element = name_match
        else:
            first_toc_element = id_match
        # check that we didnt miss other pages of toc
        if not first_toc_element:
            raise ValueError("couldnt find section of first element in TOC")
        
        # get all tables before the first header found in toc
        tables = first_toc_element.find_all_previous("table")
        track_ids_done = []
        section_start_elements = []
        section_start_ids = []
        for idx in range(len(tables)-1, -1, -1):
            table = tables[idx]
            hrefs = table.findChildren("a", href=True)
            ids = []
            for a in hrefs:
                id = a["href"]
                toc_title = " ".join([s for s in a.strings]).lower()
                ids.append((id, toc_title))
            section_start_ids.append(ids)
        for entry in sum(section_start_ids, []):
            id = entry[0]
            if id not in track_ids_done:
                id_match = doc.find(id=id[1:])
                if id_match is None:
                    id_match = doc.find(attrs={"name":id[1:]})
                track_ids_done.append(id)
                if id_match:
                    print(id_match, entry)
                    section_start_elements.append({"ele": id_match, "section_title": entry[1]})
                else:
                    print("NO ID MATCH FOR", entry)

        return self._split_into_sections_by_tags(doc, section_start_elements=section_start_elements)
 
    



class ParserS1(HtmlFilingParser):

    def get_calculation_of_registration_fee_table(self, doc: BeautifulSoup):
        wanted_field = [
            # "Title of Each Class of Securities to be Registered",
            # "Title of Each Class of Security Being Registered",
            "Amount(\s*)of(\s*)Registration(\s*)Fee",
            "Title(\s*)of(\s*)Each(\s*)Class(\s*)(.*)Regi(.*)",
            "Amount(\s*)(Being|to(\s*)be)(\s*)Registered"
        ]
        for table in self.get_unparsed_tables(doc):
            if self.table_has_header(table):
                header, colspans, body = self.parse_htmltable_header(table)
                if not header:
                    logging.debug(f"table assumed to have header but doesnt. header: ${header}")
                    raise ValueError("Header is empty")
                # logging.debug(header)
                for w in wanted_field:
                    reg = re.compile(w, re.I | re.DOTALL)
                    for h in header:
                        if re.search(reg, h):
                            return self.parse_htmltable_with_header(table, colspan_mode="merge")
        return None

                
class Parser424B5(HtmlFilingParser):
    def convert_htmltable(self, htmltable):
        # only does tables without headers
        table = {}
        for row in htmltable.find_all("tr"):
            values = []
            for entry in row.find_all("td"):
                if len([e for e in entry.children]) > 0:
                    fonts = entry.find_all("font")
                    for f in fonts:
                        f = f.string
                        if f!=None:
                            values.append(f)

            if values != []:
                if len(values[1:]) == 1:
                    table[values[0]] = values[1:][0]
                else:
                    table[values[0]] = values[1:]
        return table

    def get_offering_table(self, doc: BeautifulSoup):
        def is_offering_div(tag):
            if tag.name != "div":
                return False
            if not tag.find("font"):
                return False
            elif tag.find("font", string=re.compile("the(\s*)offering(\s*)$", re.I)):
                return True
            return False
        divs = doc.find_all(is_offering_div)
        max_distance = 10
        current_distance = 0
        table = []
        for div in divs:
            for sibling in div.next_siblings:
                if current_distance == max_distance:
                    current_distance = 0
                    break
                if sibling.find("table") != None:
                    table = self.convert_htmltable(sibling.find("table"))
                    break
                else:
                    current_distance += 1
        return table
    
    def get_dilution_table(self, doc: BeautifulSoup):
        def is_dilution_div(tag):
            if tag.name != "div":
                return False
            if not tag.find("font"):
                return False
            elif tag.find("font", string=re.compile("dilution$", re.I)):
                return True
            return False
        divs = doc.find_all(is_dilution_div)
        max_distance = 10
        table = []
        for div in divs:
            current_distance = 0
            for sibling in div.next_siblings:
                if current_distance == max_distance:
                    current_distance = 0
                    break
                if sibling.find("table") != None:
                    table = self.convert_htmltable(sibling.find("table"))
                    try:
                        table["About this Prospectus"]
                    except KeyError:
                        pass
                    else:
                        break
                else:
                    current_distance += 1
        return table


# class DEF14AParser(HtmlFilingParser):
    # filing_subtypes = [
    #     "Preliminary Proxy",
    #     "Confidental",
    #     "Definitive Proxy",
    #     "Definitive Additional Materials",
    #     "Soliciting Material"]

    # def check_for_outstanding_shares(self, doc: BeautifulSoup)

    # def determine_filing_subtype(self, doc: BeautifulSoup):
    #   difficult to accomplish across the board in a quick way, so disregard for now
    #     # get right table
    #     # -> go from top and check content of parsed table until we find it
    #     # marked one is the one different
    #     count = 0
    #     subtype_table = None
    #     for t in doc.find_all("table"):
    #         table = self.primitive_htmltable_parse(t)
    #         count += 1
    #         if count <= 3:
    #             print(table)
    #         try:
    #             first_entry = table[0][0]
    #             # print(first_entry)
    #         except IndexError:
    #             continue
    #         except AttributeError:
    #             continue

    #         if re.search(re.compile("check the appropiate box", re.I), first_entry):
    #             print(table)
    
    



    

# class FilingSectionBound:
#     elements: list[element.Tag]
#     elements_start: int
#     elements_end: int
#     parent_doc: str
#     text: str
#     norm_text: str




parser = Parser8K()
Items = {}
# for p in [[s for s in r.glob("*.htm")][0] for r in Path(r"C:\Users\Olivi\Testing\sec_scraping\resources\test_set\0001718405\8-K").glob("*")]:
#     with open(p, "r") as f:
#         h = f.read()
#         matches = parser.get_Items(h)
#         for m in matches:
#             logger.debug(m)
#             logger.debug(re.search("Item(.*)((/d){0,3}\.(/d){0,3})", m[0]))
        
            



                    


        
        





