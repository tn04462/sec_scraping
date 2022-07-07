import pytest
from main.configs import FactoryConfig, GlobalConfig
from dilution_db import DilutionDB
from pytest_postgresql import factories
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

cnf = FactoryConfig(GlobalConfig(ENV_STATE="dev").ENV_STATE)()

postgresql_my_proc = factories.postgresql_proc(
    host=cnf.DILUTION_DB_HOST,
    port=cnf.DILUTION_DB_PORT, 
    user=cnf.DILUTION_DB_USER,
    password=cnf.DILUTION_DB_PASSWORD,
    dbname=cnf.DILUTION_DB_DATABASE_NAME,
    load=str(Path(__file__).parent.parent.parent / "main" / "sql" / "dilution_db_schema.sql")
    )

@pytest.fixture
def get_session():
    session_factory = sessionmaker(bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING))
    session = session_factory()
    yield session

def test_connect(get_session):
    session = get_session
    tables = session.execute(text("Select * from information_schema.tables")).fetchall()
    assert len(tables) > 10


