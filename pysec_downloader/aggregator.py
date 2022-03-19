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
'''

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