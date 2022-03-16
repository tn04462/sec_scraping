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
   

'''
from asyncio import gather
import requests
from urllib3.util import Retry
from pathlib import Path
import time
from functools import wraps

SEC_RATE_LIMIT_DELAY = 1000 #ms
EDGAR_SEARCH_API_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_ARCHIVES_BASE_PATH = Path("https://www.sec.gov/Archives/edgar/data")


class Downloader:
    def __init__(self, root_path: str, retries: int = 10, user_agent: dict = None, logs=True):
        self.root_path = Path(root_path)
        self.session = self._create_session(retry=retries)
        self.user_agent = user_agent if user_agent else "max musterman max@muster.com"
        self._next_try_systime_ms = self._get_systime_ms()
    
    def _get_systime_ms(self):
        return int(time.time() * SEC_RATE_LIMIT_DELAY)
    
    def _get_base_metadata_from_hit(self, hit: dict):
        accession_number, filing_details_filename = hit["_id"].split(":", 1)
        accession_number_no_dash = accession_number.replace("-", "", 2)
        cik = hit["_source"]["ciks"][-1]
        submission_base_url = EDGAR_ARCHIVES_BASE_PATH / cik / accession_number_no_dash
        xsl = hit["_source"]["xsl"] if hit["_source"]["xsl"] else None
        return {
            "accession_number": accession_number,
            "cik": cik,
            "base_url": submission_base_url,
            "main_file_name": filing_details_filename,
            "xsl": xsl}

    def _guess_full_url(self, base_meta, form_type, wanted_file_type):
        base_url = base_meta["base_url"]
        accession_number = base_meta["accession_number"]
        if (form_type == ("10-Q" or "10-K")) and (wanted_file_type == "xbrl.zip"):
            base_meta["file_url"] = base_url / accession_number + "-xbrl.zip"
            



    
    def _json_from_search_api(
            self,
            ticker_or_cik: str,
            filing_type: str,
            number_of_filings: int = 1,
            want_amendments = False,
            start_date: str = "",
            end_date: str = "",
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
                "startdt": start_date,
                "enddt": end_date,
                "entityName": ticker_or_cik,
                "forms": [filing_type],
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
                res_filing_type = res["_source"]["file_type"]
                is_amendment = res_filing_type[-2:] == "/A"
                if not want_amendments and is_amendment:
                    continue
                # make sure that no wrong filing type is added
                if (not is_amendment) and (res_filing_type != filing_type):
                    continue
                gathered_responses.append(res)

            query_size = result["query"]["size"]
            start_index += query_size

        return gathered_responses[:number_of_filings]
    
    def rate_limit(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._next_try_systime_ms = self._get_systime_ms(
            ) + SEC_RATE_LIMIT_DELAY 
            result = func(self, *args, **kwargs)
            self._next_try_systime_ms = self._get_systime_ms(
            ) + SEC_RATE_LIMIT_DELAY 
            return result
        return wrapper
        
    @rate_limit
    def _get(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)
    
    @rate_limit
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
    



