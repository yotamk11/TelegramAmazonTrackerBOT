import sqlite3
from datetime import datetime


def init_db():
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_products (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            url          TEXT,
            last_price   REAL,
            target_price REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            price      REAL,
            timestamp  TEXT
        )
    ''')

    # Migrations for older table versions
    for col in ('target_price REAL', 'title TEXT'):
        try:
            cursor.execute(f'ALTER TABLE tracked_products ADD COLUMN {col}')
        except sqlite3.OperationalError:
            pass

    # Backfill history for any existing product that has no history yet
    cursor.execute("""
        INSERT INTO price_history (product_id, price, timestamp)
        SELECT id, last_price, strftime('%Y-%m-%dT%H:%M:%f', 'now')
        FROM tracked_products
        WHERE id NOT IN (SELECT DISTINCT product_id FROM price_history)
          AND last_price IS NOT NULL
    """)

    conn.commit()
    conn.close()


def add_product(user_id, url, last_price, target_price, title=None):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tracked_products (user_id, url, last_price, target_price, title) VALUES (?, ?, ?, ?, ?)',
        (user_id, url, float(last_price), float(target_price), title)
    )
    product_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return product_id



def get_user_product_by_asin(user_id, asin):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, url, last_price, target_price, title FROM tracked_products WHERE user_id = ? AND url LIKE ?',
        (user_id, f'%/dp/{asin}%')
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_target_price(product_id, new_target):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE tracked_products SET target_price = ? WHERE id = ?',
        (float(new_target), product_id)
    )
    conn.commit()
    conn.close()


def get_all_tracked():
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, url, last_price, target_price, id, title FROM tracked_products')
    products = cursor.fetchall()
    conn.close()
    return products


def get_user_products(user_id):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, url, last_price, target_price, title FROM tracked_products WHERE user_id = ?',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_product_by_id(product_id):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, url, last_price, target_price, title, user_id FROM tracked_products WHERE id = ?',
        (product_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def update_price(product_id, new_price):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE tracked_products SET last_price = ? WHERE id = ?',
        (float(new_price), product_id)
    )
    conn.commit()
    conn.close()


def remove_product(product_id):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tracked_products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    print(f"DEBUG: Product {product_id} removed from database.")


def delete_product_and_history(product_id):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM price_history    WHERE product_id = ?', (product_id,))
    cursor.execute('DELETE FROM tracked_products WHERE id = ?',         (product_id,))
    conn.commit()
    conn.close()


def record_price_history(product_id, price):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)',
        (product_id, float(price), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_all_price_history_for_training():
    """Returns {product_id: [price, ...]} oldest-first, for all products."""
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT product_id, price FROM price_history ORDER BY product_id, timestamp')
    rows = cursor.fetchall()
    conn.close()
    history = {}
    for product_id, price in rows:
        history.setdefault(product_id, []).append(price)
    return history


def get_all_products_with_history():
    """Returns [(user_id, product_id, title, [prices])] for every tracked product."""
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tp.user_id, tp.id, tp.title, ph.price
        FROM tracked_products tp
        JOIN price_history ph ON tp.id = ph.product_id
        ORDER BY tp.id, ph.timestamp
    ''')
    rows = cursor.fetchall()
    conn.close()
    products = {}
    for user_id, product_id, title, price in rows:
        if product_id not in products:
            products[product_id] = (user_id, title, [])
        products[product_id][2].append(price)
    return [(user_id, pid, title, prices) for pid, (user_id, title, prices) in products.items()]


def get_price_history(product_id):
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT price, timestamp FROM price_history WHERE product_id = ? ORDER BY timestamp',
        (product_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
