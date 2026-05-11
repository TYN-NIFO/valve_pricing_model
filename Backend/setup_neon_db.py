import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


CREATE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS valve_price_predictions (
    id BIGSERIAL PRIMARY KEY,
    valve_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    service_fluid TEXT NOT NULL,
    valve_type TEXT NOT NULL,
    body_material_grade TEXT NOT NULL,
    actuator_type TEXT NOT NULL,
    end_connection TEXT NOT NULL,
    seat_type TEXT NOT NULL,
    pressure_class_asme INTEGER NOT NULL,
    nps_inch DOUBLE PRECISION NOT NULL,
    operating_pressure_bar DOUBLE PRECISION NOT NULL,
    operating_temperature_c DOUBLE PRECISION NOT NULL,
    deltap_bar DOUBLE PRECISION NOT NULL,
    cv DOUBLE PRECISION NOT NULL,
    predicted_price_inr DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION,
    lower_price_range DOUBLE PRECISION,
    upper_price_range DOUBLE PRECISION,
    model_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_valve_predictions_created_at
    ON valve_price_predictions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_valve_predictions_valve_id
    ON valve_price_predictions (valve_id);
"""


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("DATABASE_URL is not set.")
        print("Example:")
        print('  $env:DATABASE_URL="postgresql://user:password@host/dbname?sslmode=require"')
        sys.exit(1)

    conn = psycopg2.connect(database_url)

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
        print("Neon database setup complete.")
        print("Created or verified table: valve_price_predictions")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
