from email.parser import Parser

from urllib3 import connection_from_url
from main.data_aggregation.polygon_basic import PolygonClient
from main.configs import cnf

from main.data_aggregation.bulk_files import update_bulk_files


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
    
    def init_8k_items(self):
        with self.conn() as connection:
            for i in self.items8k:
                connection.execute("INSERT INTO items8k(item_name) VALUES(%s)",[i])
    
    def add_8k_content(self, cik, item, content):
        normalized_item = self.normalize_8kitem(item)
        with self.conn() as connection:
            # print(item)
            connection.execute("INSERT INTO form8k(cik, item_id, content) VALUES(%(cik)s, (SELECT id from items8k WHERE item_name = %(item)s), %(content)s)",
            {"cik": cik,
            "item": normalized_item,
            "content": content})
    
    def add_all_8k_content(self, paths):
        for f in parse_all_8k(paths):
            fdb.add_8k_content(f[0], f[1], f[2])


def get_all_8k(cnf):
        paths_folder = [r.glob("8-K") for r in ((Path(cnf.DOWNLOADER_ROOT_PATH))/"filings").glob("*")]
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

def parse_all_8k(paths):
    paths = get_all_8k(cnf)
    discard_count_other = 0
    discard_count_attr = 0
    discard_keys = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            cik = p.parent.parent.parent.name
            file = f.read()
            filing = parser.preprocess_filing(file)
            try:
                items = parser.parse_items(filing)
            except AttributeError:
                print(p)
                discard_count_attr += 1
                continue
            for item in items:
                for key, value in item.items():
                    # print(key, value)
                    try:
                        yield (str(cik), key, value)
                    except Exception as e:
                        discard_count_other += 1
                        discard_keys.apppend(key)
                        pass

                    # try:
                    #     fdb.add_8k_content(str(cik), key, value)
                    # except Exception as e:
                    #     discard_count_other += 1
                    #     discard_keys.append(key)
                    #     pass
    print(f"discarded -> (other:{discard_count_other}, attr: {discard_count_attr}) of a total of {len(paths)}")
    print(set(discard_keys))



if __name__ == "__main__":
    connection_string = "postgres://postgres:admin@localhost/postgres"

    fdb = FilingDB(connection_string)
    fdb.execute_sql("./main/sql/db_delete_all_tables.sql")
    fdb.execute_sql("./main/sql/filings_db_schema.sql")
    fdb.init_8k_items()
# # first get all 8ks
    paths = get_all_8k(cnf)
    parse_all_8k(paths)