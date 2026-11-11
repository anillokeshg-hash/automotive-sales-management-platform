"""SQLite database: schema and sample data."""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "autosales.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vehicles (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    make   TEXT NOT NULL,
    model  TEXT NOT NULL,
    year   INTEGER NOT NULL,
    price  REAL NOT NULL CHECK (price > 0),
    stock  INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
);
CREATE TABLE IF NOT EXISTS customers (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    phone TEXT,
    email TEXT
);
CREATE TABLE IF NOT EXISTS sales (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id    INTEGER NOT NULL REFERENCES vehicles(id),
    customer_id   INTEGER NOT NULL REFERENCES customers(id),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    price_at_sale REAL NOT NULL,
    sale_date     TEXT NOT NULL,
    salesperson   TEXT
);
"""


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = connect()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == 0:
        seed(conn)
    conn.commit()
    conn.close()


def seed(conn):
    vehicles = [
        ("Maruti Suzuki", "Swift", 2025, 650000, 8),
        ("Hyundai", "Creta", 2025, 1200000, 5),
        ("Tata", "Nexon", 2025, 950000, 6),
        ("Mahindra", "XUV700", 2025, 1700000, 2),
        ("Toyota", "Innova Crysta", 2025, 2200000, 3),
        ("Honda", "City", 2025, 1250000, 4),
        ("Kia", "Seltos", 2025, 1300000, 1),
        ("Tata", "Punch", 2025, 700000, 9),
    ]
    conn.executemany("INSERT INTO vehicles (make, model, year, price, stock) VALUES (?,?,?,?,?)",
                     vehicles)
    customers = [
        ("Ravi Kumar", "9876543210", "ravi@example.com"),
        ("Anita Sharma", "9123456780", "anita@example.com"),
        ("Suresh Reddy", "9988776655", "suresh@example.com"),
        ("Priya Nair", "9090909090", "priya@example.com"),
        ("Imran Khan", "9012345678", "imran@example.com"),
    ]
    conn.executemany("INSERT INTO customers (name, phone, email) VALUES (?,?,?)", customers)

    today = date.today()
    # (vehicle_id, customer_id, qty, discount %, days ago, salesperson)
    sales = [
        (1, 1, 1, 2, 3, "Arjun"), (2, 2, 1, 0, 6, "Meera"), (3, 3, 1, 3, 9, "Arjun"),
        (8, 4, 2, 1, 14, "Meera"), (4, 5, 1, 0, 20, "Arjun"), (5, 1, 1, 5, 27, "Meera"),
        (6, 2, 1, 2, 33, "Arjun"), (1, 3, 2, 4, 41, "Meera"), (2, 4, 1, 0, 48, "Arjun"),
        (7, 5, 1, 3, 55, "Meera"), (3, 1, 1, 2, 62, "Arjun"), (8, 2, 1, 0, 70, "Meera"),
    ]
    price = {i + 1: v[3] for i, v in enumerate(vehicles)}
    for vid, cid, qty, disc, ago, rep in sales:
        conn.execute(
            "INSERT INTO sales (vehicle_id, customer_id, quantity, price_at_sale, sale_date, salesperson)"
            " VALUES (?,?,?,?,?,?)",
            (vid, cid, qty, round(price[vid] * (1 - disc / 100), 2),
             (today - timedelta(days=ago)).isoformat(), rep))
