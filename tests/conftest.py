import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main.configs import FactoryConfig, GlobalConfig
from main.services import unit_of_work
from dilution_db import DilutionDBUtil, DilutionDB
from boot import bootstrap_dilution_db
  


@pytest.fixture
def get_fake_db(get_test_config):
    cnf = get_test_config
    db = bootstrap_dilution_db(
        start_orm=False,
        uow=unit_of_work.FakeCompanyUnitOfWork(),
        config=cnf
    )
    yield db
    del db

@pytest.fixture
def get_fake_util(get_fake_db):
    db = get_fake_db
    util = DilutionDBUtil(db)
    yield util
    del util

@pytest.fixture
def get_test_config():
    cnf = FactoryConfig("test")()
    yield cnf
    del cnf

@pytest.fixture
def get_session(postgresql_np, get_test_config):
    cnf = get_test_config
    session_factory = sessionmaker(
        bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING),
        expire_on_commit=False)
    session = session_factory()
    yield session
    session.rollback()
    # session.execute("DROP ALL")

@pytest.fixture
def get_session_factory(get_test_config, postgresql_np):
    cnf = get_test_config
    session_factory = sessionmaker(
        bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING),
        expire_on_commit=False)
    yield session_factory


@pytest.fixture
def get_uow(get_session_factory):
    return unit_of_work.SqlAlchemyCompanyUnitOfWork(session_factory=get_session_factory)


