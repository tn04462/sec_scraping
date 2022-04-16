CREATE TABLE IF NOT EXISTS items8k(
    id SERIAL PRIMARY KEY,
    item_name VARCHAR(200) UNIQUE
);

CREATE TABLE IF NOT EXISTS form8k(
    cik VARCHAR(20),
    item_id SERIAL,
    content TEXT NOT NULL,
    
    CONSTRAINT fk_item_id
        FOREIGN KEY (item_id)
            REFERENCES items8k(id)
);