from sec_edgar_downloader import Downloader
from pathlib import Path


START_DATE = "2020-01-01"


dl = Downloader(Path(r"C:\Users\Olivi\Testing\sec_scraping_testing\filings"))
aapl_10ks = dl.get("10-K", "PHUN", amount=1)
