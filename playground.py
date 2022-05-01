
from inspect import Attribute
from turtle import update
from bs4 import BeautifulSoup
from urllib3 import connection_from_url
# from dilution_db import DilutionDB
# from main.data_aggregation.polygon_basic import PolygonClient
# from main.configs import cnf

# from main.data_aggregation.bulk_files import update_bulk_files


from main.parser.text_parser import HtmlFilingParser, Parser8K
from pathlib import Path
parser = Parser8K()

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.errors import ProgrammingError, UniqueViolation, ForeignKeyViolation
from psycopg_pool import ConnectionPool

import pandas as pd
import logging
logging.basicConfig(level=logging.INFO)



class GenericDB:
    def __init__(self, connectionString):
        self.connectionString = connectionString
        self.pool = ConnectionPool(
            self.connectionString, kwargs={"row_factory": dict_row}
        )
        self.conn = self.pool.connection
    
    def execute_sql(self, path):
        with self.conn() as c:
            with open(path, "r") as sql:
                res = c.execute(sql.read())
                try:
                    for row in res:
                        print(row)
                except ProgrammingError:
                    pass
    
    def read(self, query, values):
        with self.conn() as c:
            res = c.execute(query, values)
            rows = [row for row in res]
            return rows

class FilingDB(GenericDB):
    def __init__(self, *args):
        super().__init__(*args)
        self.parser8k = Parser8K()
        self.items8k = [
            'item101',
            'item102',
            'item103',
            'item104',
            'item201',
            'item202',
            'item203',
            'item204',
            'item205',
            'item206',
            'item301',
            'item302',
            'item303',
            'item401',
            'item402',
            'item501',
            'item502',
            'item503',
            'item504',
            'item505',
            'item506',
            'item507',
            'item508',
            'item601',
            'item602',
            'item603',
            'item604',
            'item605',
            'item701',
            'item801',
            'item901']
    
    def normalize_8kitem(self, item: str):
        '''normalize and extract the first 7 chars to assign to one specific item'''
        return item.lower().replace(" ", "").replace(".", "").replace("\xa0", " ").replace("\n", "")[:7]
    
    def get_items_count_summary(self):
        entries = self.read("SELECT f.item_id as item_id, f.file_date, i.item_name as item_name FROM form8k as f JOIN items8k as i ON i.id = f.item_id", [])
        summary = {}
        for e in entries:
            if e["item_name"] not in summary.keys():
                summary[e["item_name"]] = 0
            else:
                summary[e["item_name"]] += 1

        return summary
    
    def init_8k_items(self):
        with self.conn() as connection:
            for i in self.items8k:
                connection.execute("INSERT INTO items8k(item_name) VALUES(%s)",[i])
    
    
    def add_8k_content(self, cik, file_date, item, content):
        normalized_item = self.normalize_8kitem(item)
        if normalized_item not in self.items8k:
            logging.info(f"skipping 8-k section, because couldnt find a valid item in it, item found: {item}. cik:{cik}; file_date:{file_date}; content:{content}")
            return
        with self.conn() as connection:
            # print(item)
            connection.execute("INSERT INTO form8k(cik, file_date, item_id, content) VALUES(%(cik)s, %(file_date)s, (SELECT id from items8k WHERE item_name = %(item)s), %(content)s) ON CONFLICT ON CONSTRAINT unique_entry DO NOTHING",
            {"cik": cik,
            "file_date": file_date,
            "item": normalized_item,
            "content": content})
    
    def parse_and_add_all_8k_content(self, paths):
        for p in tqdm(paths, mininterval=1):
            split_8k = self.parser8k.split_into_items(p, get_cik=True)
            if split_8k is None:
                print(f"failed to split into items or get date: {p}")
                continue
            cik = split_8k["cik"]
            file_date = split_8k["file_date"]
            for entries in split_8k["items"]:
                for item, content in entries.items():
                    self.add_8k_content(
                        cik,
                        file_date,
                        item,
                        content)


def get_all_8k(root_path):
        '''get all .htm files in the 8-k subdirectories. entry point is the root path of /filings'''
        paths_folder = [r.glob("8-K") for r in (Path(root_path)).glob("*")]
        paths_folder = [[f for f in r] for r in paths_folder]
        # print(paths_folder)
        paths_files = [[f.rglob("*.htm") for f in r] for r in paths_folder]
        paths = []
        for l in paths_files:
            # print(l)
            for each in l:
                # print(each)
                for r in each:
                    # print(r)
                    paths.append(r)
        return paths

