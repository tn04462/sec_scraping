from psycopg.rows import dict_row
from psycopg import ProgrammingError
from psycopg_pool import ConnectionPool
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
            # c.execute(r"COPY sics FROM 'c:\Users\Olivi\Testing\sec_scraping\resources\sics.csv' WITH DELIMITER ','  CSV HEADER")


if __name__ == "__main__":
    
    db = DilutionDB(config["dilution_db"]["connectionString"])
    # with db.conn() as c:
    #     res = c.execute("SELECT * FROM sics")
    #     for r in res:
    #         print(r)
    # db._delete_all_tables()
    # db._create_tables()
    db.create_sics()





