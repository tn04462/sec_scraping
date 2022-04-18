# from cgitb import text
# from sec_edgar_downloader import Downloader
# from pathlib import Path
# import re
# from bs4 import BeautifulSoup
# import pandas as pd
# from datetime import datetime

# from xbrl_parser import *
# from xbrl_structure import *
# from filing_handler import *




# # dl = Downloader(Path(r"C:\Users\Olivi\Testing\sec_scraping_testing\filings"))
# # aapl_10ks = dl.get("10-Q", "PHUN", amount=10)

# r""" with open(r"C:\Users\Olivi\Testing\sec_scraping\filings\sec-edgar-filings\PHUN\424B3\0001213900-18-015809\full-submission.txt", "r") as f:
#     text = f.read()
#     metaparser = TextMetaParser()
#     metadata_doc = metaparser.process_document_metadata(text)
#     logging.debug(metadata_doc)
#     pass """

# # TEST FOR ParserXBRL
# # path = r"C:\Users\Olivi\Testing\sec_scraping\filings\sec-edgar-filings\PHUN\10-Q\0001213900-19-008896"
# paths = sorted(Path(r"C:\Users\Olivi\Testing\sec_scraping\filings\sec-edgar-filings\PHUN\10-Q").glob("*"))
# handler = FilingHandler()
# shares_outstanding = []
# for p in paths:
# # path = r"C:\Users\Olivi\Testing\sec_scraping_testing\filings\sec-edgar-filings\PHUN\10-Q\0001628280-21-023228" 
#     # fts = FullTextSubmission(p)
#     now = datetime.now()
#     p = p / "full-submission.txt"
#     with open(p, "r") as f:
#         full_text = f.read()
#         doc = handler.preprocess_documents(full_text)
#         file = handler.process_file(doc)
        
        
#         facts = file.search_fact("Commonstocksharesoutstanding", None, namespace="us-gaap")
#         for fact in facts:
#             d = fact.convert_to_dict()
#             if d not in shares_outstanding:
#                 shares_outstanding.append(d)
#         # print([facts[0] == facts[i] for i in range(len(facts))])
#         # if file:
#         #     matches = file.search_for_key(re.compile("sharesoutstanding", re.I))
#         #     for m in matches:
#         #         print(file.facts[m])
#         #         print([f.get_members() for f in file.facts[m]])
#         elapsed = datetime.now() - now
#         # print([f.convert_to_dict() for f in facts])
#         # print(f"time for processing: {elapsed}"
# logging.getLogger("matplotlib").setLevel(level=logging.ERROR)
# logging.getLogger("PIL").setLevel(level=logging.ERROR)

# df = pd.DataFrame(shares_outstanding)
# # df.drop("members", axis=1, inplace=True)
# # df.drop_duplicates(inplace=True)
# df["period"] = pd.to_datetime(df["period"])
# df["value"] = pd.to_numeric(df["value"])
# df.sort_values(by="period", inplace=True)

# print(df)



# # import matplotlib.pyplot as plt
# # df.plot(x="period",y="value", kind="bar")
# # plt.show(block=True)



# # TEST XBRLElement classes for equality
# # fact1 = Fact(
# #             Tag("us", "common"),
# #             Context(id="1", entity=Entity(identifier="1"), period=Instant("2020-09-03")),
# #             Value("29", unit=Unit("usd"))
# #             )

# # fact2 = Fact(
# #             Tag("us", "common"),
# #             Context(id="1", entity=Entity(identifier="1"), period=Instant("2020-09-03")),
# #             Value("29", unit=Unit("usd"))
# #             )
# # print(fact1 == fact2, fact1 is fact2)


# # TEST FOR ParserS1
# # S1_path = r"C:\Users\Olivi\Testing\sec_scraping_testing\filings\sec-edgar-filings\PHUN\S-1\0001213900-16-014630\filing-details.html"
# # with open(S1_path, "rb") as f:
# #     text = f.read()
# #     parser = ParserS1()
# #     parser.make_soup(text)
# #     parser.get_unparsed_tables()
# #     registration_fee_table = parser.get_calculation_of_registration_fee_table()
# #     print(registration_fee_table[0])
# #     df = pd.DataFrame(columns=registration_fee_table[0], data=registration_fee_table[1:])
# #     print(df)