def flatten(lol):
    '''flatten a list of lists (lol).'''
    if len(lol) == 0:
        return lol
    if isinstance(lol[0], list):
        return flatten(lol[0]) + flatten(lol[1:])
    return lol[:1] + flatten(lol[1:])

def get_all_filings_path(root_path: Path, form_type: str):
    '''get all files in the "form_type" subdirectories. entry point is the root path of /filings'''
    paths_folder = [r.glob(form_type) for r in (Path(root_path)).glob("*")]
    form_folders = flatten([[f for f in r] for r in paths_folder])
    file_folders = flatten([list(r.glob("*")) for r in form_folders])
    paths = flatten([list(r.glob("*")) for r in file_folders])
    return paths




if __name__ == "__main__":
    

    from main.configs import cnf
    from db_updater import get_filing_set
    from pysec_downloader.downloader import Downloader
    from tqdm import tqdm
    from dilution_db import DilutionDB
    import json
    import csv
    from main.parser.text_parser import Parser8K
    import spacy
    import datetime
    from spacy import displacy
    # nlp = spacy.load("en_core_web_sm")

    # db = DilutionDB(cnf.DILUTION_DB_CONNECTION_STRING)
    # dl = Downloader(cnf.DOWNLOADER_ROOT_PATH, retries=100, user_agent=cnf.SEC_USER_AGENT)
    # import logging
    # logging.basicConfig(level=logging.INFO)
    # dlog = logging.getLogger("urllib3.connectionpool")
    # dlog.setLevel(logging.CRITICAL)
    # with open("./resources/company_tickers.json", "r") as f:
    #     tickers = list(json.load(f).keys())
    #     for ticker in tqdm(tickers):
    #         db.util.get_filing_set(dl, ticker, cnf.APP_CONFIG.TRACKED_FORMS, "2017-01-01", number_of_filings=10)

    # with open("./resources/company_tickers.json", "r") as f:
    #     tickers = list(json.load(f).keys())
    #     db.util.get_overview_files(cnf.DOWNLOADER_ROOT_PATH, cnf.POLYGON_OVERVIEW_FILES_PATH, cnf.POLYGON_API_KEY, tickers)

# delete and recreate tables, populate 8-k item names
# extract item:content pairs from all 8-k filings in the downloader_root_path
# and add them to the database (currently not having filing_date, 
# important for querying the results later) if not other way, get filing date 
# by using cik and accn to query the submissions file 

def init_fdb():
    connection_string = "postgres://postgres:admin@localhost/postgres"
    fdb = FilingDB(connection_string)

    fdb.execute_sql("./main/sql/db_delete_all_tables.sql")
    fdb.execute_sql("./main/sql/filings_db_schema.sql")
    fdb.init_8k_items()
    paths = []
    with open(r"E:\pysec_test_folder\paths.txt", "r") as pf:
        while len(paths) < 20000:
            paths.append(pf.readline().strip("\n").lstrip("."))
    # paths = get_all_8k(Path(r"E:\sec_scraping\resources\datasets") / "filings")
    fdb.parse_and_add_all_8k_content(paths)
    return fdb

def retrieve_data_set():
    data = fdb.read("SELECT f.item_id as item_id, f.file_date, i.item_name as item_name, f.content FROM form8k as f JOIN items8k as i ON i.id = f.item_id WHERE item_name = 'item801' AND f.file_date > %s ORDER BY f.file_date LIMIT 1", [datetime.datetime(2021, 1, 1)])
    j = []
    for d in data:
        pass
    with open(r"E:\pysec_test_folder\k8s1v1.txt", "w", encoding="utf-8") as f:
        # json.dump(j, f)
        for r in data:
                f.write(r["content"].replace("\n", " ") + "\n")

# init_fdb()
# items = parser.split_into_items(r"E:\sec_scraping\resources\datasets\filings\0000023197\8-K\0000023197-20-000144\cmtl-20201130.htm")
# print(items)
# retrieve_data_set()
# print(fdb.get_items_count_summary())

def try_spacy():
    texts = fdb.read("SELECT f.item_id as item_id, f.file_date, i.item_name as item_name, f.content FROM form8k as f JOIN items8k as i ON i.id = f.item_id WHERE item_name = 'item801' ORDER BY f.file_date LIMIT 30", [])
    text = ""
    contents = [text["content"] for text in texts]
    for content in nlp.pipe(contents, disable=["attribute_ruler", "lemmatizer", "ner"]):
        # text = text + "\n\n" + content
        print([s for s in content.sents])
    # displacy.serve(doc, style="ent")
        
