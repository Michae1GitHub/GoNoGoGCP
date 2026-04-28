"""
GoNoGo — Visa Requirement Lookup Application
CS411 Team-046 (lateBloomers) | Stage 4 Checkpoint 1
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from mysql.connector import Error
import hashlib
import random
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'gonogo-cs411-secret-2026'

INSTANCE_CONNECTION_NAME = os.environ.get("INSTANCE_CONNECTION_NAME")

DB_CONFIG = {
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASS", ""),
    "database": os.environ.get("DB_NAME", "gonogo"),
}

if INSTANCE_CONNECTION_NAME:
    DB_CONFIG["unix_socket"] = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
else:
    DB_CONFIG["host"] = os.environ.get("DB_HOST", "localhost")
    DB_CONFIG["port"] = int(os.environ.get("DB_PORT", 3306))

DEVELOPERS = {'jenys2', 'johnw14', 'zhiyunl3', 'akshay11'}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def serialize(row):
    for k, v in row.items():
        if isinstance(v, datetime):
            row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        elif hasattr(v, 'isoformat'):
            row[k] = str(v)
    return row


def is_dev():
    return session.get('user_id') in DEVELOPERS


# Default supporting-document set used whenever a visa is required and the
# DB has no document rows for the route.  Visa-free routes get an empty list.
DEFAULT_DOCS_COMMON = [
    'Valid passport',
    'Accommodation booking',
    'Trip itinerary',
    'Round-trip flight ticket',
    'Travel insurance',
    'Recent passport-size photo',
    '3-month bank statement',
    'Lease or utility bill',
]
# Extra documents only required for the strictest "Visa Required" routes.
DEFAULT_DOCS_REQUIRED_EXTRA = [
    'Family status / civil documents',
    'Proof of current employment',
]


def default_docs_for(is_evisa, visa_on_arrival, max_stay_days):
    """Return the synthetic document list for a route based on its visa type."""
    # Visa-free → no paperwork
    if max_stay_days is not None:
        return []
    docs = [{'doc_name': name, 'is_mandatory': 1, 'notes': None}
            for name in DEFAULT_DOCS_COMMON]
    # Visa Required (i.e. not e-visa, not visa-on-arrival, not visa-free)
    if not is_evisa and not visa_on_arrival:
        docs.extend({'doc_name': name, 'is_mandatory': 1, 'notes': None}
                    for name in DEFAULT_DOCS_REQUIRED_EXTRA)
    return docs


# ── Page routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html',
                           user_id=session['user_id'],
                           email=session.get('email', ''),
                           is_developer=is_dev())


@app.route('/admin')
def admin():
    if not is_dev():
        return render_template('access_denied.html'), 403
    return render_template('admin.html', user_id=session['user_id'], is_developer=True)


@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('analytics.html',
                           user_id=session['user_id'],
                           is_developer=is_dev())


# ── Auth API ──────────────────────────────────────────────────────────────────

@app.route('/api/login', methods=['POST'])
def login():
    data     = request.get_json()
    user_id  = (data.get('user_id') or '').strip()
    password = data.get('password', '')

    if not user_id or not password:
        return jsonify({'error': 'User ID and password are required'}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, email, password_hash FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        return jsonify({'error': 'User not found'}), 401
    if user['password_hash'] != pw_hash:
        return jsonify({'error': 'Incorrect password'}), 401

    session['user_id'] = user['user_id']
    session['email']   = user['email']

    dest = '/admin' if user['user_id'] in DEVELOPERS else '/dashboard'
    return jsonify({'message': 'Login successful', 'redirect': dest,
                    'is_developer': user['user_id'] in DEVELOPERS})


@app.route('/api/register', methods=['POST'])
def register():
    data               = request.get_json()
    user_id            = (data.get('user_id') or '').strip()
    email              = (data.get('email') or '').strip()
    password           = data.get('password', '')
    passport_country   = (data.get('passport_country') or '').strip()

    if not all([user_id, email, password, passport_country]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    pnum    = f"P{random.randint(10000000, 99999999)}"

    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (user_id, email, password_hash) VALUES (%s, %s, %s)",
                       (user_id, email, pw_hash))
        cursor.execute(
            "INSERT INTO passport (passport_number, user_id, issuing_country_id, expiry_date, created_at) "
            "VALUES (%s, %s, %s, '2035-01-01', CURDATE())",
            (pnum, user_id, passport_country))
        conn.commit()
        cursor.close()
        conn.close()
        session['user_id'] = user_id
        session['email']   = email
        return jsonify({'message': 'Account created!', 'redirect': '/dashboard'}), 201
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'User ID or email already taken'}), 400
        return jsonify({'error': str(e)}), 400


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'redirect': '/'})


# ── Current user info ─────────────────────────────────────────────────────────

@app.route('/api/me')
def get_me():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.passport_number, c.country_id, c.country_name AS passport_country, p.expiry_date
        FROM passport p
        JOIN country c ON p.issuing_country_id = c.country_id
        WHERE p.user_id = %s
        LIMIT 1
    """, (session['user_id'],))
    passport = cursor.fetchone()
    if passport:
        serialize(passport)
    cursor.close()
    conn.close()
    return jsonify({
        'user_id':      session['user_id'],
        'email':        session.get('email', ''),
        'passport':     passport,
        'is_developer': is_dev()
    })


