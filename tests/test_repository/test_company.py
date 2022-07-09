import pytest
from dilution_db import DilutionDB
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from test_database import company_data, get_session, get_session_factory, postgresql_my_proc, postgresql_np
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
        "secu": model.CommonShare(name=data["security_name"]),
        "underlying": data
    }
    return security

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
def get_uow(get_session_factory):
    return unit_of_work.SqlAlchemyCompanyUnitOfWork(session_factory=get_session_factory)

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
    common_dict = create_common_shares_dict()
    # common = 
    uow = get_uow
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        print(common_dict)
        company.add_security(name=common_dict["name"], secu_type=common_dict["secu_type"], secu=common_dict["secu"])
        u.commit()
    with uow as u:
        company = u.company.get(company_data["companies"]["symbol"])
        security = company.get_security_by_name(name=company_data["securities"]["security_name"])
        print(security.security_type, common_dict)
        assert security == common_dict
        
    

    









