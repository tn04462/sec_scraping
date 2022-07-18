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

company_data_conversion = {
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
        "offering_status":{
            "id": 1,
            "name_": "active"
        },
        "companies": {
            "id": 1,
            "cik": "0000000001",
            "sic": "9000",
            "symbol": "RAND",
            "name_": "Rand Inc.",
            "description_": "Solely a test company meant for usage with pytest"
        },
        "shelf_registrations": {
            "id": 1,
            "company_id": 1,
            "accn": "0000123456789",
            "form_type": "S-3",
            "capacity": 100000,
            "total_amount_raised": 0,
            "effect_date": datetime.date(2022, 1, 1),
            "last_update": datetime.datetime.now().date(),
            "expiry": datetime.date(2022, 1, 1) + datetime.timedelta(days=1125),
            "filing_date": datetime.date(2022, 1, 1),
            "is_active": True
        },
        "securities": [
            {
                "id": 1,
                "company_id": 1,
                "security_name": "common stock",
                # "security_type": "CommonShare",
                "security_attributes": model.CommonShare(name="common stock").json()
            },
            {
                "id": 2,
                "company_id": 1,
                "security_name": "preferred stock 1",
                # "security_type": "PreferredShare",
                "security_attributes": model.PreferredShare(name="preferred stock 1").json()
            },
            {
                "id": 3,
                "company_id": 1,
                "security_name": "preferred stock 2",
                # "security_type": "PreferredShare",
                "security_attributes": model.PreferredShare(name="preferred stock 2").json()
            }
        ],
        "securities_conversion":[
            {
                "id": 1,
                "from_security_id": 2,
                "to_security_id": 1,
                "conversion_attributes": model.ConvertibleFeature(conversion_ratio=10).json()
            },
            {
                "id": 2,
                "from_security_id": 2,
                "to_security_id": 3,
                "conversion_attributes": model.ConvertibleFeature(conversion_ratio=50).json()
            }
        ],
        "shelf_offerings": {
            "id": 1,
            "shelf_registrations_id": 1,
            "accn": "00921310923",
            "filing_date": datetime.date(2022, 1, 1),
            "offering_type": "atm",
            "final_offering_amount": None,
            "anticipated_offering_ammount": 100000,
            "offering_status_id": 1,
            "commencment_date": datetime.date(2022, 2, 1),
            "end_date": datetime.date(2022, 3, 1)
        }
    }

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
    with uow as u:
        yield u.company.get(company_data["companies"]["symbol"])

    
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

def test_add_company(get_session):
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

def test_add_sic(get_session):
    session = get_session
    sic = _add_sic(session)
    received = session.query(model.Sic).filter_by(sic=company_data["sics"]["sic"]).first()
    print(sic, received)
    assert sic == received

def test_repo_add_company(add_base_company):
    received = add_base_company
    new_company = create_company()
    print(locals())
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
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        security = company.get_security_by_name(name=secu_args["name"])
        print(security, posted)
        assert security == posted

def populate_database_for_conversion(session):
    for table, v in company_data_conversion.items():
        if isinstance(v, list):
            for i in v:
                columns = ", ".join(list(i.keys()))
                values = ", ".join(["'" + str(value) + "'" for value in i.values()])
                try:
                    t = text(f"INSERT INTO {table}({columns}) VALUES({values})")
                    session.execute(t)
                except IntegrityError as e:
                    session.rollback()
                    print(e)
                else:
                    session.commit()
        else:
            columns = ", ".join(list(v.keys()))
            values = ", ".join(["'" + str(value) + "'" for value in v.values()])
            try:
                t = text(f"INSERT INTO {table}({columns}) VALUES({values})")
                session.execute(t)
            except IntegrityError as e:
                session.rollback()
                print(e)
            else:
                session.commit()   

def test_repo_add_conversion_attribute(get_uow, add_base_company):
    uow = get_uow
    add_security(create_common_shares_dict, uow)
    add_security(create_preferred_shares_dict, uow)
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        secu1 = company.get_security_by_name(create_common_shares_dict()["name"])
        secu2 = company.get_security_by_name(create_preferred_shares_dict()["name"])
        conversion_feature = model.ConvertibleFeature(conversion_ratio=10)
        secu_conversion = model.SecurityConversion(conversion_feature.json(), secu1, secu2)
        company.add_security_conversion(secu_conversion)
        u.company.add(company)
        u.commit()
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        print(company.security_conversion[0], "/n", secu_conversion)
        assert company.security_conversion[0] == secu_conversion
    
def test_repo_add_security_outstanding(get_uow, add_base_company):
    uow = get_uow
    add_security(create_common_shares_dict, uow)
    new_outstanding = model.SecurityOutstanding(5000, datetime.date(2022, 1, 1))
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        secu = company.get_security_by_name(create_common_shares_dict()["name"])
        secu.add_outstanding(model.SecurityOutstanding(5000, datetime.date(2022, 1, 1)))
        u.company.add(company)
        u.commit()
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        secu = company.get_security_by_name(create_common_shares_dict()["name"])
        assert new_outstanding in secu.outstanding

def test_repo_add_security_authorized(get_uow, add_base_company):
    uow = get_uow
    new_authorized = model.SecurityAuthorized("CommonShare", 10000, datetime.date(2022, 1, 1))
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        company.add_security_authorized(model.SecurityAuthorized("CommonShare", 10000, datetime.date(2022, 1, 1)))
        u.company.add(company)
        u.commit()
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        assert new_authorized in company.securities_authorized

# def test_repo_add_shelf_security_registration_with_source_security(get_uow, add_base_company):
#     uow = get_uow
#     add_security(create_common_shares_dict, uow)
#     add_security(create_preferred_shares_dict, uow)
#     with uow as u:
#         company: model.Company = u.company.get(company_data["companies"]["symbol"])
#         # company.add_security_shelf_registration()

def test_repo_get_company_speed(get_uow, add_base_company):
    uow = get_uow
    add_security(create_common_shares_dict, uow)
    add_security(create_preferred_shares_dict, uow)
    add_security(create_warrant_dict, uow)
    with uow as u:
        company: model.Company = u.company.get(company_data["companies"]["symbol"])
        secu = company.get_security_by_name(create_common_shares_dict()["name"])
        for x in range(25):
            for y in range(12):
                secu.add_outstanding(model.SecurityOutstanding(5000, datetime.date(2022, y, x)))
        u.company.add(company)
        u.commit()
    durations = []
    for count in range(100):
        start = datetime.datetime.now()
        with uow as u:
            company: model.Company = u.company.get(company_data["companies"]["symbol"])
        duration  = datetime.datetime.now() - start
        durations.append(durations)
    import pandas as pd
    s = pd.Series(durations)
    print(s.describe())
    assert 1 == 2


        
    

    









