"""
Simple SQLite database for OAuth token persistence
"""

import sqlite3
import json
import time
import os
from datetime import datetime, timedelta

# Database file path
DB_PATH = "/tmp/oauth_tokens.db"

def init_db():
    """Initialize the SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # OAuth clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oauth_clients (
            client_id TEXT PRIMARY KEY,
            client_secret TEXT NOT NULL,
            redirect_uris TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Authorization codes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_codes (
            auth_code TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            user_email TEXT,
            user_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    ''')

    # Access tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_tokens (
            access_token TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            auth_code TEXT,
            user_email TEXT,
            user_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def store_oauth_client(client_id, client_secret, redirect_uris):
    """Store OAuth client credentials"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    redirect_uris_json = json.dumps(redirect_uris)
    cursor.execute('''
        INSERT OR REPLACE INTO oauth_clients (client_id, client_secret, redirect_uris)
        VALUES (?, ?, ?)
    ''', (client_id, client_secret, redirect_uris_json))

    conn.commit()
    conn.close()

def get_oauth_client(client_id):
    """Get OAuth client by client_id"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM oauth_clients WHERE client_id = ?', (client_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "client_id": row[0],
            "client_secret": row[1],
            "redirect_uris": json.loads(row[2]),
            "created_at": row[3]
        }
    return None

def store_auth_code(auth_code, client_id, user_email=None, user_password=None, expires_in=600):
    """Store authorization code with expiration"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    expires_at = datetime.now() + timedelta(seconds=expires_in)
    cursor.execute('''
        INSERT OR REPLACE INTO auth_codes
        (auth_code, client_id, user_email, user_password, expires_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (auth_code, client_id, user_email, user_password, expires_at))

    conn.commit()
    conn.close()

def get_auth_code(auth_code):
    """Get and validate authorization code"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM auth_codes WHERE auth_code = ?', (auth_code,))
    row = cursor.fetchone()

    if row:
        # Check if expired
        expires_at = datetime.fromisoformat(row[5])
        if datetime.now() > expires_at:
            # Delete expired code
            cursor.execute('DELETE FROM auth_codes WHERE auth_code = ?', (auth_code,))
            conn.commit()
            conn.close()
            return None

        conn.close()
        return {
            "auth_code": row[0],
            "client_id": row[1],
            "user_email": row[2],
            "user_password": row[3],
            "created_at": row[4],
            "expires_at": row[5]
        }

    conn.close()
    return None

def delete_auth_code(auth_code):
    """Delete authorization code after use"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM auth_codes WHERE auth_code = ?', (auth_code,))
    conn.commit()
    conn.close()

def store_access_token(access_token, client_id, auth_code=None, user_email=None, user_password=None, expires_in=3600):
    """Store access token with expiration"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    expires_at = datetime.now() + timedelta(seconds=expires_in)
    cursor.execute('''
        INSERT OR REPLACE INTO access_tokens
        (access_token, client_id, auth_code, user_email, user_password, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (access_token, client_id, auth_code, user_email, user_password, expires_at))

    conn.commit()
    conn.close()

def get_access_token(access_token):
    """Get and validate access token"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM access_tokens WHERE access_token = ?', (access_token,))
    row = cursor.fetchone()

    if row:
        # Check if expired
        expires_at = datetime.fromisoformat(row[6])
        if datetime.now() > expires_at:
            # Delete expired token
            cursor.execute('DELETE FROM access_tokens WHERE access_token = ?', (access_token,))
            conn.commit()
            conn.close()
            return None

        conn.close()
        return {
            "access_token": row[0],
            "client_id": row[1],
            "auth_code": row[2],
            "user_email": row[3],
            "user_password": row[4],
            "created_at": row[5],
            "expires_at": row[6]
        }

    conn.close()
    return None

def cleanup_expired_tokens():
    """Clean up expired tokens and codes"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now()

    # Clean up expired auth codes
    cursor.execute('DELETE FROM auth_codes WHERE expires_at < ?', (now,))

    # Clean up expired access tokens
    cursor.execute('DELETE FROM access_tokens WHERE expires_at < ?', (now,))

    conn.commit()
    conn.close()