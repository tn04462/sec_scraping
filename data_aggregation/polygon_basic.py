from requests.exceptions import HTTPError
from polygon import RESTClient
from configparser import ConfigParser
from os import path
from pathlib import Path
from time import sleep, time
import json
import logging

logger = logging.getLogger(__package__)

config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "config.cfg"))
config = ConfigParser()
config.read(config_path)

if config.getboolean("environment", "production") is False:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


key = config["polygon"]["api_key"]
save_folder = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "resources/company_overview"))
rate_limit = 12.5

class PolygonClient:
    def __init__(self, api_key):
        self._sleep_time = None
        self._end_sleep_time = time()
        self._min_sleep = 12500
        self.client = RESTClient(api_key)

    def _get_time_ms(self):
        return time() * 1000
    
    def get_overview_single_ticker(self, ticker):
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
    
    # def get_overview_for_tracked_tickers(self):
    #     tickers = [t.strip() for t in config["general"]["tracked_tickers"].strip("[]").split(",")]
    #     if not Path(save_folder).exists():
    #         Path(save_folder).mkdir(parents=True)
    #     for ticker in tickers:
    #         with RESTClient(key) as client:
    #             try:
    #                 self._get_overview(client, ticker)
    #             except HTTPError as e:
    #                 raise e
            

    # def _get_overview(self, client, ticker):
    #     start = time()
    #     try:
    #         res = client.reference_ticker_details_vx(ticker)
    #     except HTTPError as e:
    #         end = time()
    #         duration = end-start
    #         sleep_time = rate_limit - duration
    #         sleep(sleep_time)
    #         return
    #     result = dict(res.results.items())
    #     file_path = path.join(save_folder, f"{ticker}.json")
    #     with open(file_path, "w+") as f:
    #         json.dump(result, f)
    #     end = time()
    #     duration = end-start
    #     sleep_time = rate_limit - duration

    
# if __name__ == "__main__":
#     test_tickers = ["HYMC", "AAPL"]
#     poly = PolygonClient(key)
#     for t in test_tickers:
#         res = poly.get_overview_single_ticker(t)
#         print(res)
    
    # get_overview_for_tracked_tickers()