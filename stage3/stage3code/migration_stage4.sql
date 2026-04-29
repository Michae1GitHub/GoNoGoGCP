-- ============================================================
-- GoNoGo — Stage 4 Migration
-- Adds: CHECK constraints, audit table, two triggers,
--       and one stored procedure with two advanced queries.
--
-- Apply with:
--   mysql -u root -p gonogo < migration_stage4.sql
-- ============================================================

USE gonogo;

-- ── 1. Audit table (target of the AFTER UPDATE trigger) ──────
DROP TABLE IF EXISTS route_audit;
CREATE TABLE route_audit (
    audit_id                INT AUTO_INCREMENT PRIMARY KEY,
    visa_req_id             INT NOT NULL,
    origin_country_id       CHAR(3) NOT NULL,
    destination_country_id  CHAR(3) NOT NULL,
    old_is_evisa            BOOLEAN,
    new_is_evisa            BOOLEAN,
    old_visa_on_arrival     BOOLEAN,
    new_visa_on_arrival     BOOLEAN,
    old_max_stay_days       INT,
    new_max_stay_days       INT,
    changed_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_route   (origin_country_id, destination_country_id),
    INDEX idx_audit_when    (changed_at DESC)
);

-- ── 2. Tuple/attribute-level CHECK constraints ───────────────
-- (MySQL 8.0+ enforces CHECK; older versions parse but ignore.)
-- Drop first so this script is idempotent (safe to re-run).
DROP PROCEDURE IF EXISTS _drop_check_if_exists;
DELIMITER $$
CREATE PROCEDURE _drop_check_if_exists(IN tbl VARCHAR(64), IN cname VARCHAR(64))
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.CHECK_CONSTRAINTS
        WHERE CONSTRAINT_SCHEMA = DATABASE() AND CONSTRAINT_NAME = cname
    ) THEN
        SET @s = CONCAT('ALTER TABLE `', tbl, '` DROP CHECK `', cname, '`');
        PREPARE stmt FROM @s; EXECUTE stmt; DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;

CALL _drop_check_if_exists('visa_cost',        'chk_cost_nonneg');
CALL _drop_check_if_exists('visa_requirement', 'chk_max_stay_nonneg');
CALL _drop_check_if_exists('trip_plan',        'chk_trip_dates');
DROP PROCEDURE _drop_check_if_exists;

ALTER TABLE visa_cost
    ADD CONSTRAINT chk_cost_nonneg
        CHECK (cost_amount >= 0);

ALTER TABLE visa_requirement
    ADD CONSTRAINT chk_max_stay_nonneg
        CHECK (max_stay_days IS NULL OR max_stay_days >= 0);

ALTER TABLE trip_plan
    ADD CONSTRAINT chk_trip_dates
        CHECK (entry_date IS NULL
            OR exit_date  IS NULL
            OR entry_date <= exit_date);

-- ── 3. Trigger #1 — date validation on trip_plan inserts ─────
DROP TRIGGER IF EXISTS trg_trip_plan_dates;
DELIMITER $$
CREATE TRIGGER trg_trip_plan_dates
BEFORE INSERT ON trip_plan
FOR EACH ROW
BEGIN
    IF NEW.entry_date IS NOT NULL
       AND NEW.exit_date IS NOT NULL
       AND NEW.entry_date > NEW.exit_date THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Trigger: entry_date must be on or before exit_date';
    END IF;
END$$
DELIMITER ;

-- ── 4. Trigger #2 — audit any change to visa_requirement ─────
DROP TRIGGER IF EXISTS trg_visa_req_audit;
DELIMITER $$
CREATE TRIGGER trg_visa_req_audit
AFTER UPDATE ON visa_requirement
FOR EACH ROW
BEGIN
    -- IF condition: only log when something actually changed
    IF NOT (OLD.is_evisa        <=> NEW.is_evisa)
       OR NOT (OLD.visa_on_arrival <=> NEW.visa_on_arrival)
       OR NOT (OLD.max_stay_days   <=> NEW.max_stay_days)
    THEN
        INSERT INTO route_audit (
            visa_req_id, origin_country_id, destination_country_id,
            old_is_evisa, new_is_evisa,
            old_visa_on_arrival, new_visa_on_arrival,
            old_max_stay_days, new_max_stay_days
        )
        VALUES (
            NEW.visa_req_id, NEW.origin_country_id, NEW.destination_country_id,
            OLD.is_evisa, NEW.is_evisa,
            OLD.visa_on_arrival, NEW.visa_on_arrival,
            OLD.max_stay_days, NEW.max_stay_days
        );
    END IF;
END$$
DELIMITER ;

-- ── 5. Stored Procedure — sp_passport_summary ────────────────
-- Two advanced queries, IF/ELSE control structure, application utility.
DROP PROCEDURE IF EXISTS sp_passport_summary;
DELIMITER $$
CREATE PROCEDURE sp_passport_summary(IN uid VARCHAR(100))
BEGIN
    DECLARE v_origin CHAR(3) DEFAULT NULL;

    -- Look up the user's passport country
    SELECT issuing_country_id
      INTO v_origin
      FROM passport
     WHERE user_id = uid
     LIMIT 1;

    -- Control structure: short-circuit when no passport on file
    IF v_origin IS NULL THEN
        SELECT 'no_passport' AS status,
               NULL AS region_name,
               0    AS total_destinations,
               0    AS visa_free_count,
               0    AS evisa_count,
               NULL AS avg_max_stay;
    ELSE
        -- ── Advanced query #1: JOIN + GROUP BY + conditional aggregation ──
        SELECT 'ok'                                                AS status,
               dest.region_name,
               COUNT(*)                                            AS total_destinations,
               SUM(CASE WHEN vr.max_stay_days IS NOT NULL
                        THEN 1 ELSE 0 END)                         AS visa_free_count,
               SUM(CASE WHEN vr.is_evisa = 1
                        THEN 1 ELSE 0 END)                         AS evisa_count,
               ROUND(AVG(vr.max_stay_days), 1)                     AS avg_max_stay
          FROM visa_requirement vr
          JOIN country dest ON vr.destination_country_id = dest.country_id
         WHERE vr.origin_country_id = v_origin
         GROUP BY dest.region_name
         ORDER BY visa_free_count DESC;

        -- ── Advanced query #2: cheapest destination per region ──
        --     correlated subquery (cannot be replaced by a plain JOIN)
        SELECT dest.country_name      AS destination,
               dest.region_name,
               vc.cost_amount
          FROM visa_cost vc
          JOIN country   dest ON vc.destination_country_id = dest.country_id
         WHERE vc.origin_country_id = v_origin
           AND vc.cost_amount = (
               SELECT MIN(vc2.cost_amount)
                 FROM visa_cost vc2
                 JOIN country c2 ON vc2.destination_country_id = c2.country_id
                WHERE vc2.origin_country_id = v_origin
                  AND c2.region_name        = dest.region_name
           )
         ORDER BY vc.cost_amount ASC
         LIMIT 10;
    END IF;
END$$
DELIMITER ;

-- ── Done ─────────────────────────────────────────────────────
SELECT 'Stage 4 migration applied.' AS status;
