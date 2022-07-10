

CREATE TYPE SECURITY_TYPES as ENUM (
    'CommonShare',
    'PreferredShare',
    'DebtSecurity',
    'Option',
    'Warrant',
    'ConvertiblePreferredShares',
    'ConvertibleDebtSecurity'
    );


CREATE TABLE IF NOT EXISTS files_last_update(
    submissions_zip_lud TIMESTAMP,
    companyfacts_zip_lud TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sics (
    sic INT PRIMARY KEY,
    sector VARCHAR(255) NOT NULL,
    industry VARCHAR(255) NOT NULL,
    division VARCHAR(255) NOT NULL,

    UNIQUE(sector, industry)
);

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    cik VARCHAR(80) NOT NULL,
    sic INT,
    symbol VARCHAR(10) UNIQUE,
    name_ VARCHAR(255),
    description_ VARCHAR,
    
    CONSTRAINT fk_sic
        FOREIGN KEY (sic)
            REFERENCES sics(sic)
);




CREATE TABLE IF NOT EXISTS company_last_update(
    company_id INTEGER UNIQUE,
    filings_download_lud TIMESTAMP,
    filing_links_lud TIMESTAMP,
    outstanding_shares_lud TIMESTAMP,
    net_cash_and_equivalents_lud TIMESTAMP,
    cash_burn_rate_lud TIMESTAMP,
    
    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id)
);

-- so i know which filings have been parsed
CREATE TABLE IF NOT EXISTS filing_parse_history(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    accession_number VARCHAR,
    date_parsed DATE,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT unique_co_accn
        UNIQUE(company_id, accession_number)
);



-- maybe add taxonomy, name and accn to know source
CREATE TABLE IF NOT EXISTS outstanding_shares(
    company_id INTEGER,
    instant DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, instant)
);

CREATE TABLE IF NOT EXISTS market_cap(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    instant DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, instant)
);

-- CREATE TABLE IF NOT EXISTS free_float(
--     company_id INTEGER,
--     instant DATE,
--     amount BIGINT,

--     CONSTRAINT fk_company_id
--         FOREIGN KEY (company_id)
--             REFERENCES companies(id),
--     UNIQUE(company_id, instant)
-- )

CREATE TABLE IF NOT EXISTS cash_operating(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    from_date DATE,
    to_date DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date)
);

CREATE TABLE IF NOT EXISTS cash_financing(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    from_date DATE,
    to_date DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date)
);

CREATE TABLE IF NOT EXISTS cash_investing(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    from_date DATE,
    to_date DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date)
);

CREATE TABLE IF NOT EXISTS net_cash_and_equivalents(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    instant DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, instant)
);


CREATE TABLE IF NOT EXISTS cash_burn_rate(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    burn_rate_operating FLOAT,
    burn_rate_financing FLOAT,
    burn_rate_investing FLOAT,
    burn_rate_total FLOAT,
    from_date DATE,
    to_date DATE,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date),
    CONSTRAINT unique_from_date UNIQUE(company_id, from_date)
);

CREATE TABLE IF NOT EXISTS cash_burn_summary(
    company_id INTEGER,
    burn_rate FLOAT,
    burn_rate_date DATE,
    net_cash FLOAT,
    net_cash_date DATE,
    days_of_cash FLOAT,
    days_of_cash_date DATE,


    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT unique_company_id UNIQUE(company_id)
);

