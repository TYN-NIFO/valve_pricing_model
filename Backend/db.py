import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "valve_ml_db",
    "user": "postgres",
    "password": "264638"
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)