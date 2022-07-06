from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    Integer,
    Column,
    String,
    Table,
    ForeignKey,
    Text
)
from sqlalchemy.orm import (
    relationship,
    registry
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import types
from domain_model import (
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
    CashNetAndEquivalents,
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
            "name": underwriters.name_
        }
    )

    offering_status_mapper = reg.map_imperatively(
        OfferingStatus,
        offering_status,
        properties={
            "name": offering_status.name_
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
            "name": securities.security_name,
            "underlying_name": 
        }
    )


