from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    Integer,
    Column,
    String,
    Table,
    ForeignKey
)
from sqlalchemy.orm import (
    relationship,
    registry
)
from sqlalchemy import types
from main.domain.model import (
    Underwriter,
    OfferingStatus,
    SecurityCusip,
    Security,
    SecurityConversionAttributes,
    SecurityOutstanding,
    SecurityAuthorized,
    ShelfOffering,
    ShelfSecurityRegistration,
    ShelfSecurityComplete,
    ShelfRegistration,
    ResaleSecurityRegistration,
    ResaleSecurityComplete,
    ResaleRegistration,
    Sic,
    FilingParseHistoryEntry,
    FilingLink,
    CashOperating,
    CashFinancing,
    CashInvesting,
    NetCashAndEquivalents,
    Company
)

class SecurityTypes(types.TypeDecorator):
    impl = types.String
    cache_ok = True


reg = registry()

underwriters = Table(
    "underwriters",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("name_", String)
)

underwriters_shelf_offerings = Table(
    "underwriters_shelf_offerings",
    reg.metadata,
    Column("offerings_id", ForeignKey("shelf_offerings.id")),
    Column("underwriter_id", ForeignKey("underwriters.id"))
)

offering_status = Table(
    "offering_status",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("name_", String)
)

securities_cusip = Table(
    "securities_cusip",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("cusip_number", String),
    Column("security_id", ForeignKey("securities.id"))
)

securities = Table(
    "securities",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("security_name", String),
    Column("security_type", SecurityTypes),
    Column("underlying_security_id", ForeignKey("securities.id")),
    Column("security_attributes", JSON)
)

securities_conversion = Table(
    "securities_conversion",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("from_security_id", ForeignKey("securities.id")),
    Column("to_security_id", ForeignKey("securities.id")),
    Column("conversion_attributes", JSON)
)

securities_outstanding = Table(
    "securities_outstanding",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("securities_id", ForeignKey("securities.id")),
    Column("amount", BigInteger),
    Column("instant", Date)
)

securities_authorized = Table(
    "securities_authorized",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("security_type",  SecurityTypes),
    Column("amount", BigInteger),
    Column("instant", Date)
)

shelf_offerings =  Table(
    "shelf_offerings",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("shelf_registrations_id", ForeignKey("shelf_registrations.id")),
    Column("accn", String),
    Column("filing_date", Date),
    Column("offering_type", String),
    Column("final_offering_amount", BigInteger),
    Column("anticipated_offering_amount", BigInteger),
    Column("offering_status_id", ForeignKey("offering_status.id")),
    Column("commencment_date", Date),
    Column("end_date", Date)
)

securities_shelf_offerings_registered = Table(
    "securities_shelf_offerings_registered",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("security_id", ForeignKey("securities.id")),
    Column("shelf_offerings_id", ForeignKey("shelf_offerings.id")),
    Column("source_security_id", ForeignKey("securities.id")),
    Column("amount", BigInteger)
)

securities_shelf_offerings_completed = Table(
    "securities_shelf_offerings_completed",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("security_id", ForeignKey("securities.id")),
    Column("shelf_offerings_id", ForeignKey("shelf_offerings.id")),
    Column("source_security_id", ForeignKey("securities.id")),
    Column("amount", BigInteger)
)

securities_resale_registered = Table(
    "securities_resale_registered",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("security_id", ForeignKey("securities.id")),
    Column("resale_registrations_id", ForeignKey("resale_registrations.id")),
    Column("source_security_id", ForeignKey("securities.id")),
    Column("amount", BigInteger)
)

securities_resale_comnpleted = Table(
    "securities_resale_comnpleted",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("security_id", ForeignKey("securities.id")),
    Column("resale_registrations_id", ForeignKey("resale_registrations.id")),
    Column("source_security_id", ForeignKey("securities.id")),
    Column("amount", BigInteger)
)

shelf_registrations = Table(
    "shelf_registrations",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("accn", String),
    Column("form_type", ForeignKey("form_types.form_type")),
    Column("capacity", BigInteger),
    Column("total_amount_raised", BigInteger),
    Column("effect_date", Date),
    Column("last_update", Date),
    Column("expiry", Date),
    Column("filing_date", Date),
    Column("is_active", Boolean),
)

