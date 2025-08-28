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
        # Create main serials table with Phase 2.1 enhancements
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS serials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                serial TEXT NOT NULL,
                device_type TEXT,
                confidence REAL,
                source TEXT DEFAULT 'server',
                notes TEXT,
                validation_passed BOOLEAN DEFAULT 1,
                confidence_acceptable BOOLEAN DEFAULT 1
            )
            """
        )
        
        # Add new columns if they don't exist (for backward compatibility)
        try:
            conn.execute("ALTER TABLE serials ADD COLUMN source TEXT DEFAULT 'server'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE serials ADD COLUMN notes TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE serials ADD COLUMN validation_passed BOOLEAN DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE serials ADD COLUMN confidence_acceptable BOOLEAN DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()


def insert_serial(
    serial: str, 
    device_type: Optional[str], 
    confidence: Optional[float],
    source: str = "server",
    notes: Optional[str] = None,
    validation_passed: bool = True,
    confidence_acceptable: bool = True
) -> int:
    """Insert serial with Phase 2.1 enhanced fields"""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO serials (
                created_at, serial, device_type, confidence, 
                source, notes, validation_passed, confidence_acceptable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(), 
                serial, 
                device_type, 
                confidence,
                source,
                notes,
                validation_passed,
                confidence_acceptable
            ),
        )
        conn.commit()
        return cursor.lastrowid


def fetch_serials() -> List[Tuple[int, str, str, Optional[str], Optional[float], str, Optional[str], bool, bool]]:
    """Fetch serials with Phase 2.1 enhanced fields"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, serial, device_type, confidence, 
                   source, notes, validation_passed, confidence_acceptable 
            FROM serials 
            ORDER BY id DESC
            """
        ).fetchall()
    return rows


def fetch_serials_by_source(source: str) -> List[Tuple[int, str, str, Optional[str], Optional[float], str, Optional[str], bool, bool]]:
    """Fetch serials by source (ios/mac/server)"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, serial, device_type, confidence, 
                   source, notes, validation_passed, confidence_acceptable 
            FROM serials 
            WHERE source = ?
            ORDER BY id DESC
            """,
            (source,)
        ).fetchall()
    return rows


def get_serial_stats() -> dict:
    """Get statistics for Phase 2.1 observability"""
    with get_connection() as conn:
        # Total counts
        total = conn.execute("SELECT COUNT(*) FROM serials").fetchone()[0]
        
        # By source
        ios_count = conn.execute("SELECT COUNT(*) FROM serials WHERE source = 'ios'").fetchone()[0]
        mac_count = conn.execute("SELECT COUNT(*) FROM serials WHERE source = 'mac'").fetchone()[0]
        server_count = conn.execute("SELECT COUNT(*) FROM serials WHERE source = 'server'").fetchone()[0]
        
        # Validation stats
        valid_count = conn.execute("SELECT COUNT(*) FROM serials WHERE validation_passed = 1").fetchone()[0]
        confidence_ok_count = conn.execute("SELECT COUNT(*) FROM serials WHERE confidence_acceptable = 1").fetchone()[0]
        
        # Average confidence
        avg_confidence = conn.execute("SELECT AVG(confidence) FROM serials WHERE confidence IS NOT NULL").fetchone()[0]
        
        return {
            "total_serials": total,
            "by_source": {
                "ios": ios_count,
                "mac": mac_count,
                "server": server_count
            },
            "validation_stats": {
                "valid": valid_count,
                "confidence_acceptable": confidence_ok_count
            },
            "avg_confidence": round(avg_confidence, 3) if avg_confidence else 0.0
        }
