import re
import json
import logging

from bs4 import BeautifulSoup


logging.basicConfig(level=logging.DEBUG)

class TextMetaParser():

    def __init__(self):
        self.re_doc = re.compile("<DOCUMENT>(.*?)</DOCUMENT>", flags=re.DOTALL)
        self.re_sec_doc = re.compile("<SEC-DOCUMENT>(.*?)</SEC-DOCUMENT>", flags=re.DOTALL)
        self.re_text = re.compile("<TEXT>(.*?)</TEXT>", flags=re.DOTALL)
        self.re_sec_header = re.compile("<SEC-HEADER>.*?\n(.*?)</SEC-HEADER>", flags=re.DOTALL)

    def process_document_metadata(self, doc):
        """Process the metadata of an embedded document.
        Args:
            doc (str): Document to extract meta data from.
        Return:
            dict: Dictionary with fields parsed from document.
        """
        metadata_doc = {}

        # Document type
        type_m = re.search("<TYPE>(.*?)\n", doc)
        if type_m:
            metadata_doc["type"] = type_m.group(1)

        # Document sequence
        seq_m = re.search("<SEQUENCE>(.*?)\n", doc)
        if seq_m:
            metadata_doc["sequence"] = seq_m.group(1)

        # Document filename
        fn_m = re.search("<FILENAME>(.*?)\n", doc)
        metadata_doc["filename"] = fn_m.group(1)

        return metadata_doc
    
    def process_document(self, doc, pattern_dict):
        pass

class HtmlFilingParser():
    def __init__(self):
        self.soup = None
        self.unparsed_tables = None
        self.tables = None

    
    def make_soup(self, doc):
        self.soup = BeautifulSoup(doc, "html.parser")
    
    def get_unparsed_tables(self):
        self.unparsed_tables = self.soup.find_all("table")
    
    def get_element_text_content(self, td):
        content = " ".join([s.strip().replace("\n", "' '") for s in td.strings]).strip()
        return content


    def parse_htmltable_with_header(self, htmltable):
        table = {}
        # parse the header
        header = self.parse_htmltable_header(htmltable)
        rows = []
        # parse each row
        for row in htmltable.find_all("tr"):
            rows.append(row)
        
    
    def parse_htmltable_header(self, htmltable):
        header = {}
        parsed_header = []
        unparsed_header = []
        if htmltable.find_all("th") != (None or []):
            # logging.debug(f"value of htmltable.find_all('th'): {htmltable.find_all('th')}")
            for th in htmltable.find_all("th"):
                parsed_header.append(self.get_element_text_content(th))
            # logging.debug(f"parsed <th> header: ${parsed_header}")
        else:
            unparsed_header = htmltable.find("tr")
            # logging.debug(f"unparsed not <th>_header: {unparsed_header}")
            parsed_header = [self.get_element_text_content(td) for td in unparsed_header.find_all("td")]
            # logging.debug(f"parsed not <th> header: {parsed_header}")

        return parsed_header

    def table_has_header(self, htmltable):
        has_header = False
        #has header if it has <th> tags in table
        if htmltable.find("th"):
            # logging.debug("found <th> element")
            has_header = True
            return has_header
        else:
            #finding first <tr> element to check if it is empty or not
            possible_header = htmltable.find("tr")
            # logging.debug(f"possible_header: ${possible_header}")
            header_fields = [self.get_element_text_content(td) for td in possible_header.find_all("td")]
            # logging.debug(f"header_fields strings: ${header_fields}")
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
            "Amount of Registration Fee"
            "Titel of Each Class (.*) Regi(.*)"
        ]
        for table in self.unparsed_tables:
            if self.table_has_header(table):
                header = self.parse_htmltable_header(table)
                if not header:
                    logging.debug(f"table assumed to have header but doesnt. header: ${header}")
                    raise ValueError("Header is empty")
                logging.debug(header)
                for w in wanted_field:
                    reg = re.compile(w, re.I | re.DOTALL)
                    for h in header:
                        if re.match(reg, h):
                            return (True, header, table)
        return (False, None, None)

                


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
    
            



                    


        
        





r""" with open(r"C:\Users\Olivi\Testing\sec_scraping\filings\sec-edgar-filings\PHUN\424B3\0001213900-18-015809\full-submission.txt", "r") as f:
    text = f.read()
    metaparser = TextMetaParser()
    metadata_doc = metaparser.process_document_metadata(text)
    logging.debug(metadata_doc)
    pass """

# TEST FOR ParserS1
S1_path = r"C:\Users\Olivi\Testing\sec_scraping_testing\filings\sec-edgar-filings\PHUN\S-1\0001213900-16-014630\filing-details.html"
with open(S1_path, "rb") as f:
    text = f.read()
    parser = ParserS1()
    parser.make_soup(text)
    parser.get_unparsed_tables()
    registration_fee_table = parser.get_calculation_of_registration_fee_table()
    logging.debug(registration_fee_table)


# TEST FOR Parser424B5
# with open(r"C:\Users\Olivi\Testing\sec_scraping\filings\sec-edgar-filings\PHUN\424B5\0001628280-20-012767\filing-details.html", "rb") as f:
#     text = f.read()
#     parser = Parser424B5()
#     parser.make_soup(text)
#     # print(parser.get_offering_table())
#     print(parser.get_dilution_table())
#         # print(parser.get_tables())