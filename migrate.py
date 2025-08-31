import sqlite3
from datetime import datetime

conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result REAL NOT NULL,
    created_at TEXT NOT NULL
)
""")

conn.commit()
conn.close()