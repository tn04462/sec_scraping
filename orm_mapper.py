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
    Column("_name", String)
)

offering_status = Table(
    "offering_status",
    reg.metadata,
    Column("id", Integer, primary_key=True),
    Column("_name", String)
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