@app.route('/api/me/passport', methods=['PUT'])
def update_my_passport():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data              = request.get_json()
    new_country       = (data.get('passport_country') or '').strip()
    if not new_country:
        return jsonify({'error': 'Passport country is required'}), 400

    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT passport_number FROM passport WHERE user_id = %s LIMIT 1",
                       (session['user_id'],))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE passport SET issuing_country_id = %s WHERE passport_number = %s",
                           (new_country, row[0]))
        else:
            pnum = f"P{random.randint(10000000, 99999999)}"
            cursor.execute(
                "INSERT INTO passport (passport_number, user_id, issuing_country_id, expiry_date, created_at) "
                "VALUES (%s, %s, %s, '2035-01-01', CURDATE())",
                (pnum, session['user_id'], new_country))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Passport updated!'})
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


# ── Countries & Visa Lookup ───────────────────────────────────────────────────

@app.route('/api/ping')
def ping():
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM country")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({'status': 'ok', 'country_count': count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/countries')
def get_countries():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT country_id, country_name FROM country ORDER BY country_name")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route('/api/visa')
def lookup_visa():
    origin      = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    if not origin or not destination:
        return jsonify({'error': 'Both origin and destination are required'}), 400

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT vr.visa_req_id,
               c1.country_name AS origin_country, c1.country_id AS origin_id,
               c2.country_name AS destination_country, c2.country_id AS destination_id,
               vr.is_evisa, vr.visa_on_arrival, vr.max_stay_days,
               vc.cost_amount, vc.currency_code
        FROM visa_requirement vr
        JOIN country c1 ON vr.origin_country_id      = c1.country_id
        JOIN country c2 ON vr.destination_country_id = c2.country_id
        LEFT JOIN visa_cost vc
               ON vc.origin_country_id      = vr.origin_country_id
              AND vc.destination_country_id = vr.destination_country_id
        WHERE vr.origin_country_id = %s AND vr.destination_country_id = %s
    """, (origin, destination))
    result = cursor.fetchone()

    docs = []
    if result:
        cursor.execute("""
            SELECT d.doc_name, vrd.is_mandatory, vrd.notes
            FROM visa_req_document vrd
            JOIN document d ON vrd.doc_id = d.doc_id
            WHERE vrd.visa_req_id = %s
            ORDER BY vrd.is_mandatory DESC, d.doc_name
        """, (result['visa_req_id'],))
        docs = cursor.fetchall()

    cursor.close()
    conn.close()

    if not result:
        return jsonify({'error': 'No visa requirement data found for this route'}), 404

    is_visa_free = result['max_stay_days'] is not None

    # Update #1 — visa-free routes never carry a fee
    if is_visa_free:
        result['cost_amount']   = 0.0
        result['currency_code'] = result.get('currency_code') or 'USD'
        result['is_free']       = True
    else:
        result['is_free'] = False
        if result.get('cost_amount') is not None:
            result['cost_amount'] = float(result['cost_amount'])

    # Update #2 — if the route needs a visa but has no paperwork on file,
    # synthesise the standard document list so every visa-needed route shows
    # something useful.
    if not docs and not is_visa_free:
        docs = default_docs_for(
            bool(result.get('is_evisa')),
            bool(result.get('visa_on_arrival')),
            result.get('max_stay_days'),
        )

    result['documents'] = docs
    return jsonify(result)


# ── Trips ─────────────────────────────────────────────────────────────────────

@app.route('/api/passports')
def get_passports():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.passport_number, c.country_name AS issuing_country,
               c.country_id, p.expiry_date
        FROM passport p
        JOIN country c ON p.issuing_country_id = c.country_id
        WHERE p.user_id = %s
    """, (session['user_id'],))
    rows = cursor.fetchall()
    for r in rows:
        serialize(r)
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route('/api/trips')
def get_trips():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT tp.plan_id, tp.entry_date, tp.exit_date, tp.purpose, tp.created_at,
               c.country_name        AS destination,
               origin_c.country_name AS passport_country,
               vr.is_evisa, vr.visa_on_arrival, vr.max_stay_days
        FROM trip_plan tp
        JOIN country c        ON tp.destination_country_id = c.country_id
        JOIN passport p       ON tp.passport_number = p.passport_number
        JOIN country origin_c ON p.issuing_country_id = origin_c.country_id
        JOIN visa_requirement vr ON tp.visa_req_id = vr.visa_req_id
        WHERE tp.user_id = %s
        ORDER BY tp.created_at DESC
    """, (session['user_id'],))
    rows = cursor.fetchall()
    for r in rows:
        serialize(r)
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route('/api/trips', methods=['POST'])
def save_trip():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data                   = request.get_json()
    passport_number        = data.get('passport_number')
    destination_country_id = data.get('destination_country_id')
    visa_req_id            = data.get('visa_req_id')
    entry_date             = data.get('entry_date') or None
    exit_date              = data.get('exit_date') or None
    purpose                = data.get('purpose', 'tourism')

    if not all([passport_number, destination_country_id, visa_req_id]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO trip_plan
                (user_id, passport_number, destination_country_id, visa_req_id, entry_date, exit_date, purpose)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session['user_id'], passport_number, destination_country_id,
              visa_req_id, entry_date, exit_date, purpose))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Trip saved!'}), 201
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


@app.route('/api/trips/<int:plan_id>', methods=['DELETE'])
def delete_trip(plan_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trip_plan WHERE plan_id = %s AND user_id = %s",
                   (plan_id, session['user_id']))
    conn.commit()
    deleted = cursor.rowcount
    cursor.close()
    conn.close()
    return jsonify({'message': 'Trip removed'}) if deleted else (jsonify({'error': 'Not found'}), 404)


# ── Admin — User CRUD ─────────────────────────────────────────────────────────

@app.route('/api/users')
def get_users():
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    search = request.args.get('search', '')
    limit  = request.args.get('limit', 20, type=int)
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    if search:
        cursor.execute(
            "SELECT user_id, email, created_at FROM users "
            "WHERE user_id LIKE %s OR email LIKE %s ORDER BY created_at DESC LIMIT %s",
            (f'%{search}%', f'%{search}%', limit))
    else:
        cursor.execute(
            "SELECT user_id, email, created_at FROM users ORDER BY created_at DESC LIMIT %s",
            (limit,))
    rows = cursor.fetchall()
    for r in rows:
        serialize(r)
    cursor.close()
    conn.close()
    return jsonify(rows)


@app.route('/api/users', methods=['POST'])
def create_user():
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    data     = request.get_json()
    user_id  = (data.get('user_id') or '').strip()
    email    = (data.get('email') or '').strip()
    password = data.get('password', '')
    if not user_id or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (user_id, email, password_hash) VALUES (%s, %s, %s)",
                       (user_id, email, pw_hash))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'User created', 'user_id': user_id}), 201
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    data      = request.get_json()
    new_email = (data.get('email') or '').strip()
    if not new_email:
        return jsonify({'error': 'Email required'}), 400
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET email = %s WHERE user_id = %s", (new_email, user_id))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'User updated'})
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


@app.route('/api/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    conn   = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM passport WHERE user_id = %s", (user_id,))
        if cursor.fetchone()[0] > 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'User has linked passports — delete those first'}), 400
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'User not found'}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'User deleted'})
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


# ── Admin — Visa Route Editor ────────────────────────────────────────────────

@app.route('/api/admin/route')
def admin_get_route():
    """Fetch the full visa-route record (visa_requirement + visa_cost) for an
    origin/destination pair so the admin UI can pre-fill the edit form."""
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    origin      = (request.args.get('origin') or '').strip()
    destination = (request.args.get('destination') or '').strip()
    if not origin or not destination:
        return jsonify({'error': 'origin and destination required'}), 400

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT vr.visa_req_id,
               c1.country_id   AS origin_id,    c1.country_name AS origin_country,
               c2.country_id   AS destination_id, c2.country_name AS destination_country,
               vr.is_evisa, vr.visa_on_arrival, vr.max_stay_days, vr.last_updated,
               vc.visa_cost_id, vc.cost_amount, vc.currency_code
        FROM visa_requirement vr
        JOIN country c1 ON vr.origin_country_id      = c1.country_id
        JOIN country c2 ON vr.destination_country_id = c2.country_id
        LEFT JOIN visa_cost vc
               ON vc.origin_country_id      = vr.origin_country_id
              AND vc.destination_country_id = vr.destination_country_id
        WHERE vr.origin_country_id = %s AND vr.destination_country_id = %s
    """, (origin, destination))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({'error': 'No visa route exists for this pair'}), 404
    if row.get('cost_amount') is not None:
        row['cost_amount'] = float(row['cost_amount'])
    serialize(row)
    return jsonify(row)


