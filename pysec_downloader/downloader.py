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

debug = True
if debug is True:
    logger = logging.getLogger("downloader")
    logger.setLevel(logging.DEBUG)



class Downloader:
    def __init__(self, root_path: str, retries: int = 10, user_agent: dict = None, save=True,save_function=None):
        self.root_path = Path(root_path)
        self.session = self._create_session(retry=retries)
        self.user_agent = user_agent if user_agent else "max musterman max@muster.com"
        self._next_try_systime_ms = self._get_systime_ms()
        self.save_function = save_function
        self.save = save
  
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
                    if self.save_function:
                        self.save_function(ticker_or_cik, base_meta, file)
                    self._save_file(ticker_or_cik, m, file)
                else:
                    if self.save is True:
                        logging.debug("didnt save filing despite wanting to. response from request: {}", resp)
                        break
        return
    

    def _download_file(self, base_meta):
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
            if resp.status == 404:
                resp = self._get(url=base_meta["fallback_url"], headers=headers)
                base_meta["save_name"] = Path(base_meta["fallback_url"]).name
        else:
            base_meta["save_name"] = Path(base_meta["file_url"]).name
        filing = resp.content if resp.content else None
        return filing


    def _save_file(self, ticker_or_cik, base_meta, file):
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

    # save by cik would be most consistent but allow
    # for switching to ticker_or_cik term.
    # allow for user created save function,
    # which gets ticker_or_cik, file and base_meta passed
    # could be used for parsing before saving or
    # save in another file structure 



    def _guess_full_url(self, base_meta, prefered_file_type, skip_not_prefered):
        skip = False
        base_url = base_meta["base_url"]
        accession_number = base_meta["accession_number"]
        if prefered_file_type == "xbrl":
            # only ever download the zip file for xbrl to reduce amount of requests
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
        return self.session.get(*args, **kwargs)


    @_rate_limit
    def _post(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)
        

    def _create_session(self, retry=10) -> requests.Session:
        r = Retry(
            total=retry,
            read=retry,
            connect=retry,
            backoff_factor= float(0.7),
            status_forcelist=(500, 502, 503, 504, 403))
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=r) 
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    



