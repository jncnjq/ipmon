#!/usr/bin/env python3
import sqlite3
import threading
from pathlib import Path
DB_FILE = "ipmon.db"
SCHEMA_FILE = "schema.sql"
_db_lock = threading.Lock()
class Database:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
    def connect(self):
        conn = sqlite3.connect(
            self.db_file,
            timeout=30,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute(
            "PRAGMA journal_mode=WAL"
        )
        conn.execute(
            "PRAGMA synchronous=NORMAL"
        )
        return conn
    def initialize(self):
        if not Path(SCHEMA_FILE).exists():
            raise RuntimeError(
                f"{SCHEMA_FILE} not found"
            )
        conn = self.connect()
        with open(
            SCHEMA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            conn.executescript(
                f.read()
            )
        conn.commit()
        conn.close()
    def execute(
        self,
        sql,
        params=()
    ):
        with _db_lock:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute(
                sql,
                params
            )
            conn.commit()
            conn.close()
    def query_one(
        self,
        sql,
        params=()
    ):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            sql,
            params
        )
        row = cur.fetchone()
        conn.close()
        return row
    def query_all(
        self,
        sql,
        params=()
    ):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute(
            sql,
            params
        )
        rows = cur.fetchall()
        conn.close()
        return rows
db = Database()