# # TEST FOR Parser424B5
# # with open(r"C:\Users\Olivi\Testing\sec_scraping\filings\sec-edgar-filings\PHUN\424B5\0001628280-20-012767\filing-details.html", "rb") as f:
# #     text = f.read()
# #     parser = Parser424B5()
# #     parser.make_soup(text)
# #     # print(parser.get_offering_table())
# #     print(parser.get_dilution_table())
# #         # print(parser.get_tables())



# import pandas

# sic2 =  pandas.read_csv(r"C:\Users\Olivi\Desktop\sic-codes4.csv")
# sic1 =  pandas.read_csv(r"C:\Users\Olivi\Desktop\sic-codes2.csv")
# sic0 =  pandas.read_csv(r"C:\Users\Olivi\Desktop\sic-codes1.csv")
# industry_groups = pandas.read_csv(r"C:\Users\Olivi\Desktop\industry-groups.csv")


# print(sic0.columns, sic1.columns, sic2.columns)

# sic3 = sic2.merge(sic1, on=["Major Group", "Division"])

# sic3 = sic3.merge(sic0, on="Division")
# sic3 = sic3.merge(industry_groups, on=["Major Group", "Division", "Industry Group"], suffixes=["sic3", "ig"])
# print(sic3.head())

# # print(sic4.head())
# sic3.drop("Division", axis=1, inplace=True)
# sic5 = sic3.rename({"Description_y": "Sector", "Descriptionsic3": "Division", "Description_x": "Industry"}, axis=1)
# sic6 = sic5[["SIC", "Industry", "Sector", "Division"]]
# sic6.set_index("SIC", inplace=True)
# print(sic6.head())
# sic6.to_csv(r"C:\Users\Olivi\Desktop\sics.csv")

# import pysec_downloader.downloader

# print(pysec_downloader)

# dl = pysec_downloader.downloader.Downloader(r"C:\Users\Olivi\Downloads")
# dl._json_from_search_api("PHUN", "S-3")

from re import search
import time
from contextlib import ContextDecorator
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Optional

class TimerError(Exception):
    """A custom exception used to report errors in use of Timer class"""

@dataclass
class Timer(ContextDecorator):
    """Time your code using a class, context manager, or decorator"""

    timers: ClassVar[Dict[str, float]] = {}
    name: Optional[str] = None
    text: str = "Elapsed time: {:0.4f} seconds"
    logger: Optional[Callable[[str], None]] = print
    _start_time: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialization: add timer to dict of timers"""
        if self.name:
            self.timers.setdefault(self.name, 0)

    def start(self) -> None:
        """Start a new timer"""
        if self._start_time is not None:
            raise TimerError(f"Timer is running. Use .stop() to stop it")

        self._start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop the timer, and report the elapsed time"""
        if self._start_time is None:
            raise TimerError(f"Timer is not running. Use .start() to start it")

        # Calculate elapsed time
        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None

        # Report elapsed time
        if self.logger:
            self.logger(self.text.format(elapsed_time))
        if self.name:
            self.timers[self.name] += elapsed_time

        return elapsed_time

    def __enter__(self) -> "Timer":
        """Start a new timer as a context manager"""
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Stop the context manager timer"""
        self.stop()


if __name__ == "__main__":
    from pathlib import Path
    import json
    import re
    

    @Timer()
    def open_and_close_all(paths):
        for p in paths:
            with open(p, "r") as f:
                j = json.load(f)
            del j

    @Timer()
    def search_new_filings(paths, after):
        '''
        get new filings after certain date from a submission file
        Args:
            paths:  path to the submission file of the company
            after: after what date to consider a filing a new filing'''
        new_filings = {}
        for p in paths:
            with open(p, "r") as f:
                j = json.load(f)
                print(j)
                stop_idx = None
                try:
                    filing_dates = j["filings"]["recent"]["filingDate"]
                    len_f_dates = len(filing_dates)

                    for r in range(0, len_f_dates, 1):
                        if filing_dates[r] <= after:
                            if r == len_f_dates:
                                break
                            stop_idx = r
                            print(stop_idx, len(filing_dates), filing_dates[stop_idx])
                            break
                    if stop_idx is not None:
                        new_filings[j["cik"]] = [[j["filings"]["recent"]["accessionNumber"][idx], j["filings"]["recent"]["filingDate"][idx]
                        ] for idx in range(0, stop_idx, 1)]
                except KeyError as e:
                    pass #second filing not handled yet
                finally:
                    del j
        return new_filings

    # open_and_close_all(paths)
    # search_new_filings(paths, "1998-03-02")

    #_______


