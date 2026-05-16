import sqlite3
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "media.db")
SQL_DIR = Path(__file__).parent / "sql"

SQL = {f.stem: f.read_text() for f in SQL_DIR.glob("*.sql")}


def get_database_connection():
    """Open and return a SQLite connection with Row factory enabled for dict-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
