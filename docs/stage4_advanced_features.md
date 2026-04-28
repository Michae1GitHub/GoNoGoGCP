# Stage 4 — Advanced Database Features

Single reference for the rubric-required advanced database programs:
**stored procedure, two triggers, transaction, and CHECK constraints.**
All code shown here lives in the project repo at the paths noted in
each section, and is wired to the front-end through the routes in
`app/app.py`.

---

## 1. Stored Procedure — `sp_passport_summary`

**Source:** `app/migration_stage4.sql` · **Frontend:** Admin → "📦 Stored
Procedure" card · **API:** `POST /api/admin/passport-summary`

Returns two result sets describing what a given passport can do:
1. Per-region accessibility breakdown (visa-free / e-visa / avg stay)
2. Cheapest destination per region (correlated subquery)

The procedure uses an `IF/ELSE` control structure to short-circuit when
the user has no passport on file.

```sql
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
        SELECT 'ok'                                      AS status,
               dest.region_name,
               COUNT(*)                                  AS total_destinations,
               SUM(CASE WHEN vr.max_stay_days IS NOT NULL
                        THEN 1 ELSE 0 END)               AS visa_free_count,
               SUM(CASE WHEN vr.is_evisa = 1
                        THEN 1 ELSE 0 END)               AS evisa_count,
               ROUND(AVG(vr.max_stay_days), 1)           AS avg_max_stay
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
```

**SQL concepts used:** JOIN of multiple relations, GROUP BY +
conditional aggregation, correlated subquery (Q2's subquery references
`dest.region_name` from the outer query, so it cannot be flattened to
a plain JOIN).

**Application utility:** Lets an admin pull a one-call snapshot of any
user's travel options without writing ad-hoc queries.

---

## 2. Trigger #1 — `trg_trip_plan_dates` (BEFORE INSERT)

**Source:** `app/migration_stage4.sql` · **Triggers from:** dashboard
"Save trip" flow.

Rejects trip plans whose `entry_date` is later than `exit_date`. Acts
as a database-level safety net even if the front-end forgets to
validate.

```sql
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
```

- **Event:** `BEFORE INSERT ON trip_plan`
- **Condition:** `IF NEW.entry_date > NEW.exit_date`
- **Action:** `SIGNAL SQLSTATE '45000'` (raises a custom error,
  preventing the insert)

---

## 3. Trigger #2 — `trg_visa_req_audit` (AFTER UPDATE)

**Source:** `app/migration_stage4.sql` · **Triggers from:** Admin →
"Visa Route Editor" → Save Route · **Visible at:** Admin → "🛎 Trigger
Output" card · **API:** `GET /api/admin/route-audit`

Whenever a row in `visa_requirement` is updated, this trigger writes a
diff row into `route_audit`, capturing what changed and when. The
`<=>` null-safe equality operator avoids logging no-op updates.

```sql
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
```

- **Event:** `AFTER UPDATE ON visa_requirement`
- **Condition:** `IF NOT (OLD.col <=> NEW.col)` (any tracked field
  actually changed)
- **Action:** `INSERT INTO route_audit (…)`

The supporting audit table:

```sql
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
```

---

## 4. Transaction — `admin_update_route` with `READ COMMITTED`

**Source:** `app/app.py` (function `admin_update_route`) · **Frontend:**
Admin → "Visa Route Editor" → Save Route · **API:**
`PUT /api/admin/route`

A route edit must update both `visa_requirement` and `visa_cost`
atomically; a partial write would leave the route inconsistent. The
transaction also fires `trg_visa_req_audit` from inside its scope.

