import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data.sqlite3"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema = (Path(__file__).resolve().parent / "db.sql").read_text(encoding="utf-8")
    with get_conn() as c:
        c.executescript(schema)