CREATE TABLE IF NOT EXISTS form_types(
    form_type VARCHAR(200) PRIMARY KEY,
    category VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS filing_links(
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    filing_html VARCHAR(500),
    form_type VARCHAR(200),
    filing_date DATE,
    description_ VARCHAR(2000),
    file_number VARCHAR(1000),

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (form_type)
            REFERENCES form_types(form_type)
);



CREATE TABLE IF NOT EXISTS underwriters(
    id SERIAL PRIMARY KEY,
    name_ VARCHAR(255)
);



CREATE TABLE IF NOT EXISTS shelf_registrations(
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    accn VARCHAR(30) NOT NULL,
    form_type VARCHAR NOT NULL,
    capacity BIGINT,
    total_amount_raised BIGINT,
    effect_date DATE,
    last_update DATE,
    expiry DATE,
    filing_date DATE,
    is_active BOOLEAN,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (form_type)
            REFERENCES form_types(form_type)
);

CREATE TABLE IF NOT EXISTS resale_registrations(
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    accn VARCHAR(30) NOT NULL,
    form_type VARCHAR NOT NULL,
    effect_date DATE,
    last_update DATE,
    expiry DATE,
    filing_date DATE,
    is_active BOOLEAN,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (form_type)
            REFERENCES form_types(form_type)
);

CREATE TABLE IF NOT EXISTS offering_status(
    id SERIAL PRIMARY KEY,
    name_ VARCHAR UNIQUE
);

CREATE TABLE IF NOT EXISTS shelf_offerings(
    id SERIAL PRIMARY KEY,
    shelf_registrations_id INTEGER NOT NULL,
    accn VARCHAR(30) NOT NULL,
    filing_date DATE,
    offering_type VARCHAR,
    final_offering_amount BIGINT,
    anticipated_offering_amount BIGINT,
    offering_status_id INTEGER,
    commencment_date TIMESTAMP,
    end_date TIMESTAMP,
      
    CONSTRAINT fk_offering_status_id
        FOREIGN KEY (offering_status_id)
            REFERENCES offering_status(id),
    CONSTRAINT fk_shelf_registrations_id
        FOREIGN KEY (shelf_registrations_id)
            REFERENCES shelf_registrations(id)
);

CREATE TABLE IF NOT EXISTS underwriters_shelf_offerings(
    offerings_id INTEGER,
    underwriter_id INTEGER,

    CONSTRAINT fk_offerings_id
        FOREIGN KEY (offerings_id)
            REFERENCES shelf_offerings(id),
    CONSTRAINT fk_underwriter_id
        FOREIGN KEY (underwriter_id)
            REFERENCES underwriters(id)
);


-- tables: shelf_registrations_shelf_offerings, shelf_offerings_underwriters, shelf_offerings_securities, securities, security as json?



CREATE TABLE IF NOT EXISTS securities (
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    security_name VARCHAR,
    security_type SECURITY_TYPES,
    underlying_security_id INTEGER,
    security_attributes JSON,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_underlying_security_id
        FOREIGN KEY (underlying_security_id)
            REFERENCES securities(id),
    CONSTRAINT unique_name_company
        UNIQUE(company_id, security_name)

);

CREATE TABLE IF NOT EXISTS securities_cusip(
    id SERIAL PRIMARY KEY,
    cusip_number VARCHAR (16),
    security_id INTEGER,

    CONSTRAINT fk_security_id
        FOREIGN KEY (security_id)
            REFERENCES securities(id)
);


CREATE TABLE IF NOT EXISTS securities_conversion (
    id SERIAL PRIMARY KEY,
    from_security_id INTEGER,
    to_security_id INTEGER,
    conversion_attributes JSON,

    CONSTRAINT fk_from_security
        FOREIGN KEY (from_security_id)
            REFERENCES securities(id),
    CONSTRAINT fk_to_security
        FOREIGN KEY (to_security_id)
            REFERENCES securities(id)
);

CREATE TABLE IF NOT EXISTS securities_shelf_offerings_completed (
    id SERIAL PRIMARY KEY,
    security_id INTEGER,
    shelf_offerings_id INTEGER,
    source_security_id INTEGER NULL,
    amount BIGINT,

    CONSTRAINT fk_security_id
        FOREIGN KEY (security_id)
            REFERENCES securities(id),
    CONSTRAINT fk_shelf_offerings
        FOREIGN KEY (shelf_offerings_id)
            REFERENCES shelf_offerings(id),
     CONSTRAINT fk_source_security_id
        FOREIGN KEY (source_security_id)
            REFERENCES securities(id),
    
    CONSTRAINT security_offering_source_security_amount_completed
        UNIQUE (security_id, shelf_offerings_id, source_security_id, amount)
);

CREATE TABLE IF NOT EXISTS securities_shelf_offerings_registered (
    id SERIAL PRIMARY KEY,
    security_id INTEGER,
    shelf_offerings_id INTEGER,
    source_security_id INTEGER NULL,
    amount BIGINT,

    CONSTRAINT fk_security_id
        FOREIGN KEY (security_id)
            REFERENCES securities(id),
    CONSTRAINT fk_shelf_offerings
        FOREIGN KEY (shelf_offerings_id)
            REFERENCES shelf_offerings(id),
    CONSTRAINT fk_source_security_id
        FOREIGN KEY (source_security_id)
            REFERENCES securities(id),

    CONSTRAINT security_offering_source_security_amount_registered
        UNIQUE (security_id, shelf_offerings_id, source_security_id, amount)
);

CREATE TABLE IF NOT EXISTS securities_resale_completed (
    id SERIAL PRIMARY KEY,
    security_id INTEGER,
    resale_registrations_id INTEGER,
    source_security_id INTEGER NULL,
    amount BIGINT,

    CONSTRAINT fk_security_id
        FOREIGN KEY (security_id)
            REFERENCES securities(id),
    CONSTRAINT fk_resale_registrations_id
        FOREIGN KEY (resale_registrations_id)
            REFERENCES resale_registrations(id),
     CONSTRAINT fk_source_security_id
        FOREIGN KEY (source_security_id)
            REFERENCES securities(id),
    
    CONSTRAINT security_resale_source_security_amount_completed
        UNIQUE (security_id, resale_registrations_id, source_security_id, amount)
);

CREATE TABLE IF NOT EXISTS securities_resale_registered (
    id SERIAL PRIMARY KEY,
    security_id INTEGER,
    resale_registrations_id INTEGER,
    source_security_id INTEGER NULL,
    amount BIGINT,

    CONSTRAINT fk_security_id
        FOREIGN KEY (security_id)
            REFERENCES securities(id),
    CONSTRAINT fk_resale_registrations_id
        FOREIGN KEY (resale_registrations_id)
            REFERENCES resale_registrations(id),
    CONSTRAINT fk_source_security_id
        FOREIGN KEY (source_security_id)
            REFERENCES securities(id),

    CONSTRAINT security_resale_source_security_amount_registered
        UNIQUE (security_id, resale_registrations_id, source_security_id, amount)
);

CREATE TABLE IF NOT EXISTS securities_outstanding (
    id SERIAL PRIMARY KEY,
    security_id INTEGER,
    amount_outstanding BIGINT,
    instant DATE,

    CONSTRAINT fk_security_id
        FOREIGN KEY (security_id)
            REFERENCES securities(id)
);

CREATE TABLE IF NOT EXISTS securities_authorized (
    id SERIAL PRIMARY KEY,
    company_id INTEGER,
    security_type VARCHAR,
    amount_authorized BIGINT,
    instant DATE,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id)
    
);