@app.route('/api/admin/route', methods=['PUT'])
def admin_update_route():
    """Upsert visa_requirement + visa_cost for an origin/destination pair.
    Body fields: origin, destination, is_evisa, visa_on_arrival, max_stay_days,
    cost_amount, currency_code."""
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403

    data        = request.get_json() or {}
    origin      = (data.get('origin') or '').strip()
    destination = (data.get('destination') or '').strip()
    if not origin or not destination:
        return jsonify({'error': 'origin and destination required'}), 400

    # Booleans
    is_evisa        = 1 if data.get('is_evisa')        in (True, 1, '1', 'true', 'True') else 0
    visa_on_arrival = 1 if data.get('visa_on_arrival') in (True, 1, '1', 'true', 'True') else 0
    # Optional numerics
    max_stay = data.get('max_stay_days')
    if max_stay in ('', None):
        max_stay = None
    else:
        try:    max_stay = int(max_stay)
        except (ValueError, TypeError):
            return jsonify({'error': 'max_stay_days must be an integer'}), 400

    cost = data.get('cost_amount')
    if cost in ('', None):
        cost = None
    else:
        try:    cost = float(cost)
        except (ValueError, TypeError):
            return jsonify({'error': 'cost_amount must be a number'}), 400
    currency = (data.get('currency_code') or 'USD').strip()[:3] or 'USD'

    # ── Explicit transaction with chosen isolation level ─────────────
    # The two writes (visa_requirement + visa_cost) must succeed or fail
    # together; the AFTER UPDATE trigger fires inside this transaction.
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
                                SELECT region_name FROM country WHERE country_id = %s
                            )
                  )
        """, (origin,))
        cursor.fetchone()  # consumed; available for logging if desired

        # Upsert visa_requirement (fires trg_visa_req_audit when this is an UPDATE)
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
        cursor.close()
        conn.close()
        return jsonify({'message': 'Route saved (transactional)'})
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


@app.route('/api/admin/route', methods=['DELETE'])
def admin_delete_route():
    """Delete a visa route + its visa_cost row. Completes CRUD on visa_requirement."""
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    origin      = (request.args.get('origin') or '').strip()
    destination = (request.args.get('destination') or '').strip()
    if not origin or not destination:
        return jsonify({'error': 'origin and destination required'}), 400

    conn   = get_db()
    cursor = conn.cursor()
    try:
        # Block deletion if a saved trip references this route
        cursor.execute("""
            SELECT COUNT(*) FROM trip_plan tp
            JOIN visa_requirement vr ON tp.visa_req_id = vr.visa_req_id
            WHERE vr.origin_country_id = %s AND vr.destination_country_id = %s
        """, (origin, destination))
        if cursor.fetchone()[0] > 0:
            cursor.close(); conn.close()
            return jsonify({'error': 'Trips reference this route — cannot delete.'}), 400

        cursor.execute("""
            DELETE FROM visa_cost
            WHERE origin_country_id = %s AND destination_country_id = %s
        """, (origin, destination))
        cursor.execute("""
            DELETE FROM visa_requirement
            WHERE origin_country_id = %s AND destination_country_id = %s
        """, (origin, destination))
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Route deleted'}) if deleted \
               else (jsonify({'error': 'No such route'}), 404)
    except Error as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


# ── Stored Procedure call (Stage 4 requirement) ──────────────────────────────

@app.route('/api/admin/passport-summary', methods=['POST'])
def admin_passport_summary():
    """Call sp_passport_summary(uid) and return both result sets."""
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json() or {}
    uid  = (data.get('user_id') or session.get('user_id') or '').strip()
    if not uid:
        return jsonify({'error': 'user_id required'}), 400

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.callproc('sp_passport_summary', [uid])
        result_sets = []
        for rs in cursor.stored_results():
            rows = rs.fetchall()
            for r in rows:
                if r.get('avg_max_stay') is not None:
                    r['avg_max_stay'] = float(r['avg_max_stay'])
                if r.get('cost_amount') is not None:
                    r['cost_amount'] = float(r['cost_amount'])
            result_sets.append(rows)
        cursor.close()
        conn.close()
        return jsonify({
            'user_id':       uid,
            'regional':      result_sets[0] if len(result_sets) > 0 else [],
            'cheapest':      result_sets[1] if len(result_sets) > 1 else [],
        })
    except Error as e:
        cursor.close()
        conn.close()
        return jsonify({'error': str(e)}), 400


# ── Trigger output: route audit log ──────────────────────────────────────────

@app.route('/api/admin/route-audit')
def admin_route_audit():
    """Read recent rows written by trg_visa_req_audit."""
    if not is_dev():
        return jsonify({'error': 'Unauthorized'}), 403
    limit  = request.args.get('limit', 25, type=int)
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT ra.audit_id, ra.visa_req_id,
               ra.origin_country_id, ra.destination_country_id,
               c1.country_name AS origin_name,
               c2.country_name AS destination_name,
               ra.old_is_evisa, ra.new_is_evisa,
               ra.old_visa_on_arrival, ra.new_visa_on_arrival,
               ra.old_max_stay_days,   ra.new_max_stay_days,
               ra.changed_at
        FROM   route_audit ra
        JOIN   country c1 ON ra.origin_country_id      = c1.country_id
        JOIN   country c2 ON ra.destination_country_id = c2.country_id
        ORDER  BY ra.changed_at DESC
        LIMIT  %s
    """, (limit,))
    rows = cursor.fetchall()
    for r in rows:
        serialize(r)
    cursor.close()
    conn.close()
    return jsonify(rows)


