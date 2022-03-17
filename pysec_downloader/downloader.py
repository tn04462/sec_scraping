'''
Aim: Be able to download any SEC file type in every(as long as available
 on website) file format for every filer identified either by
 CIK or ticker symbol. While respecting the sec guidelines:
  https://www.sec.gov/privacy.htm#security
  
  the most important are:
    - respect rate limit
    - have user_agent header
    - stress sec systems as little as possible

Sec information:
    https://www.sec.gov/os/accessing-edgar-data
    https://www.sec.gov/os/webmaster-faq#developers

Flow of Program:
    * Downloader creates session
    * 
    1) call is made to get_filings("aapl", 10-Q, from_date=2020-01-01, max_amount=10)
    2) get the base-url to the wanted filings by making post request to search-API
    3) get metadata from results 
    4) try to get the prefered_file_extension by building the url with consideration of form type
    5) downloaded each file and save or yield it
    
Things to add:
    * splitting a full text submission and writting individual files 

Things to fix:
    * "html" as prefered file type doesnt match .htm files same for "htm" and .html
    * 
        

Other Notes:
        create an index file that makes lookup by case number faster

        bulk data instead of pulling every 10-Q/10-K and parsing the xbrl
        compare in case of PHUN for shares outstanding to see if relevant
        facts are omitted by not linking them to us-gaap or dei

        still need to pull individual S-1, S-3, 424B's ect
        and parse those to get information on dilutive data
        like shelves, notes, offerings ect!
        need to parse those in html...
        
        see below for relevance of filing and specificatiosn:
        https://www.sec.gov/dera/data/dera_edgarfilingcounts
        https://www.sec.gov/edgar/filer-information/current-edgar-filer-manual

   

'''
from tempfile import TemporaryFile
import requests
import json
from urllib3.util import Retry
import time
from functools import wraps
import re
import logging
from posixpath import join as urljoin
from pathlib import Path
from urllib.parse import urlparse
import zipfile

from _constants import *

debug = True
if debug is True:
    logger = logging.getLogger("downloader")
    logger.setLevel(logging.DEBUG)

r'''download interface for various SEC files.


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
    
    # when using as generator make sure the save argument is False
    for filing in dl.get_filings("AAPL", "8-K", number_of_filings=50, save=False):
        do something with each individual filing...
        

    file = dl.get_xbrl_companyconcept("AAPL", "us-gaap", "AccountsPayableCurrent") 

    other_file = dl.get_file_company_tickers()
    '''


