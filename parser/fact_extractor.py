


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
import re

def get_fact_data(companyfacts, name, taxonomy, unit="USD"):
    facts = {}
    data_points = companyfacts["facts"][taxonomy]
    if isinstance(name, re.Pattern):
        for d in data_points:
            fname = re.search(name, d)
            if fname:
                fstring = fname.string
                for unit in companyfacts["facts"][taxonomy][fstring]["units"]:
                    for single_fact in companyfacts["facts"][taxonomy][fstring]["units"][unit]:
                        single_fact["taxonomy"] = taxonomy
                        single_fact["unit"] = unit
                        single_fact["name"] = fstring
                        if fstring in facts.keys():
                            facts[fstring].append(single_fact)
                        else:
                            facts[fstring] = [single_fact]
    else:
        for d in data_points:
            fname = re.search(re.compile("(.*)("+name+")(.*)", re.I), d)
            if fname:
                fstring = fname.string
                for unit in companyfacts["facts"][taxonomy][fstring]["units"]:
                    for single_fact in companyfacts["facts"][taxonomy][fstring]["units"][unit]:
                        single_fact["taxonomy"] = taxonomy
                        single_fact["unit"] = unit
                        single_fact["name"] = fstring
                        if fstring in facts.keys():
                            facts[fstring].append(single_fact)
                        else:
                            facts[fstring] = [single_fact]
    return facts


if __name__ == "__main__":
        
    import json
    import re
    from pathlib import Path

    # dl = Downloader(r"C:\Users\Olivi\Testing\sec_scraping_testing\pysec_downloader\companyfacts", user_agent="john smith js@test.com")
    # print(len(dl._lookuptable_ticker_cik.keys()))
    # symb = ["PHUN", "GNUS", "IMPP"]
    # for s in symb:
    #     j = dl.get_xbrl_companyfacts(s)
    #     with open((dl.root_path / (s +".json")), "w") as f:
    #         json.dump(j, f)

    with open(Path(r"C:\Users\Olivi\Testing\sec_scraping\pysec_downloader\companyfacts") / ("PHUN" + ".json"), "r") as f:
        j = json.load(f)
        f = get_fact_data(j, "sharesIssued", "us-gaap")
        print(f)

    # for s in symb:
    #         # j = dl.get_xbrl_companyfacts(s)
    #         # with open((dl.root_path / (s +".json")), "w") as f:
    #         #     json.dump(j, f)
    #         with open(Path(r"C:\Users\Olivi\Testing\sec_scraping_testing\pysec_downloader\companyfacts") / (s + ".json"), "r") as f:
    #             j = json.load(f)
    #             matches = []
    #             for each in j["facts"].keys():
    #                 for possible in j["facts"][each]:
                        
    #                     if re.search(re.compile("ProceedsFromIssuance(.*)", re.I), possible):
    #                         matches.append(possible)
    #             print([j["facts"]["us-gaap"][p] for p in matches])