# ── Keyword search (Stage 4 requirement) ─────────────────────────────────────

@app.route('/api/search/countries')
def search_countries():
    """Free-text keyword search across country name, region, and ISO codes."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify([])
    like = f'%{q}%'
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT country_id, country_name, region_name, iso_alpha2
        FROM   country
        WHERE  country_name LIKE %s
            OR region_name  LIKE %s
            OR country_id   LIKE %s
            OR iso_alpha2   LIKE %s
        ORDER  BY country_name
        LIMIT  25
    """, (like, like, like, like))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)


# ── Analytics — 3 Advanced Queries ───────────────────────────────────────────

@app.route('/api/analytics/visa-map')
def analytics_visa_map():
    """Return visa requirement status for every destination, plus the user's
    own passport country, so the front-end map can color each country.
    Status values: 'visa_free' | 'on_arrival' | 'e_visa' | 'required'.
    Also returns an ISO-numeric → ISO-alpha3 mapping so the world TopoJSON
    (which is keyed by numeric ISO codes) can be matched to our country_id.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # Find the user's passport country
    cursor.execute("""
        SELECT c.country_id, c.country_name, c.iso_numeric
        FROM passport p
        JOIN country  c ON p.issuing_country_id = c.country_id
        WHERE p.user_id = %s
        LIMIT 1
    """, (session['user_id'],))
    passport_row = cursor.fetchone()

    # Numeric → alpha3 mapping for ALL countries (used by the front-end map)
    cursor.execute("SELECT country_id, country_name, iso_numeric, region_name FROM country")
    all_countries = cursor.fetchall()
    iso_num_to_a3 = {}
    a3_to_meta    = {}
    for c in all_countries:
        if c.get('iso_numeric') is not None:
            iso_num_to_a3[str(c['iso_numeric'])] = c['country_id']
        a3_to_meta[c['country_id']] = {
            'name':   c['country_name'],
            'region': c['region_name']
        }

    statuses = {}
    if passport_row:
        cursor.execute("""
            SELECT vr.destination_country_id AS dest_id,
                   vr.is_evisa,
                   vr.visa_on_arrival,
                   vr.max_stay_days
            FROM   visa_requirement vr
            WHERE  vr.origin_country_id = %s
        """, (passport_row['country_id'],))
        for row in cursor.fetchall():
            if row['max_stay_days'] is not None:
                status = 'visa_free'
            elif row['visa_on_arrival']:
                status = 'on_arrival'
            elif row['is_evisa']:
                status = 'e_visa'
            else:
                status = 'required'
            statuses[row['dest_id']] = {
                'status':        status,
                'max_stay_days': row['max_stay_days'],
                'name':          a3_to_meta.get(row['dest_id'], {}).get('name', row['dest_id']),
                'region':        a3_to_meta.get(row['dest_id'], {}).get('region', '')
            }

    cursor.close()
    conn.close()

    return jsonify({
        'no_passport':    passport_row is None,
        'passport':       {
            'country_id':   passport_row['country_id']   if passport_row else None,
            'country_name': passport_row['country_name'] if passport_row else None,
        },
        'iso_num_to_a3':  iso_num_to_a3,
        'a3_to_meta':     a3_to_meta,
        'statuses':       statuses
    })


@app.route('/api/analytics/budget')
def analytics_budget():
    """Query 1: Destinations cheaper than their regional average — based on user's saved passport."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    # Verify user has a passport
    cursor.execute("SELECT COUNT(*) AS cnt FROM passport WHERE user_id = %s", (session['user_id'],))
    if cursor.fetchone()['cnt'] == 0:
        cursor.close()
        conn.close()
        return jsonify({'no_passport': True, 'results': []}), 200

    cursor.execute("""
        SELECT dest.country_id   AS country_id,
               dest.country_name AS destination,
               dest.region_name,
               vr.is_evisa,
               vr.max_stay_days,
               vc.cost_amount,
               vc.currency_code
        FROM passport p
        JOIN country origin_c    ON p.issuing_country_id      = origin_c.country_id
        JOIN visa_requirement vr ON vr.origin_country_id      = origin_c.country_id
        JOIN country dest        ON vr.destination_country_id = dest.country_id
        JOIN visa_cost vc        ON vc.origin_country_id      = origin_c.country_id
                                AND vc.destination_country_id = dest.country_id
        WHERE p.user_id = %s
          AND vr.max_stay_days IS NULL              -- exclude visa-free routes (no fee)
          AND vc.cost_amount > 0
          AND vc.cost_amount < (
              SELECT AVG(vc2.cost_amount)
              FROM visa_cost vc2
              JOIN country c2 ON vc2.destination_country_id = c2.country_id
              JOIN visa_requirement vr2
                ON vr2.origin_country_id      = vc2.origin_country_id
               AND vr2.destination_country_id = vc2.destination_country_id
              WHERE c2.region_name = dest.region_name
                AND vr2.max_stay_days IS NULL
                AND vc2.cost_amount > 0
          )
        ORDER BY dest.region_name, vc.cost_amount ASC
        LIMIT 15
    """, (session['user_id'],))
    rows = cursor.fetchall()
    for r in rows:
        if r.get('cost_amount') is not None:
            r['cost_amount'] = float(r['cost_amount'])
    cursor.close()
    conn.close()
    return jsonify({'no_passport': False, 'results': rows})


