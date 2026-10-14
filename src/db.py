import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "app_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def setup_table():
    ddl = """
    CREATE TABLE IF NOT EXISTS pdf_extractions (
        id          SERIAL PRIMARY KEY,
        filename    TEXT NOT NULL,
        extractor   TEXT NOT NULL,
        content     TEXT,
        extracted_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (filename, extractor)
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def insert_extraction(filename: str, extractor: str, content: str):
    sql = """
    INSERT INTO pdf_extractions (filename, extractor, content)
    VALUES (%s, %s, %s)
    ON CONFLICT (filename, extractor)
    DO UPDATE SET content = EXCLUDED.content, extracted_at = NOW()
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (filename, extractor, content))
        conn.commit()
