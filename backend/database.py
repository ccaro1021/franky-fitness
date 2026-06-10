import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/franky_fitness")


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def setup_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id SERIAL PRIMARY KEY,
                    person_name VARCHAR(50) NOT NULL,
                    type VARCHAR(20) NOT NULL,
                    content JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id SERIAL PRIMARY KEY,
                    agent_type VARCHAR(50) NOT NULL,
                    person_name VARCHAR(50) NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    latency_ms INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    person_name VARCHAR(50) NOT NULL,
                    plan_id INTEGER REFERENCES plans(id),
                    item_type VARCHAR(20) NOT NULL,
                    item_name VARCHAR(200) NOT NULL,
                    rating VARCHAR(10) NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preference_summaries (
                    person_name VARCHAR(50) PRIMARY KEY,
                    summary JSONB NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        conn.commit()
