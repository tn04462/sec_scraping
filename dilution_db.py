from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# make Database class a singleton
class DilutionDB:
    def __init__(self, 
        connectionString):
        self.connectionString = connectionString
        self.pool = ConnectionPool(self.connectionString, kwargs={"row_factory": dict_row})
        self.conn = self.pool.connection

    # CU for 
    def read(self, query, values):
        with self.conn() as c:
            res = c.execute(query, values)
            rows = [row for row in res]
            return rows


