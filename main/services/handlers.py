from dataclasses import asdict
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation
from typing import List, Dict, Callable, Type, TYPE_CHECKING
from main.domain import commands, model
from main.services.unit_of_work import AbstractUnitOfWork
import logging

logger = logging.getLogger(__name__)

def add_company(cmd: commands.AddCompany, uow: AbstractUnitOfWork):
    with uow as u:
        u.company.add(cmd.company)
        u.commit()

def add_sic(cmd: commands.AddSic, uow: AbstractUnitOfWork):
    with uow as u:
        u.session.add(cmd.sic)
        try:
            u.session.commit()
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                pass
            else:
                raise e

def add_form_type(cmd: commands.AddFormType, uow: AbstractUnitOfWork):
    with uow as u:
        u.session.add(cmd.form_type)
        try:
            u.session.commit()
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                pass
            else:
                raise e

def add_filing_links(cmd: commands.AddFilingLinks, uow: AbstractUnitOfWork):
    with uow as u:
        form_types = set(u.session.query(model.FormType).all())
        print(form_types, type(form_types))
        company = u.company.get(symbol=cmd.symbol, lazy=True)
        for filing_link in cmd.filing_links:
            try:
                if filing_link.form_type not in form_types:
                    # add emitting of event here ? eg: event.NewFormTypeAdded
                    u.session.add(model.FormType(filing_link.form_type, "unspecified"))
                    u.session.commit()
                company.add_filing_link(filing_link)
            except Exception as e:
                raise e
        u.company.add(company)
        u.commit()

def add_securities(cmd: commands.AddSecurities, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol, lazy=True)
        for security in cmd.securities:
            if security not in company.securities:
                local_security_object = u.session.merge(security)
                company.add_security(local_security_object)
        u.company.add(company)
        u.commit()

def add_shelf_registration(cmd: commands.AddShelfRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol, lazy=True)
        # add info of session state here for debug
        local_shelf_object = u.session.merge(cmd.shelf_registration)
        company.add_shelf(local_shelf_object)
        u.company.add(company)
        u.commit()

def add_resale_registration(cmd: commands.AddResaleRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol, lazy=True)
        local_resale_object = u.session.merge(cmd.resale_registration)
        company.add_resale(local_resale_object)
        u.company.add(company)
        u.commit()

def add_shelf_security_registration(cmd: commands.AddShelfSecurityRegistration, uow: AbstractUnitOfWork):
    with uow as u:
        company: model.Company = u.company.get(symbol=cmd.symbol, lazy=True)
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
    commands.AddShelfSecurityRegistration: add_shelf_security_registration,

    commands.AddSic: add_sic,
    commands.AddFormType: add_form_type,
    commands.AddFilingLinks: add_filing_links,
}

