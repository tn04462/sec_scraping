from requests.exceptions import HTTPError
from polygon import RESTClient
from ..configs import cnf
from os import path
from time import sleep, time
import logging


logger = logging.getLogger(__package__)
if cnf.ENV_STATE == "dev":
    logger.setLevel(logging.DEBUG)


class PolygonClient:
    '''wrapper for features of the polygon api I use.'''
    def __init__(self, api_key):
        self._sleep_time = None
        self._end_sleep_time = time()
        self._min_sleep = 12500
        self.client = RESTClient(api_key)

    def _get_time_ms(self):
        return time() * 1000
    
    def get_overview_single_ticker(self, ticker):
        '''get the company overview'''
        now = self._get_time_ms()
        if self._end_sleep_time > now:
            sleep((self._end_sleep_time-now)/1000)
        self._end_sleep_time = self._get_time_ms() + self._min_sleep
        
        with self.client as c:
            try:
                res = c.reference_ticker_details_vx(ticker)
            except HTTPError as e:
                logger.debug("unhandled HTTPError in get_overview_single_ticker")
                raise e
            return dict(res.results.items())
    
    
# if __name__ == "__main__":
    # key = cnf.POLYGON_API_KEY
    # save_folder = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "resources/company_overview"))
    # rate_limit = 12.5
#     test_tickers = ["HYMC", "AAPL"]
#     poly = PolygonClient(key)
#     for t in test_tickers:
#         res = poly.get_overview_single_ticker(t)
#         print(res)
    
    # get_overview_for_tracked_tickers()