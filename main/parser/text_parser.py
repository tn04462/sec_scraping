import re
import json
import logging
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
import re
from pyparsing import Each
import soupsieve



logging.basicConfig(level=logging.DEBUG)

Items8k = {
"Item1.01":"Item(?:\s*|.)1\.01(?:\s*|\.|.)Entry\s*into\s*a\s*Material\s*Definitive\s*Agreement",
"Item1.02":"Item(?:\s*|.)1\.02(?:\s*|\.|.)Termination\s*of\s*a\s*Material\s*Definitive\s*Agreement",
"Item1.03":"Item(?:\s*|.)1\.03(?:\s*|\.|.)Bankruptcy\s*or\s*Receivership",
"Item1.04":"Item(?:\s*|.)1\.04(?:\s*|\.|.)Mine\s*Safety",
"Item2.01":"Item(?:\s*|.)2\.01(?:\s*|\.|.)Completion\s*of\s*Acquisition\s*or\s*Disposition\s*of\s*Assets",
"Item2.02":"Item(?:\s*|.)2\.02(?:\s*|\.|.)Results\s*of\s*Operations\s*and\s*Financial\s*Condition",
"Item2.03":"Item(?:\s*|.)2\.03(?:\s*|\.|.)Creation\s*of\s*a\s*Direct\s*Financial\s*Obligation\s*or\s*an\s*Obligation\s*under\s*an\s*Off-Balance\s*Sheet\s*Arrangement\s*of\s*a\s*Registrant",
"Item2.04":"Item(?:\s*|.)2\.04(?:\s*|\.|.)Triggering\s*Events\s*That\s*Accelerate\s*or\s*Increase\s*a\s*Direct\s*Financial\s*Obligation\s*or\s*an\s*Obligation\s*under\s*an\s*Off-Balance\s*Sheet\s*Arrangement",
"Item2.05":"Item(?:\s*|.)2\.05(?:\s*|\.|.)Costs\s*Associated\s*with\s*Exit\s*or\s*Disposal\s*Activities",
"Item2.06":"Item(?:\s*|.)2\.06(?:\s*|\.|.)Material\s*Impairments",
"Item3.01":"Item(?:\s*|.)3\.01(?:\s*|\.|.)Notice\s*of\s*Delisting\s*or\s*Failure\s*to\s*Satisfy\s*a\s*Continued\s*Listing\s*Rule\s*or\s*Standard;\s*Transfer\s*of\s*Listing",
"Item3.02":"Item(?:\s*|.)3\.02(?:\s*|\.|.)Unregistered\s*Sales\s*of\s*Equity\s*Securities",
"Item3.03":"Item(?:\s*|.)3\.03(?:\s*|\.|.)Material\s*Modification\s*to\s*Rights\s*of\s*Security\s*Holders",
"Item4.01":"Item(?:\s*|.)4\.01(?:\s*|\.|.)Changes\s*in\s*Registrant's\s*Certifying\s*Accountant",
"Item4.02":"Item(?:\s*|.)4\.02(?:\s*|\.|.)Non-Reliance\s*on\s*Previously\s*Issued(?:\s* | \.)((Financial\s*Statements)|(Related\s*Audit\s*Report)|(Completed\s*Interim\s*Review))",
"Item5.01":"Item(?:\s*|.)5\.01(?:\s*|\.|.)Changes\s*in\s*Control\s*of\s*Registrant",
"Item5.02":"Item(?:\s*|.)5\.02(?:\s*|\.|.)(?:(Departure\s*of\s*Directors\s*or\s*Certain\s*Officers)|(.Election\s*of\s*Directors)|(.Appointment\s*of\s*Certain\s*Officers)|(.Compensatory\s*Arrangements\s*of\s*Certain\s*Officers))",
"Item5.03":"Item(?:\s*|.)5\.03(?:\s*|\.|.)Amendments\s*to\s*Articles\s*of\s*Incorporation\s*or\s*Bylaws;\s*Change\s*in\s*Fiscal\s*Year",
"Item5.04":"Item(?:\s*|.)5\.04(?:\s*|\.|.)Temporary\s*Suspension\s*of\s*Trading\s*Under\s*Registrant's\s*Employee\s*Benefit\s*Plans",
"Item5.05":"Item(?:\s*|.)5\.05(?:\s*|\.|.)Amendment\s*to\s*Registrant's\s*Code\s*of\s*Ethics,\s*or\s*Waiver\s*of\s*a\s*Provision\s*of\s*the\s*Code\s*of\s*Ethics",
"Item5.06":"Item(?:\s*|.)5\.06(?:\s*|\.|.)Change\s*in\s*Shell\s*Company\s*Status",
"Item5.07":"Item(?:\s*|.)5\.07(?:\s*|\.|.)Submission\s*of\s*Matters\s*to\s*a\s*Vote\s*of\s*Security\s*Holders",
"Item5.08":"Item(?:\s*|.)5\.08(?:\s*|\.|.)Shareholder\s*Director\s*Nominations",
"Item6.01":"Item(?:\s*|.)6\.01(?:\s*|\.|.)ABS\s*Informational\s*and\s*Computational\s*Material",
"Item6.02":"Item(?:\s*|.)6\.02(?:\s*|\.|.)Change\s*of\s*Servicer\s*or\s*Trustee",
"Item6.03":"Item(?:\s*|.)6\.03(?:\s*|\.|.)Change\s*in\s*Credit\s*Enhancement\s*or\s*Other\s*External\s*Support",
"Item6.04":"Item(?:\s*|.)6\.04(?:\s*|\.|.)Failure\s*to\s*Make\s*a\s*Required\s*Distribution",
"Item6.05":"Item(?:\s*|.)6\.05(?:\s*|\.|.)Securities\s*Act\s*Updating\s*Disclosure",
"Item7.01":"Item(?:\s*|.)7\.01(?:\s*|\.|.)Regulation\s*FD\s*Disclosure",
"Item8.01":"Item(?:\s*|.)8\.01(?:\s*|\.|.)Other(?:\s*|.)Events",
"Item9.01":"Item(?:\s*|.)9\.01(?:\s*|\.|.)Financial\s*Statements\s*and\s*Exhibits"
}

