import sqlite3
import pandas as pd

def init_db():
    conn = sqlite3.connect('faves.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (title TEXT, score REAL, mood TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_rating(title, score, mood):
    conn = sqlite3.connect('faves.db')
    c = conn.cursor()
    c.execute("INSERT INTO ratings (title, score, mood) VALUES (?, ?, ?)", (title, score, mood))
    conn.commit()
    conn.close()

def get_top_faves(mood=None):
    conn = sqlite3.connect('faves.db')
    query = "SELECT title, AVG(score) as avg_score FROM ratings GROUP BY title"
    if mood:
        query += f" HAVING mood = '{mood}'"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.sort_values('avg_score', ascending=False).head(5)