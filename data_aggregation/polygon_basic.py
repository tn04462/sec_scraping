from requests.exceptions import HTTPError
from polygon import RESTClient
from configparser import ConfigParser
from os import path
from pathlib import Path
from time import sleep, time
import json
config_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "config.cfg"))
config = ConfigParser()
config.read(config_path)

tickers = [t.strip() for t in config["general"]["tracked_tickers"].strip("[]").split(",")]
key = config["polygon"]["api_key"]
save_folder = path.normpath(path.join(path.dirname(path.abspath(__file__)), '..', "resources/company_overview"))
rate_limit = 12.5

# def get_tracked_tickers():
#     if not Path(save_folder).exists():
#         Path(save_folder).mkdir(parents=True)
#     with RESTClient(key) as client:
#         for ticker in tickers:
#             get_overview(client, ticker)

def get_tracked_tickers():
    if not Path(save_folder).exists():
        Path(save_folder).mkdir(parents=True)
    for ticker in tickers:
        with RESTClient(key) as client:
            get_overview(client, ticker)

def get_overview(client, ticker):
    start = time()
    try:
        res = client.reference_ticker_details_vx(ticker)
    except HTTPError as e:
        print(type(e))
        print(ticker)
        print("Excepted ERROR ________________")
        end = time()
        duration = end-start
        sleep_time = rate_limit - duration
        sleep(sleep_time)
        return
    print(res)
    #  except rate limit exceeded
    result = dict(res.results.items())
    file_path = path.join(save_folder, f"{ticker}.json")
    with open(file_path, "w+") as f:
        json.dump(result, f)
    end = time()
    duration = end-start
    sleep_time = rate_limit - duration
    sleep(sleep_time)
    print(duration, sleep_time)
    # except key error -> no result
    # except IOError
    
if __name__ == "__main__":
    get_tracked_tickers()