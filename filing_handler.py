import re
from pathlib import Path
from bs4 import BeautifulSoup
import logging
logging.basicConfig(level=logging.DEBUG)

from xbrl_parser import ParserXBRL


# class FullTextSubmission():
#     def __init__(self, path):
#         self.path = Path(path)
#         self.form_type = None
#         self.filing_number = None
#         self.CIK = None
#         self.full_text = None
#         self.main_document = None
#         self.init_filings()

#     def init_filings(self):
#         with open((self.path / "full-submission.txt"), "r") as f:
#             self.full_text = f.read()
#         with open((self.path / "filing-details.html"), "rb") as f:
#             self.main_document = BeautifulSoup(f.read(), "html.parser")
        
#         self.form_type = re.search("FORM TYPE:(.*)", self.full_text).group(1).strip()
#         self.filing_number = re.search("SEC FILE NUMBER:(.*)", self.full_text).group(1).strip()
#         self.CIK = re.search("CENTRAL INDEX KEY:(.*)", self.full_text).group(1).strip()

class Document():
    def __init__(self, file_name, description, type_, filing_number, content):
        self.file_name = file_name
        self.description = description
        self.type_ = type_
        self.filing_number = filing_number
        self.content = content


class SECFilingInfo():
    '''class to pass info between process steps'''
    def __init__(self, parsing_type=None, form_type=None, filing_number=None, cik=None):
        self.parsing_type = parsing_type
        self.form_type = form_type
        self.filing_number = filing_number
        self.cik = cik


class UnhandledFile():
    '''unhandled preprocessed filetype'''
    def __init__(self, doc, info: SECFilingInfo):
        self.info = info
        self.doc = doc
        

class XBRLFile():
    '''unparsed full text documents that are needed to parse xbrl.
    label file: for more readable keys - not implemented
    instance file: to get context, facts ect.
    ''' 
    def __init__(self, instance_file, label_file, info: SECFilingInfo):
        self.info = info
        self.ins = instance_file
        self.lab = label_file
        


class FilingHandler():
    '''handle the different filing types. parse and return the needed content.
    '''

    def parse_filing(self, path):
        '''path: path to full-submission.txt of filing'''
        with open(path, "r") as f:
            full_text = f.read()
            pp = self.preprocess_documents(full_text)
            parsed = self.process_file(pp)
            return parsed


    def preprocess_documents(self, full_text):
        """
        returns a prepocessed File-class that needs to have an info: SECFilingInfo  attribute
        """
        # get list of individual documents
        divided_full_text = re.findall(re.compile("<DOCUMENT>(.*?)</DOCUMENT>", re.DOTALL), full_text)
        filing_number = re.search("SEC FILE NUMBER:(.*)", full_text).group(1).strip()
        documents = {}
        form_type = self.get_form_type(full_text)
        cik = self.get_cik(full_text)
        for doc in divided_full_text:
            type_ = re.findall("<TYPE>(.*)", doc)[0] if re.findall("<TYPE>(.*)", doc) else None
            desc = re.findall("<DESCRIPTION>(.*)", doc)[0] if re.findall("<DESCRIPTION>(.*)", doc) else None
            file_name = None if re.search("<FILENAME>(.*)", doc) == None else re.search("<FILENAME>(.*)", doc).group(1).strip()
            if (desc is None) or (file_name is None):
                pass
            else:
                documents[file_name] = Document(file_name, desc, type_, filing_number, doc)
        if form_type == ("10-Q" or "10-K"):
            instance_file, label_file, xbrl_file_name_root, xbrl = None, None, None, None
            # find schema file to get root of the xbrl file_name
            for fn in documents.keys():
                if re.search("\.xsd", fn):
                    xbrl_file_name_root = fn.replace(".xsd", "")
                    break
            for fn in documents.keys():
                # look for xbrl-instance and -label file in all documents of the submission
                if instance_file is None:
                    if self._is_xbrl_instance_file(
                        fn,
                        documents[file_name].type_,
                        documents[file_name].description,
                        xbrl_file_name_root):
                        instance_file = documents[fn]
                if label_file is None:
                    if self._is_xbrl_label_file(fn, xbrl_file_name_root):
                        label_file = documents[fn]
                if (instance_file != None) and (label_file != None):
                    souped_ins = self.soup_xbrl_file(instance_file.content)
                    souped_lab = self.soup_xbrl_file(label_file.content)
                    info = SECFilingInfo("xbrl", form_type, filing_number, cik)
                    return XBRLFile(souped_ins, souped_lab, info)

            info = SECFilingInfo("html", form_type, filing_number, cik)
            logging.debug(f"couldnt find relevant xbrl files in {form_type}, parsing first file as html")
            logging.debug(("descriptions, filenames, type_ (s): ", [(documents[fn].description, fn, documents[fn].type_) for fn in documents.keys()]))
            return UnhandledFile(self.soup_html_file(divided_full_text[0]), info)
    
    def process_file(self, file):
        if file.info.parsing_type == "xbrl":
            parser = ParserXBRL()
            xbrl = parser.parse_xbrl(file)
            return xbrl
        if file.info.parsing_type == "html":
            logging.debug("NOT IMPLEMENTED HANDLING OF HTML FILE")
            return
        else:
            logging.debug(f"NOT IMPLEMENTED HANDLING OF FILE")
            return
    
    def _is_xbrl_label_file(self, file_name, xbrl_file_name_root):
        if re.search(re.escape("lab.xml"), file_name):
            return True
        elif xbrl_file_name_root:
            if re.match(re.escape(xbrl_file_name_root + "_lab.xml"), file_name):
                return True
        return False

    
    def _is_xbrl_instance_file(self, file_name, type_, description, xbrl_file_name_root):
        if re.search("\.xml", file_name):
            if re.search(re.compile(".*\.ins", re.I), ):
                return True
            elif re.search(re.compile("INSTANCE", re.I), description):
                return True
            elif xbrl_file_name_root:
                if (re.match(re.escape(xbrl_file_name_root + "_htm.xml"), file_name)
                ) or (
                re.match(re.escape(xbrl_file_name_root + ".xml"), file_name)):
                    return True
        return False
    
    def get_form_type(self, full_text):
        header = re.search(re.compile("<SEC-HEADER>(.*)</SEC-HEADER>", re.DOTALL), full_text).group(1)
        form_type = re.search(re.compile("CONFORMED SUBMISSION TYPE:(.*)"), header).group(1).strip()
        return form_type
    
    def get_cik(self, full_text):
        cik = re.search(re.compile("CENTRAL INDEX KEY:(.*)"), full_text).group(1).strip()
        return cik

               
    def soup_xbrl_file(self, file):
        return BeautifulSoup(file, "xml")
    
    def soup_html_file(self, file):
        return BeautifulSoup(file, "lxml")
                                       
    # def parse_filing(self, filing):
    #     if filing.form_type == "S-1":
    #         pass