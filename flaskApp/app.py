from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
import sqlite3
import datetime
import hashlib
import os
import uuid
import csv
import io
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)

# Database path
DB_PATH = "pos_database.db"

# Add this to the top of your Flask app
def init_db():
    """Initialize the database if it doesn't exist"""
    if not os.path.exists(DB_PATH):
        print("Database not found. Initializing...")
        setup_database()
    else:
        # Check if the users table exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='users'
        """)
        
        if not cursor.fetchone():
            print("Users table not found. Reinitializing database...")
            conn.close()
            setup_database()
        else:
            conn.close()

# Add this function to your Flask app
def setup_database():
    """Create the database and all required tables"""
    # Remove existing database if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    # Create database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables (same as in init_db.py)
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
    
    # Insert sample products
    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("Burger", "Classic beef burger", 1, 0.6, 50, 10, 5))
    
    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("Pizza", "Margherita pizza", 2, 1.5, 30, 5, 5))
    
    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("Coke", "330ml can", 0.5, 0.3, 100, 20, 5))
    
    cursor.execute("""
    INSERT INTO products (name, description, category_id, price, cost_price, stock, min_stock, tax_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("Coffee", "Hot coffee", 1.2, 0.5, 80, 15, 5))
    
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

# Add this to the bottom of your Flask app, before the if __name__ == "__main__": block
# Initialize the database
init_db()