class Parser8K:

    '''
    process and 8-k filing.
    
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
        for key, val in Items8k.items():
            reg_items = reg_items + "("+val+")|"
        reg_items = reg_items[:-2] + "))"
        return re.compile(reg_items, re.I)
            

    def make_soup(self, doc):
        self.soup = BeautifulSoup(doc, "html.parser")
    
    def get_text_content(self, filing: BeautifulSoup=None):
        '''extract the unstructured language'''
        if filing is None:
            filing = self.soup
        # [s.extract() for s in filing(['style', 'script', '[document]', 'head', "title"])]
        return filing.getText().replace("\xa0", " ")

    def get_item_matches(self, filing: str):
        '''get matches for the 8-k items.
        
        Args:
            filing: should be a cleaned 8-k filing (only text content, no html ect)'''
        matches = []
        for match in re.finditer(self.first_match_group, filing):
            matches.append([match.start(), match.end(), match.group(0)])
        return matches

    def parse_date_of_report(self, filing: str):
        print(filing)
        date = re.search(re.compile("Date of Report (Date of earliest event reported): (.*)", re.I), filing)
        return date
    
    def get_signature_matches(self, filing: str):
        '''get matches for the signatures'''
        signature_matches = []
        for smatch in re.finditer(re.compile("(signatures|signature)", re.I), filing):
            signature_matches.append([smatch.start(), smatch.end(), smatch.start() - smatch.end()])
        return signature_matches

    def parse_items(self, filing: str):
        '''extract the items from the filing and their associated paragraph
        
        Raises:
            AttributeError: when items came after the signatures'''
        # first get items and signatures
        extracted_items = []
        items = self.get_item_matches(filing)
        signatures = self.get_signature_matches(filing)
        # ensure that there is one signature which comes after all the items
        # otherwise discard the signature
        last_idx = len(items)-1
        for idx, sig in enumerate(signatures):
            # print(sig)
            for item in items:
                if sig[1] < item[1]:
                    try:
                        signatures.pop(idx)
                    except TypeError as e:
                        print(f"unhandled exception type error: ", sig, signatures)
                        print(e)
            if len(signatures) == 0:
                continue
        for idx, item in enumerate(items):
            # last item
            if idx == last_idx:
                try:
                    body = filing[item[1]:signatures[0][0]]
                except Exception as e:
                    # print(f"filing{filing}, item: {item}, signatures: {signatures}")
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
        return self.get_text_content()
    
        

    
class HtmlFilingParser():
    def __init__(self):
        self.soup = None
        self.unparsed_tables = None
        self.tables = None

    
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
#             print(m)
#             print(re.search("Item(.*)((/d){0,3}\.(/d){0,3})", m[0]))
        
            



                    


        
        





