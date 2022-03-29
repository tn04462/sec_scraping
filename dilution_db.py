from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

create_tables_path = r"C:\Users\Olivi\Testing\sec_scraping\sql\dilution_db_schema.sql"


# make Database class a singleton
class Database:
    def __init__(self, 
        connectionString,
        host,
        user,
        password,
        port,
        database):
        self.connectionString = connectionString
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.pool = ConnectionPool(self.connectionString, kwargs={"row_factory": dict_row})
        self.conn = self.pool.connection

    def connect(self):
        pass

db = Database(connectionString = "postgres://postgres:admin@localhost/dilution_db",
        host = "localhost",
        user = "postgres",
        password ="admin",
        port = "5432",
        database = "dilution_db")

if __name__ == "__main__":
    with open(r"C:\Users\Olivi\Testing\sec_scraping\sql\dilution_db_schema.sql", "r") as f:
        with db.conn() as conn:
            rf = f.read()
            conn.execute(rf)
    # import subprocess
    # subprocess.call(r"psql -f C:\Users\Olivi\Testing\sec_scraping\sql\dilution_db_schema.sql", shell=True)
    with db.conn() as conn:
        res = conn.execute("SELECT * FROM information_schema.tables WHERE table_schema = 'public'")
        for row in res:
            print(row)
    # with db.conn() as conn:
    #     conn.execute("CREATE TABLE IF NOT EXISTS sics (sic INT PRIMARY KEY, sector VARCHAR(255) NOT NULL, industry VARCHAR(255) NOT NULL,UNIQUE(sector, industry));")

    # # with db.conn() as conn:
    # #     conn.execute("INSERT INTO sics(sic, sector, industry) VALUES('1', 'this', 'that')")
    # with db.conn() as conn:
    #     res = conn.execute("SELECT * FROM sics")
    #     for row in res:
    #         print(row)