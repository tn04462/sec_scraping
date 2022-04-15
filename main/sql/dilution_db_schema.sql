

CREATE TABLE IF NOT EXISTS files_last_update(
    filing_links_lud DATE,
    submissions_zip_lud DATE,
    companyfacts_zip_lud DATE
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
    description_ VARCHAR(3000),
    
    CONSTRAINT fk_sic
        FOREIGN KEY (sic)
            REFERENCES sics(sic)
);

CREATE TABLE IF NOT EXISTS company_last_update(
    company_id SERIAL,
    outstanding_shares_lud DATE,
    net_cash_and_equivalents_lud DATE,
    cash_burn_rate_lud DATE,
    
    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id)
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

-- check performance with index and without 
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

CREATE TABLE IF NOT EXISTS shelfs(
    shelf_id SERIAL PRIMARY KEY,
    company_id SERIAL,
    acn_number VARCHAR(255) NOT NULL,
    form_type VARCHAR(200) NOT NULL,
    shelf_capacity BIGINT,
    underwriter_id SERIAL,
    total_amount_raised BIGINT,
    total_amount_raised_unit VARCHAR(255),
    effect_date DATE,
    last_update DATE,
    expiry DATE,
    filing_date DATE,

    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_underwriter_id
        FOREIGN KEY (underwriter_id)
            REFERENCES underwriters(underwriter_id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (form_type)
            REFERENCES form_types(form_type)
);



CREATE TABLE IF NOT EXISTS filing_status(
    id SERIAL PRIMARY KEY,
    status_name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS offerings(
    offering_id SERIAL PRIMARY KEY,
    company_id SERIAL,
    acn_number VARCHAR(255) NOT NULL,
    inital_form_type VARCHAR(255) NOT NULL,
    underwriter_id SERIAL,
    final_offering_amount_usd BIGINT,
    anticipated_offering_amount_usd BIGINT,
    filing_status SERIAL,
    filing_date DATE,
      
    CONSTRAINT fk_company_id
        FOREIGN KEY (company_id)
            REFERENCES companies(id),
    CONSTRAINT fk_underwriter_id
        FOREIGN KEY (underwriter_id)
            REFERENCES underwriters(underwriter_id),
    CONSTRAINT fk_filing_status_id
        FOREIGN KEY (filing_status)
            REFERENCES filing_status(id),
    CONSTRAINT fk_form_type
        FOREIGN KEY (inital_form_type)
            REFERENCES form_types(form_type)
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
