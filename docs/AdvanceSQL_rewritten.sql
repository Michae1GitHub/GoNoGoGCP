-- Rewritten advanced SQL queries for the GoNoGo schema
-- Based on table_generation_1.sql
-- Maintains the original query logic, but fixes table/attribute references
-- and uses reusable variables that match the current schema.

USE gonogo;

SET @test_user_id = 'rubyreed907';
SET @test_passport_number = 'P27467099';

-- Speeds up JOIN + filter on visa_cost
CREATE INDEX idx_vc_origin_dest_cost 
    ON visa_cost(origin_country_id, destination_country_id, cost_amount); 
-- query1

-- Speeds up subquery filtering by region_name
CREATE INDEX idx_country_region 
    ON country(region_name); 
-- query1

CREATE INDEX hello
    ON visa_requirement(destination_country_id, origin_country_id, is_evisa, max_stay_days); 
-- query1

CREATE INDEX idx_vr_origin_evisa_stay_2
ON visa_requirement(origin_country_id, is_evisa, max_stay_days); 
-- query2

CREATE INDEX idx_tp_user_passport_visa
ON trip_plan(user_id, passport_number, visa_req_id); -- query2

CREATE INDEX idx_country_id_region
ON country(country_id, region_name); -- query2

CREATE INDEX idx_vrd_req_mandatory
ON visa_req_document(visa_req_id, is_mandatory); 
-- query3

CREATE INDEX cost3
ON visa_cost(origin_country_id, destination_country_id, cost_amount); -- query3

CREATE INDEX visa_req3
ON visa_requirement(origin_country_id, destination_country_id, is_evisa, max_stay_days);

-- Query 1 — Visa Cost Analysis:
-- Destinations with Cheaper Visa Costs than Their Regional Average
-- Concepts: JOIN + Subquery in WHERE

SELECT
    dest.country_name AS destination,
    dest.region_name,
    vr.is_evisa,
    vr.max_stay_days,
    vc.cost_amount,
    vc.currency_code
FROM passport p
JOIN country origin_c
    ON p.issuing_country_id = origin_c.country_id
JOIN visa_requirement vr
    ON vr.origin_country_id = origin_c.country_id
JOIN country dest
    ON vr.destination_country_id = dest.country_id
JOIN visa_cost vc
    ON vc.origin_country_id = origin_c.country_id
   AND vc.destination_country_id = dest.country_id
WHERE p.user_id = @test_user_id
  AND vc.cost_amount < (
        SELECT AVG(vc2.cost_amount)
        FROM visa_cost vc2
        JOIN country c2
            ON vc2.destination_country_id = c2.country_id
        WHERE c2.region_name = dest.region_name
      )
ORDER BY dest.region_name, vc.cost_amount ASC
LIMIT 15;



-- Query 2 — Regional Visa Accessibility:
-- Average Max Stay and E-Visa Availability by Region
-- Concepts: JOIN + UNION + Aggregation + Conditional Aggregation

SELECT
    region_name,
    COUNT(*) AS total_destinations,
    ROUND(AVG(max_stay_days), 1) AS avg_max_stay_days,
    SUM(CASE WHEN is_evisa = FALSE THEN 1 ELSE 0 END) AS no_evisa_count
FROM (
    -- Branch 1: destinations from the user's saved trip plans
    SELECT
        dest.region_name,
        vr.max_stay_days,
        vr.is_evisa
    FROM trip_plan tp
    JOIN passport p
        ON tp.passport_number = p.passport_number
    JOIN visa_requirement vr
        ON tp.visa_req_id = vr.visa_req_id
    JOIN country dest
        ON vr.destination_country_id = dest.country_id
    WHERE tp.user_id = @test_user_id

    UNION

    -- Branch 2: destinations available to the user's passports
    -- with no e-visa required and stay of at least 30 days
    SELECT
        dest.region_name,
        vr.max_stay_days,
        vr.is_evisa
    FROM passport p
    JOIN visa_requirement vr
        ON vr.origin_country_id = p.issuing_country_id
    JOIN country dest
        ON vr.destination_country_id = dest.country_id
    WHERE p.user_id = @test_user_id
      AND vr.is_evisa = FALSE
      AND vr.max_stay_days >= 30
) AS combined
GROUP BY region_name
ORDER BY avg_max_stay_days DESC
LIMIT 15;



-- Query 3 — Visa Complexity Score:
-- Top 15 Most Complex Visa Requirements for a User's Passport
-- Concepts: JOIN + Subqueries in SELECT + Conditional Logic in SELECT

SELECT
    dest.country_name AS destination,
    dest.region_name,
    vr.max_stay_days,
    COALESCE(vc.cost_amount, 0) AS visa_cost,
    (
        SELECT COUNT(*)
        FROM visa_req_document vrd
        WHERE vrd.visa_req_id = vr.visa_req_id
          AND vrd.is_mandatory = TRUE
    ) AS mandatory_doc_count,
    (
        CASE
            WHEN vr.is_evisa = FALSE
             AND COALESCE(vc.cost_amount, 0) = 0 THEN 0
            WHEN vr.is_evisa = TRUE THEN 20
            ELSE 40
        END
        + CASE
            WHEN COALESCE(vc.cost_amount, 0) > 100 THEN 30
            ELSE 10
          END
        + CASE
            WHEN vr.max_stay_days IS NULL
              OR vr.max_stay_days < 30 THEN 20
            ELSE 0
          END
        + CASE
            WHEN (
                SELECT COUNT(*)
                FROM visa_req_document vrd2
                WHERE vrd2.visa_req_id = vr.visa_req_id
                  AND vrd2.is_mandatory = TRUE
            ) > 3 THEN 10
            ELSE 0
          END
    ) AS complexity_score
FROM passport p
JOIN country origin_c
    ON p.issuing_country_id = origin_c.country_id
JOIN visa_requirement vr
    ON vr.origin_country_id = origin_c.country_id
JOIN country dest
    ON vr.destination_country_id = dest.country_id
LEFT JOIN visa_cost vc
    ON vc.origin_country_id = origin_c.country_id
   AND vc.destination_country_id = dest.country_id
WHERE p.passport_number = @test_passport_number
ORDER BY complexity_score DESC
LIMIT 15;
