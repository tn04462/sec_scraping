from psycopg.rows import dict_row
from psycopg.errors import ProgrammingError, UniqueViolation
from psycopg_pool import ConnectionPool
from json import load
from os import path
import pandas as pd
import logging

from configparser import ConfigParser

logger = logging.getLogger(__package__)

config = ConfigParser()
config.read("./config.cfg")
if config.getboolean("environment", "production") is False:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

# make Database class a singleton
class DilutionDB:
    def __init__(self, 
        connectionString):
        self.connectionString = connectionString
        self.pool = ConnectionPool(self.connectionString, kwargs={"row_factory": dict_row})
        self.conn = self.pool.connection
        self.tracked_tickers = self._init_tracked_tickers()
    
    def _init_tracked_tickers(self):
        # add try except when needed for good error message
            return [t.strip() for t in config["general"]["tracked_tickers"].strip("[]").split(",")]
    
    def execute_sql_file(self, path):
        with self.conn() as c:
            with open(path, "r") as sql:
                res = c.execute(sql.read())
                try:
                    for row in res:
                        logging.DEBUG(row)
                except ProgrammingError:
                    pass
            
    
    def _delete_all_tables(self):
        with self.conn() as c:
            with open("./sql/db_delete_all_tables.sql", "r") as sql:
                c.execute(sql.read())
    
    def _create_tables(self):
        with self.conn() as c:
            with open("./sql/dilution_db_schema.sql", "r") as sql:
                c.execute(sql.read())


    # CU for 
    def read(self, query, values):
        with self.conn() as c:
            res = c.execute(query, values)
            rows = [row for row in res]
            return rows
    
    def create_sics(self):
        sics_path = path.normpath(path.join(path.dirname(path.abspath(__file__)), '.', "resources/sics.csv"))
        sics = pd.read_csv(sics_path)
        with self.conn() as c:
            with c.cursor().copy("COPY sics(sic, industry, sector, division) FROM STDIN") as copy:
                for val in sics.values:
                    copy.write_row(val)
    
    def create_sic(self, sic, sector, industry, division):
        with self.conn() as c:
            c.execute("INSERT INTO sics(sic, industry, sector, division) VALUES(%s, %s, %s, %s)",
            [sic, sector, industry, division])
    
    def create_company(self, cik, sic, symbol, name, description):
        with self.conn() as c:
                c.execute("INSERT INTO companies(cik, sic, symbol, name_, description_) VALUES(%s, %s, %s, %s, %s)",
                [cik, sic, symbol, name, description])

    def create_tracked_companies(self):
        base_path = config["polygon"]["overview_files_path"]
        for ticker in self.tracked_tickers:
            company_overview_file_path = path.join(base_path, f"{ticker}.json")
            with open(company_overview_file_path, "r") as company:
                corp = load(company)
                try:
                    self.create_company(corp["cik"], corp["sic_code"], ticker, corp["name"], corp["description"])
                except UniqueViolation:
                    logger.debug("couldnt create {}:company, already present in db.", ticker)
                    pass
                except Exception as e:
                    if "fk_sic" in str(e):
                        self.create_sic(corp["sic_code"], "unclassfied", corp["sic_description"], "unclassified")
                        self.create_company(corp["cik"], corp["sic_code"], ticker, corp["name"], corp["description"])
                    else:
                        raise e

if __name__ == "__main__":
    
    db = DilutionDB(config["dilution_db"]["connectionString"])
    # with db.conn() as c:
    #     res = c.execute("SELECT * FROM companies JOIN sics ON companies.sic = sics.sic")
    #     for r in res:
    #         print(r)
    # db._delete_all_tables()
    # db._create_tables()
    # db.create_sics()
    db.create_tracked_companies()






