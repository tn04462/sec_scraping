

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


CREATE TABLE IF NOT EXISTS securities(
    company_id SERIAL, --issuer
    cusip_number VARCHAR (16) PRIMARY KEY,
    class VARCHAR,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS company_last_update(
    company_id SERIAL UNIQUE,
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
    company_id SERIAL,
    accession_number VARCHAR,
    date_parsed DATE,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT unique_co_accn
        UNIQUE(company_id, accession_number)
);

-- not sure if it makes sense to store the values like this after parsing
-- JSON structure has to be enforced application side with value, unit, ect for given field_name
-- reasoning: this way i can add new fields more easily and keep the validation on the parsing side, does it make sense to do it this way?
CREATE TABLE IF NOT EXISTS filing_values(
    company_id SERIAL, -- which company filed it
    accession_number VARCHAR, -- what filing the values come from
    date_parsed DATE, -- on which date the parse was done
    field_name VARCHAR NOT NULL, -- the field name
    field_values JSON,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT unique_co_accn_field_name UNIQUE(company_id, accession_number, field_name)
);

-- maybe add taxonomy, name and accn to know source
CREATE TABLE IF NOT EXISTS outstanding_shares(
    company_id SERIAL,
    instant DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, instant)
);

CREATE TABLE IF NOT EXISTS market_cap(
    company_id SERIAL,
    instant DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, instant)
);

-- CREATE TABLE IF NOT EXISTS free_float(
--     company_id SERIAL,
--     instant DATE,
--     amount BIGINT,

--     CONSTRAINT fk_company_id
--         FOREIGN KEY (company_id)
--             REFERENCES companies(id),
--     UNIQUE(company_id, instant)
-- )

CREATE TABLE IF NOT EXISTS cash_operating(
    company_id SERIAL,
    from_date DATE,
    to_date DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date)
);

CREATE TABLE IF NOT EXISTS cash_financing(
    company_id SERIAL,
    from_date DATE,
    to_date DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date)
);

CREATE TABLE IF NOT EXISTS cash_investing(
    company_id SERIAL,
    from_date DATE,
    to_date DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, from_date, to_date)
);

CREATE TABLE IF NOT EXISTS net_cash_and_equivalents(
    company_id SERIAL,
    instant DATE,
    amount BIGINT,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    UNIQUE(company_id, instant)
);


CREATE TABLE IF NOT EXISTS cash_burn_rate(
    company_id SERIAL,
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
    company_id SERIAL,
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
    company_id SERIAL,
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



CREATE TABLE IF NOT EXISTS capital_raise(
    company_id SERIAL,
    shelf_id SERIAL,
    kind VARCHAR(255),
    amount_usd BIGINT,
    form_type VARCHAR(200),
    form_acn VARCHAR(255),
    

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (form_type)
            REFERENCES form_types(form_type)
);

CREATE TABLE IF NOT EXISTS underwriters(
    underwriter_id SERIAL PRIMARY KEY,
    underwriter_name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS underwriters_shelfs(
    shelf_id SERIAL,
    underwriter_id SERIAL,

    CONSTRAINT fk_shelf_id
        FOREIGN KEY (shelf_id)
            REFERENCES shelfs(id),
    CONSTRAINT fk_underwriter_id
        FOREIGN KEY (underwriter_id)
            REFERENCES underwriters(underwriter_id),
)

CREATE TABLE IF NOT EXISTS shelfs(
    id SERIAL PRIMARY KEY,
    company_id SERIAL NOT NULL,
    accn VARCHAR(30) NOT NULL,
    form_type VARCHAR NOT NULL,
    shelf_capacity BIGINT,
    total_amount_raised BIGINT,
    total_amount_raised_unit VARCHAR,
    effect_date DATE,
    last_update DATE,
    expiry DATE,
    filing_date DATE,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (form_type)
            REFERENCES form_types(form_type)
);



CREATE TABLE IF NOT EXISTS offering_status(
    id SERIAL PRIMARY KEY,
    status_name VARCHAR
);
-- tables: shelfs_offerings, offerings_underwriters, offerings_securities, securities, security as json?

CREATE TABLE IF NOT EXISTS offerings(
    id SERIAL PRIMARY KEY,
    company_id SERIAL,
    shelf_id NOT NULL,
    final_offering_amount_usd BIGINT,
    anticipated_offering_amount_usd BIGINT,
    offering_status_name SERIAL,
    commencment_date TIMESTAMP,
    end_date TIMESTAMP,
      
    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_offering_status_id
        FOREIGN KEY (offering_status_name)
            REFERENCES offering_status(status_name)
);


CREATE TABLE IF NOT EXISTS warrants(
    id SERIAL PRIMARY KEY,
    warrant_name VARCHAR(255),
    offering_id SERIAL,
    shelf_id SERIAL,
    acn_number VARCHAR(255),
    amount_usd_equivalent BIGINT,
    amount_issued BIGINT,
    shares_per_unit FLOAT,
    exercise_price FLOAT,
    expiration_date DATE,
    
    CONSTRAINT fk_offering_id
        FOREIGN KEY (offering_id)
            REFERENCES offerings(offering_id),
    CONSTRAINT fk_shelf_id
        FOREIGN KEY (shelf_id)
            REFERENCES shelfs(shelf_id)
);


CREATE TABLE IF NOT EXISTS convertible_note_warrants(
    id SERIAL PRIMARY KEY,
    note_warrant_name VARCHAR(255),
    offering_id SERIAL,
    shelf_id SERIAL,
    exercise_price FLOAT,
    amount_issued BIGINT,
    price_protection INT,
    issue_date DATE,
    exercisable_date DATE,
    last_update DATE,
    additional_notes VARCHAR(1000),

    CONSTRAINT fk_offering_id
        FOREIGN KEY (offering_id)
            REFERENCES offerings(offering_id),
    CONSTRAINT fk_shelf_id
        FOREIGN KEY (shelf_id)
            REFERENCES shelfs(shelf_id)
);

CREATE TABLE IF NOT EXISTS convertible_notes(
    id SERIAL PRIMARY KEY,
    offering_id SERIAL,
    shelf_id SERIAL,

    CONSTRAINT fk_offering_id
        FOREIGN KEY (offering_id)
            REFERENCES offerings(offering_id),
    CONSTRAINT fk_shelf_id
        FOREIGN KEY (shelf_id)
            REFERENCES shelfs(shelf_id)

);

CREATE TABLE IF NOT EXISTS atm(
    id SERIAL PRIMARY KEY,
    offering_id SERIAL,
    shelf_id SERIAL,
    total_capacity BIGINT,
    underwriter_id SERIAL,
    agreement_start_date DATE,

    CONSTRAINT fk_offering_id
        FOREIGN KEY (offering_id)
            REFERENCES offerings(offering_id),
    CONSTRAINT fk_shelf_id
        FOREIGN KEY (shelf_id)
            REFERENCES shelfs(shelf_id),
    CONSTRAINT fk_underwriter_id
      FOREIGN KEY (underwriter_id)
        REFERENCES underwriters(underwriter_id)

);