class Downloader:
    '''suit to download various files from the sec
    
    enables easier access to download files from the sec. tries to follow the
    SEC guidelines concerning automated access (AFAIK, if I missed something
    let me know: camelket.develop@gmail.com)

    Attributes:
        root_path: where to save the downloaded files unless the method has
                   an argument to specify an alternative
        user_agent: str of 'name surname email' to comply with sec guidelines
    Args:
        retries: how many retries per request are allowed
    '''
    def __init__(self, root_path: str, retries: int = 10, user_agent: str = None):
        self.root_path = Path(root_path)
        self.user_agent = user_agent if user_agent else "max musterman max@muster.com"
        self._is_ratelimiting = True
        self._session = self._create_session(retry=retries)
        self._next_try_systime_ms = self._get_systime_ms()
        self._lookuptable_ticker_cik = self._load_or_update_lookuptable_ticker_cik()
        self._sec_files_headers = self._construct_sec_files_headers()
        self._sec_xbrl_api_headers = self._construct_sec_xbrl_api_headers()


    def get_filings(
        self,
        ticker_or_cik: str,
        form_type: str,
        after_date: str = "",
        before_date: str = "",
        query: str = "",
        prefered_file_type: str = "",
        number_of_filings: int = 100,
        want_amendments: bool = True,
        skip_not_prefered: bool = False,
        save: bool = True):
        '''download filings. if param:save is False turns into
        a generator yielding downloaded filing. 
        
        Args:
            ticker_or_cik: either a ticker symbol "AAPL" or a 10digit cik
            form_type: what form you want. valid forms are found in SUPPORTED_FILINGS
            after_date: date from which to consider filings
            before_date: date before which to consider filings
            query: query according to https://www.sec.gov/edgar/search/efts-faq.html.
            prefered_file_type: what filetype to prefer when looking for filings, see PREFERED_FILE_TYPES for handled extensions
            number_of_filings: how many filings to download.
            want_amendements: if we want to include amendment files or not
            skip_not_prefered: either download or exclude if prefered_file_type
                               fails to match/download
            save: toggles saving or yielding of files downloaded.

        '''
        if prefered_file_type == (None or ""):
            prefered_file_type = (PREFERED_FILE_TYPE_MAP[form_type] 
                                 if PREFERED_FILE_TYPE_MAP[form_type]
                                 else "html")

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
            file = self._download_filing(m)
            if save is True:
                if file:
                    self._save_filing(ticker_or_cik, m, file)
                    continue
                else:
                    logging.debug("didnt save filing despite wanting to. response from request: {}", resp)
                    break
            else:
                yield file
        return
    

    def get_xbrl_companyconcept(self, ticker_or_cik: str, taxonomy: str, tag: str):
        '''
        Args:
            ticker_or_cik: ticker like "AAPL" or cik like "1852973" or "0001852973"
            taxonomy: a taxonomy like "us-gaap" 
            tag: a concept tag like "AccountsPayableCurrent"
        Returns:
            python representation of the json file with contents described
            by the SEC as: "all the XBRL disclosures from a single company
            (CIK) and concept (a taxonomy and tag) [...] ,with a separate 
            array of facts for each units on measure that the company has
            chosen to disclose" 
            - https://www.sec.gov/edgar/sec-api-documentation
        '''
        cik10 = self._convert_to_cik10(ticker_or_cik)
        filename = tag + ".json"
        urlcik = "CIK"+cik10
        url = SEC_API_XBRL_COMPANYCONCEPT_URL
        for x in [urlcik, taxonomy, filename]:
            url = urljoin(url, x)
        resp = self._get(url=url, headers=self._sec_xbrl_api_headers)
        content = resp.json()
        return content
    
    def get_xbrl_companyfacts(self, ticker_or_cik: str) -> dict:
        '''download a companyfacts file.
        
        Args:
            ticker_or_cik: ticker like "AAPL" or cik like "1852973" or "0001852973"
        
        Returns:
            python representation of the json file with contents described
            by the SEC as: "all the company concepts data for a company"
            - https://www.sec.gov/edgar/sec-api-documentation
        '''     
        cik10 = self._convert_to_cik10(ticker_or_cik)
        # build URL
        filename = "CIK" + cik10 + ".json"
        url = urljoin(SEC_API_XBRL_COMPANYFACTS_URL, filename)
        # make call
        resp = self._get(url=url, headers=self._sec_xbrl_api_headers)
        content = resp.json()
        return content



    def get_file_company_tickers(self) -> dict:
        '''download the cik, tickers file from the sec.
        
        The file structure: {index: {"cik_str": CIK, "ticker": ticker}}
        size: ~1MB
        '''
        resp = self._get(url=SEC_FILES_COMPANY_TICKERS, headers=self._sec_files_headers)
        content = resp.json()
        if "error" in content:
            logging.ERROR("Couldnt fetch company_tickers.json file. got: {}", content)
        return content


    def get_file_company_tickers_exchange(self) -> dict:
        '''download the cik, ticker, exchange file from the sec
        
        The file structure: {"fields": [fields], "data": [[entry], [entry],...]}
        fields are: "cik", "name", "ticker", "exchange"
        size: ~600KB
        '''
        headers = { 
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"}
        resp = self._get(url=SEC_FILES_COMPANY_TICKERS_EXCHANGES, headers=headers)
        content = resp.json()
        if "error" in content:
            logging.ERROR("Couldnt fetch company_ticker_exchange.json file. got: {}", content)
        return content

      
    def lookup_cik(self, ticker: str) -> str:
        '''look up the corresponding CIK for ticker and return it or an exception.

            Args:
                ticker: a symbol/ticker like: "AAPL"
            Raises:
                KeyError: ticker not present in lookuptable
        '''
        ticker = ticker.upper()
        cik = None
        try:
            cik = self._lookuptable_ticker_cik[ticker]
            return cik
        except KeyError as e:
            logging.ERROR(f"{ticker} caused KeyError when looking up the CIK.")
            return e
        except Exception as e:
            logging.ERROR(f"unhandled exception in lookup_cik: {e}")
            return e

    
    def set_session(self, session: requests.Session, sec_rate_limiting: bool = True):
        '''use a custom session object.

         Args:
            session: your instantiated session object
            sec_rate_limiting: toggle internal sec rate limiting,
                               can result in being locked out.
                               Not advised to set False.   
        '''
        try:
            self._set_ratelimiting(sec_rate_limiting)
            if self._session:
                self._session.close()
            self._session = session
        except Exception as e:
            logging.ERROR((
                f"Couldnt set new session, encountered {e}"
                f"Creating new default session"))
            self._create_session()
        return
    
    def _construct_sec_xbrl_api_headers(self):
        parsed = urlparse(SEC_API_XBRL_BASE)
        host = parsed.netloc
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": host}
    
    def _construct_sec_files_headers(self):
        parsed = urlparse(SEC_FILES_COMPANY_TICKERS)
        host = parsed.netloc
        print(host)
        return {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": host}
    
    def _convert_to_cik10(self, ticker_or_cik: str):
        '''try to get the 10 digit cik from a ticker or a cik
        Args:
            ticker_or_cik: ticker like "AAPL" or cik like "1852973" or "0001852973"
        Returns:
            a 10 digit CIK as a string. ex: "0001841800"
        '''
        cik = None
        try:
            int(ticker_or_cik)
        except ValueError:
            #assume it is a ticker and not a cik
            cik = self.lookup_cik(ticker_or_cik)
        else:
            cik = ticker_or_cik
        if not isinstance(cik, str):
            cik = str(cik)
        cik10 = cik.zfill(10)
        return cik10

    def _set_ratelimiting(self, is_ratelimiting: bool):
        self._is_ratelimiting = is_ratelimiting
    
    def _load_or_update_lookuptable_ticker_cik(self) -> dict:
        '''load the tickers:cik lookup table and return it'''
        file = Path(TICKERS_CIK_FILE)
        if not file.exists():
            self._update_lookuptable_tickers_cik()
        with open(file, "r") as f:
            try:
                lookup_table = json.load(f)
                return lookup_table
            except IOError as e:        
                logging.ERROR("couldnt load lookup table:  {}", e)
        return None
 
    def _update_lookuptable_tickers_cik(self):
        '''update or create the ticker:cik file'''
        content = self.get_file_company_tickers()
        if content:
            try:
                transformed_content = {}
                for d in content.values():
                    transformed_content[d["ticker"]] = d["cik_str"]
                with open(Path(TICKERS_CIK_FILE), "w") as f:
                    f.write(json.dumps(transformed_content))
            except Exception as e:
                logging.ERROR((
                    f"couldnt update ticker_cik file."
                    f"unhandled exception: {e}"))
            # should add finally clause which restores file to inital state?
        else:
            raise ValueError("Didnt get content returned from get_file_company_tickers")
        return

    def _download_filing(self, base_meta):
        '''download a file and fallback on secondary url if 404. adds save_name to base_meta'''
        if base_meta["skip"]:
            logging.debug("skipping {}", base_meta)
            return
        headers = self._sec_files_headers
        try:
            resp = self._get(url=base_meta["file_url"], headers=headers)
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


    def _save_filing(self, ticker_or_cik, base_meta, file):
        '''save the filing and extract zips.'''
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
        base_meta["fallback_url"] = urljoin(base_url, base_meta["main_file_name"])
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
        return base_meta

    
    def _transform_from_full_text(self, full_text: str, form_type: str, file_extension: list):
        # quick to implement as most code is already in parser
        pass 
    
    def _get_systime_ms(self):
        return int(time.time() * SEC_RATE_LIMIT_DELAY)
    
    def _get_base_metadata_from_hit(self, hit: dict):
        '''getting the most relevant information out of a entry. returning a dict'''
        accession_number, filing_details_filename = hit["_id"].split(":", 1)
        accession_number_no_dash = accession_number.replace("-", "", 2)
        cik = hit["_source"]["ciks"][-1]
        submission_base_url = urljoin(urljoin(EDGAR_ARCHIVES_BASE_URL, cik),(accession_number_no_dash))
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
            number_of_filings: int = 20,
            want_amendments = False,
            after_date: str = "",
            before_date: str = "",
            query: str = ""
            ) -> dict:
        '''gets a list of filings submitted to the sec.'''
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
            resp = self._post(url=SEC_SEARCH_API_URL, json=post_body, headers=headers)
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
        '''decorate a function to limit call rate in a synchronous program.
        Can be toggled on/off by calling set_ratelimiting(bool)'''
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._is_ratelimiting is False:
                return func(self, *args, **kwargs)
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
        '''wrapped to comply with sec rate limit across calls'''
        return self._session.get(*args, **kwargs)


    @_rate_limit
    def _post(self, *args, **kwargs):
        '''wrapped to comply with sec rate limit across calls'''
        return self._session.post(*args, **kwargs)
        

    def _create_session(self, retry=10) -> requests.Session:
        '''create a session used by the Downloader with a retry
        strategy on all urls. retries on status:
            500, 502, 503, 504, 403 .'''
        r = Retry(
            total=retry,
            read=retry,
            connect=retry,
            backoff_factor = float(0.3),
            status_forcelist=(500, 502, 503, 504, 403))
        r.backoff_max = 10
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=r) 
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    



