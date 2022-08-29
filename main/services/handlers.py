from dataclasses import asdict
from typing import List, Dict, Callable, Type, TYPE_CHECKING
from main.domain import commands, model
from main.services.unit_of_work import AbstractUnitOfWork

def add_company(cmd: commands.AddCompany, uow: AbstractUnitOfWork):
    with uow as u:
        u.company.add(cmd.company)
        u.commit()

def add_securities(cmd: commands.AddSecurities, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        for security in cmd.securities:
            company.add_security(security)
        u.company.add(company)
        u.commit()

def add_shelf_registration(cmd: commands.AddShelfRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        company.add_shelf(cmd.shelf_registration)
        u.company.add(company)
        u.commit()

def add_resale_registration(cmd: commands.AddResaleRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        company.add_resale(cmd.resale_registration)
        u.company.add(company)
        u.commit()

def add_shelf_security_registration(cmd: commands.AddShelfSecurityRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        offering: model.ShelfOffering = company.get_shelf_offering(offering_accn=cmd.offering_accn)
        if offering:
            offering.add_registration(registered=cmd.security_registration)
            u.company.add(company)
            u.commit()
        else:
            u.rollback()
            raise AttributeError(f"Couldnt add ShelfSecurityRegistration, because this company doesnt have a shelf offering associated with accn: {cmd.offering_accn}.")



COMMAND_HANDLERS = {
    commands.AddCompany: add_company,
    commands.AddSecurities: add_securities,
    commands.AddShelfRegistration: add_shelf_registration,
    commands.AddResaleRegistration: add_resale_registration,
    commands.AddShelfSecurityRegistration: add_shelf_security_registration
}

