from multiprocessing.sharedctypes import Value
import pytest
from pytest_postgresql import factories
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from psycopg.rows import dict_row
from psycopg.errors import ProgrammingError
from psycopg_pool import ConnectionPool
from psycopg import Connection
import datetime
from dilution_db import DilutionDB


from main.configs import FactoryConfig, GlobalConfig
from main.domain import model
from boot import bootstrap_dilution_db



cnf = FactoryConfig(GlobalConfig(ENV_STATE="dev").ENV_STATE)()
dilution_db_schema = str(Path(__file__).parent.parent / "main" / "sql" / "dilution_db_schema.sql")
delete_tables = str(Path(__file__).parent.parent / "main" / "sql" / "db_delete_all_tables.sql")

company_data = {
        "sics": {
            "sic": 9000,
            "sector": "test_sector",
            "industry": "test_industry",
            "division": "test_division"
        },
        "form_types": {
            "form_type": "S-3",
            "category": "prospectus"
        },
        "companies": {
            "id": 1,
            "cik": "0000000001",
            "sic": 9000,
            "symbol": "RAND",
            "name_": "Rand Inc.",
            "description_": "Solely a test company meant for usage with pytest"
        },
        "shelf_registrations": {
            "id": 1,
            "company_id": 1,
            "accn": "0000123456789",
            "file_number": "222",
            "form_type": "S-3",
            "capacity": 100000,
            "total_amount_raised": 0,
            "effect_date": datetime.date(2022, 1, 1),
            "last_update": datetime.datetime.now().date(),
            "expiry": datetime.date(2022, 1, 1) + datetime.timedelta(days=1125),
            "filing_date": datetime.date(2022, 1, 1),
            "is_active": True
        },
        "securities": {
            "id": 1,
            "company_id": 1,
            "security_name": "common stock",
            "security_type": "CommonShare",
            "underlying_security_id": None,
            "security_attributes": model.CommonShare(name="common stock").json()
        }
    }

company_data_expected = {
        "sics": {
            "sic": 9000,
            "sector": "test_sector",
            "industry": "test_industry",
            "division": "test_division"
        },
        "form_types": {
            "form_type": "S-3",
            "category": "prospectus"
        },
        "companies": {
            "id": 1,
            "cik": "0000000001",
            "sic": 9000,
            "symbol": "RAND",
            "name_": "Rand Inc.",
            "description_": "Solely a test company meant for usage with pytest"
        },
        "shelf_registrations": {
            "id": 1,
            "company_id": 1,
            "accn": "0000123456789",
            "file_number": "222",
            "form_type": "S-3",
            "capacity": 100000,
            "total_amount_raised": 0,
            "effect_date": datetime.date(2022, 1, 1),
            "last_update": datetime.datetime.now().date(),
            "expiry": datetime.date(2022, 1, 1) + datetime.timedelta(days=1125),
            "filing_date": datetime.date(2022, 1, 1),
            "is_active": True
        },
        "securities": {
            "id": 1,
            "company_id": 1,
            "security_name": "common stock",
            "security_type": "CommonShare",
            "underlying_security_id": None,
            "security_attributes": model.CommonShare(name="common stock").dict()
        }
    }



def load_schema(user, password, host, port, dbname):
    connectionstring = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    pool = ConnectionPool(
            connectionstring, kwargs={"row_factory": dict_row}
        )
    with pool.connection() as c:
        with open(delete_tables, "r") as sql:
            c.execute(sql.read())
    with pool.connection() as c:
        with open(dilution_db_schema, "r") as sql:
            c.execute(sql.read())
         

postgresql_my_proc = factories.postgresql_noproc(
    host=cnf.DILUTION_DB_HOST,
    port=cnf.DILUTION_DB_PORT,
    user=cnf.DILUTION_DB_USER,
    password=cnf.DILUTION_DB_PASSWORD,
    dbname=cnf.DILUTION_DB_DATABASE_NAME,
    load=[load_schema]
    )
postgresql_np = factories.postgresql("postgresql_my_proc", dbname=cnf.DILUTION_DB_DATABASE_NAME)

@pytest.fixture
def get_bootstrapped_dilution_db(postgresql_np):
    dilution_db = bootstrap_dilution_db(
        start_orm=False,
        config=cnf
    )
    yield dilution_db
    del dilution_db




@pytest.fixture
def populate_database(get_session):
    session = get_session
    for table, v in company_data.items():
        columns = ", ".join(list(v.keys()))
        values = ", ".join(["'" + str(value) + "'" if value is not None else "NULL" for value in v.values()])
        try:
            t = text(f"INSERT INTO {table}({columns}) VALUES({values})")
            session.execute(t)
        except IntegrityError as e:
            session.rollback()
            print(f"!encountered error during population of database: {e}")
        else:
            session.commit()

def test_connect(get_session):
    session = get_session
    tables = session.execute(text("Select * from information_schema.tables")).fetchall()
    assert len(tables) > 200    

def test_inserts(get_session, populate_database):
    session = get_session
    values = []
    for k, _ in company_data.items():
        v = session.execute(text(f"SELECT * FROM {k}"))
        values.append(v.fetchall())
    for expected, received in zip(company_data_expected.values(), values):
        print(f"expected: {tuple(expected.values())}")
        print(f"received: {received}")
        for v1, v2 in zip(tuple(expected.values()), received[0]):
            assert v1 == v2


def test_dilution_db_inital_population(get_bootstrapped_dilution_db, get_uow):
    if cnf.ENV_STATE != "dev":
        raise ValueError("config other than 'dev' loaded, aborting test.")
    test_tickers = ["CEI"]
    db: DilutionDB = get_bootstrapped_dilution_db
    # setup tables/make sure they exist
    db.util.inital_table_setup()
    # make sure bulk zip files are up to date
    db.updater.update_bulk_files()
    # do donwloads and inital population
    db.util.inital_company_setup(
        cnf.DOWNLOADER_ROOT_PATH,
        cnf.POLYGON_OVERVIEW_FILES_PATH,
        cnf.POLYGON_API_KEY,
        cnf.APP_CONFIG.TRACKED_FORMS,
        test_tickers,
        after="2021-01-01",
        before="2021-05-01")
    # do parse of existing filings
    for ticker in test_tickers:
        with db.conn() as conn:
            db.updater.update_filing_values(conn, ticker)
    # do download and parse of newer filings
    for ticker in test_tickers:
        db.updater.update_ticker(ticker)
    
    uow = get_uow
    for ticker in test_tickers:
        with uow as u:
            company = u.company.get(ticker)
            print(f"Company({ticker}): {company}")
    
    assert 1 == 2
    
    
    
    









