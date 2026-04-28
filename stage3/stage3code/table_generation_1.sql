CREATE DATABASE IF NOT EXISTS gonogo;
USE gonogo;

DROP TABLE IF EXISTS visa_req_document;
DROP TABLE IF EXISTS trip_plan;
DROP TABLE IF EXISTS visa_cost;
DROP TABLE IF EXISTS visa_requirement;
DROP TABLE IF EXISTS passport;
DROP TABLE IF EXISTS document;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS country;

CREATE TABLE country (
    country_id CHAR(3) PRIMARY KEY,
    country_name VARCHAR(150),
    region_name VARCHAR(100),
    iso_alpha2 CHAR(2),
    iso_alpha3 CHAR(3),
    iso_numeric SMALLINT
);

CREATE TABLE users (
    user_id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE passport (
    passport_number VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    issuing_country_id CHAR(3) NOT NULL,
    expiry_date DATE,
    created_at DATE,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (issuing_country_id) REFERENCES country(country_id)
);

CREATE TABLE visa_requirement (
    visa_req_id INT AUTO_INCREMENT PRIMARY KEY,
    origin_country_id CHAR(3) NOT NULL,
    destination_country_id CHAR(3) NOT NULL,
    is_evisa BOOLEAN,
    visa_on_arrival BOOLEAN,
    max_stay_days INT,
    last_updated DATE,
    UNIQUE (origin_country_id, destination_country_id),
    FOREIGN KEY (origin_country_id) REFERENCES country(country_id),
    FOREIGN KEY (destination_country_id) REFERENCES country(country_id)
);

CREATE TABLE visa_cost (
    visa_cost_id INT AUTO_INCREMENT PRIMARY KEY,
    origin_country_id CHAR(3) NOT NULL,
    destination_country_id CHAR(3) NOT NULL,
    cost_amount DECIMAL(10,2),
    currency_code CHAR(3),
    last_updated DATE,
    UNIQUE (origin_country_id, destination_country_id),
    FOREIGN KEY (origin_country_id) REFERENCES country(country_id),
    FOREIGN KEY (destination_country_id) REFERENCES country(country_id)
);

CREATE TABLE document (
    doc_id INT AUTO_INCREMENT PRIMARY KEY,
    doc_name VARCHAR(120),
    description VARCHAR(400)
);

CREATE TABLE trip_plan (
    plan_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    passport_number VARCHAR(50) NOT NULL,
    destination_country_id CHAR(3) NOT NULL,
    visa_req_id INT NOT NULL,
    entry_date DATE,
    exit_date DATE,
    purpose VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (passport_number) REFERENCES passport(passport_number),
    FOREIGN KEY (destination_country_id) REFERENCES country(country_id),
    FOREIGN KEY (visa_req_id) REFERENCES visa_requirement(visa_req_id)
);

CREATE TABLE visa_req_document (
    visa_req_id INT NOT NULL,
    doc_id INT NOT NULL,
    is_mandatory BOOLEAN,
    notes VARCHAR(300),
    PRIMARY KEY (visa_req_id, doc_id),
    FOREIGN KEY (visa_req_id) REFERENCES visa_requirement(visa_req_id),
    FOREIGN KEY (doc_id) REFERENCES document(doc_id)
);

LOAD DATA LOCAL INFILE 'data/country_sql.csv'
INTO TABLE country
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
IGNORE 1 LINES
(country_name, region_name, iso_alpha2, @iso3, iso_numeric)
SET country_id = @iso3,
    iso_alpha3 = @iso3;




LOAD DATA LOCAL INFILE 'data/passport-index-tidy-iso3.csv'
INTO TABLE visa_requirement
FIELDS TERMINATED BY ','
IGNORE 1 LINES
(origin_country_id, destination_country_id, @requirement)
SET
    is_evisa = (@requirement = 'e-visa'),
    visa_on_arrival = (@requirement = 'visa on arrival'),
    max_stay_days = IF(@requirement REGEXP '^[0-9]+$', @requirement, NULL),
    last_updated = '2025-01-12';


LOAD DATA LOCAL INFILE 'data/GMP_GlobalVisaCostDataset.csv'
INTO TABLE visa_cost
FIELDS TERMINATED BY '\t'
OPTIONALLY ENCLOSED BY '"'
IGNORE 1 LINES
(
    @source,
    @target,
    origin_country_id,
    destination_country_id,
    @tourist_cost,
    @student_visa,
    @business_visa,
    @work_visa,
    @family_visa,
    @transit_visa,
    @other_visa,
    @source_region,
    @source_subregion,
    @target_region,
    @target_subregion,
    @updated,
    @tourist_perdailyincome,
    @student_perdailyincome,
    @business_perdailyincome,
    @work_perdailyincome,
    @family_perdailyincome,
    @transit_perdailyincome,
    @other_perdailyincome
)
SET
    cost_amount = NULLIF(@tourist_cost, ''),
    currency_code = 'USD',
    last_updated = '2019-01-01';






LOAD DATA LOCAL INFILE 'data/users_fake.csv'
INTO TABLE users
FIELDS TERMINATED BY ','
IGNORE 1 LINES
(user_id, email, password_hash, created_at);


LOAD DATA LOCAL INFILE 'data/passports_fake.csv'
INTO TABLE passport
FIELDS TERMINATED BY ','
IGNORE 1 LINES
(passport_number, user_id, issuing_country_id, expiry_date, created_at);

INSERT INTO document (doc_name, description) VALUES
('Valid Passport',             'Passport with at least 6 months validity beyond the intended stay and at least one blank visa page.'),
('Passport-Size Photographs',  'Two recent color photographs (35x45 mm) against a white background, taken within the last 6 months.'),
('Proof of Accommodation',     'Hotel booking confirmation, rental agreement, or letter of invitation from a host in the destination country.'),
('Return / Onward Ticket',     'Confirmed flight or transport booking showing departure from the destination country.'),
('Bank Statement',             'Personal bank statements for the last 3 months demonstrating sufficient funds for the trip duration.'),
('Travel Insurance',           'Policy covering medical expenses and emergency repatriation for the full duration of the stay.'),
('Visa Application Form',      'Completed and signed official visa application form issued by the destination country embassy or consulate.'),
('Employment Letter',          'Letter from employer confirming leave approval, job title, salary, and length of employment.');




INSERT INTO trip_plan (user_id, passport_number, destination_country_id, visa_req_id, entry_date, exit_date, purpose) VALUES
('jenymitchell43',   'P62208371', 'FRA', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'USA' AND destination_country_id = 'FRA'), '2025-06-10', '2025-06-24', 'tourism'),
('annacooper8',      'P36563711', 'JPN', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'USA' AND destination_country_id = 'JPN'), '2025-07-01', '2025-07-15', 'tourism'),
('michaeltaylor51',  'P15207573', 'DEU', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'GBR' AND destination_country_id = 'DEU'), '2025-08-05', '2025-08-20', 'business'),
('akshayturner157',  'P84151166', 'AUS', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'IND' AND destination_country_id = 'AUS'), '2025-09-12', '2025-09-26', 'study'),
('jenyhill124',      'P07285547', 'CAN', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'KOR' AND destination_country_id = 'CAN'), '2025-10-03', '2025-10-17', 'tourism'),
('jenywilson305',    'P04493170', 'PRT', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'BRA' AND destination_country_id = 'PRT'), '2025-11-20', '2025-11-30', 'family'),
('akshayjohnson174', 'P78825323', 'THA', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'CHN' AND destination_country_id = 'THA'), '2025-05-01', '2025-05-14', 'tourism'),
('akshayedwards487', 'P33792945', 'ESP', (SELECT visa_req_id FROM visa_requirement WHERE origin_country_id = 'MEX' AND destination_country_id = 'ESP'), '2026-01-15', '2026-01-28', 'business');


