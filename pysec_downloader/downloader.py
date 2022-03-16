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
    2) create the urls to the wanted filings by making post request to search-API
    3)
   

'''
import requests
from urllib3.util import Retry
from pathlib import Path
import time
from functools import wraps

SEC_RATE_LIMIT_DELAY = 1000 #ms
EDGAR_SEARCH_API = "https://efts.sec.gov/LATEST/search-index"

class Downloader:
    def __init__(self, root_path: str, retries: int = 10, user_agent: dict = None, logs=True):
        self.root_path = Path(root_path)
        self.session = self._create_session(retry=retries)
        self.user_agent = user_agent if user_agent else "max musterman max@muster.com"

        self._next_try_systime_ms = self._get_systime_ms()
    
    def _get_systime_ms(self):
        return int(time.time() * SEC_RATE_LIMIT_DELAY)
    
    def _json_from_search_api(
            self,
            ticker_or_cik: str,
            filing_types: str,
            number_of_filings: int = 1,
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
                "forms": [filing_types],
                "from": start_index,
                "q": query}
            resp = self._post(EDGAR_SEARCH_API, json=post_body, headers=headers)
            resp.raise_for_status()
            result = resp.json()
            #check here for errors befoer adding
            gathered_responses.append(result)    
        return result
    

    def rate_limit(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._next_try_systime_ms = self._get_systime_ms() + SEC_RATE_LIMIT_DELAY 
            result = func(self, *args, **kwargs)
            self._next_try_systime_ms = self._get_systime_ms() + SEC_RATE_LIMIT_DELAY 
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
    



