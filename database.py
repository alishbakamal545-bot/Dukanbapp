"""Dukan AI - Database Layer"""
import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
import pandas as pd
import config


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                name_urdu TEXT,
                category TEXT,
                cost_price REAL NOT NULL DEFAULT 0,
                sell_price REAL NOT NULL DEFAULT 0,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'pcs',
                max_stock REAL NOT NULL DEFAULT 100,
                yolo_label TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                sell_price REAL NOT NULL,
                total REAL NOT NULL,
                sold_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS restocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                cost_price REAL NOT NULL,
                restocked_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """)

    if get_product_count() == 0:
        _seed_sample_data()


# --- Auth Functions (Fixed for Case-Insensitive Login) ---
def add_user(email: str, password: str) -> bool:
    clean_email = email.strip().lower()
    clean_password = password.strip()
    
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO users (email, password) VALUES (?, ?)",
                (clean_email, clean_password),
            )
            return True
        except sqlite3.IntegrityError:
            return False  # Email already exists


def check_user(email: str, password: str) -> bool:
    clean_email = email.strip().lower()
    clean_password = password.strip()
    
    with get_conn() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(email)=? AND password=?",
            (clean_email, clean_password),
        ).fetchone()
        return user is not None


def _seed_sample_data():
    now = datetime.now().isoformat()
    samples = [
        ("Basmati Rice 1kg", "باسمتی چاول", "Grocery", 180, 220, 50, "kg", 100, "rice"),
        ("Sugar", "چینی", "Grocery", 120, 145, 30, "kg", 80, "sugar"),
        ("Cooking Oil 1L", "کوکنگ آئل", "Grocery", 350, 410, 25, "ltr", 60, "bottle"),
        ("Wheat Flour 1kg", "آٹا", "Grocery", 90, 115, 60, "kg", 120, "flour"),
        ("Red Chili Powder", "لال مرچ", "Spices", 30, 45, 5, "kg", 30, "bottle"),
        ("Turmeric Powder", "ہلدی", "Spices", 25, 40, 8, "kg", 30, "bottle"),
        ("Salt 1kg", "نمک", "Grocery", 15, 25, 40, "kg", 80, None),
        ("Green Tea 100g", "سبز چائے", "Beverages", 120, 170, 15, "pcs", 40, None),
        ("Tapal Danedar 200g", "تاپال چائے", "Beverages", 220, 280, 20, "pcs", 50, None),
        ("Nestle Milk 1L", "نسٹلے دودھ", "Dairy", 190, 235, 12, "ltr", 40, "bottle"),
        ("Dawn Bread", "ڈان بریڈ", "Bakery", 90, 120, 8, "pcs", 25, None),
        ("Eggs (12 pack)", "انڈے", "Dairy", 240, 300, 18, "dozen", 40, None),
        ("Surf Excel 1kg", "سرف", "Household", 310, 390, 14, "pcs", 35, None),
        ("Lifebuoy Soap", "لائف بوائے صابن", "Household", 45, 65, 22, "pcs", 50, None),
        ("Colgate 100g", "کولگیٹ", "Household", 130, 170, 10, "pcs", 30, None),
    ]
    with get_conn() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO products
               (name, name_urdu, category, cost_price, sell_price, quantity,
                unit, max_stock, yolo_label, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(*row, now) for row in samples],
        )


def get_product_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]


def get_all_products() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(
            "SELECT * FROM products ORDER BY category, name", conn
        )


def get_product(product_id: int) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        return dict(row) if row else None


def add_product(name, name_urdu, category, cost_price, sell_price,
                quantity, unit, max_stock, yolo_label=None) -> int:
    now = datetime.now().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO products
               (name, name_urdu, category, cost_price, sell_price, quantity,
                unit, max_stock, yolo_label, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, name_urdu, category, cost_price, sell_price, quantity,
             unit, max_stock, yolo_label, now),
        )
        return cur.lastrowid


def update_stock(product_id: int, new_quantity: float):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET quantity = ?, updated_at = ? WHERE id = ?",
            (new_quantity, now, product_id),
        )


def update_prices(product_id: int, cost_price: float, sell_price: float):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET cost_price = ?, sell_price = ?, updated_at = ? WHERE id = ?",
            (cost_price, sell_price, now, product_id),
        )


def delete_product(product_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))


def record_sale(product_id: int, quantity: float):
    product = get_product(product_id)
    if not product:
        raise ValueError(f"Product ID {product_id} not found.")
    if product["quantity"] < quantity:
        raise ValueError(
            f"Not enough stock! Only {product['quantity']} {product['unit']} available."
        )
    total = quantity * product["sell_price"]
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sales
               (product_id, quantity, sell_price, total, sold_at)
               VALUES (?, ?, ?, ?, ?)""",
            (product_id, quantity, product["sell_price"], total, now),
        )
        conn.execute(
            "UPDATE products SET quantity = quantity - ?, updated_at = ? WHERE id = ?",
            (quantity, now, product_id),
        )


def get_sales_history(limit: int = 50) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql(
            """SELECT s.id, p.name AS product, s.quantity, s.sell_price,
                      s.total, s.sold_at
               FROM sales s JOIN products p ON s.product_id = p.id
               ORDER BY s.sold_at DESC LIMIT ?""",
            conn, params=(limit,),
        )


def record_restock(product_id: int, quantity: float, cost_price: float = None):
    product = get_product(product_id)
    if not product:
        raise ValueError(f"Product ID {product_id} not found.")
    cp = cost_price if cost_price is not None else product["cost_price"]
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO restocks
               (product_id, quantity, cost_price, restocked_at)
               VALUES (?, ?, ?, ?)""",
            (product_id, quantity, cp, now),
        )
        conn.execute(
            "UPDATE products SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
            (quantity, now, product_id),
        )


def get_low_stock_alerts() -> list[dict]:
    threshold = config.LOW_STOCK_THRESHOLD_PCT / 100.0
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, name, name_urdu, quantity, max_stock, unit, category
               FROM products
               WHERE (quantity * 1.0 / NULLIF(max_stock, 0)) < ?
               ORDER BY (quantity * 1.0 / NULLIF(max_stock, 0)) ASC""",
            (threshold,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_alert(product_id: int, message: str):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alerts (product_id, message, is_read, created_at) VALUES (?, ?, 0, ?)",
            (product_id, message, now),
        )


def get_unread_alerts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT a.id, a.message, a.created_at, p.name AS product
               FROM alerts a JOIN products p ON a.product_id = p.id
               WHERE a.is_read = 0
               ORDER BY a.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def mark_alert_read(alert_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,)
        )


def get_dashboard_stats() -> dict:
    with get_conn() as conn:
        total_products = conn.execute(
            "SELECT COUNT(*) AS c FROM products"
        ).fetchone()["c"]
        total_stock_value = conn.execute(
            "SELECT COALESCE(SUM(quantity * cost_price), 0) AS v FROM products"
        ).fetchone()["v"]
        total_sales_today = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS v FROM sales "
            "WHERE DATE(sold_at) = DATE('now', 'localtime')"
        ).fetchone()["v"]
        total_sales_all = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS v FROM sales"
        ).fetchone()["v"]
        low_stock_count = len(get_low_stock_alerts())

    return {
        "total_products": total_products,
        "stock_value": total_stock_value,
        "sales_today": total_sales_today,
        "sales_all_time": total_sales_all,
        "low_stock_count": low_stock_count,
    }