# Helper functions
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') not in ['admin', 'manager']:
            flash('Manager access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password', 'danger')
            return render_template('login.html')
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check credentials
        conn = get_db_connection()
        user = conn.execute("""
        SELECT id, username, role, name FROM users
        WHERE username = ? AND password = ? AND active = 1
        """, (username, password_hash)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['name'] = user['name']
            
            # Check if there's an open shift for this user
            conn = get_db_connection()
            shift = conn.execute("""
            SELECT id, start_time, opening_cash FROM shifts
            WHERE user_id = ? AND status = 'open'
            """, (user['id'],)).fetchone()
            conn.close()
            
            if shift:
                session['shift_id'] = shift['id']
                session['shift_start'] = shift['start_time']
                session['shift_opening_cash'] = shift['opening_cash']
            
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    
    # Get today's sales
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    today_sales = conn.execute("""
    SELECT COUNT(id) as orders, SUM(total_amount) as sales
    FROM orders
    WHERE DATE(order_date) = ? AND status = 'completed'
    """, (today,)).fetchone()
    
    # Get low stock products
    low_stock = conn.execute("""
    SELECT id, name, stock, min_stock FROM products
    WHERE stock <= min_stock AND active = 1
    ORDER BY stock
    LIMIT 5
    """).fetchall()
    
    # Get best selling products
    best_sellers = conn.execute("""
    SELECT p.id, p.name, SUM(oi.quantity) as quantity
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    JOIN orders o ON oi.order_id = o.id
    WHERE DATE(o.order_date) = ? AND o.status = 'completed'
    GROUP BY p.id
    ORDER BY quantity DESC
    LIMIT 5
    """, (today,)).fetchall()
    
    # Get recent orders
    recent_orders = conn.execute("""
    SELECT id, order_number, order_date, total_amount, status
    FROM orders
    WHERE DATE(order_date) = ?
    ORDER BY order_date DESC
    LIMIT 5
    """, (today,)).fetchall()
    
    conn.close()
    
    return render_template(
        'dashboard.html',
        today_sales=today_sales,
        low_stock=low_stock,
        best_sellers=best_sellers,
        recent_orders=recent_orders
    )

@app.route('/pos')
@login_required
def pos():
    conn = get_db_connection()
    
    # Get categories
    categories = conn.execute("""
    SELECT id, name FROM categories
    ORDER BY name
    """).fetchall()
    
    # Get products
    products = conn.execute("""
    SELECT p.id, p.name, p.price, c.name as category_name
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.active = 1
    ORDER BY p.name
    """).fetchall()
    
    # Get customers
    customers = conn.execute("""
    SELECT id, name FROM customers
    ORDER BY name
    """).fetchall()
    
    # Get payment methods
    payment_methods = conn.execute("""
    SELECT id, name FROM payment_methods
    WHERE active = 1
    ORDER BY name
    """).fetchall()
    
    conn.close()
    
    return render_template(
        'pos.html',
        categories=categories,
        products=products,
        customers=customers,
        payment_methods=payment_methods
    )

@app.route('/api/products')
@login_required
def api_products():
    category_id = request.args.get('category_id')
    search = request.args.get('search')
    
    conn = get_db_connection()
    
    query = """
    SELECT p.id, p.name, p.price, p.stock, c.name as category_name
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.active = 1
    """
    params = []
    
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    
    if search:
        query += " AND (LOWER(p.name) LIKE ? COLLATE NOCASE OR LOWER(p.description) LIKE ? COLLATE NOCASE)"
        params.extend([f"%{search.lower()}%", f"%{search.lower()}%"])
    
    query += " ORDER BY p.name"
    
    products = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify([dict(product) for product in products])

@app.route('/api/add_to_cart', methods=['POST'])
@login_required
def api_add_to_cart():
    product_id = request.json.get('product_id')
    quantity = request.json.get('quantity', 1)
    
    if not product_id:
        return jsonify({'error': 'Product ID is required'}), 400
    
    conn = get_db_connection()
    
    # Get product details
    product = conn.execute("""
    SELECT id, name, price, tax_rate, stock FROM products
    WHERE id = ? AND active = 1
    """, (product_id,)).fetchone()
    
    if not product:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404
    
    if product['stock'] < quantity:
        conn.close()
        return jsonify({'error': 'Insufficient stock'}), 400
    
    # Get tax rate
    tax_rate = product['tax_rate']
    
    conn.close()
    
    # Add to cart in session
    if 'cart' not in session:
        session['cart'] = []
    
    # Check if product already in cart
    for item in session['cart']:
        if item['id'] == product_id:
            item['quantity'] += quantity
            session.modified = True
            return jsonify({'success': True, 'cart': session['cart']})
    
    # Add new item to cart
    cart_item = {
        'id': product['id'],
        'name': product['name'],
        'price': product['price'],
        'quantity': quantity,
        'tax_rate': tax_rate
    }
    
    session['cart'].append(cart_item)
    session.modified = True
    
    return jsonify({'success': True, 'cart': session['cart']})

@app.route('/api/update_cart', methods=['POST'])
@login_required
def api_update_cart():
    product_id = request.json.get('product_id')
    quantity = request.json.get('quantity')
    
    if not product_id or quantity is None:
        return jsonify({'error': 'Product ID and quantity are required'}), 400
    
    if 'cart' not in session:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Find item in cart
    for item in session['cart']:
        if item['id'] == product_id:
            if quantity <= 0:
                # Remove item from cart
                session['cart'] = [i for i in session['cart'] if i['id'] != product_id]
            else:
                # Update quantity
                item['quantity'] = quantity
            
            session.modified = True
            return jsonify({'success': True, 'cart': session['cart']})
    
    return jsonify({'error': 'Product not found in cart'}), 404

@app.route('/api/remove_from_cart', methods=['POST'])
@login_required
def api_remove_from_cart():
    product_id = request.json.get('product_id')
    
    if not product_id:
        return jsonify({'error': 'Product ID is required'}), 400
    
    if 'cart' not in session:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Remove item from cart
    session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
    session.modified = True
    
    return jsonify({'success': True, 'cart': session['cart']})

@app.route('/api/clear_cart', methods=['POST'])
@login_required
def api_clear_cart():
    session['cart'] = []
    session.modified = True
    
    return jsonify({'success': True})

@app.route('/api/calculate_totals')
@login_required
def api_calculate_totals():
    if 'cart' not in session or not session['cart']:
        return jsonify({
            'subtotal': 0,
            'tax': 0,
            'total': 0
        })
    
    subtotal = 0
    tax = 0
    
    for item in session['cart']:
        item_total = item['price'] * item['quantity']
        item_tax = item_total * (item['tax_rate'] / 100)
        
        subtotal += item_total
        tax += item_tax
    
    total = subtotal + tax
    
    return jsonify({
        'subtotal': subtotal,
        'tax': tax,
        'total': total
    })

@app.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    if 'cart' not in session or not session['cart']:
        return jsonify({"error": "Cart is empty"}), 400
    
    customer_id = request.json.get('customer_id')
    payment_method = request.json.get('payment_method')
    cash_amount = request.json.get('cash_amount', 0)
    discount = request.json.get('discount', 0)
    discount_type = request.json.get('discount_type', 'fixed')
    template_type = request.json.get('template_type', 'default')
    
    if not payment_method:
        return jsonify({"error": "Payment method is required"}), 400
    
    # Calculate totals
    subtotal = 0
    tax = 0
    
    for item in session['cart']:
        item_total = item['price'] * item['quantity']
        item_tax = item_total * (item['tax_rate'] / 100)
        
        subtotal += item_total
        tax += item_tax
    
    # Calculate discount
    if discount_type == 'percentage':
        discount_amount = subtotal * (discount / 100)
    else:
        discount_amount = discount
    
    total = subtotal + tax - discount_amount
    
    # Validate cash payment
    if payment_method == 'Cash' and float(cash_amount) < total:
        return jsonify({"error": "Cash amount is less than total"}), 400
    
    # Generate order number
    order_number = f"ORD-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
    
    # Create order in database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO orders (
            order_number, user_id, customer_id, status, 
            order_date, total_amount, tax_amount, discount_amount, 
            payment_method, payment_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number, 
            session['user_id'], 
            customer_id, 
            'completed',
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total,
            tax,
            discount_amount,
            payment_method,
            'paid'
        ))
        
        order_id = cursor.lastrowid
        
        # Insert order items and update stock
        for item in session['cart']:
            cursor.execute("""
            INSERT INTO order_items (
                order_id, product_id, quantity, price, tax_rate
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                item['id'],
                item['quantity'],
                item['price'],
                item['tax_rate']
            ))
            
            # Update product stock
            cursor.execute("""
            UPDATE products SET stock = stock - ? WHERE id = ?
            """, (item['quantity'], item['id']))
        
        conn.commit()
        
        # Clear cart
        session['cart'] = []
        session.modified = True
        
        # Return success response with order details and template type
        return jsonify({
            "success": True,
            "order_id": order_id,
            "order_number": order_number,
            "template_type": template_type
        })
    
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    
    finally:
        conn.close()
@app.route('/orders')
@login_required
def orders():
    conn = get_db_connection()
    
    # Get orders
    orders = conn.execute("""
    SELECT o.*, c.name as customer_name
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.id
    ORDER BY o.order_date DESC
    LIMIT 50
    """).fetchall()
    
    conn.close()
    
    return render_template('orders.html', orders=orders)

@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    conn = get_db_connection()
    
    # Get order
    order = conn.execute("""
    SELECT o.*, c.name as customer_name, u.name as user_name
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.id
    LEFT JOIN users u ON o.user_id = u.id
    WHERE o.id = ?
    """, (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found', 'danger')
        return redirect(url_for('orders'))
    
    # Get order items
    order_items = conn.execute("""
    SELECT oi.*, p.name as product_name
    FROM order_items oi
    JOIN products p ON oi.product_id = p.id
    WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    
    conn.close()
    
    return render_template('order_detail.html', order=order, order_items=order_items)

@app.route('/inventory')
@login_required
@manager_required
def inventory():
    conn = get_db_connection()
    
    # Get categories
    categories = conn.execute("""
    SELECT id, name FROM categories
    ORDER BY name
    """).fetchall()
    
    # Get products
    products = conn.execute("""
    SELECT p.*, c.name as category_name
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    ORDER BY p.name
    """).fetchall()
    
    # Calculate inventory statistics
    total_products = len(products)
    
    # Calculate total inventory value
    total_value = conn.execute("""
    SELECT SUM(stock * price) as value
    FROM products
    WHERE active = 1
    """).fetchone()[0] or 0
    
    # Count low stock products
    low_stock_count = conn.execute("""
    SELECT COUNT(*) as count
    FROM products
    WHERE stock <= min_stock AND active = 1
    """).fetchone()[0] or 0
    
    # Count out of stock products
    out_of_stock_count = conn.execute("""
    SELECT COUNT(*) as count
    FROM products
    WHERE stock = 0 AND active = 1
    """).fetchone()[0] or 0
    
    conn.close()
    
    return render_template(
        'inventory.html', 
        categories=categories, 
        products=products,
        total_products=total_products,
        total_value=total_value,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count
    )

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@manager_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        price = request.form.get('price')
        cost_price = request.form.get('cost_price')
        stock = request.form.get('stock')
        min_stock = request.form.get('min_stock')
        barcode = request.form.get('barcode')
        tax_rate = request.form.get('tax_rate')
        
        if not name or not price or not stock:
            flash('Name, price, and stock are required', 'danger')
            return render_template('add_product.html')
        
        try:
            price = float(price)
            stock = int(stock)
            min_stock = int(min_stock) if min_stock else 0
            tax_rate = float(tax_rate) if tax_rate else 0
            cost_price = float(cost_price) if cost_price else None
        except ValueError:
            flash('Invalid numeric values', 'danger')
            return render_template('add_product.html')
        
        conn = get_db_connection()
        
        try:
            conn.execute("""
            INSERT INTO products (
                name, description, category_id, price, cost_price, stock, 
                min_stock, barcode, tax_rate, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, description, category_id, price, cost_price, stock,
                min_stock, barcode, tax_rate, True
            ))
            
            conn.commit()
            flash('Product added successfully', 'success')
            return redirect(url_for('inventory'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    # Get categories
    conn = get_db_connection()
    categories = conn.execute("""
    SELECT id, name FROM categories
    ORDER BY name
    """).fetchall()
    conn.close()
    
    return render_template('add_product.html', categories=categories)

@app.route('/inventory/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_product(product_id):
    conn = get_db_connection()
    
    # Get product
    product = conn.execute("""
    SELECT * FROM products WHERE id = ?
    """, (product_id,)).fetchone()
    
    if not product:
        conn.close()
        flash('Product not found', 'danger')
        return redirect(url_for('inventory'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        price = request.form.get('price')
        cost_price = request.form.get('cost_price')
        stock = request.form.get('stock')
        min_stock = request.form.get('min_stock')
        barcode = request.form.get('barcode')
        tax_rate = request.form.get('tax_rate')
        active = 'active' in request.form
        
        if not name or not price or not stock:
            flash('Name, price, and stock are required', 'danger')
            return render_template('edit_product.html', product=product)
        
        try:
            price = float(price)
            stock = int(stock)
            min_stock = int(min_stock) if min_stock else 0
            tax_rate = float(tax_rate) if tax_rate else 0
            cost_price = float(cost_price) if cost_price else None
        except ValueError:
            flash('Invalid numeric values', 'danger')
            return render_template('edit_product.html', product=product)
        
        try:
            conn.execute("""
            UPDATE products SET
                name = ?, description = ?, category_id = ?, price = ?, cost_price = ?, 
                stock = ?, min_stock = ?, barcode = ?, tax_rate = ?, active = ?
            WHERE id = ?
            """, (
                name, description, category_id, price, cost_price, stock,
                min_stock, barcode, tax_rate, active, product_id
            ))
            
            conn.commit()
            flash('Product updated successfully', 'success')
            return redirect(url_for('inventory'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    # Get categories
    categories = conn.execute("""
    SELECT id, name FROM categories
    ORDER BY name
    """).fetchall()
    conn.close()
    
    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/inventory/toggle/<int:product_id>')
@login_required
@manager_required
def toggle_product(product_id):
    conn = get_db_connection()
    
    # Get current status
    product = conn.execute("""
    SELECT active FROM products WHERE id = ?
    """, (product_id,)).fetchone()
    
    if not product:
        conn.close()
        flash('Product not found', 'danger')
        return redirect(url_for('inventory'))
    
    # Toggle status
    new_status = not product['active']
    
    try:
        conn.execute("""
        UPDATE products SET active = ? WHERE id = ?
        """, (new_status, product_id))
        
        conn.commit()
        flash(f'Product {"enabled" if new_status else "disabled"} successfully', 'success')
    
    except Exception as e:
        conn.rollback()
        flash(f'Error updating product: {str(e)}', 'danger')
    
    finally:
        conn.close()
    
    return redirect(url_for('inventory'))

@app.route('/inventory/import', methods=['POST'])
@login_required
@manager_required
def import_products():
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('inventory'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('inventory'))
    
    if file and file.filename.endswith('.csv'):
        try:
            # Read CSV file
            stream = io.StringIO(file.stream.read().decode("utf-8"))
            csv_reader = csv.DictReader(stream)
            
            conn = get_db_connection()
            
            # Get categories
            categories = {cat['name']: cat['id'] for cat in conn.execute("""
            SELECT id, name FROM categories
            """).fetchall()}
            
            imported_count = 0
            skipped_count = 0
            
            for row in csv_reader:
                # Check if product already exists
                existing = conn.execute("""
                SELECT id FROM products WHERE name = ?
                """, (row.get('name', ''),)).fetchone()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Get category ID
                category_name = row.get('category', '')
                category_id = categories.get(category_name) if category_name else None
                
                # If category doesn't exist, create it
                if category_name and not category_id:
                    cursor = conn.execute("""
                    INSERT INTO categories (name) VALUES (?)
                    """, (category_name,))
                    category_id = cursor.lastrowid
                    categories[category_name] = category_id
                
                # Insert product
                try:
                    conn.execute("""
                    INSERT INTO products (
                        name, description, category_id, price, cost_price, stock, 
                        min_stock, barcode, tax_rate, active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row.get('name', ''),
                        row.get('description', ''),
                        category_id,
                        float(row.get('price', 0)),
                        float(row.get('cost_price', 0)) if row.get('cost_price') else None,
                        int(row.get('stock', 0)),
                        int(row.get('min_stock', 0)),
                        row.get('barcode', ''),
                        float(row.get('tax_rate', 0)),
                        bool(int(row.get('active', 1)))
                    ))
                    
                    imported_count += 1
                except Exception as e:
                    print(f"Error importing product {row.get('name', '')}: {str(e)}")
            
            conn.commit()
            conn.close()
            
            flash(f'Imported {imported_count} products. Skipped {skipped_count} products.', 'success')
        
        except Exception as e:
            flash(f'Error importing products: {str(e)}', 'danger')
    else:
        flash('Invalid file format. Please upload a CSV file.', 'danger')
    
    return redirect(url_for('inventory'))

@app.route('/inventory/export')
@login_required
@manager_required
def export_products():
    conn = get_db_connection()
    
    # Get products
    products = conn.execute("""
    SELECT p.*, c.name as category_name
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    ORDER BY p.name
    """).fetchall()
    
    conn.close()
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = [
        'name', 'description', 'category', 'price', 'cost_price', 
        'stock', 'min_stock', 'barcode', 'tax_rate', 'active'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    
    writer.writeheader()
    
    for product in products:
        writer.writerow({
            'name': product['name'],
            'description': product['description'] or '',
            'category': product['category_name'] or '',
            'price': product['price'],
            'cost_price': product['cost_price'] or '',
            'stock': product['stock'],
            'min_stock': product['min_stock'],
            'barcode': product['barcode'] or '',
            'tax_rate': product['tax_rate'],
            'active': int(product['active'])
        })
    
    # Create response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='products.csv'
    )



# Add these routes to the Flask app

@app.route('/invoice/<int:order_id>')
@login_required
def invoice(order_id):
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute("""
    SELECT orders.*, customers.name as customer_name, customers.email, customers.phone, customers.address,
           users.name as cashier_name
    FROM orders
    LEFT JOIN customers ON orders.customer_id = customers.id
    LEFT JOIN users ON orders.user_id = users.id
    WHERE orders.id = ?
    """, (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found', 'danger')
        return redirect(url_for('orders'))
    
    # Get order items
    order_items = conn.execute("""
    SELECT order_items.*, products.name as product_name
    FROM order_items
    LEFT JOIN products ON order_items.product_id = products.id
    WHERE order_items.order_id = ?
    """, (order_id,)).fetchall()
    
    # Get business settings
    business = conn.execute("SELECT * FROM business_settings LIMIT 1").fetchone()
    
    conn.close()
    
    return render_template('invoice.html', order=order, order_items=order_items, business=business)

@app.route('/invoice/<int:order_id>/<template_type>')
@login_required
def invoice_with_template(order_id, template_type):
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute("""
    SELECT orders.*, customers.name as customer_name, customers.email, customers.phone, customers.address,
           users.name as cashier_name
    FROM orders
    LEFT JOIN customers ON orders.customer_id = customers.id
    LEFT JOIN users ON orders.user_id = users.id
    WHERE orders.id = ?
    """, (order_id,)).fetchone()
    
    if not order:
        conn.close()
        flash('Order not found', 'danger')
        return redirect(url_for('orders'))
    
    # Get order items
    order_items = conn.execute("""
    SELECT order_items.*, products.name as product_name
    FROM order_items
    LEFT JOIN products ON order_items.product_id = products.id
    WHERE order_items.order_id = ?
    """, (order_id,)).fetchall()
    
    # Get business settings
    business = conn.execute("SELECT * FROM business_settings LIMIT 1").fetchone()
    
    conn.close()
    
    # Generate invoice based on template type
    if template_type == "restaurant":
        return render_template('invoice_restaurant.html', order=order, order_items=order_items, business=business)
    elif template_type == "retail":
        return render_template('invoice_retail.html', order=order, order_items=order_items, business=business)
    elif template_type == "supermarket":
        return render_template('invoice_supermarket.html', order=order, order_items=order_items, business=business)
    else:
        return render_template('invoice.html', order=order, order_items=order_items, business=business)

@app.route('/api/invoice/<int:order_id>')
@login_required
def api_invoice(order_id):
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute("""
    SELECT orders.*, customers.name as customer_name, customers.email, customers.phone, customers.address,
           users.name as cashier_name
    FROM orders
    LEFT JOIN customers ON orders.customer_id = customers.id
    LEFT JOIN users ON orders.user_id = users.id
    WHERE orders.id = ?
    """, (order_id,)).fetchone()
    
    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
    
    # Get order items
    order_items = conn.execute("""
    SELECT order_items.*, products.name as product_name
    FROM order_items
    LEFT JOIN products ON order_items.product_id = products.id
    WHERE order_items.order_id = ?
    """, (order_id,)).fetchall()
    
    # Get business settings
    business = conn.execute("SELECT * FROM business_settings LIMIT 1").fetchone()
    
    conn.close()
    
    # Generate invoice data
    invoice_data = {
        "business": {
            "name": business[1],
            "address": business[2],
            "phone": business[3],
            "email": business[4],
            "tax_id": business[5],
            "currency": business[6],
            "footer": business[9]
        },
        "order": {
            "id": order[0],
            "order_number": order[1],
            "date": order[6],
            "customer_name": order[14],
            "cashier_name": order[15],
            "subtotal": order[7] - order[8] - order[9],
            "tax": order[8],
            "discount": order[9],
            "total": order[7],
            "payment_method": order[10]
        },
        "items": []
    }
    
    for item in order_items:
        invoice_data["items"].append({
            "id": item[0],
            "product_name": item[10],
            "quantity": item[4],
            "price": item[3],
            "tax_rate": item[5],
            "total": item[3] * item[4]
        })
    
    return jsonify(invoice_data)

@app.route('/api/invoice/<int:order_id>/<template_type>')
@login_required
def api_invoice_with_template(order_id, template_type):
    conn = get_db_connection()
    
    # Get order details
    order = conn.execute("""
    SELECT orders.*, customers.name as customer_name, customers.email, customers.phone, customers.address,
           users.name as cashier_name
    FROM orders
    LEFT JOIN customers ON orders.customer_id = customers.id
    LEFT JOIN users ON orders.user_id = users.id
    WHERE orders.id = ?
    """, (order_id,)).fetchone()
    
    if not order:
        conn.close()
        return jsonify({"error": "Order not found"}), 404
    
    # Get order items
    order_items = conn.execute("""
    SELECT order_items.*, products.name as product_name
    FROM order_items
    LEFT JOIN products ON order_items.product_id = products.id
    WHERE order_items.order_id = ?
    """, (order_id,)).fetchall()
    
    # Get business settings
    business = conn.execute("SELECT * FROM business_settings LIMIT 1").fetchone()
    
    conn.close()
    
    # Generate invoice based on template type
    if template_type == "restaurant":
        return jsonify(generate_restaurant_invoice_data(order, order_items, business))
    elif template_type == "retail":
        return jsonify(generate_retail_invoice_data(order, order_items, business))
    elif template_type == "supermarket":
        return jsonify(generate_supermarket_invoice_data(order, order_items, business))
    else:
        return jsonify(generate_default_invoice_data(order, order_items, business))

def generate_default_invoice_data(order, order_items, business):
    """Generate default invoice data"""
    invoice_data = {
        "template": "default",
        "business": {
            "name": business[1],
            "address": business[2],
            "phone": business[3],
            "email": business[4],
            "tax_id": business[5],
            "currency": business[6],
            "footer": business[9]
        },
        "order": {
            "id": order[0],
            "order_number": order[1],
            "date": order[6],
            "customer_name": order[14],
            "cashier_name": order[15],
            "subtotal": order[7] - order[8] - order[9],
            "tax": order[8],
            "discount": order[9],
            "total": order[7],
            "payment_method": order[10]
        },
        "items": []
    }
    
    for item in order_items:
        invoice_data["items"].append({
            "id": item[0],
            "product_name": item[10],
            "quantity": item[4],
            "price": item[3],
            "tax_rate": item[5],
            "total": item[3] * item[4]
        })
    
    return invoice_data

def generate_restaurant_invoice_data(order, order_items, business):
    """Generate restaurant invoice data"""
    subtotal = sum(item[3] * item[4] for item in order_items)
    service_charge = subtotal * 0.05  # 5% service charge
    
    invoice_data = {
        "template": "restaurant",
        "business": {
            "name": business[1],
            "address": business[2],
            "phone": business[3],
            "email": business[4],
            "tax_id": business[5],
            "currency": business[6],
            "footer": business[9]
        },
        "order": {
            "id": order[0],
            "order_number": order[1],
            "date": order[6],
            "table": order[12],
            "customer_name": order[14],
            "cashier_name": order[15],
            "subtotal": subtotal,
            "tax": order[8],
            "service_charge": service_charge,
            "discount": order[9],
            "total": order[7] + service_charge,
            "payment_method": order[10]
        },
        "items": []
    }
    
    for item in order_items:
        invoice_data["items"].append({
            "id": item[0],
            "product_name": item[10],
            "quantity": item[4],
            "price": item[3],
            "tax_rate": item[5],
            "total": item[3] * item[4]
        })
    
    return invoice_data

def generate_retail_invoice_data(order, order_items, business):
    """Generate retail invoice data"""
    invoice_data = {
        "template": "retail",
        "business": {
            "name": business[1],
            "address": business[2],
            "phone": business[3],
            "email": business[4],
            "tax_id": business[5],
            "currency": business[6],
            "footer": business[9]
        },
        "order": {
            "id": order[0],
            "order_number": order[1],
            "date": order[6],
            "customer_name": order[14],
            "cashier_name": order[15],
            "subtotal": order[7] - order[8] - order[9],
            "tax": order[8],
            "discount": order[9],
            "total": order[7],
            "payment_method": order[10],
            "amount_in_words": number_to_words(order[7])
        },
        "items": []
    }
    
    for item in order_items:
        invoice_data["items"].append({
            "id": item[0],
            "product_name": item[10],
            "quantity": item[4],
            "price": item[3],
            "tax_rate": item[5],
            "total": item[3] * item[4]
        })
    
    return invoice_data

def generate_supermarket_invoice_data(order, order_items, business):
    """Generate supermarket invoice data"""
    invoice_data = {
        "template": "supermarket",
        "business": {
            "name": business[1],
            "address": business[2],
            "phone": business[3],
            "email": business[4],
            "tax_id": business[5],
            "currency": business[6],
            "footer": business[9]
        },
        "order": {
            "id": order[0],
            "order_number": order[1],
            "date": order[6],
            "time": datetime.datetime.now().strftime('%H:%M:%S'),
            "customer_name": order[14],
            "cashier_name": order[15],
            "item_count": len(order_items),
            "subtotal": order[7] - order[8] - order[9],
            "tax": order[8],
            "discount": order[9],
            "total": order[7],
            "payment_method": order[10]
        },
        "items": []
    }
    
    for item in order_items:
        # Generate a simple item code (first 3 letters of product name + item ID)
        item_code = (item[10][:3] + str(item[1])).upper()
        
        invoice_data["items"].append({
            "id": item[0],
            "item_code": item_code,
            "product_name": item[10],
            "quantity": item[4],
            "mrp": item[3],
            "price": item[3],
            "tax_rate": item[5],
            "total": item[3] * item[4]
        })
    
    return invoice_data

def number_to_words(num):
    """Convert a number to words (Indian currency format)"""
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    tens = ["", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    specials = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    
    num = int(num)
    if num == 0:
        return "Zero"
    
    result = ""
    
    # Crores
    crore = num // 10000000
    if crore > 0:
        result += ones[crore] + " Crore "
        num %= 10000000
    
    # Lakhs
    lakh = num // 100000
    if lakh > 0:
        if lakh > 1:
            result += ones[lakh] + " Lakhs "
        else:
            result += "One Lakh "
        num %= 100000
    
    # Thousands
    thousand = num // 1000
    if thousand > 0:
        if thousand > 1:
            result += ones[thousand] + " Thousand "
        else:
            result += "One Thousand "
        num %= 1000
    
    # Hundreds
    hundred = num // 100
    if hundred > 0:
        result += ones[hundred] + " Hundred "
        num %= 100
    
    # Tens and ones
    if num > 0:
        if num < 10:
            result += ones[num]
        elif num < 20:
            result += specials[num - 10]
        else:
            ten = num // 10
            one = num % 10
            result += tens[ten]
            if one > 0:
                result += " " + ones[one]
    
    return result + " Rupees Only"



@app.route('/reports')
@login_required
@manager_required
def reports():
    from datetime import datetime, timedelta
    
    now = datetime.now().strftime('%Y-%m-%d')
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template(
        'reports.html',
        now=now,
        thirty_days_ago=thirty_days_ago
    )

@app.route('/ai_settings', methods=['GET', 'POST'])
@login_required
@admin_required
def ai_settings():
    if request.method == 'POST':
        # Update AI settings
        settings = {
            # 'n8n_webhook_url': request.form.get('n8n_webhook_url'),
            # 'n8n_api_key': request.form.get('n8n_api_key'),
            'ai_enabled': 'ai_enabled' in request.form,
            'forecasting_enabled': 'forecasting_enabled' in request.form,
            'anomaly_detection_enabled': 'anomaly_detection_enabled' in request.form,
            'automated_reports_enabled': 'automated_reports_enabled' in request.form,
            'predictive_inventory_enabled': 'predictive_inventory_enabled' in request.form,
            'voice_commands_enabled': 'voice_commands_enabled' in request.form
        }
        
        # In a real implementation, these settings would be saved to the database
        # For now, we'll just show a success message
        flash('AI settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    # Get current settings (in a real implementation, these would be from the database)
    settings = {
        # 'n8n_webhook_url': N8N_WEBHOOK_URL,
        # 'n8n_api_key': N8N_API_KEY,
        'ai_enabled': True,
        'forecasting_enabled': True,
        'anomaly_detection_enabled': True,
        'automated_reports_enabled': True,
        'predictive_inventory_enabled': True,
        'voice_commands_enabled': True
    }
    
    return render_template('ai_settings.html', settings=settings)

# Add these routes to your Flask app

@app.route('/ai_insights')
@login_required
@manager_required
def ai_insights():
    return render_template('ai_insights.html')

@app.route('/ai_anomaly_detection')
@login_required
@manager_required
def ai_anomaly_detection():
    return render_template('ai_anomaly_detection.html')

@app.route('/ai_automated_reports')
@login_required
@manager_required
def ai_automated_reports():
    return render_template('ai_automated_reports.html')

@app.route('/ai_predictive_inventory')
@login_required
@manager_required
def ai_predictive_inventory():
    return render_template('ai_predictive_inventory.html')

@app.route('/ai_customer_segmentation')
@login_required
@manager_required
def ai_customer_segmentation():
    return render_template('ai_customer_segmentation.html')

@app.route('/ai_marketing_recommendations')
@login_required
@manager_required
def ai_marketing_recommendations():
    return render_template('ai_marketing_recommendations.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/chatbot/message', methods=['POST'])
@login_required
def chatbot_message():
    user_message = request.json.get('message')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # Get context data based on the message
    context = get_context_for_message(user_message)
    
    # Create the prompt for the AI
    prompt = f"""
    You are an AI assistant for a Point of Sale (POS) system. Your goal is to help the user with their business.
    
    User: {session['name']} (Role: {session['role']})
    Date: {datetime.now().strftime('%Y-%m-%d')}
    
    Context:
    {json.dumps(context, indent=2)}
    
    User message: {user_message}
    
    Please provide a helpful response. If the user is asking for data, format it clearly.
    If the user is asking to perform an action, explain what you would do and ask for confirmation.
    """
    
    try:
        # Get response from OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant for a POS system."},
                {"role": "user", "content": prompt}
            ]
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Check if the response contains an action that needs confirmation
        if "ACTION:" in ai_response:
            # Extract the action and confirmation message
            parts = ai_response.split("CONFIRMATION:")
            if len(parts) > 1:
                action = parts[0].replace("ACTION:", "").strip()
                confirmation_message = parts[1].strip()
                
                return jsonify({
                    "response": confirmation_message,
                    "action": action,
                    "requires_confirmation": True
                })
        
        return jsonify({
            "response": ai_response,
            "requires_confirmation": False
        })
    
    except Exception as e:
        return jsonify({
            "error": f"Sorry, I encountered an error: {str(e)}"
        }), 500

@app.route('/chatbot/execute-action', methods=['POST'])
@login_required
def execute_chatbot_action():
    action = request.json.get('action')
    
    if not action:
        return jsonify({"error": "No action provided"}), 400
    
    try:
        # Parse the action and execute it
        # This is a simplified example - in a real implementation, you would have a more robust action parser
        
        if "generate report" in action.lower():
            # Generate a report
            return jsonify({
                "response": "Report generated successfully!",
                "redirect": url_for('reports')
            })
            
        elif "create promotion" in action.lower():
            # Create a promotion
            return jsonify({
                "response": "Promotion created successfully!",
                "redirect": url_for('settings')
            })
            
        elif "send email" in action.lower():
            # Send an email
            return jsonify({
                "response": "Email sent successfully!"
            })
            
        else:
            # Unknown action
            return jsonify({
                "error": f"Sorry, I don't know how to: {action}"
            }), 400
    
    except Exception as e:
        return jsonify({
            "error": f"Error executing action: {str(e)}"
        }), 500

@app.route('/chatbot/voice', methods=['POST'])
@login_required
def chatbot_voice():
    # In a real implementation, this would receive audio data and transcribe it
    # For now, we'll just return a placeholder response
    return jsonify({
        "response": "Voice input would be processed here.",
        "transcript": "This is a placeholder transcript."
    })

def get_context_for_message(message):
    """Get relevant context data based on the user's message"""
    context = {}
    
    # Convert message to lowercase for easier matching
    message_lower = message.lower()
    
    # Check if the user is asking about sales
    if any(word in message_lower for word in ['sales', 'revenue', 'income', 'today', 'yesterday', 'week', 'month']):
        conn = get_db_connection()
        
        # Get today's sales
        today = datetime.now().strftime('%Y-%m-%d')
        today_sales = conn.execute("""
        SELECT COUNT(id) as orders, SUM(total_amount) as sales
        FROM orders
        WHERE DATE(order_date) = ? AND status = 'completed'
        """, (today,)).fetchone()
        
        context['today_sales'] = {
            'orders': today_sales['orders'] if today_sales else 0,
            'sales': today_sales['sales'] if today_sales else 0
        }
        
        # Get yesterday's sales
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_sales = conn.execute("""
        SELECT COUNT(id) as orders, SUM(total_amount) as sales
        FROM orders
        WHERE DATE(order_date) = ? AND status = 'completed'
        """, (yesterday,)).fetchone()
        
        context['yesterday_sales'] = {
            'orders': yesterday_sales['orders'] if yesterday_sales else 0,
            'sales': yesterday_sales['sales'] if yesterday_sales else 0
        }
        
        # Get this week's sales
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y-%m-%d')
        week_sales = conn.execute("""
        SELECT COUNT(id) as orders, SUM(total_amount) as sales
        FROM orders
        WHERE DATE(order_date) >= ? AND status = 'completed'
        """, (week_start,)).fetchone()
        
        context['week_sales'] = {
            'orders': week_sales['orders'] if week_sales else 0,
            'sales': week_sales['sales'] if week_sales else 0
        }
        
        # Get this month's sales
        month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        month_sales = conn.execute("""
        SELECT COUNT(id) as orders, SUM(total_amount) as sales
        FROM orders
        WHERE DATE(order_date) >= ? AND status = 'completed'
        """, (month_start,)).fetchone()
        
        context['month_sales'] = {
            'orders': month_sales['orders'] if month_sales else 0,
            'sales': month_sales['sales'] if month_sales else 0
        }
        
        conn.close()
    
    # Check if the user is asking about inventory
    if any(word in message_lower for word in ['inventory', 'stock', 'product', 'low', 'out']):
        conn = get_db_connection()
        
        # Get low stock products
        low_stock = conn.execute("""
        SELECT id, name, stock, min_stock FROM products
        WHERE stock <= min_stock AND active = 1
        ORDER BY stock
        LIMIT 10
        """).fetchall()
        
        context['low_stock'] = [dict(row) for row in low_stock]
        
        # Get out of stock products
        out_of_stock = conn.execute("""
        SELECT id, name FROM products
        WHERE stock = 0 AND active = 1
        ORDER BY name
        LIMIT 10
        """).fetchall()
        
        context['out_of_stock'] = [dict(row) for row in out_of_stock]
        
        # Get total inventory value
        inventory_value = conn.execute("""
        SELECT SUM(stock * price) as value
        FROM products
        WHERE active = 1
        """).fetchone()
        
        context['inventory_value'] = inventory_value['value'] if inventory_value and inventory_value['value'] else 0
        
        conn.close()
    
    # Check if the user is asking about customers
    if any(word in message_lower for word in ['customer', 'customers', 'best', 'loyalty']):
        conn = get_db_connection()
        
        # Get top customers by spending
        top_customers = conn.execute("""
        SELECT c.id, c.name, COUNT(o.id) as orders, SUM(o.total_amount) as total_spent
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id
        ORDER BY total_spent DESC
        LIMIT 10
        """).fetchall()
        
        context['top_customers'] = [dict(row) for row in top_customers]
        
        # Get customers with high loyalty points
        loyal_customers = conn.execute("""
        SELECT id, name, loyalty_points FROM customers
        ORDER BY loyalty_points DESC
        LIMIT 10
        """).fetchall()
        
        context['loyal_customers'] = [dict(row) for row in loyal_customers]
        
        conn.close()
    
    # Check if the user is asking about orders
    if any(word in message_lower for word in ['order', 'orders', 'recent']):
        conn = get_db_connection()
        
        # Get recent orders
        recent_orders = conn.execute("""
        SELECT id, order_number, order_date, total_amount, status
        FROM orders
        ORDER BY order_date DESC
        LIMIT 10
        """).fetchall()
        
        context['recent_orders'] = [dict(row) for row in recent_orders]
        
        conn.close()
    
    return context


@app.route('/reports/sales')
@login_required
@manager_required
def sales_report():
    from_date = request.args.get('from_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    
    conn = get_db_connection()
    
    # Get daily sales summary
    daily_sales = conn.execute("""
    SELECT 
        DATE(order_date) as date,
        COUNT(id) as orders,
        SUM(total_amount) as sales,
        SUM(tax_amount) as tax,
        SUM(discount_amount) as discount,
        SUM(total_amount - discount_amount) as net_sales
    FROM orders
    WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
    GROUP BY DATE(order_date)
    ORDER BY date
    """, (from_date, to_date)).fetchall()
    
    # Get totals
    totals = conn.execute("""
    SELECT 
        COUNT(id) as orders,
        SUM(total_amount) as sales,
        SUM(tax_amount) as tax,
        SUM(discount_amount) as discount,
        SUM(total_amount - discount_amount) as net_sales
    FROM orders
    WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
    """, (from_date, to_date)).fetchone()
    
    conn.close()
    
    return render_template(
        'sales_report.html',
        from_date=from_date,
        to_date=to_date,
        daily_sales=daily_sales,
        totals=totals
    )

@app.route('/reports/category')
@login_required
@manager_required
def category_report():
    from_date = request.args.get('from_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    
    conn = get_db_connection()
    
    # Get sales by category
    category_sales = conn.execute("""
    SELECT 
        c.name as category,
        SUM(oi.quantity) as items_sold,
        SUM(oi.quantity * oi.price) as sales,
        SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
        SUM(o.discount_amount * oi.quantity * oi.price / (o.total_amount - o.discount_amount)) as discount,
        SUM(oi.quantity * oi.price - o.discount_amount * oi.quantity * oi.price / (o.total_amount - o.discount_amount)) as net_sales
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    JOIN products p ON oi.product_id = p.id
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
    GROUP BY c.name
    ORDER BY net_sales DESC
    """, (from_date, to_date)).fetchall()
    
    # Get totals
    totals = conn.execute("""
    SELECT 
        SUM(oi.quantity) as items_sold,
        SUM(oi.quantity * oi.price) as sales,
        SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
        SUM(o.discount_amount) as discount,
        SUM(o.total_amount - o.discount_amount) as net_sales
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
    """, (from_date, to_date)).fetchone()
    
    conn.close()
    
    return render_template(
        'category_report.html',
        from_date=from_date,
        to_date=to_date,
        category_sales=category_sales,
        totals=totals
    )

@app.route('/reports/product')
@login_required
@manager_required
def product_report():
    from_date = request.args.get('from_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    
    conn = get_db_connection()
    
    # Get sales by product
    product_sales = conn.execute("""
    SELECT 
        p.name as product,
        c.name as category,
        SUM(oi.quantity) as quantity,
        SUM(oi.quantity * oi.price) as sales,
        SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
        SUM(o.discount_amount * oi.quantity * oi.price / (o.total_amount - o.discount_amount)) as discount,
        SUM(oi.quantity * oi.price - o.discount_amount * oi.quantity * oi.price / (o.total_amount - o.discount_amount)) as net_sales
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    JOIN products p ON oi.product_id = p.id
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
    GROUP BY p.id
    ORDER BY net_sales DESC
    """, (from_date, to_date)).fetchall()
    
    # Get totals
    totals = conn.execute("""
    SELECT 
        SUM(oi.quantity) as quantity,
        SUM(oi.quantity * oi.price) as sales,
        SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
        SUM(o.discount_amount) as discount,
        SUM(o.total_amount - o.discount_amount) as net_sales
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.id
    WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
    """, (from_date, to_date)).fetchone()
    
    conn.close()
    
    return render_template(
        'product_report.html',
        from_date=from_date,
        to_date=to_date,
        product_sales=product_sales,
        totals=totals
    )

@app.route('/reports/payment')
@login_required
@manager_required
def payment_report():
    from_date = request.args.get('from_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.datetime.now().strftime('%Y-%m-%d'))
    
    conn = get_db_connection()
    
    # Get payment methods summary
    payment_methods = conn.execute("""
    SELECT 
        payment_method,
        COUNT(id) as transactions,
        SUM(total_amount) as amount
    FROM orders
    WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
    GROUP BY payment_method
    ORDER BY amount DESC
    """, (from_date, to_date)).fetchall()
    
    # Get total amount
    total_amount = conn.execute("""
    SELECT SUM(total_amount) as total
    FROM orders
    WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
    """, (from_date, to_date)).fetchone()['total']
    
    conn.close()
    
    return render_template(
        'payment_report.html',
        from_date=from_date,
        to_date=to_date,
        payment_methods=payment_methods,
        total_amount=total_amount
    )

@app.route('/customers')
@login_required
def customers():
    conn = get_db_connection()
    
    # Get customers
    customers = conn.execute("""
    SELECT * FROM customers
    ORDER BY name
    """).fetchall()
    
    conn.close()
    
    return render_template('customers.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not name:
            flash('Customer name is required', 'danger')
            return render_template('add_customer.html')
        
        conn = get_db_connection()
        
        try:
            conn.execute("""
            INSERT INTO customers (name, email, phone, address)
            VALUES (?, ?, ?, ?)
            """, (name, email, phone, address))
            
            conn.commit()
            flash('Customer added successfully', 'success')
            return redirect(url_for('customers'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error adding customer: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    return render_template('add_customer.html')

@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    conn = get_db_connection()
    
    # Get customer
    customer = conn.execute("""
    SELECT * FROM customers WHERE id = ?
    """, (customer_id,)).fetchone()
    
    if not customer:
        conn.close()
        flash('Customer not found', 'danger')
        return redirect(url_for('customers'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        if not name:
            flash('Customer name is required', 'danger')
            return render_template('edit_customer.html', customer=customer)
        
        try:
            conn.execute("""
            UPDATE customers SET
                name = ?, email = ?, phone = ?, address = ?
            WHERE id = ?
            """, (name, email, phone, address, customer_id))
            
            conn.commit()
            flash('Customer updated successfully', 'success')
            return redirect(url_for('customers'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error updating customer: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    conn.close()
    return render_template('edit_customer.html', customer=customer)

@app.route('/settings')
@login_required
@admin_required
def settings():
    conn = get_db_connection()
    
    # Get business settings
    settings = conn.execute("""
    SELECT * FROM business_settings LIMIT 1
    """).fetchone()
    
    # Convert the row to a dictionary for easier access
    settings_dict = dict(settings) if settings else {}
    
    # Add AI settings (in a real implementation, these would be stored in the database)
    settings_dict.update({
        # 'n8n_webhook_url': N8N_WEBHOOK_URL,
        # 'n8n_api_key': N8N_API_KEY,
        'ai_enabled': True,
        'forecasting_enabled': True,
        'anomaly_detection_enabled': True,
        'automated_reports_enabled': True,
        'predictive_inventory_enabled': True,
        'voice_commands_enabled': True
    })
    
    conn.close()
    
    return render_template('settings.html', settings=settings_dict)

@app.route('/settings/save', methods=['POST'])
@login_required
@admin_required
def save_settings():
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    email = request.form.get('email')
    tax_id = request.form.get('tax_id')
    currency = request.form.get('currency')
    receipt_footer = request.form.get('receipt_footer')
    tax_inclusive = 'tax_inclusive' in request.form
    
    if not name:
        flash('Business name is required', 'danger')
        return redirect(url_for('settings'))
    
    conn = get_db_connection()
    
    try:
        conn.execute("""
        UPDATE business_settings SET
            name = ?, address = ?, phone = ?, email = ?, tax_id = ?,
            currency = ?, receipt_footer = ?, tax_inclusive = ?
        """, (name, address, phone, email, tax_id, currency, receipt_footer, tax_inclusive))
        
        conn.commit()
        flash('Settings saved successfully', 'success')
    
    except Exception as e:
        conn.rollback()
        flash(f'Error saving settings: {str(e)}', 'danger')
    
    finally:
        conn.close()
    
    return redirect(url_for('settings'))

@app.route('/users')
@login_required
@admin_required
def users():
    conn = get_db_connection()
    
    # Get users
    users = conn.execute("""
    SELECT id, username, name, role, email, phone, active FROM users
    ORDER BY username
    """).fetchall()
    
    conn.close()
    
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        
        if not username or not password or not role:
            flash('Username, password, and role are required', 'danger')
            return render_template('add_user.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('add_user.html')
        
        # Check if username already exists
        conn = get_db_connection()
        existing = conn.execute("""
        SELECT id FROM users WHERE username = ?
        """, (username,)).fetchone()
        
        if existing:
            conn.close()
            flash('Username already exists', 'danger')
            return render_template('add_user.html')
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            conn.execute("""
            INSERT INTO users (username, password, role, name, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (username, password_hash, role, name, email, phone))
            
            conn.commit()
            flash('User added successfully', 'success')
            return redirect(url_for('users'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error adding user: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    return render_template('add_user.html')

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    conn = get_db_connection()
    
    # Get user
    user = conn.execute("""
    SELECT id, username, name, role, email, phone, active FROM users WHERE id = ?
    """, (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('User not found', 'danger')
        return redirect(url_for('users'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        active = 'active' in request.form
        
        try:
            conn.execute("""
            UPDATE users SET
                name = ?, email = ?, phone = ?, role = ?, active = ?
            WHERE id = ?
            """, (name, email, phone, role, active, user_id))
            
            conn.commit()
            flash('User updated successfully', 'success')
            return redirect(url_for('users'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    conn.close()
    return render_template('edit_user.html', user=user)

@app.route('/users/toggle/<int:user_id>')
@login_required
@admin_required
def toggle_user(user_id):
    conn = get_db_connection()
    
    # Get current status
    user = conn.execute("""
    SELECT active FROM users WHERE id = ?
    """, (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('User not found', 'danger')
        return redirect(url_for('users'))
    
    # Toggle status
    new_status = not user['active']
    
    try:
        conn.execute("""
        UPDATE users SET active = ? WHERE id = ?
        """, (new_status, user_id))
        
        conn.commit()
        flash(f'User {"enabled" if new_status else "disabled"} successfully', 'success')
    
    except Exception as e:
        conn.rollback()
        flash(f'Error updating user: {str(e)}', 'danger')
    
    finally:
        conn.close()
    
    return redirect(url_for('users'))

@app.route('/users/reset_password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    conn = get_db_connection()
    
    # Get user
    user = conn.execute("""
    SELECT id, username, name FROM users WHERE id = ?
    """, (user_id,)).fetchone()
    
    if not user:
        conn.close()
        flash('User not found', 'danger')
        return redirect(url_for('users'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password:
            flash('Password is required', 'danger')
            return render_template('reset_password.html', user=user)
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('reset_password.html', user=user)
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            conn.execute("""
            UPDATE users SET password = ? WHERE id = ?
            """, (password_hash, user_id))
            
            conn.commit()
            flash('Password reset successfully', 'success')
            return redirect(url_for('users'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error resetting password: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    conn.close()
    return render_template('reset_password.html', user=user)

@app.route('/shifts')
@login_required
def shifts():
    conn = get_db_connection()
    
    # Get shifts
    shifts = conn.execute("""
    SELECT s.*, u.name as user_name
    FROM shifts s
    JOIN users u ON s.user_id = u.id
    ORDER BY s.start_time DESC
    LIMIT 20
    """).fetchall()
    
    conn.close()
    
    return render_template('shifts.html', shifts=shifts)

@app.route('/shifts/open', methods=['GET', 'POST'])
@login_required
def open_shift():
    if 'shift_id' in session:
        flash('You already have an open shift', 'warning')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        opening_cash = request.form.get('opening_cash')
        notes = request.form.get('notes')
        
        if not opening_cash:
            flash('Opening cash amount is required', 'danger')
            return render_template('open_shift.html')
        
        try:
            opening_cash = float(opening_cash)
        except ValueError:
            flash('Invalid opening cash amount', 'danger')
            return render_template('open_shift.html')
        
        conn = get_db_connection()
        
        try:
            cursor = conn.execute("""
            INSERT INTO shifts (
                user_id, start_time, opening_cash, status, notes
            ) VALUES (?, ?, ?, ?, ?)
            """, (
                session['user_id'],
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                opening_cash,
                'open',
                notes
            ))
            
            shift_id = cursor.lastrowid
            conn.commit()
            
            # Update session
            session['shift_id'] = shift_id
            session['shift_start'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session['shift_opening_cash'] = opening_cash
            
            flash('Shift opened successfully', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error opening shift: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    return render_template('open_shift.html')

@app.route('/shifts/close', methods=['GET', 'POST'])
@login_required
def close_shift():
    if 'shift_id' not in session:
        flash('You do not have an open shift', 'warning')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    
    # Get shift sales
    shift_date = session['shift_start'].split()[0]
    sales_data = conn.execute("""
    SELECT 
        COUNT(id) as orders,
        SUM(total_amount) as sales,
        SUM(CASE WHEN payment_method = 'Cash' THEN total_amount ELSE 0 END) as cash_sales
    FROM orders
    WHERE user_id = ? AND DATE(order_date) = ? AND status = 'completed'
    """, (session['user_id'], shift_date)).fetchone()
    
    expected_cash = session['shift_opening_cash'] + (sales_data['cash_sales'] or 0)
    
    if request.method == 'POST':
        closing_cash = request.form.get('closing_cash')
        notes = request.form.get('notes')
        
        if not closing_cash:
            flash('Closing cash amount is required', 'danger')
            return render_template(
                'close_shift.html',
                shift_start=session['shift_start'],
                opening_cash=session['shift_opening_cash'],
                sales_data=sales_data,
                expected_cash=expected_cash
            )
        
        try:
            closing_cash = float(closing_cash)
        except ValueError:
            flash('Invalid closing cash amount', 'danger')
            return render_template(
                'close_shift.html',
                shift_start=session['shift_start'],
                opening_cash=session['shift_opening_cash'],
                sales_data=sales_data,
                expected_cash=expected_cash
            )
        
        difference = closing_cash - expected_cash
        
        try:
            conn.execute("""
            UPDATE shifts SET
                end_time = ?,
                closing_cash = ?,
                expected_cash = ?,
                difference = ?,
                status = ?,
                notes = ?
            WHERE id = ?
            """, (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                closing_cash,
                expected_cash,
                difference,
                'closed',
                notes,
                session['shift_id']
            ))
            
            conn.commit()
            
            # Clear shift from session
            session.pop('shift_id', None)
            session.pop('shift_start', None)
            session.pop('shift_opening_cash', None)
            
            flash('Shift closed successfully', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            conn.rollback()
            flash(f'Error closing shift: {str(e)}', 'danger')
        
        finally:
            conn.close()
    
    conn.close()
    
    return render_template(
        'close_shift.html',
        shift_start=session['shift_start'],
        opening_cash=session['shift_opening_cash'],
        sales_data=sales_data,
        expected_cash=expected_cash
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)