-- USA → FRA
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='FRA'), 1, 1, 'Valid for 90 days beyond stay'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='FRA'), 4, 1, 'Onward ticket may be checked at border'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='FRA'), 3, 0, 'Recommended — may be requested at entry'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='FRA'), 5, 0, 'Proof of funds may be requested');

-- USA → JPN
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='JPN'), 1, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='JPN'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='JPN'), 3, 0, 'Hotel booking recommended'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='USA' AND destination_country_id='JPN'), 6, 0, 'Strongly recommended');

-- GBR → DEU
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='GBR' AND destination_country_id='DEU'), 1, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='GBR' AND destination_country_id='DEU'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='GBR' AND destination_country_id='DEU'), 3, 0, 'Hotel booking recommended'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='GBR' AND destination_country_id='DEU'), 5, 0, 'Proof of funds may be requested');

-- IND to AUS
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 1, 1, 'Valid for 6 months beyond stay'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 2, 1, '2 photos required for visa application'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 3, 1, 'Hotel or host letter required'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 5, 1, 'Minimum AUD 5,000 or equivalent'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 6, 1, 'Must cover full period of stay'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 7, 1, 'Online application via ImmiAccount'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='IND' AND destination_country_id='AUS'), 8, 0, 'Required if employed');

-- KOR to CAN
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='KOR' AND destination_country_id='CAN'), 1, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='KOR' AND destination_country_id='CAN'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='KOR' AND destination_country_id='CAN'), 3, 1, 'Hotel booking confirmation'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='KOR' AND destination_country_id='CAN'), 5, 0, 'Last 3 months statements'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='KOR' AND destination_country_id='CAN'), 6, 0, 'Recommended');

-- BRA to PRT
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='BRA' AND destination_country_id='PRT'), 1, 1, 'Valid for at least 3 months beyond stay'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='BRA' AND destination_country_id='PRT'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='BRA' AND destination_country_id='PRT'), 3, 0, 'Hotel booking or host letter'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='BRA' AND destination_country_id='PRT'), 5, 0, 'Proof of sufficient funds recommended');

-- CHN to THA
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='CHN' AND destination_country_id='THA'), 1, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='CHN' AND destination_country_id='THA'), 2, 1, '1 photo for VOA form'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='CHN' AND destination_country_id='THA'), 3, 1, 'Hotel booking required for visa on arrival'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='CHN' AND destination_country_id='THA'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='CHN' AND destination_country_id='THA'), 5, 0, 'Min. 10,000 THB cash or equivalent');

-- MEX to ESP
INSERT INTO visa_req_document (visa_req_id, doc_id, is_mandatory, notes)
VALUES
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 1, 1, 'Valid for 3 months beyond intended stay'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 2, 1, '2 photos required'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 3, 1, 'Hotel booking or invitation letter'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 4, 1, NULL),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 5, 1, 'Last 3 months, min. €500/month of stay'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 6, 1, 'Min. €30,000 Schengen-compliant coverage'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 7, 1, 'Spain Schengen visa application form'),
  ((SELECT visa_req_id FROM visa_requirement WHERE origin_country_id='MEX' AND destination_country_id='ESP'), 8, 0, 'Required for employed applicants');