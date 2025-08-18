import os
import sqlite3
from datetime import datetime
from typing import Iterable, List, Tuple, Optional

DB_DIR = "storage/database"
DB_PATH = os.path.join(DB_DIR, "app.db")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def initialize_storage() -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs("storage/exports", exist_ok=True)
    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/backups", exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS serials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                serial TEXT NOT NULL,
                device_type TEXT,
                confidence REAL
            )
            """
        )
        conn.commit()


def insert_serial(serial: str, device_type: Optional[str], confidence: Optional[float]) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO serials (created_at, serial, device_type, confidence) VALUES (?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), serial, device_type, confidence),
        )
        conn.commit()


def fetch_serials() -> List[Tuple[int, str, str, Optional[str], Optional[float]]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, created_at, serial, device_type, confidence FROM serials ORDER BY id ASC"
        ).fetchall()
    return rows
