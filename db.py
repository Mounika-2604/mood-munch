import sqlite3
import json
import pandas as pd


def _get_connection():
    """Create a SQLite connection with sane defaults for a Streamlit app."""
    conn = sqlite3.connect('faves.db')
    # Improve concurrency and durability for lightweight workloads
    try:
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA foreign_keys=ON;')
    except sqlite3.Error:
        pass
    return conn

def init_db():
    """Create required tables if they do not exist."""
    conn = _get_connection()
    c = conn.cursor()
    # Ratings captured from UI
    c.execute(
        '''CREATE TABLE IF NOT EXISTS ratings (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               title TEXT NOT NULL,
               score REAL NOT NULL CHECK(score >= 1 AND score <= 5),
               mood TEXT NOT NULL,
               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
           )'''
    )
    # Minimal events table for analytics/usage tracking
    c.execute(
        '''CREATE TABLE IF NOT EXISTS events (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               event TEXT NOT NULL,
               properties TEXT,
               timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
           )'''
    )
    # Helpful indices
    c.execute('CREATE INDEX IF NOT EXISTS idx_ratings_title ON ratings(title)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_ratings_mood ON ratings(mood)')
    conn.commit()
    conn.close()

def save_rating(title: str, score: float, mood: str) -> None:
    """Persist a user rating safely."""
    conn = _get_connection()
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO ratings (title, score, mood) VALUES (?, ?, ?)',
            (str(title), float(score), str(mood)),
        )
        conn.commit()
    finally:
        conn.close()

def get_top_faves(mood: str | None = None) -> pd.DataFrame:
    """Return top 5 favorites, optionally filtered by mood.

    Uses parameterized SQL and correct aggregation semantics.
    """
    conn = _get_connection()
    if mood:
        query = (
            'SELECT title, AVG(score) AS avg_score '
            'FROM ratings WHERE mood = ? GROUP BY title '
            'ORDER BY avg_score DESC LIMIT 5'
        )
        params = (mood,)
    else:
        query = (
            'SELECT title, AVG(score) AS avg_score '
            'FROM ratings GROUP BY title '
            'ORDER BY avg_score DESC LIMIT 5'
        )
        params = ()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df
def get_ratings_df() -> pd.DataFrame:
    conn = _get_connection()
    df = pd.read_sql_query('SELECT title, score, mood, timestamp FROM ratings', conn)
    conn.close()
    return df


def log_event(event: str, properties: dict | None = None) -> None:
    """Write a lightweight analytics event to the database.

    properties are stored as a JSON string for flexibility.
    """
    conn = _get_connection()
    c = conn.cursor()
    try:
        props_json = json.dumps(properties or {})
        c.execute('INSERT INTO events (event, properties) VALUES (?, ?)', (event, props_json))
        conn.commit()
    finally:
        conn.close()