import sqlite3
from pathlib import Path
from threading import Lock

import psycopg
from psycopg.rows import dict_row


_schema_lock = Lock()
_initialized_urls = set()


class PostgresDatabase:
    def __init__(self, url):
        self.connection = psycopg.connect(url, autocommit=True, row_factory=dict_row)

    def execute(self, sql, parameters=()):
        return self.connection.execute(sql.replace("?", "%s"), parameters)

    def __enter__(self):
        self.transaction = self.connection.transaction()
        self.transaction.__enter__()
        return self

    def __exit__(self, *args):
        return self.transaction.__exit__(*args)

    def close(self):
        self.connection.close()

    def initialize(self):
        schema = Path(__file__).with_name("schema_postgres.sql").read_text(encoding="utf-8")
        with self:
            self.execute("SELECT pg_advisory_xact_lock(97162517)")
            self.connection.execute(schema)


def connect(url, data_dir):
    if url:
        database = PostgresDatabase(url)
        try:
            with _schema_lock:
                if url not in _initialized_urls:
                    database.initialize()
                    _initialized_urls.add(url)
        except Exception:
            database.close()
            raise
        return database
    connection = sqlite3.connect(data_dir / "portal.sqlite3")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