@app.route('/api/analytics/regional')
def analytics_regional():
    """Query 2: Regional accessibility using UNION of trip plans + visa-free destinations."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS cnt FROM passport WHERE user_id = %s", (session['user_id'],))
    if cursor.fetchone()['cnt'] == 0:
        cursor.close()
        conn.close()
        return jsonify({'no_passport': True, 'results': []}), 200

    cursor.execute("""
        SELECT region_name,
               COUNT(*) AS total_destinations,
               ROUND(AVG(max_stay_days), 1) AS avg_max_stay_days,
               SUM(CASE WHEN is_evisa = 0 THEN 1 ELSE 0 END) AS no_evisa_count
        FROM (
            SELECT dest.region_name, vr.max_stay_days, vr.is_evisa
            FROM trip_plan tp
            JOIN passport p          ON tp.passport_number = p.passport_number
            JOIN visa_requirement vr ON tp.visa_req_id     = vr.visa_req_id
            JOIN country dest        ON vr.destination_country_id = dest.country_id
            WHERE tp.user_id = %s

            UNION

            SELECT dest.region_name, vr.max_stay_days, vr.is_evisa
            FROM passport p
            JOIN visa_requirement vr ON vr.origin_country_id = p.issuing_country_id
            JOIN country dest        ON vr.destination_country_id = dest.country_id
            WHERE p.user_id = %s
              AND vr.is_evisa = 0
              AND vr.max_stay_days >= 30
        ) AS combined
        GROUP BY region_name
        ORDER BY avg_max_stay_days DESC
        LIMIT 15
    """, (session['user_id'], session['user_id']))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify({'no_passport': False, 'results': rows})


@app.route('/api/analytics/complexity')
def analytics_complexity():
    """Query 3: Top 15 most complex visa routes for the user's passport country."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT passport_number FROM passport WHERE user_id = %s LIMIT 1",
        (session['user_id'],))
    prow = cursor.fetchone()
    if not prow:
        cursor.close()
        conn.close()
        return jsonify({'no_passport': True, 'results': [], 'passport_number': None}), 200

    passport_number = prow['passport_number']
    cursor.execute("""
        SELECT dest.country_id   AS country_id,
               dest.country_name AS destination,
               dest.region_name,
               vr.max_stay_days,
               CASE WHEN vr.max_stay_days IS NOT NULL THEN 0
                    ELSE COALESCE(vc.cost_amount, 0) END AS visa_cost,
               (SELECT COUNT(*) FROM visa_req_document vrd
                WHERE vrd.visa_req_id = vr.visa_req_id AND vrd.is_mandatory = 1
               ) AS mandatory_doc_count,
               (
                   CASE WHEN vr.is_evisa = 0 AND COALESCE(vc.cost_amount,0) = 0 THEN 0
                        WHEN vr.is_evisa = 1 THEN 20
                        ELSE 40 END
                   + CASE WHEN COALESCE(vc.cost_amount,0) > 100 THEN 30 ELSE 10 END
                   + CASE WHEN vr.max_stay_days IS NULL OR vr.max_stay_days < 30 THEN 20 ELSE 0 END
                   + CASE WHEN (SELECT COUNT(*) FROM visa_req_document vrd2
                                WHERE vrd2.visa_req_id = vr.visa_req_id AND vrd2.is_mandatory = 1
                               ) > 3 THEN 10 ELSE 0 END
               ) AS complexity_score
        FROM passport p
        JOIN country origin_c      ON p.issuing_country_id      = origin_c.country_id
        JOIN visa_requirement vr   ON vr.origin_country_id      = origin_c.country_id
        JOIN country dest          ON vr.destination_country_id = dest.country_id
        LEFT JOIN visa_cost vc     ON vc.origin_country_id      = origin_c.country_id
                                  AND vc.destination_country_id = dest.country_id
        WHERE p.passport_number = %s
        ORDER BY complexity_score DESC
        LIMIT 15
    """, (passport_number,))
    rows = cursor.fetchall()
    for r in rows:
        r['visa_cost'] = float(r['visa_cost']) if r.get('visa_cost') is not None else 0
    cursor.close()
    conn.close()
    return jsonify({'no_passport': False, 'results': rows, 'passport_number': passport_number})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
