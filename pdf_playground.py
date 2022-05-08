pdf = r"C:\Users\Olivi\OneDrive\QuickShare\13flist2022q1.pdf"

# from pdfminer.high_level import extract_text
# text = extract_text(pdf)
# print(text)

import re
from io import StringIO

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser


cusip_re = re.compile("CUSIP\s*NO.*STATUS(.*)", re.DOTALL | re.MULTILINE)

output_string = StringIO()
with open(pdf, 'rb') as in_file:
    parser = PDFParser(in_file)
    doc = PDFDocument(parser)
    rsrcmgr = PDFResourceManager()
    device = TextConverter(rsrcmgr, output_string, laparams=LAParams(line_margin=2, boxes_flow=None))
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in list(PDFPage.create_pages(doc))[2:3]:
        interpreter.process_page(page)
        output_string.write("---delimiter---")

raw_pages = output_string.getvalue()
print(raw_pages)
# raw_pages = str(raw_pages)
raw_pages = raw_pages.split("---delimiter---")

# only values for status column are added/deleted
# so iter range(4) and check if last element is either otherwise assign to new row 


# print(raw_pages)
entries = []
for rp in raw_pages:
    # print(rp)
    raw_content = re.search(cusip_re, rp)
    if raw_content:
        content_entries = raw_content.groups()[0].split("\n\n")
        len_entries = len(content_entries)
        counter = 0
        idx = 0
        current_item = []
        while True:
            if len_entries == idx:
                break
            
            item = content_entries[idx]
            if item == "":
                pass
            else:
                if counter == 3:
                    if re.search("(ADDED)|(DELETED)", item):
                        current_item.append(item)
                    else:
                        counter = 0
                        idx -= 1
                    entries.append(current_item)
                    current_item = []
                else:
                    current_item.append(item)
                    counter += 1
            idx += 1

print(entries)
                

            


    # print(raw_content)

# 1) search for cusip no -> status
# 2) parse from that point, exclude total count on last page
import re
