# GoNoGo
Developer: Zhiyun Liu, Akshay Akhileshwaran, Jeny Sheng, John Wang
Public Application Website: https://gonogo-513554228020.us-east4.run.app  Hosted via Google Cloud

A visa-requirement lookup and travel-planning app. Pick your passport
country, look up visa requirements for any destination, save trips,
explore an interactive world map, and (as an admin) edit the underlying
visa-route data.

> Stage 4 submission. All Stage 4 advanced database features
> (stored procedure, transaction, two triggers, CHECK constraints) are
> wired through the Flask UI.

---

## Repository layout

```
.
├── app/                              # Flask application
│   ├── app.py                        # All routes + REST API
│   ├── seed.py                       # Seeds the 4 developer accounts
│   ├── migration_stage4.sql          # Stage-4 advanced DB features
│   ├── requirements.txt              # Python deps
│   ├── README.md                     # How to run the app
│   └── templates/                    # Jinja templates (dashboard, visa map, admin, …)
├── docs/
│   ├── project_proposal.md
│   ├── GoNoGo-Stage2.pdf             # ER diagram + relational schema
│   ├── APP Sturecture.pdf            # System architecture
│   ├── UI-mockup.jpg
│   ├── AdvanceSQL_rewritten.sql      # Stage-3 three advanced queries (with indexes)
│   ├── migration_stage4.sql          # Mirror of app/migration_stage4.sql
│   └── stage4_advanced_features.md   # ★ Procedure + triggers + transaction reference
├── stage3/
│   ├── stage3code/                   # Schema + data ETL scripts (table_generation_1.sql, …)
│   ├── stage2_revisions.pdf
│   └── Part 2- Indexing.pdf
└── README.md                         # (this file)
```

---

## Quick start (grader instructions)

### 1. Database

```bash
cd stage3/stage3code
mysql -u root -p < table_generation_1.sql        # schema + base data load
cd ../../app
mysql -u root -p gonogo < migration_stage4.sql   # Stage-4: triggers, procedure, CHECK constraints
```

### 2. Application

```bash
cd app
pip install -r requirements.txt
python3 seed.py                                  # creates the 4 dev accounts
python3 app.py                                   # serves on http://localhost:5001
```

Open [http://localhost:5001](http://localhost:5001).

### 3. Login

Any of `jenys2 / johnw14 / zhiyunl3 / akshay11`, password
`password12138`. All four are flagged as developers and can access the
Admin panel.

---

## Where each Stage-4 requirement lives

| Requirement | File / route | UI entry point |
|---|---|---|
| **CRUD on `visa_requirement` (non-user table)** | `app.py` — `admin_get_route`, `admin_update_route`, `admin_delete_route` | Admin → "🛂 Visa Route Editor" |
| **Keyword search** | `app.py` — `search_countries` (`/api/search/countries`) | Dashboard → "🔎 Country Keyword Search" card |
| **Stored procedure (`sp_passport_summary`)** | `app/migration_stage4.sql` § 5 | Admin → "📦 Stored Procedure" card |
| **Transaction with isolation level** | `app.py` — `admin_update_route` (`SET TRANSACTION ISOLATION LEVEL READ COMMITTED`) | Admin → Save Route |
| **Trigger #1 — `trg_trip_plan_dates`** | `app/migration_stage4.sql` § 3 | Dashboard → Save Trip with bad dates |
| **Trigger #2 — `trg_visa_req_audit`** | `app/migration_stage4.sql` § 4 | Admin → Save Route → "🛎 Trigger Output" card |
| **CHECK constraints** | `app/migration_stage4.sql` § 2 (`chk_cost_nonneg`, `chk_max_stay_nonneg`, `chk_trip_dates`) | Enforced on every INSERT / UPDATE |
| **Three advanced SQL queries (Stage-3 carry-over)** | `app.py` — `analytics_budget`, `analytics_regional`, `analytics_complexity` | Visa Map page → side panel buttons |
| **Creative component** | `app/templates/analytics.html` — interactive d3 + topojson world map | Visa Map page |

A single rubric-friendly reference for the advanced features lives at
[`docs/stage4_advanced_features.md`](docs/stage4_advanced_features.md).

---

## Tech stack

- **Backend:** Python 3, Flask, mysql-connector-python (raw SQL — **no ORM**)
- **Database:** MySQL 8.0+
- **Frontend:** Vanilla HTML + CSS, d3 v7 + topojson-client for the world map

---

## Team

See `TeamInfo.md`.
