"""
GoNoGo — Seed Script
Run once: python3 seed.py
Creates the 4 developer accounts with password 'password12138' and a default USA passport.
"""

import mysql.connector
import hashlib
import random
import os

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASS', ''),
    'database': os.environ.get('DB_NAME', 'gonogo'),
    'port': int(os.environ.get('DB_PORT', 3306))
}

DEVELOPERS = [
    {'user_id': 'jenys2',   'email': 'jenys2@illinois.edu'},
    {'user_id': 'johnw14',  'email': 'johnw14@illinois.edu'},
    {'user_id': 'zhiyunl3', 'email': 'zhiyunl3@illinois.edu'},
    {'user_id': 'akshay11', 'email': 'akshay11@illinois.edu'},
]

DEV_PASSWORD = 'password12138'
DEV_HASH     = hashlib.sha256(DEV_PASSWORD.encode()).hexdigest()
DEFAULT_PASSPORT_COUNTRY = 'USA'

conn   = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

for dev in DEVELOPERS:
    # Upsert user
    cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (dev['user_id'],))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET password_hash = %s, email = %s WHERE user_id = %s",
                       (DEV_HASH, dev['email'], dev['user_id']))
        print(f"  Updated  {dev['user_id']}")
    else:
        cursor.execute("INSERT INTO users (user_id, email, password_hash) VALUES (%s, %s, %s)",
                       (dev['user_id'], dev['email'], DEV_HASH))
        print(f"  Created  {dev['user_id']}")

    # Create passport if none exists
    cursor.execute("SELECT passport_number FROM passport WHERE user_id = %s LIMIT 1", (dev['user_id'],))
    if not cursor.fetchone():
        pnum = f"D{random.randint(10000000, 99999999)}"
        cursor.execute(
            "INSERT INTO passport (passport_number, user_id, issuing_country_id, expiry_date, created_at) "
            "VALUES (%s, %s, %s, '2035-01-01', CURDATE())",
            (pnum, dev['user_id'], DEFAULT_PASSPORT_COUNTRY))
        print(f"  Passport {pnum} ({DEFAULT_PASSPORT_COUNTRY}) created for {dev['user_id']}")
    else:
        print(f"  Passport already exists for {dev['user_id']}")

conn.commit()
cursor.close()
conn.close()
print("\nDone! Developer accounts ready.")
print(f"Login with any of: jenys2 / johnw14 / zhiyunl3 / akshay11")
print(f"Password: {DEV_PASSWORD}")
