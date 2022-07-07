import abc
from typing import Set
from . import orm
from . import domain_model


class AbstractRepository(abc.ABC):
    def __init__(self):
        pass 

    def add(self):
        raise NotImplementedError

    def get(self):
        raise NotImplementedError


class SqlAlchemyCompanyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, company):
        self.session.add(company)

    def _get(self, symbol):
        return self.session.query(domain_model.Company).filter_by(symbol=symbol).first()