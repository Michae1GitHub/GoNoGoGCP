# GoNoGo — Stage 4 (Checkpoint 2)

Visa-requirement lookup, trip planning, interactive world map, and
admin route editor. All Stage-4 advanced database features (stored
procedure, transaction with isolation level, two triggers, CHECK
constraints) are wired through the UI.

---

## Quick start

### 1. Install dependencies
```bash
cd app
pip install -r requirements.txt
```

### 2. Configure the database connection
Edit `app.py` and update `DB_CONFIG` with your MySQL credentials:
```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'YOUR_PASSWORD_HERE',
    'database': 'gonogo',
    'port': 3306,
}
```

### 3. Apply the schema and Stage-4 migration
```bash
# Base schema + data load (from project root)
mysql -u root -p < ../stage3/stage3code/table_generation_1.sql

# Stage-4: triggers, stored procedure, CHECK constraints, audit table
mysql -u root -p gonogo < migration_stage4.sql
```
The migration is idempotent — safe to re-run.

### 4. Seed the developer accounts
```bash
python3 seed.py
```
Creates `jenys2 / johnw14 / zhiyunl3 / akshay11` with password
`password12138` and a default USA passport on each account.

### 5. Run the app
```bash
python3 app.py
```
Opens on [http://localhost:5001](http://localhost:5001).

---

## Stage-4 feature → page → API map

| Stage-4 requirement | UI location | Backing API |
|---|---|---|
| **Read** a route | Admin → Visa Route Editor → Look up | `GET  /api/admin/route` |
| **Create / Update** a route (transactional) | Admin → Visa Route Editor → Save Route | `PUT  /api/admin/route` |
| **Delete** a route | Admin → Visa Route Editor → Delete Route | `DELETE /api/admin/route` |
| **Keyword search** (countries) | Dashboard → "🔎 Country Keyword Search" | `GET  /api/search/countries?q=…` |
| **Stored procedure** `sp_passport_summary` | Admin → "📦 Stored Procedure" → Run | `POST /api/admin/passport-summary` |
| **Trigger output** `route_audit` | Admin → "🛎 Trigger Output" | `GET  /api/admin/route-audit` |
| **Visa map** (creative component) | Visa Map page | `GET  /api/analytics/visa-map` |
| **Three advanced queries** | Visa Map page side panel | `/api/analytics/budget`, `/regional`, `/complexity` |

Trigger `trg_trip_plan_dates` fires on the dashboard's **Save Trip**
flow when entry/exit dates are reversed; CHECK constraints fire on any
write that violates them.

---

## REST API reference

### Auth & users
| Method | Endpoint | Description |
|---|---|---|
| POST   | `/api/login`               | Login with `user_id` + `password` |
| POST   | `/api/register`            | Register a new account + passport |
| POST   | `/api/logout`              | Clear session |
| GET    | `/api/me`                  | Current user + passport |
| PUT    | `/api/me/passport`         | Update the current user's passport country |
| GET    | `/api/users?search=&limit=` | Admin: list/search users |
| POST   | `/api/users`               | Admin: create user |
| PUT    | `/api/users/<id>`          | Admin: update user email |
| DELETE | `/api/users/<id>`          | Admin: delete user (blocked if linked passports) |

### Countries, visa lookup, trips
| Method | Endpoint | Description |
|---|---|---|
| GET    | `/api/countries`                              | All countries (for dropdowns) |
| GET    | `/api/visa?origin=XXX&destination=YYY`        | Visa requirement + documents for a route |
| GET    | `/api/passports`                              | Current user's passports |
| GET    | `/api/trips`                                  | Current user's saved trips |
| POST   | `/api/trips`                                  | Save a trip plan (fires `trg_trip_plan_dates`) |
| DELETE | `/api/trips/<plan_id>`                        | Remove a trip |

### Stage-4 advanced features
| Method | Endpoint | Description |
|---|---|---|
| GET    | `/api/admin/route?origin=X&destination=Y`     | Read a visa route |
| PUT    | `/api/admin/route`                            | Upsert visa route (transactional, fires `trg_visa_req_audit`) |
| DELETE | `/api/admin/route?origin=X&destination=Y`     | Delete a visa route + cost |
| POST   | `/api/admin/passport-summary`                 | Call `sp_passport_summary(uid)` |
| GET    | `/api/admin/route-audit?limit=N`              | Read trigger output from `route_audit` |
| GET    | `/api/search/countries?q=…`                   | Keyword search |

### Analytics (Stage-3 advanced queries)
| Method | Endpoint | Description |
|---|---|---|
| GET    | `/api/analytics/visa-map`     | Visa status per destination + ISO mapping |
| GET    | `/api/analytics/budget`       | Q1 — destinations cheaper than regional avg |
| GET    | `/api/analytics/regional`     | Q2 — visa-free access by region (UNION + GROUP BY) |
| GET    | `/api/analytics/complexity`   | Q3 — top-15 hardest visa routes |

### Health
| Method | Endpoint | Description |
|---|---|---|
| GET    | `/api/ping`                                   | DB connectivity check |