resale_registrations = Table(
    "resale_registrations",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("accn", String),
    Column("form_type", ForeignKey("form_types.form_type")),
    Column("effect_date", Date),
    Column("last_update", Date),
    Column("expiry", Date),
    Column("filing_date", Date),
    Column("is_active", Boolean),
)

sics = Table(
    "sics",
    reg.metadata,
    Column("sic", Integer, primary_key=True),
    Column("sector", String),
    Column("industry", String),
    Column("division", String)
)

filing_parse_history = Table(
    "filing_parse_history",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("accession_number", String),
    Column("date_parsed", Date)
)

filing_links = Table(
    "filing_link",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("filing_html", String),
    Column("form_type", ForeignKey("form_types.form_type")),
    Column("filing_date", Date),
    Column("description_", String),
    Column("file_number", String)
)

cash_operating = Table(
    "cash_operating",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("from_date", Date),
    Column("to_date", Date),
    Column("amount", BigInteger)
)

cash_financing = Table(
    "cash_financing",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("from_date", Date),
    Column("to_date", Date),
    Column("amount", BigInteger)
)

cash_investing = Table(
    "cash_investing",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("from_date", Date),
    Column("to_date", Date),
    Column("amount", BigInteger)
)

net_cash_and_equivalents = Table(
    "net_cash_and_equivalents",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("company_id", ForeignKey("companies.id")),
    Column("instant", Date),
    Column("amount", BigInteger)
)

companies = Table(
    "companies",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("cik", String, nullable=False),
    Column("sic", ForeignKey("sics.sic")),
    Column("symbol", String, unique=True),
    Column("name_", String),
    Column("description_", String)
)

