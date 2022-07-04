from sqlalchemy import (
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
from domain_model import (
    Underwriter,
    OfferingStatus,
    SecurityCusip,
    Security,
    SecurityConversionAttributes,
    SecurityOutstanding,
    SecurityAuthorized,
    ShelfSecurityRegistration,
    ShelfSecurityComplete,
    ShelfRegistration,
    ResaleSecurityRegistration,
    ResaleSecurityComplete,
    ResaleRegistration,
    Company
)

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
    Column("security_type", ),
    Column()
)

