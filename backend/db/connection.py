"""Database connection helper for PostgreSQL + pgvector."""

from __future__ import annotations

import logging
import os
from typing import Optional

import psycopg
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger("db_connection")


def get_db_connection(conn_str: Optional[str] = None) -> psycopg.Connection:
    """Creates a psycopg connection using environment variables or connection string."""
    if conn_str:
        return psycopg.connect(conn_str)

    load_dotenv(override=True)
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5434"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "fashion_search")

    connect_timeout = int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "2"))

    return psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=connect_timeout,
    )
