
from inspect import Attribute
from urllib3 import connection_from_url
# from dilution_db import DilutionDB
# from main.data_aggregation.polygon_basic import PolygonClient
# from main.configs import cnf

# from main.data_aggregation.bulk_files import update_bulk_files


from main.parser.text_parser import Parser8K
from pathlib import Path
parser = Parser8K()

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.errors import ProgrammingError, UniqueViolation, ForeignKeyViolation
from psycopg_pool import ConnectionPool

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
                print(f"failed to find date: {p}")
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





if __name__ == "__main__":
    connection_string = "postgres://postgres:admin@localhost/postgres"

    fdb = FilingDB(connection_string)

    from main.configs import cnf
    from db_updater import get_filing_set
    from pysec_downloader.downloader import Downloader
    from tqdm import tqdm
    from dilution_db import DilutionDB
    import json
    import csv
    from main.parser.text_parser import Parser8K

    db = DilutionDB(cnf.DILUTION_DB_CONNECTION_STRING)
    dl = Downloader(cnf.DOWNLOADER_ROOT_PATH, retries=100, user_agent=cnf.SEC_USER_AGENT)
    # import logging
    # logging.basicConfig(level=logging.INFO)
    # dlog = logging.getLogger("urllib3.connectionpool")
    # dlog.setLevel(logging.CRITICAL)
    # with open("./resources/company_tickers.json", "r") as f:
    #     tickers = list(json.load(f).keys())
    #     for ticker in tqdm(tickers[6368:]):
    #         db.util.get_filing_set(dl, ticker, ["8-K"], "2017-01-01", number_of_filings=250)

    # with open("./resources/company_tickers.json", "r") as f:
    #     tickers = list(json.load(f).keys())
    #     db.util.get_overview_files(cnf.DOWNLOADER_ROOT_PATH, cnf.POLYGON_OVERVIEW_FILES_PATH, cnf.POLYGON_API_KEY, tickers)

# delete and recreate tables, populate 8-k item names
# extract item:content pairs from all 8-k filings in the downloader_root_path
# and add them to the database (currently not having filing_date, 
# important for querying the results later) if not other way, get filing date 
# by using cik and accn to query the submissions file 
def init_fdb():
    fdb.execute_sql("./main/sql/db_delete_all_tables.sql")
    fdb.execute_sql("./main/sql/filings_db_schema.sql")
    fdb.init_8k_items()
    paths = []
    with open(r"E:\pysec_test_folder\paths.txt", "r") as pf:
        while len(paths) < 3000:
            paths.append(pf.readline().strip("\n"))
    # paths = get_all_8k(Path(r"E:\sec_scraping\resources\datasets") / "filings")
    fdb.parse_and_add_all_8k_content(paths)

def retrieve_data_set():
    data = fdb.read("SELECT f.item_id as item_id, f.file_date, i.item_name as item_name, f.content FROM form8k as f JOIN items8k as i ON i.id = f.item_id WHERE item_name = 'item801' ORDER BY f.file_date LIMIT 400", [])
    with open(r"E:\pysec_test_folder\k8s.txt", "w", encoding="utf-8") as f:
        for r in data:
            f.write(r["content"])
            f.write("\n-----\n")
# init_fdb()
retrieve_data_set()
# print(fdb.get_items_count_summary())

    # with open(p, "r", encoding="utf-8") as f:
    #     filing = parser.preprocess_filing(f.read())
    #     # print(filing)
    #     print(len(parser.parse_items(filing)))

# item count in all 8-k's of the filings-database
