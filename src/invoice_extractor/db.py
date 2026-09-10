"""SQLite vendors / formats / runs store (portable data/invoice_formats.db)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "invoice_formats.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB
    conn = connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                aliases TEXT
            );
            CREATE TABLE IF NOT EXISTS formats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                match_hints TEXT,
                rules_json TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(vendor_id, version),
                FOREIGN KEY(vendor_id) REFERENCES vendors(id)
            );
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash TEXT,
                source_file TEXT,
                format_id INTEGER,
                gold_json TEXT,
                rules_json_out TEXT,
                checker_verdict TEXT,
                confidence TEXT,
                needs_human INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    return path


def upsert_vendor(conn: sqlite3.Connection, name: str, aliases: list[str] | None = None) -> int:
    aliases_s = json.dumps(aliases or [], ensure_ascii=False)
    row = conn.execute("SELECT id FROM vendors WHERE name = ?", (name,)).fetchone()
    if row:
        conn.execute("UPDATE vendors SET aliases = ? WHERE id = ?", (aliases_s, row["id"]))
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO vendors (name, aliases) VALUES (?, ?)", (name, aliases_s)
    )
    return int(cur.lastrowid)


def insert_format(
    conn: sqlite3.Connection,
    vendor_id: int,
    version: int,
    match_hints: dict[str, Any],
    rules_json: dict[str, Any],
    notes: str = "",
    status: str = "active",
) -> int:
    existing = conn.execute(
        "SELECT id FROM formats WHERE vendor_id = ? AND version = ?",
        (vendor_id, version),
    ).fetchone()
    payload = (
        status,
        json.dumps(match_hints, ensure_ascii=False),
        json.dumps(rules_json, ensure_ascii=False),
        notes,
    )
    if existing:
        conn.execute(
            "UPDATE formats SET status=?, match_hints=?, rules_json=?, notes=? WHERE id=?",
            (*payload, existing["id"]),
        )
        return int(existing["id"])
    cur = conn.execute(
        """
        INSERT INTO formats (vendor_id, version, status, match_hints, rules_json, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (vendor_id, version, *payload, _utc_now()),
    )
    return int(cur.lastrowid)


def list_active_formats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT f.id, f.vendor_id, f.version, f.status, f.match_hints, f.rules_json, f.notes,
               v.name AS vendor_name
        FROM formats f
        JOIN vendors v ON v.id = f.vendor_id
        WHERE f.status = 'active'
        ORDER BY f.id
        """
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "vendor_id": r["vendor_id"],
                "vendor_name": r["vendor_name"],
                "version": r["version"],
                "status": r["status"],
                "match_hints": json.loads(r["match_hints"] or "{}"),
                "rules_json": json.loads(r["rules_json"] or "{}"),
                "notes": r["notes"],
            }
        )
    return out


def record_run(
    conn: sqlite3.Connection,
    *,
    source_hash: str,
    source_file: str,
    format_id: Optional[int],
    rules_out: dict[str, Any],
    verdict: str,
    confidence: str,
    needs_human: bool = False,
    gold_json: Optional[dict[str, Any]] = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO runs (
            source_hash, source_file, format_id, gold_json, rules_json_out,
            checker_verdict, confidence, needs_human, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_hash,
            source_file,
            format_id,
            json.dumps(gold_json, ensure_ascii=False) if gold_json else None,
            json.dumps(rules_out, ensure_ascii=False),
            verdict,
            confidence,
            1 if needs_human else 0,
            _utc_now(),
        ),
    )
    return int(cur.lastrowid)


def seed_builtin_formats(db_path: str | Path | None = None) -> Path:
    """Init DB and seed BITZER + PT Gloria formats."""
    from invoice_extractor.formats import (
        bhc_my_hub_v1,
        bitzer_v1,
        hangji_v1,
        highly_v1,
        hitachi_gls_v1,
        ma_no_period_v1,
        ma_with_period_v1,
        nidec_v1,
        pt_gloria_v1,
    )

    path = init_db(db_path)
    conn = connect(path)
    try:
        vid_b = upsert_vendor(
            conn,
            "BITZER",
            aliases=["BITZER Kühlmaschinenbau GmbH", "BHC", "Bosch Home Comfort"],
        )
        insert_format(
            conn,
            vid_b,
            version=1,
            match_hints=bitzer_v1.MATCH_HINTS,
            rules_json=bitzer_v1.RULES_JSON,
            notes=bitzer_v1.NOTES,
        )
        vid_p = upsert_vendor(
            conn,
            "Robert Bosch Power Tools GmbH",
            aliases=["PT GmbH", "Gloria", "Bosch PT", "Power Tools"],
        )
        insert_format(
            conn,
            vid_p,
            version=1,
            match_hints=pt_gloria_v1.MATCH_HINTS,
            rules_json=pt_gloria_v1.RULES_JSON,
            notes=pt_gloria_v1.NOTES,
        )
        extras = [
            ("Guangdong Hangji Metal Co., Ltd.", ["Hangji", "GDHJ", "恒基"], hangji_v1),
            ("NIDEC TECHNO MOTOR CORPORATION", ["NIDEC", "JCH"], nidec_v1),
            ("Hitachi Global Life Solutions, Inc.", ["Hitachi GLS", "MEH"], hitachi_gls_v1),
            ("HIGHLY INTERNATIONAL (HONG KONG) LIMITED", ["HIGHLY", "海立"], highly_v1),
            (
                "Robert Bosch GmbH (MA NoPeriod)",
                ["MA", "Mobility Aftermarket", "RBTW", "Bosch MA"],
                ma_no_period_v1,
            ),
            (
                "Robert Bosch GmbH (MA WithPeriod)",
                ["MA WithPeriod", "MA Declaration withPeriod"],
                ma_with_period_v1,
            ),
            (
                "Bosch Home Comfort Supply (M) Sdn. Bhd.",
                ["BHC MY-HUB", "Home Comfort Supply", "Johnson Controls Air Conditioning Supply"],
                bhc_my_hub_v1,
            ),
        ]
        for name, aliases, mod in extras:
            vid = upsert_vendor(conn, name, aliases=aliases)
            insert_format(
                conn,
                vid,
                version=1,
                match_hints=mod.MATCH_HINTS,
                rules_json=mod.RULES_JSON,
                notes=mod.NOTES,
            )
        conn.commit()
    finally:
        conn.close()
    return path
