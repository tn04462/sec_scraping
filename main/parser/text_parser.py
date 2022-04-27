import re
import json
import logging
from pathlib import Path
from attr import Attribute
import pandas as pd
from bs4 import BeautifulSoup, element
import re
from pyparsing import Each
import soupsieve



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
            
    
    def get_text_content(self, filing: BeautifulSoup=None):
        '''extract the unstructured language'''
        if filing is None:
            filing = self.soup
        # [s.extract() for s in filing(['style', 'script', '[document]', 'head', "title"])]
        return filing.getText()

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
            self.soup = filing
        else:
            self.make_soup(filing)
        filing = self.get_text_content()
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
    def __init__(self):
        self.soup = None
        self.unparsed_tables = None
        self.tables = None
    
    def split_by_table_of_contents(self, doc: BeautifulSoup):
        if doc is None:
            doc = self.soup
        
        # try and split by document by hrefs of the toc
        try:
            sections = self._split_by_tabel_of_contents_based_on_hrefs(doc)
        except AttributeError as e:
            # couldnt find toc
            logger.info(("Split_by_table_of_content: Filing doesnt have a TOC or it couldnt be determined", e), exc_info=True)
            return None
        except ValueError as e:
            # couldnt find hrefs in the toc so lets continue with different strategy
            logger.info(e, exc_info=True)
            pass
        try:
            sections = self._split_by_table_of_content_based_on_headers(doc)
        except Exception as e:
            #debug
            logger.info(e, exc_info=True)

        return sections
    
    def _split_by_table_of_content_based_on_headers(self, doc: BeautifulSoup):
        close_to_toc = doc.find(string=re.compile("(table.?.?of.?.?contents)", re.I)) 
        toc_table = close_to_toc.find_next("table")
        if toc_table is None:
            logger.info("couldnt find TOC table from close_to_toc tag")
        toc = self.parse_htmltable_with_header(toc_table, colspan_mode="separate")
        print(doc.get_text())
        print(toc)
    
    def _split_by_tabel_of_contents_based_on_hrefs(self, doc: BeautifulSoup):
        # get close to TOC
        try:
            close_to_toc = doc.find(string=re.compile("(toc|table.of.contents)", re.I | re.DOTALL))       
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
        except AttributeError:
            
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
                    section_start_elements.append({"ele": id_match, "toc_title": entry[1]})
                else:
                    print("NO ID MATCH FOR", entry)

        sections = {}
        for section_nr, start_element in enumerate(section_start_elements):
            ele = start_element["ele"]
            if len(section_start_elements)-1 == section_nr:
                section_start_elements.append({"ele": ele, "toc_title": "REST_OF_DOC"})
                ele.insert_before("-START_TOC_TITLE_REST_OF_DOC")
                while ele:
                    previous_ele = ele
                    ele = ele.find_next()
                previous_ele.insert_after("-STOP_TOC_TITLE_REST_OF_DOC")
                break
            ele.insert_before("-START_TOC_TITLE_"+start_element["toc_title"])
            while ele != section_start_elements[section_nr + 1]["ele"]:
                ele = ele.next_element
            ele.insert_before("-STOP_TOC_TITLE_"+start_element["toc_title"])
        
        text = str(doc)
        for sec in section_start_elements:
            start = re.search(re.compile("-START_TOC_TITLE_"+re.escape(sec["toc_title"]), re.MULTILINE), text)
            end = re.search(re.compile("-STOP_TOC_TITLE_"+re.escape(sec["toc_title"]), re.MULTILINE), text)
            try:
                sections[sec["toc_title"]] = text[start.span()[1]:end.span()[0]]
            except Exception as e:
                print(start, end, sec["toc_title"])
                print(e)
        return sections
                

        #insert text markers at the tags href'ed by the toc
        #then seperate based on  those inserted markers

    
    def make_soup(self, doc):
        self.soup = BeautifulSoup(doc, "html.parser")
    
    def get_unparsed_tables(self):
        self.unparsed_tables = self.soup.find_all("table")
    
    def get_element_text_content(self, ele):
        content = " ".join([s.strip().replace("\n", " ") for s in ele.strings]).strip()
        return content


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



class ParserS1(HtmlFilingParser):

    def get_calculation_of_registration_fee_table(self):
        wanted_field = [
            # "Title of Each Class of Securities to be Registered",
            # "Title of Each Class of Security Being Registered",
            "Amount(\s*)of(\s*)Registration(\s*)Fee",
            "Title(\s*)of(\s*)Each(\s*)Class(\s*)(.*)Regi(.*)",
            "Amount(\s*)(Being|to(\s*)be)(\s*)Registered"
        ]
        for table in self.unparsed_tables:
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

    def get_offering_table(self):
        def is_offering_div(tag):
            if tag.name != "div":
                return False
            if not tag.find("font"):
                return False
            elif tag.find("font", string=re.compile("the(\s*)offering(\s*)$", re.I)):
                return True
            return False
        divs = self.soup.find_all(is_offering_div)
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
    
    def get_dilution_table(self):
        def is_dilution_div(tag):
            if tag.name != "div":
                return False
            if not tag.find("font"):
                return False
            elif tag.find("font", string=re.compile("dilution$", re.I)):
                return True
            return False
        divs = self.soup.find_all(is_dilution_div)
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


parser = Parser8K()
Items = {}
# for p in [[s for s in r.glob("*.htm")][0] for r in Path(r"C:\Users\Olivi\Testing\sec_scraping\resources\test_set\0001718405\8-K").glob("*")]:
#     with open(p, "r") as f:
#         h = f.read()
#         matches = parser.get_Items(h)
#         for m in matches:
#             logger.debug(m)
#             logger.debug(re.search("Item(.*)((/d){0,3}\.(/d){0,3})", m[0]))
        
            



                    


        
        





