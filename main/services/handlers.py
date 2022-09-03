from dataclasses import asdict
from sqlalchemy import inspect
from typing import List, Dict, Callable, Type, TYPE_CHECKING
from main.domain import commands, model
from main.services.unit_of_work import AbstractUnitOfWork
import logging

logger = logging.getLogger(__name__)

def add_company(cmd: commands.AddCompany, uow: AbstractUnitOfWork):
    with uow as u:
        u.company.add(cmd.company)
        u.commit()

def add_securities(cmd: commands.AddSecurities, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        for security in cmd.securities:
            if security not in company.securities:
                local_security_object = u.session.merge(security)
                company.add_security(local_security_object)
        u.company.add(company)
        u.commit()

def add_shelf_registration(cmd: commands.AddShelfRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        logger.info(f"shelf before merge: {[x.value for x in inspect(cmd.shelf_registration).attrs]}")
        # add info of session state here for debug
        local_shelf_object = u.session.merge(cmd.shelf_registration)
        logger.info(f"shelf after merge: {[x.value for x in inspect(local_shelf_object).attrs]}")
        company.add_shelf(local_shelf_object)
        u.company.add(company)
        u.commit()

def add_resale_registration(cmd: commands.AddResaleRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        logger.info(f"resale before merge: {[x.value for x in inspect(cmd.resale_registration).attrs]}")
        local_resale_object = u.session.merge(cmd.resale_registration)
        company.add_resale(local_resale_object)
        logger.info(f"resale after merge: {[x.value for x in inspect(local_resale_object).attrs]}")
        u.company.add(company)
        u.commit()

def add_shelf_security_registration(cmd: commands.AddShelfSecurityRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol)
        offering: model.ShelfOffering = company.get_shelf_offering(offering_accn=cmd.offering_accn)
        if offering:
            local_registration_object = u.session.merge(cmd.security_registration)
            offering.add_registration(registered=local_registration_object)
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

