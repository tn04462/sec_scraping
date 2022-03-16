'''
Aim: Download any SEC file type in every(as long as available
 on website) file format for every filer identified either by
 CIK or ticker symbol. While respecting the sec guidelines:
  https://www.sec.gov/privacy.htm#security
  the most important are:
    - respect rate limit
    - have user_agent header
    - stress sec systems as little as possible

Flow of Program:
    * Downloader creates session
    * 
    1) call is made to get_xbrl("aapl", 10-Q, from_date=2020-01-01, max_amount=10)
    2) get the base-url to the wanted filings by making post request to search-API
    3) get metadata from hit 
    4) try to get the requested file_format by building the url in relation to form type
       if the download fails because 404, log urls used, then retry or fallback to the
       accession_number.txt
    
    create an index file that makes lookup by case number faster
   

'''
import requests
from urllib3.util import Retry
from pathlib import Path
import time
from functools import wraps
import re
import logging
from posixpath import join as urljoin
import zipfile

SEC_RATE_LIMIT_DELAY = 1000 #ms
EDGAR_SEARCH_API_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_ARCHIVES_BASE_PATH = "https://www.sec.gov/Archives/edgar/data"
SUPPORTED_FILINGS = {
    "1",
    "1-A",
    "1-A POS",
    "1-A-W",
    "1-E",
    "1-E AD",
    "1-K",
    "1-SA",
    "1-U",
    "1-Z",
    "1-Z-W",
    "10-12B",
    "10-12G",
    "10-D",
    "10-K",
    "10-KT",
    "10-Q",
    "10-QT",
    "11-K",
    "11-KT",
    "13F-HR",
    "13F-NT",
    "13FCONP",
    "144",
    "15-12B",
    "15-12G",
    "15-15D",
    "15F-12B",
    "15F-12G",
    "15F-15D",
    "18-12B",
    "18-K",
    "19B-4E",
    "2-A",
    "2-AF",
    "2-E",
    "20-F",
    "20FR12B",
    "20FR12G",
    "24F-2NT",
    "25",
    "25-NSE",
    "253G1",
    "253G2",
    "253G3",
    "253G4",
    "3",
    "305B2",
    "34-12H",
    "4",
    "40-17F1",
    "40-17F2",
    "40-17G",
    "40-17GCS",
    "40-202A",
    "40-203A",
    "40-206A",
    "40-24B2",
    "40-33",
    "40-6B",
    "40-8B25",
    "40-8F-2",
    "40-APP",
    "40-F",
    "40-OIP",
    "40FR12B",
    "40FR12G",
    "424A",
    "424B1",
    "424B2",
    "424B3",
    "424B4",
    "424B5",
    "424B7",
    "424B8",
    "424H",
    "425",
    "485APOS",
    "485BPOS",
    "485BXT",
    "486APOS",
    "486BPOS",
    "486BXT",
    "487",
    "497",
    "497AD",
    "497H2",
    "497J",
    "497K",
    "5",
    "6-K",
    "6B NTC",
    "6B ORDR",
    "8-A12B",
    "8-A12G",
    "8-K",
    "8-K12B",
    "8-K12G3",
    "8-K15D5",
    "8-M",
    "8F-2 NTC",
    "8F-2 ORDR",
    "9-M",
    "ABS-15G",
    "ABS-EE",
    "ADN-MTL",
    "ADV-E",
    "ADV-H-C",
    "ADV-H-T",
    "ADV-NR",
    "ANNLRPT",
    "APP NTC",
    "APP ORDR",
    "APP WD",
    "APP WDG",
    "ARS",
    "ATS-N",
    "ATS-N-C",
    "ATS-N/UA",
    "AW",
    "AW WD",
    "C",
    "C-AR",
    "C-AR-W",
    "C-TR",
    "C-TR-W",
    "C-U",
    "C-U-W",
    "C-W",
    "CB",
    "CERT",
    "CERTARCA",
    "CERTBATS",
    "CERTCBO",
    "CERTNAS",
    "CERTNYS",
    "CERTPAC",
    "CFPORTAL",
    "CFPORTAL-W",
    "CORRESP",
    "CT ORDER",
    "D",
    "DEF 14A",
    "DEF 14C",
    "DEFA14A",
    "DEFA14C",
    "DEFC14A",
    "DEFC14C",
    "DEFM14A",
    "DEFM14C",
    "DEFN14A",
    "DEFR14A",
    "DEFR14C",
    "DEL AM",
    "DFAN14A",
    "DFRN14A",
    "DOS",
    "DOSLTR",
    "DRS",
    "DRSLTR",
    "DSTRBRPT",
    "EFFECT",
    "F-1",
    "F-10",
    "F-10EF",
    "F-10POS",
    "F-1MEF",
    "F-3",
    "F-3ASR",
    "F-3D",
    "F-3DPOS",
    "F-3MEF",
    "F-4",
    "F-4 POS",
    "F-4MEF",
    "F-6",
    "F-6 POS",
    "F-6EF",
    "F-7",
    "F-7 POS",
    "F-8",
    "F-8 POS",
    "F-80",
    "F-80POS",
    "F-9",
    "F-9 POS",
    "F-N",
    "F-X",
    "FOCUSN",
    "FWP",
    "G-405",
    "G-405N",
    "G-FIN",
    "G-FINW",
    "IRANNOTICE",
    "MA",
    "MA-A",
    "MA-I",
    "MA-W",
    "MSD",
    "MSDCO",
    "MSDW",
    "N-1",
    "N-14",
    "N-14 8C",
    "N-14MEF",
    "N-18F1",
    "N-1A",
    "N-2",
    "N-23C-2",
    "N-23C3A",
    "N-23C3B",
    "N-23C3C",
    "N-2MEF",
    "N-30B-2",
    "N-30D",
    "N-4",
    "N-5",
    "N-54A",
    "N-54C",
    "N-6",
    "N-6F",
    "N-8A",
    "N-8B-2",
    "N-8F",
    "N-8F NTC",
    "N-8F ORDR",
    "N-CEN",
    "N-CR",
    "N-CSR",
    "N-CSRS",
    "N-MFP",
    "N-MFP1",
    "N-MFP2",
    "N-PX",
    "N-Q",
    "NO ACT",
    "NPORT-EX",
    "NPORT-NP",
    "NPORT-P",
    "NRSRO-CE",
    "NRSRO-UPD",
    "NSAR-A",
    "NSAR-AT",
    "NSAR-B",
    "NSAR-BT",
    "NSAR-U",
    "NT 10-D",
    "NT 10-K",
    "NT 10-Q",
    "NT 11-K",
    "NT 20-F",
    "NT N-CEN",
    "NT N-MFP",
    "NT N-MFP1",
    "NT N-MFP2",
    "NT NPORT-EX",
    "NT NPORT-P",
    "NT-NCEN",
    "NT-NCSR",
    "NT-NSAR",
    "NTFNCEN",
    "NTFNCSR",
    "NTFNSAR",
    "NTN 10D",
    "NTN 10K",
    "NTN 10Q",
    "NTN 20F",
    "OIP NTC",
    "OIP ORDR",
    "POS 8C",
    "POS AM",
    "POS AMI",
    "POS EX",
    "POS462B",
    "POS462C",
    "POSASR",
    "PRE 14A",
    "PRE 14C",
    "PREC14A",
    "PREC14C",
    "PREM14A",
    "PREM14C",
    "PREN14A",
    "PRER14A",
    "PRER14C",
    "PRRN14A",
    "PX14A6G",
    "PX14A6N",
    "QRTLYRPT",
    "QUALIF",
    "REG-NR",
    "REVOKED",
    "RW",
    "RW WD",
    "S-1",
    "S-11",
    "S-11MEF",
    "S-1MEF",
    "S-20",
    "S-3",
    "S-3ASR",
    "S-3D",
    "S-3DPOS",
    "S-3MEF",
    "S-4",
    "S-4 POS",
    "S-4EF",
    "S-4MEF",
    "S-6",
    "S-8",
    "S-8 POS",
    "S-B",
    "S-BMEF",
    "SC 13D",
    "SC 13E1",
    "SC 13E3",
    "SC 13G",
    "SC 14D9",
    "SC 14F1",
    "SC 14N",
    "SC TO-C",
    "SC TO-I",
    "SC TO-T",
    "SC13E4F",
    "SC14D1F",
    "SC14D9C",
    "SC14D9F",
    "SD",
    "SDR",
    "SE",
    "SEC ACTION",
    "SEC STAFF ACTION",
    "SEC STAFF LETTER",
    "SF-1",
    "SF-3",
    "SL",
    "SP 15D2",
    "STOP ORDER",
    "SUPPL",
    "T-3",
    "TA-1",
    "TA-2",
    "TA-W",
    "TACO",
    "TH",
    "TTW",
    "UNDER",
    "UPLOAD",
    "WDL-REQ",
    "X-17A-5",
}
PREFERED_FILE_TYPES = {"xml", "htm", "html", "xbrl", "txt"}
debug = True
if debug is True:
    logger = logging.getLogger("downloader")
    logger.setLevel(logging.DEBUG)



