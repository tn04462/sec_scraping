import pytest
from main.domain import model
import datetime

def test_security_is_equal():
    data = {
        "secu_type": "CommonShare",
        "secu_attributes": model.CommonShare(),
        "name": "common stock"
    }
    secu1 = model.Security(**data)
    secu2 = model.Security(**data)
    assert secu1 == secu2

def test_security_is_unequal():
    secu1 = model.Security(**{
        "secu_type": "CommonShare",
        "secu_attributes": model.CommonShare(),
        "name": "common stock"
    })
    secu2 = model.Security(**{
        "secu_type": "CommonShare",
        "secu_attributes": model.CommonShare(),
        "name": "common thing"
    })
    assert secu1 != secu2

def test_security_authorized_wrong_secu_type_failure():
    pytest.raises(TypeError, model.SecurityAuthorized, "NonExistantSecuType", 10000, datetime.date(2022, 1, 1))
