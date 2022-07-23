import abc
from typing import Set
from . import orm
from main.domain import model
from sqlalchemy.orm import joinedload


class AbstractRepository(abc.ABC):
    def __init__(self):
        pass 
    
    def add(self, *args, **kwargs):
        return self._add(*args, **kwargs)
    
    def get(self, *args, **kwargs):
        return self._get(*args, **kwargs)

    def _add(self):
        raise NotImplementedError

    def _get(self):
        raise NotImplementedError

class FakeCompanyRepository(AbstractRepository):
    def __init__(self):
        self.session = set()
    
    def _add(self, company: model.Company):
        self.session.add(company)
    
    def _get(self, symbol: str):
        for company in self.session:
            if company.symbol == symbol:
                return company


class SqlAlchemyCompanyRepository(AbstractRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, company: model.Company):
        self.session.add(company)

    def _get(self, symbol):
        return self.session.query(model.Company).filter_by(symbol=symbol).first()