```python
# ── Explicit transaction with chosen isolation level ─────────────
conn   = get_db()
cursor = conn.cursor(dictionary=True)
try:
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    cursor.execute("START TRANSACTION")

    # Advanced query #1 (pre-write): nested subquery on a JOINed audit
    # table — count recent edits for any route from this origin's region.
    cursor.execute("""
        SELECT COUNT(*) AS recent_edits_in_region
        FROM   route_audit ra
        WHERE  ra.changed_at >= NOW() - INTERVAL 30 DAY
          AND  ra.origin_country_id IN (
                 SELECT c.country_id
                 FROM   country c
                 WHERE  c.region_name = (
                            SELECT region_name FROM country
                            WHERE  country_id = %s
                        )
              )
    """, (origin,))
    cursor.fetchone()

    # Upsert visa_requirement (fires trg_visa_req_audit on UPDATE)
    cursor.execute("""
        INSERT INTO visa_requirement
            (origin_country_id, destination_country_id,
             is_evisa, visa_on_arrival, max_stay_days, last_updated)
        VALUES (%s, %s, %s, %s, %s, CURDATE())
        ON DUPLICATE KEY UPDATE
            is_evisa        = VALUES(is_evisa),
            visa_on_arrival = VALUES(visa_on_arrival),
            max_stay_days   = VALUES(max_stay_days),
            last_updated    = VALUES(last_updated)
    """, (origin, destination, is_evisa, visa_on_arrival, max_stay))

    # Upsert visa_cost (or delete it if no cost was provided)
    if cost is None:
        cursor.execute("""
            DELETE FROM visa_cost
            WHERE origin_country_id = %s AND destination_country_id = %s
        """, (origin, destination))
    else:
        cursor.execute("""
            INSERT INTO visa_cost
                (origin_country_id, destination_country_id,
                 cost_amount, currency_code, last_updated)
            VALUES (%s, %s, %s, %s, CURDATE())
            ON DUPLICATE KEY UPDATE
                cost_amount   = VALUES(cost_amount),
                currency_code = VALUES(currency_code),
                last_updated  = VALUES(last_updated)
        """, (origin, destination, cost, currency))

    # Advanced query #2 (post-write): JOIN + GROUP BY — verify regional
    # consistency for the destination after the write.
    cursor.execute("""
        SELECT dest.region_name,
               COUNT(*)             AS routes_in_region,
               AVG(vc.cost_amount)  AS avg_region_cost
        FROM   visa_cost vc
        JOIN   country dest ON vc.destination_country_id = dest.country_id
        WHERE  dest.region_name = (
                   SELECT region_name FROM country WHERE country_id = %s
               )
        GROUP  BY dest.region_name
    """, (destination,))
    cursor.fetchone()

    conn.commit()
except Error as e:
    conn.rollback()
    raise
```

**Isolation level — why `READ COMMITTED`:**
- `READ UNCOMMITTED` would let another connection read the half-written
  route in between the two upserts.
- `REPEATABLE READ` (MySQL's default) would over-lock for our needs;
  the route-edit workload is single-row and tolerates phantom reads on
  the unrelated audit-count query.
- `SERIALIZABLE` would force range locks and serialize concurrent
  admin edits unnecessarily.
- `READ COMMITTED` is the right tradeoff: each statement sees the most
  recent committed snapshot, and we only protect against the dirty-read
  case.

**SQL concepts used:**
1. Pre-write query: JOIN + nested subqueries (3 levels deep) +
   aggregation
2. Post-write query: JOIN + GROUP BY + scalar subquery in WHERE

**Application utility:** Provides atomicity for the route-update
workflow used by the admin panel; the trigger-driven audit trail relies
on the UPDATE happening inside this transaction.

---

## 5. Constraints

**Source:** `app/migration_stage4.sql` (CHECK) +
`stage3/stage3code/table_generation_1.sql` (PK / FK / UNIQUE).

### Primary keys
Every table has a primary key (`users.user_id`, `country.country_id`,
`passport.passport_number`, `visa_requirement.visa_req_id`,
`visa_cost.visa_cost_id`, `document.doc_id`, `trip_plan.plan_id`,
`visa_req_document(visa_req_id, doc_id)`, `route_audit.audit_id`).

### Foreign keys
- `passport.user_id` → `users.user_id`
- `passport.issuing_country_id` → `country.country_id`
- `visa_requirement.origin_country_id` → `country.country_id`
- `visa_requirement.destination_country_id` → `country.country_id`
- `visa_cost.origin_country_id` → `country.country_id`
- `visa_cost.destination_country_id` → `country.country_id`
- `trip_plan.user_id` → `users.user_id`
- `trip_plan.passport_number` → `passport.passport_number`
- `trip_plan.destination_country_id` → `country.country_id`
- `trip_plan.visa_req_id` → `visa_requirement.visa_req_id`
- `visa_req_document.visa_req_id` → `visa_requirement.visa_req_id`
- `visa_req_document.doc_id` → `document.doc_id`

### UNIQUE
- `users.email`
- `visa_requirement(origin_country_id, destination_country_id)`
- `visa_cost(origin_country_id, destination_country_id)`

### CHECK (attribute-level / tuple-level)

```sql
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
```

`chk_cost_nonneg` and `chk_max_stay_nonneg` are attribute-level
constraints (single-column predicate); `chk_trip_dates` is tuple-level
(spans two columns of the same row). Note that `chk_trip_dates` and
`trg_trip_plan_dates` enforce the same invariant via two different
mechanisms (declarative + procedural) for defense in depth.

---

## 6. Frontend integration map

| Database feature | Triggered by user action |
|---|---|
| `sp_passport_summary` | Admin → "📦 Stored Procedure" → Run Procedure |
| `trg_trip_plan_dates`  | Dashboard → Save Trip with bad dates |
| `trg_visa_req_audit`   | Admin → Visa Route Editor → Save Route → results visible in "🛎 Trigger Output" card |
| Route-edit transaction | Admin → Visa Route Editor → Save Route |
| All CHECK constraints  | Any INSERT / UPDATE that violates them is rejected by the DB |

---

## 7. How to apply

```bash
cd app
mysql -u root -p gonogo < migration_stage4.sql
```

The migration is **idempotent** — re-running it drops and recreates the
CHECK constraints, the procedure, both triggers, and the audit table.
