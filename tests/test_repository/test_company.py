import pytest
from dilution_db import DilutionDB
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from test_database import company_data, securities_data, get_session, get_session_factory, postgresql_my_proc, postgresql_np
from main.domain import model
from main.adapters import orm, repository
from main.services import unit_of_work
import datetime


orm.start_mappers()


def create_company():
    data = company_data["companies"]
    company = model.Company(
        name=data["name_"],
        cik=data["cik"],
        sic=data["sic"],
        symbol=data["symbol"],
        description_=data["description_"])
    return company

def create_common_shares_dict():
    data = company_data["securities"]
    security = {
        "name": data["security_name"],
        "secu_type": data["security_type"],
        "secu_attributes": model.CommonShare(name=data["security_name"])
    }
    return security

def create_preferred_shares_dict():
    return {
        "name": "series c preferred stock",
        "secu_type": "PreferredShare",
        "secu_attributes": model.PreferredShare(name="series c preferred stock"),
        }

def create_warrant_dict():
    return {
        "name": "pipe warrant",
        "secu_type": "Warrant",
        "secu_attributes": model.Warrant(
            name="pipe warrant",
            exercise_price=1.05,
            expiry=datetime.datetime(2027, 1, 1),
            issue_date=datetime.datetime(2022, 1, 1)
        ),
        "underlying": "common stock"
    }

def _add_sic(session):
    sic = model.Sic(**company_data["sics"])
    session.add(sic)
    session.commit()
    return sic

@pytest.fixture
def add_base_company(get_session, get_session_factory):
    session_factory = get_session_factory
    session = get_session
    new_company = create_company()
    _add_sic(session)
    uow = unit_of_work.SqlAlchemyCompanyUnitOfWork(session_factory)
    with uow as u:
        assert u.company.get(company_data["companies"]["symbol"]) is None
        u.company.add(new_company)
        u.commit()
        return u.company.get(company_data["companies"]["symbol"])

@pytest.fixture
def add_base_securities(get_uow, get_base_company):
    company = get_base_company
    uow = get_uow
    company.add_security(model.Security(securities_data[0]))
    
@pytest.fixture
def get_uow(get_session_factory):
    return unit_of_work.SqlAlchemyCompanyUnitOfWork(session_factory=get_session_factory)


def add_security(secu_args_function, uow):
    secu_args = secu_args_function()
    posted = model.Security(**secu_args)
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        company.add_security(posted)
        u.company.add(company)
        u.commit()

def test_add_model(get_session, dict_key, model_class):
    session = get_session
    new_model = model_class(**company_data[dict_key])
    session.add(new_model)
    session.commit()
    received = session.query(model_class).first()
    assert new_model == received

def test_add_company(get_session, mappers):
    session = get_session
    sic = model.Sic(9000, "test_sector", "test_industry", "test_division")
    session.add(sic)
    session.commit()
    company = create_company()
    session.add(company)
    session.commit()
    received = session.query(model.Company).filter_by(symbol=company_data["companies"]["symbol"]).first()
    print(received.__dict__, company.__dict__)
    assert company == received

def test_add_sic(get_session, mappers):
    session = get_session
    sic = _add_sic(session)
    received = session.query(model.Sic).filter_by(sic=company_data["sics"]["sic"]).first()
    print(sic, received)
    assert sic == received

def test_repo_add_company(add_base_company):
    received = add_base_company
    new_company = create_company()
    assert new_company == received

def test_repo_change_company_name(get_uow, add_base_company):
    new_name = "herpy derp corp."
    uow = get_uow
    with uow as u:
        company = u.company.get(company_data["companies"]["symbol"])
        company.change_name(new_name)
        u.commit()
        received = u.company.get(company_data["companies"]["symbol"])
        assert received.name == new_name

def test_repo_add_common_shares(get_uow, add_base_company):
    secu_args = create_common_shares_dict()
    posted = model.Security(**secu_args)
    uow = get_uow
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        company.add_security(posted)
        u.company.add(company)
        u.commit()
    with uow as u:
        company = u.company.get(company_data["companies"]["symbol"])
        security = company.get_security_by_name(name=secu_args["name"])
        print(security, posted)
        assert security == posted

def test_repo_add_preferred_shares(get_uow, add_base_company):
    secu_args = create_preferred_shares_dict()
    posted = model.Security(**secu_args)
    uow = get_uow
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        company.add_security(posted)
        u.company.add(company)
        u.commit()
    with uow as u:
        company = u.company.get(company_data["companies"]["symbol"])
        security = company.get_security_by_name(name=secu_args["name"])
        print(security, posted)
        assert security == posted

def test_repo_add_warrant(get_uow, add_base_company):
    secu_args = create_warrant_dict()
    posted = model.Security(**secu_args)
    uow = get_uow
    add_security(create_common_shares_dict, uow)
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        company.add_security(posted)
        u.company.add(company)
        u.commit()
    with uow as u:
        company = u.company.get(company_data["companies"]["symbol"])
        security = company.get_security_by_name(name=secu_args["name"])
        print(security, posted)
        assert security == posted

def test_repo_add_conversion_attribute(get_uow, add_base_company):
    uow = get_uow
    add_security(create_common_shares_dict, uow)
    add_security(create_preferred_shares_dict, uow)
    with uow as u:
        company = u.company.get(company_data["companies"]["symbol"])
        secu1 = company.get_security_by_name(create_common_shares_dict()["name"])
        secu2 = company.get_security_by_name(create_preferred_shares_dict()["name"])
        


        
    

    









