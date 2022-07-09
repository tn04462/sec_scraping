import pytest
from main.configs import FactoryConfig, GlobalConfig
from dilution_db import DilutionDB
from pytest_postgresql import factories
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from psycopg.rows import dict_row
from psycopg.errors import ProgrammingError
from psycopg_pool import ConnectionPool
from psycopg import Connection

cnf = FactoryConfig(GlobalConfig(ENV_STATE="dev").ENV_STATE)()
dilution_db_schema = str(Path(__file__).parent.parent / "main" / "sql" / "dilution_db_schema.sql")
delete_tables = str(Path(__file__).parent.parent / "main" / "sql" / "db_delete_all_tables.sql")

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
postgresql_np = factories.postgresql("postgresql_my_proc", dbname="dilution_db_test")

@pytest.fixture
def get_session(postgresql_np):
    session_factory = sessionmaker(bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING))
    session = session_factory()
    yield session

@pytest.fixture
def get_session_factory(postgresql_np):
    session_factory = sessionmaker(bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING))
    return session_factory

def test_connect(get_session):
    session = get_session
    tables = session.execute(text("Select * from information_schema.tables")).fetchall()
    assert len(tables) > 200