# try_spacy()

import re
from datetime import timedelta
import pickle
def download_samples(root, forms=["S-1", "S-3", "SC13D"]):
    dl = Downloader(root, user_agent="P licker p@licker.com")
    def get_filing_set(downloader: Downloader, ticker: str, forms: list, after: str, number_of_filings: int = 250):
        # # download the last 2 years of relevant filings
        if after is None:
            after = str((datetime.now() - timedelta(weeks=104)).date())
        for form in forms:
        #     # add check for existing file in pysec_donwloader so i dont download file twice
            try:
                downloader.get_filings(ticker, form, after, number_of_filings=number_of_filings)
            except Exception as e:
                print((ticker, form, e))
                pass
    with open("./resources/company_tickers.json", "r") as f:
        tickers = list(json.load(f).keys())
        for ticker in tqdm(tickers[5020:5120]):
            get_filing_set(dl, ticker, forms, "2017-01-01", number_of_filings=50)

def store(path: str, obj: list):
    with open(path, "wb") as f:
            pickle.dump(obj, f)

def retrieve(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)

def try_htmlparser():
    root_lap = Path(r"C:\Users\Public\Desktop\sec_scraping_testsets\example_filing_set_100_companies\filings")
    root_des = Path(r"F:\example_filing_set_100_companies\filings")
    parser = HtmlFilingParser()
    root_filing = root_lap
    file_paths = get_all_filings_path(Path(root_filing), "S-1")
    file_paths2 = get_all_filings_path(Path(root_filing), "S-3")
    # # file_paths3 = get_all_filings_path(Path(root_filing), "S-1")
    file_paths.append(file_paths2)
    # # file_paths.append(file_paths3)
    file_paths = flatten(file_paths)
    # store(r"F:\example_filing_set_100_companies\s1s3paths.txt", file_paths)$
    # file_paths = retrieve(root_lap)
    # for p in [r"F:\example_filing_set_100_companies\filings\0001556266\S-3\0001213900-20-018486\ea124224-s3a1_tdholdings.htm"]:
    file_count = 0
    test = "<body><p><a style='text-align:CENTER font: bold 1px color: red'>THIS<b>HI</b></a></p></body>"
    html = BeautifulSoup(test)
    print(html)
    found = html.select("[style*='text-align:center' i]")
                

    print(found[0].__dict__)
    main = []
    for p in file_paths[:10]:
        file_count += 1
        with open(p, "r", encoding="utf-8") as f:
            print(p)
            parser.make_soup(f.read())
            doc = str(parser.soup)
            matches = parser._get_possible_headers_based_on_style(parser.soup)
            for k, v in matches.items():
                for i in v["main"]:
                    if i:
                        print(i)
                        if isinstance(i, list):
                            pos = i[0][1]
                            first_match = parser._normalize_toc_title(i[0][0].string if i[0][0].string else " ".join([s for s in i[0][0].strings]))
                            full_text = parser._normalize_toc_title(
                                " ".join(
                                    flatten(
                                    [i[idx][0].string if i[idx][0].string else " ".join([s for s in i[idx][0].strings]) for idx in range(len(i))])))
                            main.append((first_match, full_text, pos[0], pos[1], p))
                        else:
                            pos = i[1]
                            text = i[0].string if i[0].string else " ".join([s for s in i[0].strings])
                            text = parser._normalize_toc_title(text)
                            main.append((text, text, pos[0], pos[1], p))   
    with open(root_filing.parent / "headers.csv", "w", newline="", encoding="utf-8") as f:
        # print(main)
        df = pd.DataFrame(main)
        df.to_csv(f)

def parse_headers():
    pd.read_csv(r"C:\Users\Public\Desktop\sec_scraping_testsets\example_filing_set_100_companies\headers.csv")

                
try_htmlparser()
# parse_headers()

# download_samples(r"F:\example_filing_set_100_companies")


# from main.data_aggregation.bulk_files import update_bulk_files
# update_bulk_files()
# from spacy.tokens import DocBin, Doc
# Doc.set_extension("rel", default={}, force=True)

# docbin = DocBin(store_user_data=True)
# docbin.from_disk(r"C:\Users\Olivi\Desktop\spacy_example2.spacy")
# doc = list(docbin.get_docs(nlp.vocab))[0]



    # with open(p, "r", encoding="utf-8") as f:
    #     filing = parser.preprocess_filing(f.read())
    #     # print(filing)
    #     print(len(parser.parse_items(filing)))

# item count in all 8-k's of the filings-database
