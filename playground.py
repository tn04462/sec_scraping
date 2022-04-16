from email.parser import Parser
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
        super.__init__(*args)
    
    def add_8k_item
    
    
    
# first get all 8ks
def get_all_8k(cnf):
    paths_folder = [r.glob("8-K") for r in Path(cnf.DOWNLOADER_ROOT_PATH).glob("*")]
    paths_folder = [r for r in paths_folder]
    paths_files = [[f.rglob("*.htm") for f in r] for r in paths_folder]
    paths = []
    for l in paths_files:
        for each in l:
            for r in each:
                paths.append(r)
    return paths


i = []
failures = []
paths = get_all_8k(cnf)[:2]
print(len(paths))
for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        file = f.read()
        filing = parser.preprocess_filing(file)
        items = parser.parse_items(filing)
        print(items)
            
# for x in i:
#     print(x)
#     for each in x:
#         print(each)