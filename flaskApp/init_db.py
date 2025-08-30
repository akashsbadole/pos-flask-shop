import sqlite3
import os
import hashlib
from datetime import datetime

# Database path
DB_PATH = "pos_database.db"

def setup_database():
    """Create the database and all required tables"""
    # Remove existing database if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # Create database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    # Users table
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        active INTEGER DEFAULT 1
    )
    """)
    
    # Categories table
    cursor.execute("""
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    )
    """)
    
    # Products table
    cursor.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        category_id INTEGER,
        price REAL NOT NULL,
        cost_price REAL,
        barcode TEXT,
        stock INTEGER DEFAULT 0,
        min_stock INTEGER DEFAULT 0,
        image BLOB,
        active INTEGER DEFAULT 1,
        tax_rate REAL DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    """)
    
    # Orders table
    cursor.execute("""
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        customer_id INTEGER,
        table_id INTEGER,
        status TEXT DEFAULT 'pending',
        order_date TEXT NOT NULL,
        total_amount REAL NOT NULL,
        tax_amount REAL DEFAULT 0,
        discount_amount REAL DEFAULT 0,
        payment_method TEXT,
        payment_status TEXT DEFAULT 'pending',
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)
    
    # Order items table
    cursor.execute("""
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        tax_rate REAL DEFAULT 0,
        discount REAL DEFAULT 0,
        notes TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)
    
    # Customers table
    cursor.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        loyalty_points INTEGER DEFAULT 0
    )
    """)
    
    # Tables table (for restaurants)
    cursor.execute("""
    CREATE TABLE tables (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity INTEGER,
        status TEXT DEFAULT 'available'
    )
    """)
    
    # Payment methods table
    cursor.execute("""
    CREATE TABLE payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)
    
    # Shifts table
    cursor.execute("""
    CREATE TABLE shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        start_time TEXT NOT NULL,
        end_time TEXT,
        opening_cash REAL,
        closing_cash REAL,
        expected_cash REAL,
        difference REAL,
        status TEXT DEFAULT 'open',
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    # Business settings table
    cursor.execute("""
    CREATE TABLE business_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        email TEXT,
        tax_id TEXT,
        currency TEXT DEFAULT '₹',
        logo BLOB,
        receipt_footer TEXT,
        tax_inclusive INTEGER DEFAULT 0
    )
    """)
    
    # Promotions table
    cursor.execute("""
    CREATE TABLE promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        discount_type TEXT NOT NULL,
        discount_value REAL NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)
    
    # Promotion products table
    cursor.execute("""
    CREATE TABLE promotion_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        promotion_id INTEGER,
        product_id INTEGER,
        FOREIGN KEY (promotion_id) REFERENCES promotions(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)
    
    # Email campaigns table
    cursor.execute("""
    CREATE TABLE email_campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        customer_segment TEXT,
        scheduled_date TEXT,
        status TEXT DEFAULT 'scheduled',
        sent_date TEXT
    )
    """)
    
    # Insert default admin user
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute("""
    INSERT INTO users (username, password, role, name)
    VALUES (?, ?, ?, ?)
    """, ("admin", password_hash, "admin", "Administrator"))
    
    # Insert default categories
    cursor.execute("INSERT INTO categories (name) VALUES ('Food')")
    cursor.execute("INSERT INTO categories (name) VALUES ('Drinks')")
    cursor.execute("INSERT INTO categories (name) VALUES ('Snacks')")
    cursor.execute("INSERT INTO categories (name) VALUES ('Other')")
    
    # Insert default payment methods
    cursor.execute("INSERT INTO payment_methods (name) VALUES ('Cash')")
    cursor.execute("INSERT INTO payment_methods (name) VALUES ('Card')")
    cursor.execute("INSERT INTO payment_methods (name) VALUES ('UPI')")
    cursor.execute("INSERT INTO payment_methods (name) VALUES ('Mobile Pay')")
    
    # Insert default business settings
    cursor.execute("""
    INSERT INTO business_settings (name, address, phone, email)
    VALUES (?, ?, ?, ?)
    """, ("My Business", "123 Main St, City", "1234567890", "contact@mybusiness.com"))
    
    # Insert sample products - specify columns explicitly
    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Burger", "Classic beef burger", 1, 5.0, 3.0, 50, 10, 5))

    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Pizza", "Margherita pizza", 2, 8.0, 4.0, 30, 5, 5))

    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Coke", "330ml can", 3, 1.5, 0.6, 100, 20, 5))

    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Coffee", "Hot coffee", 4, 2.5, 0.8, 80, 15, 5))

    
    # Insert sample customers
    cursor.execute("""
    INSERT INTO customers (name, email, phone, loyalty_points)
    VALUES (?, ?, ?, ?)
    """, ("John Doe", "john@example.com", "1234567890", 50))
    
    cursor.execute("""
    INSERT INTO customers (name, email, phone, loyalty_points)
    VALUES (?, ?, ?, ?)
    """, ("Jane Smith", "jane@example.com", "9876543210", 120))
    
    # Insert sample tables (for restaurants)
    cursor.execute("""
    INSERT INTO tables (name, capacity, status)
    VALUES (?, ?, ?)
    """, ("Table 1", 4, "available"))
    
    cursor.execute("""
    INSERT INTO tables (name, capacity, status)
    VALUES (?, ?, ?)
    """, ("Table 2", 6, "available"))
    
    cursor.execute("""
    INSERT INTO tables (name, capacity, status)
    VALUES (?, ?, ?)
    """, ("Table 3", 2, "available"))
    
    # Insert sample promotion
    cursor.execute("""
    INSERT INTO promotions (name, description, start_date, end_date, discount_type, discount_value)
    VALUES (?, ?, ?, ?, ?, ?)
    """, ("Weekend Special", "10% off on all items", "2023-01-01", "2023-12-31", "percentage", 10))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    setup_database()