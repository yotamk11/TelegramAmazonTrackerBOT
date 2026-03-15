import sqlite3


def init_db():
    """
    Initializes the SQLite database, creates the tracked_products table,
    and ensures the target_price column exists for legacy databases.
    """
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()

    # Create the table with all necessary columns
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS tracked_products
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       user_id
                       INTEGER,
                       url
                       TEXT,
                       last_price
                       REAL,
                       target_price
                       REAL
                   )
                   ''')

    # Migration: Add target_price column if the table already exists from an older version
    try:
        cursor.execute('ALTER TABLE tracked_products ADD COLUMN target_price REAL')
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()


def add_product(user_id, url, last_price, target_price):
    """
    Inserts a new product tracking record into the database.

    Args:
        user_id (int): The Telegram user ID.
        url (str): The Amazon product URL.
        last_price (float): The current price when tracking started.
        target_price (float): The price threshold for notifications.
    """
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO tracked_products (user_id, url, last_price, target_price) VALUES (?, ?, ?, ?)',
                   (user_id, url, float(last_price), float(target_price)))
    conn.commit()
    conn.close()


def get_all_tracked():
    """
    Retrieves all active trackers from the database.

    Returns:
        list: A list of tuples containing (user_id, url, last_price, target_price, id).
    """
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, url, last_price, target_price, id FROM tracked_products')
    products = cursor.fetchall()
    conn.close()
    return products


def update_price(product_id, new_price):
    """
    Updates the 'last_price' column for a specific product record.
    """
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE tracked_products SET last_price = ? WHERE id = ?', (float(new_price), product_id))
    conn.commit()
    conn.close()


def remove_product(product_id):
    """
    Deletes a product record from the database. Called when target price is reached.
    """
    conn = sqlite3.connect('tracker.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tracked_products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    print(f"DEBUG: Product {product_id} removed from database.")