def start_mappers():
    underwriters_mapper = reg.map_imperatively(
        Underwriter,
        underwriters,
        properties={
            "name": underwriters.c.name_
        }
    )

    offering_status_mapper = reg.map_imperatively(
        OfferingStatus,
        offering_status,
        properties={
            "name": offering_status.c.name_
        }
    )

    securities_cusip_mapper = reg.map_imperatively(
        SecurityCusip,
        securities_cusip
    )

    securities_mapper = reg.map_imperatively(
        Security,
        securities,
        properties={
            "name": securities.c.security_name,
            "underlying": relationship(
                Security,
                primaryjoin=securities.c.id==securities.c.underlying_security_id,
                remote_side=securities.c.id,
                uselist=False
            ) 
        }
    )

    securities_conversion_mapper = reg.map_imperatively(
        SecurityConversionAttributes,
        securities_conversion
    )

    securities_outstanding_mapper = reg.map_imperatively(
        SecurityOutstanding,
        securities_outstanding
    )

    securities_authorized_mapper = reg.map_imperatively(
        SecurityAuthorized,
        securities_authorized
    )

    securities_shelf_offerings_registered_mapper = reg.map_imperatively(
        ShelfSecurityRegistration,
        securities_shelf_offerings_registered,
        properties={
            "security": relationship(
                securities_mapper,
                primaryjoin=securities_shelf_offerings_registered.c.security_id==securities.c.id,
                remote_side=securities_shelf_offerings_registered.c.security_id,
                uselist=False),
            "source_security": relationship(
                securities_mapper,
                primaryjoin=securities_shelf_offerings_registered.c.source_security_id==securities.c.id,
                remote_side=securities_shelf_offerings_registered.c.source_security_id,
                uselist=False)
        }
    )

    securities_shelf_offerings_completed_mapper = reg.map_imperatively(
        ShelfSecurityComplete,
        securities_shelf_offerings_completed,
        properties={
            "security": relationship(
                securities_mapper,
                primaryjoin=securities_shelf_offerings_completed.c.security_id==securities.c.id,
                remote_side=securities_shelf_offerings_completed.c.security_id,
                uselist=False),
            "source_security": relationship(
                securities_mapper,
                primaryjoin=securities_shelf_offerings_completed.c.source_security_id==securities.c.id,
                remote_side=securities_shelf_offerings_completed.c.source_security_id,
                uselist=False)
        }
    )

    securities_resale_registered_mapper = reg.map_imperatively(
        ResaleSecurityRegistration,
        securities_resale_registered,
        properties={
            "security": relationship(
                securities_mapper,
                primaryjoin=securities_resale_registered.c.security_id==securities.c.id,
                remote_side=securities_resale_registered.c.security_id,
                uselist=False),
            "source_security": relationship(
                securities_mapper,
                primaryjoin=securities_resale_registered.c.source_security_id==securities.c.id,
                remote_side=securities_resale_registered.c.source_security_id,
                uselist=False)
        }
    )

    securities_resale_comnpleted_mapper = reg.map_imperatively(
        ResaleSecurityComplete,
        securities_resale_comnpleted,
        properties={
            "security": relationship(
                securities_mapper,
                primaryjoin=securities_resale_comnpleted.c.security_id==securities.c.id,
                remote_side=securities_resale_comnpleted.c.security_id,
                uselist=False),
            "source_security": relationship(
                securities_mapper,
                primaryjoin=securities_resale_comnpleted.c.source_security_id==securities.c.id,
                remote_side=securities_resale_comnpleted.c.source_security_id,
                uselist=False)
        }
    )

    shelf_offerings_mapper = reg.map_imperatively(
        ShelfOffering,
        shelf_offerings,
        properties={
            "underwriters": relationship(
                underwriters_mapper,
                secondary=underwriters_shelf_offerings,
                collection_class=set
            ),
            "registrations": relationship(
                securities_shelf_offerings_registered_mapper,
                collection_class=set
            ),
            "completed": relationship(
                securities_shelf_offerings_completed_mapper,
                collection_class=set
            )
        }
    )

    shelf_registrations_mapper = reg.map_imperatively(
        ShelfRegistration,
        shelf_registrations,
        properties={
            "offerings": relationship(
                shelf_offerings_mapper,
                collection_class=set
            )
        }
    )

    resale_registrations_mapper = reg.map_imperatively(
        ResaleRegistration,
        resale_registrations,
        properties={
            "registrations": relationship(
                securities_resale_registered_mapper,
                collection_class=set
            ),
            "completed": relationship(
                securities_resale_comnpleted_mapper,
                collection_class=set
            )
        }
    )

    sics_mapper = reg.map_imperatively(
        Sic,
        sics
    )

    filing_parse_history_mapper = reg.map_imperatively(
        FilingParseHistoryEntry,
        filing_parse_history
    )

    filing_links_mapper = reg.map_imperatively(
        FilingLink,
        filing_links
    )

    cash_operating_mapper = reg.map_imperatively(
        CashOperating,
        cash_operating
    )

    cash_financing_mapper = reg.map_imperatively(
        CashFinancing,
        cash_financing
    )

    cash_investing_mapper = reg.map_imperatively(
        CashInvesting,
        cash_investing
    )

    net_cash_and_equivalents_mapper = reg.map_imperatively(
        NetCashAndEquivalents,
        net_cash_and_equivalents
    )

    companies_mapper = reg.map_imperatively(
        Company,
        companies,
        properties={
            "name": companies.c.name_,
    
            "securities": relationship(
                securities_mapper,
                collection_class=set
            ),
            "shelfs": relationship(
                shelf_registrations_mapper,
                collection_class=set
            ),
            "resales": relationship(
                resale_registrations_mapper,
                collection_class=set
            ),
            "filing_parse_history": relationship(
                filing_parse_history_mapper,
                collection_class=set
            ),
            "filing_links": relationship(
                filing_links_mapper,
                collection_class=set
            ),
            "cash_operating": relationship(
                cash_operating_mapper,
                collection_class=set
            ),
            "cash_financing": relationship(
                cash_financing_mapper,
                collection_class=set
            ),
            "cash_investing": relationship(
                cash_investing_mapper,
                collection_class=set
            ),
            "net_cash_and_equivalents": relationship(
                net_cash_and_equivalents_mapper,
                collection_class=set
            )

        }
    )








