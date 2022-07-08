import pytest
from dilution_db import DilutionDB
from main.security_models.naiv_models import CommonShare
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_database import get_session, postgresql_my_proc, postgresql_np
from main.domain import model
from main.adapters import orm
import datetime

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
        "securities": {
            "id": 1,
            "company_id": 1,
            "security_name": "common stock",
            "security_type": "CommonShares",
            "security_attributes": CommonShare(name="common stock").json()
        }
    }

@pytest.fixture
def populate_database(get_session):
    session = get_session
    for table, v in company_data.items():
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
    

def test_inserts(get_session, populate_database):
    session = get_session
    values = []
    for k, _ in company_data.items():
        v = session.execute(text(f"SELECT * FROM {k}"))
        values.append(v.fetchall())
    for expected, received in zip(company_data.values(), values):
        print(tuple(expected.values()), received)
        for v1, v2 in zip(tuple(expected.values()), received[0]):
            assert v1 == v2


def create_company():
    data = company_data["companies"]
    company = model.Company(
        name=data["name_"],
        cik=data["cik"],
        sic=data["sic"],
        symbol=data["symbol"],
        description_=data["description_"])
    return company

def test_add_model(get_session, dict_key, model_class):
    session = get_session
    new_model = model_class(**company_data[dict_key])
    session.add(new_model)
    session.commit()
    received = session.query(model_class).first()
    assert new_model == received


def test_add_company(get_session):
    orm.start_mappers()
    session = get_session
    sic = model.Sic(9000, "test_sector", "test_industry", "test_division")
    session.add(sic)
    session.commit()
    company = create_company()
    company.change_name("Rand Corp.")
    session.add(company)
    session.commit()
    received = session.query(model.Company).filter_by(symbol=company_data["companies"]["symbol"]).first()
    assert company ==  received





