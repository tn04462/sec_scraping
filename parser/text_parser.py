import re
import json
import logging
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.DEBUG)

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
    
            



                    


        
        