class Downloader:
    '''
    usage: 
    dl = Downloader(r"C:\Users\Download_Folder", user_agent={john smith js@test.com})
    dl.get_filings(
        ticker_or_cik="AAPL",
        form_type="10-Q",
        after_date="2019-01-01",
        before_date="",
        prefered_file_type="xbrl",
        number_of_filings=10,
        want_amendments=False,
        skip_not_prefered=True,
        save=True)   
    '''
    def __init__(self, root_path: str, retries: int = 10, user_agent: str = None):
        self.root_path = Path(root_path)
        self.session = self._create_session(retry=retries)
        self.user_agent = user_agent if user_agent else "max musterman max@muster.com"
        self._next_try_systime_ms = self._get_systime_ms()

        '''
        params:
            root_path: where to save the files
            retries: how many retries per request are allowed
            user_agent: str of 'name surname email' to comply with sec guidelines
            save_function: feed a function to alter what happens with the  '''
  
    def get_filings(
        self,
        ticker_or_cik: str,
        form_type: str,
        after_date: str = "",
        before_date: str = "",
        query: str = "",
        prefered_file_type: str = "html",
        number_of_filings: int = 100,
        want_amendments: bool = True,
        skip_not_prefered: bool = False,
        save: bool = True):
        '''download filings. if param:save is False turns into
        a generator yielding downloaded filing. 
        
        params:
            ticker_or_cik: either a ticker symbol "AAPL" or a 10digit cik
            form_type: what form you want. valid forms are found in SUPPORTED_FILINGS
            after_date: date from which to consider filings
            before_date: date before which to consider filings
            query: query according to https://www.sec.gov/edgar/search/efts-faq.html
            prefered_file_type: what filetype to prefer when looking for filings, see PREFERED_FILE_TYPES for handled extensions
            number_of_filings: how many filings to download.
            want_amendements: if we want to include amendment files or not
            skip_not_prefered: either download or exclude if prefered_file_type
                               fails to match/download
            save: if we want to save the files according to the default function
                  OR not save them and turn this function into a generator, allowing
                  the implementation of a custom way to process filings.

        '''

        hits = self._json_from_search_api(
            ticker_or_cik=ticker_or_cik,
            form_type=form_type,
            number_of_filings=number_of_filings,
            want_amendments=want_amendments,
            after_date=after_date,
            before_date=before_date,
            query=query)
        
        base_meta = [self._get_base_metadata_from_hit(h) for h in hits]
        meta = [self._guess_full_url(
            h, prefered_file_type, skip_not_prefered) for h in base_meta]
        
        for m in meta:
            file = self._download_file(m)
            if self.save is True:
                if file:
                    self._save_file(ticker_or_cik, m, file)
                else:
                    logging.debug("didnt save filing despite wanting to. response from request: {}", resp)
                    break
            else:
                yield file
        return
    

    def _download_file(self, base_meta):
        '''download a file and fallback on secondary url if 404'''
        if base_meta["skip"]:
            logging.debug("skipping {}", base_meta)
            return
        headers = { 
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"}
        try:
            resp = self.session.get(url=base_meta["file_url"], headers=headers)
            # resp = self._get(url=base_meta["file_url"], headers=headers)
            resp.raise_for_status()
        except requests.HTTPError as e:
            if "404" in str(resp):
                resp = self._get(url=base_meta["fallback_url"], headers=headers)
                base_meta["save_name"] = Path(base_meta["fallback_url"]).name
        else:
            base_meta["save_name"] = Path(base_meta["file_url"]).name
        filing = resp.content if resp.content else None
        return filing


    def _save_file(self, ticker_or_cik, base_meta, file):
        '''save the file in specified hirarchy and extract 
        zips. returns nothing'''
        save_path = (self.root_path 
                    /ticker_or_cik
                    /base_meta["form_type"]
                    /base_meta["accession_number"]
                    /base_meta["save_name"])
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(file)
        if base_meta["save_name"][-3:] == "zip":
            with zipfile.ZipFile(save_path, "r") as z:
                z.extractall(save_path.parent)
        return

    # save by cik would be most consistent but allow
    # for switching to ticker_or_cik term.
    # allow for user created save function,
    # which gets ticker_or_cik, file and base_meta passed
    # could be used for parsing before saving or
    # save in another file structure 



    def _guess_full_url(self, base_meta, prefered_file_type, skip_not_prefered):
        '''infers the filename of a filing and adds it and
        a fallback to the base_meta dict. returns the changed base_meta dict
        '''
        skip = False
        base_url = base_meta["base_url"]
        accession_number = base_meta["accession_number"]
        if prefered_file_type == "xbrl":
            # only add link to the zip file for xbrl to reduce amount of requests
            base_meta["file_url"] = urljoin(base_url, (accession_number + "-xbrl.zip"))
        # extend for file_types: xml, html/htm, txt

        # for cases not specified: check if main_file_name has wanted extension
        # and assume main_file is the one relevant
        if not "file_url" in base_meta.keys():
            suffix = Path(base_meta["main_file_name"]).suffix.replace(".", "")
            if suffix == prefered_file_type:
                base_meta["file_url"] = urljoin(base_url, base_meta["main_file_name"])
                skip = False
            else:
                skip = skip_not_prefered
        base_meta["skip"] = skip
        base_meta["fallback_url"] = urljoin(base_url, base_meta["main_file_name"])
        return base_meta

    
    def _save_from_full_text(self, full_text: str, form_type: str, file_extension: list):
        # quick to implement as most code is already in parser
        pass 
    
    def _get_systime_ms(self):
        return int(time.time() * SEC_RATE_LIMIT_DELAY)
    
    def _get_base_metadata_from_hit(self, hit: dict):
        '''getting the most relevant information out of a entry. returning a dict'''
        accession_number, filing_details_filename = hit["_id"].split(":", 1)
        accession_number_no_dash = accession_number.replace("-", "", 2)
        cik = hit["_source"]["ciks"][-1]
        submission_base_url = urljoin(urljoin(EDGAR_ARCHIVES_BASE_PATH, cik),(accession_number_no_dash))
        xsl = hit["_source"]["xsl"] if hit["_source"]["xsl"] else None
        return {
            "form_type": hit["_source"]["root_form"],
            "accession_number": accession_number,
            "cik": cik,
            "base_url": submission_base_url,
            "main_file_name": filing_details_filename,
            "xsl": xsl}
   
    def _json_from_search_api(
            self,
            ticker_or_cik: str,
            form_type: str,
            number_of_filings: int = 1,
            want_amendments = False,
            after_date: str = "",
            before_date: str = "",
            query: str = ""
            ):
        '''getting a list of all filings of specified ticker_or_cik. returns dict of dicts'''
        gathered_responses = []
        headers = { 
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "efts.sec.gov"}
        start_index = 0
        while len(gathered_responses) < number_of_filings:
            post_body = {
                "dateRange": "custom",
                "startdt": after_date,
                "enddt": before_date,
                "entityName": ticker_or_cik,
                "forms": [form_type],
                "from": start_index,
                "q": query}
            resp = self._post(url=EDGAR_SEARCH_API_URL, json=post_body, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            
            if "error" in result:
                try:
                    root_cause = result["error"]["root_cause"]
                    if not root_cause:
                        raise ValueError
                    else:
                        raise ValueError(f"error reason: {root_cause[0]['reason']}")  
                except (KeyError, IndexError) as e:
                    raise e
            if not result:
                break
            
            for res in result["hits"]["hits"]:
                # only filter for amendments here
                res_form_type = res["_source"]["file_type"]
                is_amendment = res_form_type[-2:] == "/A"
                if not want_amendments and is_amendment:
                    continue
                # make sure that no wrong filing type is added
                if (not is_amendment) and (res_form_type != form_type):
                    continue
                gathered_responses.append(res)

            query_size = result["query"]["size"]
            start_index += query_size

        return gathered_responses[:number_of_filings]
    
    def _rate_limit(func):
        '''decorate a function to limit call rate in a synchronous program.'''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            time.sleep(
                max(0, self._next_try_systime_ms - self._get_systime_ms()
                ) / 1000) 
            result = func(self, *args, **kwargs)
            self._next_try_systime_ms = self._get_systime_ms(
            ) + SEC_RATE_LIMIT_DELAY 
            return result
        return wrapper
        
    @_rate_limit
    def _get(self, *args, **kwargs):
        '''wrapped to comply with sec rate limit'''
        return self.session.get(*args, **kwargs)


    @_rate_limit
    def _post(self, *args, **kwargs):
        '''wrapped to comply with sec rate limit'''
        return self.session.post(*args, **kwargs)
        

    def _create_session(self, retry=10) -> requests.Session:
        r = Retry(
            total=retry,
            read=retry,
            connect=retry,
            backoff_factor= float(0.7),
            status_forcelist=(500, 502, 503, 504, 403))
        '''create a session used by the Downloader'''
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=r) 
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    



