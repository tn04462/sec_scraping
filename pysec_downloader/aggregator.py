from downloader import Downloader #added to extra_path with vscode



'''aggregate following data:

resources: 
https://xbrl.us/data-rule/guid-cashflowspr/#5
https://asc.fasb.org/viewpage

- Outstanding shares [value, instant] us-gaap:CommonStockSharesOutstanding, EntityCommonStockSharesOutstanding ?

- cash and equiv. NET at end of period [value, instant] us-gaap:[
    CashAndCashEquivalentsPeriodIncreaseDecrease,
    CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect,
    CashAndCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect,
    CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect,
    CashPeriodIncreaseDecrease,
    CashPeriodIncreaseDecreaseExcludingExchangeRateEffect
]
capital rais in a period seen on sheet as proceeds from issuance of...
look for us-gaap elements that represent atms, warrants, notes ect.
- s-1 shelves
- s-3 shelves
- warrants - keys: ProceedsFromIssuanceOfWarrants
- notes
- ATM's
- what is considered to be a private placement - keys us-gaap: ProceedsFromIssuanceOfPrivatePlacement
- issuance of common stock [value, from, to] us-gaap:ProceedsFromIssuanceOfCommonStock
 CommonStockSharesIssued
- 

Unit key I want is USD so a fact i want is accessed by using json["facts"][taxonomy][fact_name][unit]
for issuance of inital public offering take the filing date as the instant of the value
for issuance of 
'''
from parser.xbrl_structure import Instant, Period
class Fact:
    def __init__(self):
        self.taxonomy = None
        self.name = None
        self.value = None
        self.unit = None
        self.period = None
        self.filing_date = None

def get_fact_data(self, companyfacts, name, taxonomy, unit="USD"):
    facts = []
    data_points = companyfacts["facts"][taxonomy][name][unit]
    for d in data_points:
        f = Fact()
        if ("start" and "end") in d.keys():
            f.period = Period(start=d["start"], end=d["end"])

'''what: a fact that contains taxonomy, name, value, period, filing_date
--> how will i use it?
    --> pass it to db to use in calculations
    
    --> what do i need to write it to db?
        the facts attributes and that is it: construct a
        function that inserts into the right tables based
        on fact name!
        --> what to consider when inserting?
        what time interests me? start, end or the filing_date (unless it is an instance where i only have to decide between filing_date and instance time)
    does it make sense to use a Fact class or am i better
    served with a dictionary or do i need to save space and
    use list of lists ?
    perform validation of period or instance where?
    

    ---> dictionary will suffice
    

'''



    return 


dl = Downloader(r"C:\Users\Olivi\Testing\sec_scraping_testing\pysec_downloader\companyfacts", user_agent="john smith js@test.com")

symb = ["PHUN", "GNUS", "IMPP"]


import json
import re
from pathlib import Path
for s in symb:
        # j = dl.get_xbrl_companyfacts(s)
        # with open((dl.root_path / (s +".json")), "w") as f:
        #     json.dump(j, f)
        with open(Path(r"C:\Users\Olivi\Testing\sec_scraping_testing\pysec_downloader\companyfacts") / (s + ".json"), "r") as f:
            j = json.load(f)
            matches = []
            for each in j["facts"].keys():
                for possible in j["facts"][each]:
                    
                    if re.search(re.compile("ProceedsFromIssuance(.*)", re.I), possible):
                        matches.append(possible)
            print([j["facts"]["us-gaap"][p] for p in matches])