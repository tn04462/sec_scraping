import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main.services import unit_of_work
from main.configs import FactoryConfig, GlobalConfig


cnf = FactoryConfig(GlobalConfig(ENV_STATE="dev").ENV_STATE)()

@pytest.fixture
def get_session(postgresql_np):
    session_factory = sessionmaker(
        bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING),
        expire_on_commit=False)
    session = session_factory()
    yield session
    session.rollback()
    # session.execute("DROP ALL")

@pytest.fixture
def get_session_factory(postgresql_np):
    session_factory = sessionmaker(
        bind=create_engine(cnf.DILUTION_DB_CONNECTION_STRING),
        expire_on_commit=False)
    yield session_factory


@pytest.fixture
def get_uow(get_session_factory):
    return unit_of_work.SqlAlchemyCompanyUnitOfWork(session_factory=get_session_factory)


