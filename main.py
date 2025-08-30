import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import datetime
import hashlib
from functools import partial
import csv
import uuid
from PIL import Image, ImageTk
import qrcode
from io import BytesIO
import base64

class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Point of Sale System")
        self.root.geometry("1200x800")
        self.root.minsize(1024, 768)
        
        # Database setup
        self.db_path = "pos_database.db"
        self.setup_database()
        
        # Session variables
        self.current_user = None
        self.current_role = None
        self.cart = []
        self.current_order_id = None
        self.current_table = None
        
        # UI Theme
        self.bg_color = "#f0f0f0"
        self.primary_color = "#3498db"
        self.secondary_color = "#2ecc71"
        self.danger_color = "#e74c3c"
        self.warning_color = "#f39c12"
        
        # Configure styles
        self.configure_styles()
        
        # Show login screen
        self.show_login_screen()
    
    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("TFrame", background=self.bg_color)
        style.configure("TButton", padding=6, relief="flat", background=self.primary_color)
        style.configure("TLabel", background=self.bg_color, font=("Arial", 10))
        style.configure("Header.TLabel", font=("Arial", 14, "bold"))
        style.configure("Title.TLabel", font=("Arial", 18, "bold"))
        
        style.map("TButton",
                  background=[("active", self.primary_color), ("pressed", "!disabled", "#2980b9")],
                  foreground=[("active", "white"), ("pressed", "white")])
    
    def setup_database(self):
        # Create database if it doesn't exist
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
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
            
            conn.commit()
            conn.close()
    
    def show_login_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create login frame
        login_frame = ttk.Frame(self.root, padding=20)
        login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Title
        title_label = ttk.Label(login_frame, text="Point of Sale System", style="Title.TLabel")
        title_label.pack(pady=20)
        
        # Login form
        form_frame = ttk.Frame(login_frame)
        form_frame.pack(pady=20)
        
        ttk.Label(form_frame, text="Username:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.username_entry = ttk.Entry(form_frame, width=20)
        self.username_entry.grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(form_frame, text="Password:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.password_entry = ttk.Entry(form_frame, width=20, show="*")
        self.password_entry.grid(row=1, column=1, padx=10, pady=10)
        
        # Login button
        login_btn = ttk.Button(form_frame, text="Login", command=self.login)
        login_btn.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Bind Enter key to login
        self.root.bind("<Return>", lambda event: self.login())
        
        # Focus on username entry
        self.username_entry.focus()
    
    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check credentials
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, username, role, name FROM users
        WHERE username = ? AND password = ? AND active = 1
        """, (username, password_hash))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = {
                'id': user[0],
                'username': user[1],
                'role': user[2],
                'name': user[3]
            }
            self.current_role = user[2]
            
            # Check if there's an open shift for this user
            self.check_open_shift()
            
            # Show main screen
            self.show_main_screen()
        else:
            messagebox.showerror("Error", "Invalid username or password")
    
    def check_open_shift(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, start_time, opening_cash FROM shifts
        WHERE user_id = ? AND status = 'open'
        """, (self.current_user['id'],))
        
        shift = cursor.fetchone()
        conn.close()
        
        if shift:
            self.current_shift = {
                'id': shift[0],
                'start_time': shift[1],
                'opening_cash': shift[2]
            }
        else:
            self.current_shift = None
    
    def show_main_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top navigation bar
        self.create_navbar(main_container)
        
        # Create main content area
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create left panel for categories and products
        left_panel = ttk.Frame(content_frame, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Create right panel for cart and payment
        right_panel = ttk.Frame(content_frame, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Create category buttons
        self.create_category_panel(left_panel)
        
        # Create product grid
        self.create_product_panel(left_panel)
        
        # Create cart panel
        self.create_cart_panel(right_panel)
        
        # Create payment panel
        self.create_payment_panel(right_panel)
        
        # Load categories and products
        self.load_categories()
        self.load_products()
    
    def create_navbar(self, parent):
        navbar = ttk.Frame(parent, height=50)
        navbar.pack(fill=tk.X)
        
        # Business name
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM business_settings LIMIT 1")
        business_name = cursor.fetchone()[0]
        conn.close()
        
        business_label = ttk.Label(navbar, text=business_name, style="Title.TLabel")
        business_label.pack(side=tk.LEFT, padx=20)
        
        # User info
        user_label = ttk.Label(navbar, text=f"User: {self.current_user['name']} ({self.current_role})")
        user_label.pack(side=tk.RIGHT, padx=20)
        
        # Date and time
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        datetime_label = ttk.Label(navbar, text=now)
        datetime_label.pack(side=tk.RIGHT, padx=20)
        
        # Navigation buttons
        nav_buttons = ttk.Frame(navbar)
        nav_buttons.pack(side=tk.LEFT, padx=20)
        
        if self.current_role in ['admin', 'manager']:
            reports_btn = ttk.Button(nav_buttons, text="Reports", command=self.show_reports_screen)
            reports_btn.pack(side=tk.LEFT, padx=5)
            
            inventory_btn = ttk.Button(nav_buttons, text="Inventory", command=self.show_inventory_screen)
            inventory_btn.pack(side=tk.LEFT, padx=5)
        
        if self.current_role == 'admin':
            settings_btn = ttk.Button(nav_buttons, text="Settings", command=self.show_settings_screen)
            settings_btn.pack(side=tk.LEFT, padx=5)
            
            users_btn = ttk.Button(nav_buttons, text="Users", command=self.show_users_screen)
            users_btn.pack(side=tk.LEFT, padx=5)
        
        # Shift button
        shift_btn = ttk.Button(nav_buttons, text="Shift", command=self.show_shift_screen)
        shift_btn.pack(side=tk.LEFT, padx=5)
        
        # Logout button
        logout_btn = ttk.Button(nav_buttons, text="Logout", command=self.logout)
        logout_btn.pack(side=tk.LEFT, padx=5)
    
    def create_category_panel(self, parent):
        category_frame = ttk.LabelFrame(parent, text="Categories", padding=10)
        category_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Category buttons container
        self.category_container = ttk.Frame(category_frame)
        self.category_container.pack(fill=tk.X)
        
        # All products button
        all_btn = ttk.Button(self.category_container, text="All", command=lambda: self.filter_products(None))
        all_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
    def create_product_panel(self, parent):
        product_frame = ttk.LabelFrame(parent, text="Products", padding=10)
        product_frame.pack(fill=tk.BOTH, expand=True)
        
        # Search bar
        search_frame = ttk.Frame(product_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", lambda event: self.search_products())
        
        # Product grid
        grid_frame = ttk.Frame(product_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable frame for products
        canvas = tk.Canvas(grid_frame)
        scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=canvas.yview)
        self.product_container = ttk.Frame(canvas)
        
        self.product_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.product_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_cart_panel(self, parent):
        cart_frame = ttk.LabelFrame(parent, text="Cart", padding=10)
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Cart items
        columns = ("id", "name", "qty", "price", "total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", height=10)
        
        # Define headings
        self.cart_tree.heading("id", text="ID")
        self.cart_tree.heading("name", text="Product")
        self.cart_tree.heading("qty", text="Qty")
        self.cart_tree.heading("price", text="Price")
        self.cart_tree.heading("total", text="Total")
        
        # Define columns
        self.cart_tree.column("id", width=40, anchor="center")
        self.cart_tree.column("name", width=150)
        self.cart_tree.column("qty", width=50, anchor="center")
        self.cart_tree.column("price", width=70, anchor="e")
        self.cart_tree.column("total", width=70, anchor="e")
        
        self.cart_tree.pack(fill=tk.BOTH, expand=True)
        
        # Cart buttons
        cart_btn_frame = ttk.Frame(cart_frame)
        cart_btn_frame.pack(fill=tk.X, pady=5)
        
        remove_btn = ttk.Button(cart_btn_frame, text="Remove", command=self.remove_from_cart)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(cart_btn_frame, text="Clear Cart", command=self.clear_cart)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Cart summary
        summary_frame = ttk.Frame(cart_frame)
        summary_frame.pack(fill=tk.X, pady=10)
        
        self.subtotal_label = ttk.Label(summary_frame, text="Subtotal: ₹0.00")
        self.subtotal_label.pack(anchor="e", padx=10)
        
        self.tax_label = ttk.Label(summary_frame, text="Tax: ₹0.00")
        self.tax_label.pack(anchor="e", padx=10)
        
        self.discount_label = ttk.Label(summary_frame, text="Discount: ₹0.00")
        self.discount_label.pack(anchor="e", padx=10)
        
        self.total_label = ttk.Label(summary_frame, text="Total: ₹0.00", font=("Arial", 12, "bold"))
        self.total_label.pack(anchor="e", padx=10)
    
    def create_payment_panel(self, parent):
        payment_frame = ttk.LabelFrame(parent, text="Payment", padding=10)
        payment_frame.pack(fill=tk.X)
        
        # Payment method
        payment_method_frame = ttk.Frame(payment_frame)
        payment_method_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(payment_method_frame, text="Payment Method:").pack(side=tk.LEFT, padx=5)
        
        self.payment_method_var = tk.StringVar(value="Cash")
        payment_methods = ["Cash", "Card", "UPI", "Mobile Pay"]
        
        for method in payment_methods:
            ttk.Radiobutton(
                payment_method_frame, 
                text=method, 
                variable=self.payment_method_var, 
                value=method
            ).pack(side=tk.LEFT, padx=5)
        
        # Cash amount
        cash_frame = ttk.Frame(payment_frame)
        cash_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(cash_frame, text="Cash Amount:").pack(side=tk.LEFT, padx=5)
        self.cash_entry = ttk.Entry(cash_frame, width=10)
        self.cash_entry.pack(side=tk.LEFT, padx=5)
        
        self.change_label = ttk.Label(cash_frame, text="Change: ₹0.00")
        self.change_label.pack(side=tk.LEFT, padx=20)
        
        # Discount
        discount_frame = ttk.Frame(payment_frame)
        discount_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(discount_frame, text="Discount:").pack(side=tk.LEFT, padx=5)
        
        self.discount_var = tk.StringVar(value="0")
        discount_entry = ttk.Entry(discount_frame, textvariable=self.discount_var, width=10)
        discount_entry.pack(side=tk.LEFT, padx=5)
        
        self.discount_type_var = tk.StringVar(value="fixed")
        ttk.Radiobutton(
            discount_frame, 
            text="Fixed", 
            variable=self.discount_type_var, 
            value="fixed"
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Radiobutton(
            discount_frame, 
            text="%", 
            variable=self.discount_type_var, 
            value="percentage"
        ).pack(side=tk.LEFT, padx=2)
        
        apply_discount_btn = ttk.Button(discount_frame, text="Apply", command=self.apply_discount)
        apply_discount_btn.pack(side=tk.LEFT, padx=5)
        
        # Customer selection
        customer_frame = ttk.Frame(payment_frame)
        customer_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(customer_frame, text="Customer:").pack(side=tk.LEFT, padx=5)
        
        self.customer_var = tk.StringVar(value="Walk-in Customer")
        self.customer_combobox = ttk.Combobox(customer_frame, textvariable=self.customer_var, width=20)
        self.customer_combobox.pack(side=tk.LEFT, padx=5)
        
        self.load_customers()
        
        new_customer_btn = ttk.Button(customer_frame, text="New", command=self.show_new_customer_dialog)
        new_customer_btn.pack(side=tk.LEFT, padx=5)
        
        # Payment buttons
        payment_btn_frame = ttk.Frame(payment_frame)
        payment_btn_frame.pack(fill=tk.X, pady=10)
        
        pay_btn = ttk.Button(payment_btn_frame, text="Pay", command=self.process_payment)
        pay_btn.pack(side=tk.LEFT, padx=5)
        
        hold_btn = ttk.Button(payment_btn_frame, text="Hold Order", command=self.hold_order)
        hold_btn.pack(side=tk.LEFT, padx=5)
        
        recall_btn = ttk.Button(payment_btn_frame, text="Recall Order", command=self.show_recall_order_dialog)
        recall_btn.pack(side=tk.LEFT, padx=5)
        
        # Receipt options
        receipt_frame = ttk.Frame(payment_frame)
        receipt_frame.pack(fill=tk.X, pady=5)
        
        self.print_receipt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            receipt_frame, 
            text="Print Receipt", 
            variable=self.print_receipt_var
        ).pack(side=tk.LEFT, padx=5)
        
        self.email_receipt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            receipt_frame, 
            text="Email Receipt", 
            variable=self.email_receipt_var
        ).pack(side=tk.LEFT, padx=5)
        
        # Bind cash entry to calculate change
        self.cash_entry.bind("<KeyRelease>", lambda event: self.calculate_change())
    
    def load_categories(self):
        # Clear existing category buttons
        for widget in self.category_container.winfo_children():
            if widget.winfo_class() != "TButton":
                continue
            widget.destroy()
        
        # Load categories from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        # Create category buttons
        for category in categories:
            btn = ttk.Button(
                self.category_container, 
                text=category[1], 
                command=lambda c=category[0]: self.filter_products(c)
            )
            btn.pack(side=tk.LEFT, padx=5, pady=5)
    
    def load_products(self, category_id=None):
        # Clear existing product buttons
        for widget in self.product_container.winfo_children():
            widget.destroy()
        
        # Load products from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category_id:
            cursor.execute("""
            SELECT id, name, price, image FROM products
            WHERE category_id = ? AND active = 1
            ORDER BY name
            """, (category_id,))
        else:
            cursor.execute("""
            SELECT id, name, price, image FROM products
            WHERE active = 1
            ORDER BY name
            """)
        
        products = cursor.fetchall()
        conn.close()
        
        # Create product buttons in a grid
        row = 0
        col = 0
        max_cols = 4
        
        for product in products:
            product_frame = ttk.Frame(self.product_container, relief=tk.RAISED, borderwidth=1)
            product_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Product image (placeholder if no image)
            image_label = ttk.Label(product_frame, text="[Image]", width=10, height=5)
            image_label.pack(pady=5)
            
            # Product name
            name_label = ttk.Label(product_frame, text=product[1], wraplength=100)
            name_label.pack(pady=2)
            
            # Product price
            price_label = ttk.Label(product_frame, text=f"₹{product[2]:.2f}", font=("Arial", 10, "bold"))
            price_label.pack(pady=2)
            
            # Add to cart button
            add_btn = ttk.Button(
                product_frame, 
                text="Add", 
                command=lambda p=product: self.add_to_cart(p)
            )
            add_btn.pack(pady=5)
            
            # Update grid position
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Configure grid weights
        for i in range(max_cols):
            self.product_container.grid_columnconfigure(i, weight=1)
    
    def filter_products(self, category_id):
        self.load_products(category_id)
    
    def search_products(self):
        search_term = self.search_entry.get().lower()
        
        # Clear existing product buttons
        for widget in self.product_container.winfo_children():
            widget.destroy()
        
        if not search_term:
            self.load_products()
            return
        
        # Search products in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT id, name, price, image FROM products
        WHERE active = 1 AND (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)
        ORDER BY name
        """, (f"%{search_term}%", f"%{search_term}%"))
        
        products = cursor.fetchall()
        conn.close()
        
        # Create product buttons in a grid
        row = 0
        col = 0
        max_cols = 4
        
        for product in products:
            product_frame = ttk.Frame(self.product_container, relief=tk.RAISED, borderwidth=1)
            product_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Product image (placeholder if no image)
            image_label = ttk.Label(product_frame, text="[Image]", width=10, height=5)
            image_label.pack(pady=5)
            
            # Product name
            name_label = ttk.Label(product_frame, text=product[1], wraplength=100)
            name_label.pack(pady=2)
            
            # Product price
            price_label = ttk.Label(product_frame, text=f"₹{product[2]:.2f}", font=("Arial", 10, "bold"))
            price_label.pack(pady=2)
            
            # Add to cart button
            add_btn = ttk.Button(
                product_frame, 
                text="Add", 
                command=lambda p=product: self.add_to_cart(p)
            )
            add_btn.pack(pady=5)
            
            # Update grid position
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Configure grid weights
        for i in range(max_cols):
            self.product_container.grid_columnconfigure(i, weight=1)
    
    def add_to_cart(self, product):
        product_id = product[0]
        product_name = product[1]
        product_price = product[2]
        
        # Check if product already in cart
        for item in self.cart:
            if item['id'] == product_id:
                item['quantity'] += 1
                self.update_cart_display()
                return
        
        # Add new item to cart
        cart_item = {
            'id': product_id,
            'name': product_name,
            'price': product_price,
            'quantity': 1,
            'tax_rate': 0  # Will be loaded from database
        }
        
        # Get tax rate for product
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tax_rate FROM products WHERE id = ?", (product_id,))
        tax_rate = cursor.fetchone()[0]
        conn.close()
        
        cart_item['tax_rate'] = tax_rate
        
        self.cart.append(cart_item)
        self.update_cart_display()
    
    def remove_from_cart(self):
        selected_item = self.cart_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an item to remove")
            return
        
        item_id = int(self.cart_tree.item(selected_item[0], 'values')[0])
        
        # Remove item from cart
        self.cart = [item for item in self.cart if item['id'] != item_id]
        self.update_cart_display()
    
    def clear_cart(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the cart?"):
            self.cart = []
            self.update_cart_display()
    
    def update_cart_display(self):
        # Clear cart tree
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        # Add items to cart tree
        subtotal = 0
        tax_total = 0
        
        for item in self.cart:
            item_total = item['price'] * item['quantity']
            item_tax = item_total * (item['tax_rate'] / 100)
            
            subtotal += item_total
            tax_total += item_tax
            
            self.cart_tree.insert(
                "", 
                "end", 
                values=(
                    item['id'],
                    item['name'],
                    f"{item['quantity']:.2f}",
                    f"₹{item['price']:.2f}",
                    f"₹{item_total:.2f}"
                )
            )
        
        # Calculate discount
        discount = 0
        if self.discount_var.get():
            try:
                discount_value = float(self.discount_var.get())
                if self.discount_type_var.get() == "percentage":
                    discount = subtotal * (discount_value / 100)
                else:
                    discount = discount_value
            except ValueError:
                pass
        
        # Calculate total
        total = subtotal + tax_total - discount
        
        # Update labels
        self.subtotal_label.config(text=f"Subtotal: ₹{subtotal:.2f}")
        self.tax_label.config(text=f"Tax: ₹{tax_total:.2f}")
        self.discount_label.config(text=f"Discount: ₹{discount:.2f}")
        self.total_label.config(text=f"Total: ₹{total:.2f}")
        
        # Update change calculation
        self.calculate_change()
    
    def apply_discount(self):
        self.update_cart_display()
    
    def calculate_change(self):
        try:
            cash = float(self.cash_entry.get() or 0)
            
            # Get total from label
            total_text = self.total_label.cget("text")
            total = float(total_text.replace("Total: ₹", ""))
            
            change = cash - total
            self.change_label.config(text=f"Change: ₹{change:.2f}")
        except ValueError:
            self.change_label.config(text="Change: ₹0.00")
    
    def load_customers(self):
        # Load customers from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM customers ORDER BY name")
        customers = cursor.fetchall()
        conn.close()
        
        # Update combobox
        customer_names = ["Walk-in Customer"] + [customer[0] for customer in customers]
        self.customer_combobox['values'] = customer_names
    
    def process_payment(self):
        if not self.cart:
            messagebox.showwarning("Warning", "Cart is empty")
            return
        
        # Get payment method
        payment_method = self.payment_method_var.get()
        
        # Get customer
        customer_name = self.customer_var.get()
        customer_id = None
        
        if customer_name != "Walk-in Customer":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM customers WHERE name = ?", (customer_name,))
            customer = cursor.fetchone()
            conn.close()
            
            if customer:
                customer_id = customer[0]
        
        # Get cash amount if cash payment
        cash_amount = 0
        if payment_method == "Cash":
            try:
                cash_amount = float(self.cash_entry.get() or 0)
            except ValueError:
                cash_amount = 0
        
        # Get total
        total_text = self.total_label.cget("text")
        total = float(total_text.replace("Total: ₹", ""))
        
        # Validate payment
        if payment_method == "Cash" and cash_amount < total:
            messagebox.showwarning("Warning", "Cash amount is less than total")
            return
        
        # Generate order number
        order_number = f"ORD-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        
        # Create order in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get tax and discount amounts
        subtotal_text = self.subtotal_label.cget("text")
        subtotal = float(subtotal_text.replace("Subtotal: ₹", ""))
        
        tax_text = self.tax_label.cget("text")
        tax_amount = float(tax_text.replace("Tax: ₹", ""))
        
        discount_text = self.discount_label.cget("text")
        discount_amount = float(discount_text.replace("Discount: ₹", ""))
        
        # Insert order
        cursor.execute("""
        INSERT INTO orders (
            order_number, user_id, customer_id, table_id, status, 
            order_date, total_amount, tax_amount, discount_amount, 
            payment_method, payment_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number, 
            self.current_user['id'], 
            customer_id, 
            self.current_table, 
            'completed',
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total,
            tax_amount,
            discount_amount,
            payment_method,
            'paid'
        ))
        
        order_id = cursor.lastrowid
        
        # Insert order items
        for item in self.cart:
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
        conn.close()
        
        # Print receipt if selected
        if self.print_receipt_var.get():
            self.print_receipt(order_id)
        
        # Email receipt if selected
        if self.email_receipt_var.get() and customer_id:
            self.email_receipt(order_id, customer_id)
        
        # Show success message
        messagebox.showinfo("Success", f"Order {order_number} completed successfully")
        
        # Clear cart
        self.cart = []
        self.update_cart_display()
        
        # Reset payment fields
        self.cash_entry.delete(0, tk.END)
        self.discount_var.set("0")
    
    def print_receipt(self, order_id):
        # Get order details
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT orders.*, customers.name, customers.email, users.name
        FROM orders
        LEFT JOIN customers ON orders.customer_id = customers.id
        LEFT JOIN users ON orders.user_id = users.id
        WHERE orders.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        
        cursor.execute("""
        SELECT order_items.*, products.name
        FROM order_items
        LEFT JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = ?
        """, (order_id,))
        
        order_items = cursor.fetchall()
        
        # Get business settings
        cursor.execute("SELECT * FROM business_settings LIMIT 1")
        business = cursor.fetchone()
        
        conn.close()
        
        # Create receipt text
        receipt = f"{business[1]}\n"
        receipt += f"{business[2]}\n"
        receipt += f"Phone: {business[3]}\n"
        receipt += f"Email: {business[4]}\n"
        receipt += f"Tax ID: {business[5]}\n"
        receipt += "-" * 30 + "\n"
        receipt += f"Order #: {order[1]}\n"
        receipt += f"Date: {order[6]}\n"
        receipt += f"Cashier: {order[15]}\n"
        
        if order[14]:
            receipt += f"Customer: {order[14]}\n"
        
        receipt += "-" * 30 + "\n"
        
        # Add order items
        for item in order_items:
            item_total = item[3] * item[4]
            receipt += f"{item[10]} x {item[4]} @ ₹{item[3]:.2f} = ₹{item_total:.2f}\n"
        
        receipt += "-" * 30 + "\n"
        receipt += f"Subtotal: ₹{order[7] - order[8] - order[9]:.2f}\n"
        receipt += f"Tax: ₹{order[8]:.2f}\n"
        receipt += f"Discount: ₹{order[9]:.2f}\n"
        receipt += f"Total: ₹{order[7]:.2f}\n"
        receipt += f"Payment: {order[10]}\n"
        
        if order[10] == "Cash":
            try:
                cash = float(self.cash_entry.get() or 0)
                change = cash - order[7]
                receipt += f"Cash: ₹{cash:.2f}\n"
                receipt += f"Change: ₹{change:.2f}\n"
            except ValueError:
                pass
        
        receipt += "-" * 30 + "\n"
        receipt += f"{business[9]}\n"
        
        # Print receipt (in a real implementation, this would send to a thermal printer)
        print(receipt)
        
        # For demo purposes, show receipt in a message box
        messagebox.showinfo("Receipt", receipt)
    
    def email_receipt(self, order_id, customer_id):
        # Get customer email
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM customers WHERE id = ?", (customer_id,))
        customer = cursor.fetchone()
        conn.close()
        
        if not customer or not customer[0]:
            messagebox.showwarning("Warning", "Customer email not found")
            return
        
        email = customer[0]
        
        # In a real implementation, this would send an email
        # For demo purposes, just show a message
        messagebox.showinfo("Email Receipt", f"Receipt would be emailed to {email}")
    
    def hold_order(self):
        if not self.cart:
            messagebox.showwarning("Warning", "Cart is empty")
            return
        
        # Get customer
        customer_name = self.customer_var.get()
        customer_id = None
        
        if customer_name != "Walk-in Customer":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM customers WHERE name = ?", (customer_name,))
            customer = cursor.fetchone()
            conn.close()
            
            if customer:
                customer_id = customer[0]
        
        # Generate order number
        order_number = f"HLD-{datetime.datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"
        
        # Create order in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get tax and discount amounts
        subtotal_text = self.subtotal_label.cget("text")
        subtotal = float(subtotal_text.replace("Subtotal: ₹", ""))
        
        tax_text = self.tax_label.cget("text")
        tax_amount = float(tax_text.replace("Tax: ₹", ""))
        
        discount_text = self.discount_label.cget("text")
        discount_amount = float(discount_text.replace("Discount: ₹", ""))
        
        total = subtotal + tax_amount - discount_amount
        
        # Insert order
        cursor.execute("""
        INSERT INTO orders (
            order_number, user_id, customer_id, table_id, status, 
            order_date, total_amount, tax_amount, discount_amount, 
            payment_method, payment_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number, 
            self.current_user['id'], 
            customer_id, 
            self.current_table, 
            'held',
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total,
            tax_amount,
            discount_amount,
            None,
            'pending'
        ))
        
        order_id = cursor.lastrowid
        
        # Insert order items
        for item in self.cart:
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
        
        conn.commit()
        conn.close()
        
        # Show success message
        messagebox.showinfo("Success", f"Order {order_number} held successfully")
        
        # Clear cart
        self.cart = []
        self.update_cart_display()
    
    def show_recall_order_dialog(self):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Recall Order")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Recall Held Order", style="Title.TLabel").pack(pady=10)
        
        # Search frame
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        search_entry = ttk.Entry(search_frame)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Orders tree
        columns = ("id", "order_number", "date", "customer", "total", "status")
        orders_tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        # Define headings
        orders_tree.heading("id", text="ID")
        orders_tree.heading("order_number", text="Order #")
        orders_tree.heading("date", text="Date")
        orders_tree.heading("customer", text="Customer")
        orders_tree.heading("total", text="Total")
        orders_tree.heading("status", text="Status")
        
        # Define columns
        orders_tree.column("id", width=40, anchor="center")
        orders_tree.column("order_number", width=100)
        orders_tree.column("date", width=150)
        orders_tree.column("customer", width=100)
        orders_tree.column("total", width=70, anchor="e")
        orders_tree.column("status", width=70, anchor="center")
        
        orders_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        recall_btn = ttk.Button(btn_frame, text="Recall", command=lambda: self.recall_order(orders_tree, dialog))
        recall_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Load held orders
        self.load_held_orders(orders_tree)
        
        # Bind search
        def search_orders(event=None):
            search_term = search_entry.get().lower()
            
            # Clear tree
            for item in orders_tree.get_children():
                orders_tree.delete(item)
            
            # Load orders based on search term
            self.load_held_orders(orders_tree, search_term)
        
        search_entry.bind("<KeyRelease>", search_orders)
    
    def load_held_orders(self, tree, search_term=None):
        # Load held orders from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if search_term:
            cursor.execute("""
            SELECT orders.id, orders.order_number, orders.order_date, 
                   customers.name, orders.total_amount, orders.status
            FROM orders
            LEFT JOIN customers ON orders.customer_id = customers.id
            WHERE orders.status = 'held' AND 
                  (orders.order_number LIKE ? OR customers.name LIKE ?)
            ORDER BY orders.order_date DESC
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("""
            SELECT orders.id, orders.order_number, orders.order_date, 
                   customers.name, orders.total_amount, orders.status
            FROM orders
            LEFT JOIN customers ON orders.customer_id = customers.id
            WHERE orders.status = 'held'
            ORDER BY orders.order_date DESC
            """)
        
        orders = cursor.fetchall()
        conn.close()
        
        # Add orders to tree
        for order in orders:
            customer_name = order[3] if order[3] else "Walk-in Customer"
            tree.insert(
                "", 
                "end", 
                values=(
                    order[0],
                    order[1],
                    order[2],
                    customer_name,
                    f"₹{order[4]:.2f}",
                    order[5]
                )
            )
    
    def recall_order(self, tree, dialog):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an order to recall")
            return
        
        order_id = int(tree.item(selected_item[0], 'values')[0])
        
        # Load order items
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT order_items.*, products.name
        FROM order_items
        LEFT JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id = ?
        """, (order_id,))
        
        order_items = cursor.fetchall()
        
        cursor.execute("SELECT customer_id FROM orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        customer_id = order[0] if order and order[0] else None
        
        conn.close()
        
        # Clear current cart
        self.cart = []
        
        # Add order items to cart
        for item in order_items:
            cart_item = {
                'id': item[1],
                'name': item[10],
                'price': item[3],
                'quantity': item[4],
                'tax_rate': item[5]
            }
            self.cart.append(cart_item)
        
        # Set customer
        if customer_id:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM customers WHERE id = ?", (customer_id,))
            customer = cursor.fetchone()
            conn.close()
            
            if customer:
                self.customer_var.set(customer[0])
        
        # Update cart display
        self.update_cart_display()
        
        # Delete the held order
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        
        # Close dialog
        dialog.destroy()
        
        # Show success message
        messagebox.showinfo("Success", "Order recalled successfully")
    
    def show_new_customer_dialog(self):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("New Customer")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="New Customer", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Email
        ttk.Label(form_frame, text="Email:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        email_entry = ttk.Entry(form_frame, width=30)
        email_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Phone
        ttk.Label(form_frame, text="Phone:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        phone_entry = ttk.Entry(form_frame, width=30)
        phone_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # Address
        ttk.Label(form_frame, text="Address:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        address_entry = ttk.Entry(form_frame, width=30)
        address_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.save_customer(
                name_entry.get(), 
                email_entry.get(), 
                phone_entry.get(), 
                address_entry.get(), 
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def save_customer(self, name, email, phone, address, dialog):
        if not name:
            messagebox.showwarning("Warning", "Customer name is required")
            return
        
        # Save customer to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO customers (name, email, phone, address)
        VALUES (?, ?, ?, ?)
        """, (name, email, phone, address))
        
        conn.commit()
        conn.close()
        
        # Update customer combobox
        self.load_customers()
        
        # Set the new customer
        self.customer_var.set(name)
        
        # Close dialog
        dialog.destroy()
        
        # Show success message
        messagebox.showinfo("Success", "Customer saved successfully")
    
    def show_reports_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top navigation bar
        self.create_navbar(main_container)
        
        # Create content frame
        content_frame = ttk.Frame(main_container, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(content_frame, text="Reports", style="Title.TLabel").pack(pady=10)
        
        # Report options
        options_frame = ttk.Frame(content_frame)
        options_frame.pack(fill=tk.X, pady=10)
        
        # Date range
        ttk.Label(options_frame, text="From:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        from_date = ttk.Entry(options_frame, width=15)
        from_date.grid(row=0, column=1, padx=5, pady=5)
        from_date.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(options_frame, text="To:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        to_date = ttk.Entry(options_frame, width=15)
        to_date.grid(row=0, column=3, padx=5, pady=5)
        to_date.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        
        # Report type
        ttk.Label(options_frame, text="Report Type:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        report_type = ttk.Combobox(options_frame, width=15)
        report_type.grid(row=1, column=1, padx=5, pady=5)
        report_type['values'] = ["Sales Summary", "Sales by Category", "Sales by Product", "Payment Methods"]
        report_type.current(0)
        
        # Generate button
        generate_btn = ttk.Button(
            options_frame, 
            text="Generate Report", 
            command=lambda: self.generate_report(
                from_date.get(), 
                to_date.get(), 
                report_type.get()
            )
        )
        generate_btn.grid(row=1, column=2, columnspan=2, padx=5, pady=5)
        
        # Export button
        export_btn = ttk.Button(
            options_frame, 
            text="Export to CSV", 
            command=lambda: self.export_report(
                from_date.get(), 
                to_date.get(), 
                report_type.get()
            )
        )
        export_btn.grid(row=1, column=4, padx=5, pady=5)
        
        # Report display
        self.report_frame = ttk.Frame(content_frame)
        self.report_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Generate initial report
        self.generate_report(from_date.get(), to_date.get(), report_type.get())
    
    def generate_report(self, from_date, to_date, report_type):
        # Clear report frame
        for widget in self.report_frame.winfo_children():
            widget.destroy()
        
        # Validate dates
        try:
            from_dt = datetime.datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.datetime.strptime(to_date, "%Y-%m-%d")
            
            if from_dt > to_dt:
                messagebox.showwarning("Warning", "From date cannot be after to date")
                return
        except ValueError:
            messagebox.showwarning("Warning", "Invalid date format. Use YYYY-MM-DD")
            return
        
        # Generate report based on type
        if report_type == "Sales Summary":
            self.generate_sales_summary_report(from_date, to_date)
        elif report_type == "Sales by Category":
            self.generate_sales_by_category_report(from_date, to_date)
        elif report_type == "Sales by Product":
            self.generate_sales_by_product_report(from_date, to_date)
        elif report_type == "Payment Methods":
            self.generate_payment_methods_report(from_date, to_date)
    
    def generate_sales_summary_report(self, from_date, to_date):
        # Create treeview for report
        columns = ("date", "orders", "sales", "tax", "discount", "net_sales")
        tree = ttk.Treeview(self.report_frame, columns=columns, show="headings")
        
        # Define headings
        tree.heading("date", text="Date")
        tree.heading("orders", text="Orders")
        tree.heading("sales", text="Sales")
        tree.heading("tax", text="Tax")
        tree.heading("discount", text="Discount")
        tree.heading("net_sales", text="Net Sales")
        
        # Define columns
        tree.column("date", width=100)
        tree.column("orders", width=70, anchor="e")
        tree.column("sales", width=100, anchor="e")
        tree.column("tax", width=100, anchor="e")
        tree.column("discount", width=100, anchor="e")
        tree.column("net_sales", width=100, anchor="e")
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get daily sales summary
        cursor.execute("""
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
        """, (from_date, to_date))
        
        daily_sales = cursor.fetchall()
        
        # Get totals
        cursor.execute("""
        SELECT 
            COUNT(id) as orders,
            SUM(total_amount) as sales,
            SUM(tax_amount) as tax,
            SUM(discount_amount) as discount,
            SUM(total_amount - discount_amount) as net_sales
        FROM orders
        WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
        """, (from_date, to_date))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Add data to tree
        for row in daily_sales:
            tree.insert(
                "", 
                "end", 
                values=(
                    row[0],
                    row[1],
                    f"₹{row[2]:.2f}",
                    f"₹{row[3]:.2f}",
                    f"₹{row[4]:.2f}",
                    f"₹{row[5]:.2f}"
                )
            )
        
        # Add totals row
        tree.insert(
            "", 
            "end", 
            values=(
                "TOTAL",
                totals[0],
                f"₹{totals[1]:.2f}",
                f"₹{totals[2]:.2f}",
                f"₹{totals[3]:.2f}",
                f"₹{totals[4]:.2f}"
            )
        )
    
    def generate_sales_by_category_report(self, from_date, to_date):
        # Create treeview for report
        columns = ("category", "items_sold", "sales", "tax", "discount", "net_sales")
        tree = ttk.Treeview(self.report_frame, columns=columns, show="headings")
        
        # Define headings
        tree.heading("category", text="Category")
        tree.heading("items_sold", text="Items Sold")
        tree.heading("sales", text="Sales")
        tree.heading("tax", text="Tax")
        tree.heading("discount", text="Discount")
        tree.heading("net_sales", text="Net Sales")
        
        # Define columns
        tree.column("category", width=150)
        tree.column("items_sold", width=100, anchor="e")
        tree.column("sales", width=100, anchor="e")
        tree.column("tax", width=100, anchor="e")
        tree.column("discount", width=100, anchor="e")
        tree.column("net_sales", width=100, anchor="e")
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get sales by category
        cursor.execute("""
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
        """, (from_date, to_date))
        
        category_sales = cursor.fetchall()
        
        # Get totals
        cursor.execute("""
        SELECT 
            SUM(oi.quantity) as items_sold,
            SUM(oi.quantity * oi.price) as sales,
            SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
            SUM(o.discount_amount) as discount,
            SUM(o.total_amount - o.discount_amount) as net_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
        """, (from_date, to_date))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Add data to tree
        for row in category_sales:
            tree.insert(
                "", 
                "end", 
                values=(
                    row[0] if row[0] else "Uncategorized",
                    f"{row[1]:.2f}",
                    f"₹{row[2]:.2f}",
                    f"₹{row[3]:.2f}",
                    f"₹{row[4]:.2f}",
                    f"₹{row[5]:.2f}"
                )
            )
        
        # Add totals row
        tree.insert(
            "", 
            "end", 
            values=(
                "TOTAL",
                f"{totals[0]:.2f}",
                f"₹{totals[1]:.2f}",
                f"₹{totals[2]:.2f}",
                f"₹{totals[3]:.2f}",
                f"₹{totals[4]:.2f}"
            )
        )
    
    def generate_sales_by_product_report(self, from_date, to_date):
        # Create treeview for report
        columns = ("product", "category", "quantity", "sales", "tax", "discount", "net_sales")
        tree = ttk.Treeview(self.report_frame, columns=columns, show="headings")
        
        # Define headings
        tree.heading("product", text="Product")
        tree.heading("category", text="Category")
        tree.heading("quantity", text="Quantity")
        tree.heading("sales", text="Sales")
        tree.heading("tax", text="Tax")
        tree.heading("discount", text="Discount")
        tree.heading("net_sales", text="Net Sales")
        
        # Define columns
        tree.column("product", width=150)
        tree.column("category", width=100)
        tree.column("quantity", width=70, anchor="e")
        tree.column("sales", width=100, anchor="e")
        tree.column("tax", width=100, anchor="e")
        tree.column("discount", width=100, anchor="e")
        tree.column("net_sales", width=100, anchor="e")
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get sales by product
        cursor.execute("""
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
        """, (from_date, to_date))
        
        product_sales = cursor.fetchall()
        
        # Get totals
        cursor.execute("""
        SELECT 
            SUM(oi.quantity) as quantity,
            SUM(oi.quantity * oi.price) as sales,
            SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
            SUM(o.discount_amount) as discount,
            SUM(o.total_amount - o.discount_amount) as net_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
        """, (from_date, to_date))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Add data to tree
        for row in product_sales:
            tree.insert(
                "", 
                "end", 
                values=(
                    row[0],
                    row[1] if row[1] else "Uncategorized",
                    f"{row[2]:.2f}",
                    f"₹{row[3]:.2f}",
                    f"₹{row[4]:.2f}",
                    f"₹{row[5]:.2f}",
                    f"₹{row[6]:.2f}"
                )
            )
        
        # Add totals row
        tree.insert(
            "", 
            "end", 
            values=(
                "TOTAL",
                "",
                f"{totals[0]:.2f}",
                f"₹{totals[1]:.2f}",
                f"₹{totals[2]:.2f}",
                f"₹{totals[3]:.2f}",
                f"₹{totals[4]:.2f}"
            )
        )
    
    def generate_payment_methods_report(self, from_date, to_date):
        # Create treeview for report
        columns = ("payment_method", "transactions", "amount", "percentage")
        tree = ttk.Treeview(self.report_frame, columns=columns, show="headings")
        
        # Define headings
        tree.heading("payment_method", text="Payment Method")
        tree.heading("transactions", text="Transactions")
        tree.heading("amount", text="Amount")
        tree.heading("percentage", text="Percentage")
        
        # Define columns
        tree.column("payment_method", width=150)
        tree.column("transactions", width=100, anchor="e")
        tree.column("amount", width=100, anchor="e")
        tree.column("percentage", width=100, anchor="e")
        
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Get data from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get payment methods summary
        cursor.execute("""
        SELECT 
            payment_method,
            COUNT(id) as transactions,
            SUM(total_amount) as amount
        FROM orders
        WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
        GROUP BY payment_method
        ORDER BY amount DESC
        """, (from_date, to_date))
        
        payment_methods = cursor.fetchall()
        
        # Get total amount
        cursor.execute("""
        SELECT SUM(total_amount) as total
        FROM orders
        WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
        """, (from_date, to_date))
        
        total_amount = cursor.fetchone()[0]
        conn.close()
        
        # Add data to tree
        for row in payment_methods:
            percentage = (row[2] / total_amount) * 100 if total_amount > 0 else 0
            tree.insert(
                "", 
                "end", 
                values=(
                    row[0],
                    row[1],
                    f"₹{row[2]:.2f}",
                    f"{percentage:.1f}%"
                )
            )
        
        # Add totals row
        tree.insert(
            "", 
            "end", 
            values=(
                "TOTAL",
                "",
                f"₹{total_amount:.2f}",
                "100%"
            )
        )
    
    def export_report(self, from_date, to_date, report_type):
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Report"
        )
        
        if not file_path:
            return
        
        # Get report data based on type
        if report_type == "Sales Summary":
            data = self.get_sales_summary_data(from_date, to_date)
        elif report_type == "Sales by Category":
            data = self.get_sales_by_category_data(from_date, to_date)
        elif report_type == "Sales by Product":
            data = self.get_sales_by_product_data(from_date, to_date)
        elif report_type == "Payment Methods":
            data = self.get_payment_methods_data(from_date, to_date)
        else:
            messagebox.showwarning("Warning", "Invalid report type")
            return
        
        # Write data to CSV file
        try:
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(data['header'])
                
                # Write data rows
                for row in data['rows']:
                    writer.writerow(row)
            
            messagebox.showinfo("Success", f"Report exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export report: {str(e)}")
    
    def get_sales_summary_data(self, from_date, to_date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get daily sales summary
        cursor.execute("""
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
        """, (from_date, to_date))
        
        daily_sales = cursor.fetchall()
        
        # Get totals
        cursor.execute("""
        SELECT 
            COUNT(id) as orders,
            SUM(total_amount) as sales,
            SUM(tax_amount) as tax,
            SUM(discount_amount) as discount,
            SUM(total_amount - discount_amount) as net_sales
        FROM orders
        WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
        """, (from_date, to_date))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Prepare data
        header = ["Date", "Orders", "Sales", "Tax", "Discount", "Net Sales"]
        rows = []
        
        for row in daily_sales:
            rows.append([
                row[0],
                row[1],
                f"{row[2]:.2f}",
                f"{row[3]:.2f}",
                f"{row[4]:.2f}",
                f"{row[5]:.2f}"
            ])
        
        # Add totals row
        rows.append([
            "TOTAL",
            totals[0],
            f"{totals[1]:.2f}",
            f"{totals[2]:.2f}",
            f"{totals[3]:.2f}",
            f"{totals[4]:.2f}"
        ])
        
        return {
            'header': header,
            'rows': rows
        }
    
    def get_sales_by_category_data(self, from_date, to_date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get sales by category
        cursor.execute("""
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
        """, (from_date, to_date))
        
        category_sales = cursor.fetchall()
        
        # Get totals
        cursor.execute("""
        SELECT 
            SUM(oi.quantity) as items_sold,
            SUM(oi.quantity * oi.price) as sales,
            SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
            SUM(o.discount_amount) as discount,
            SUM(o.total_amount - o.discount_amount) as net_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
        """, (from_date, to_date))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Prepare data
        header = ["Category", "Items Sold", "Sales", "Tax", "Discount", "Net Sales"]
        rows = []
        
        for row in category_sales:
            rows.append([
                row[0] if row[0] else "Uncategorized",
                f"{row[1]:.2f}",
                f"{row[2]:.2f}",
                f"{row[3]:.2f}",
                f"{row[4]:.2f}",
                f"{row[5]:.2f}"
            ])
        
        # Add totals row
        rows.append([
            "TOTAL",
            f"{totals[0]:.2f}",
            f"{totals[1]:.2f}",
            f"{totals[2]:.2f}",
            f"{totals[3]:.2f}",
            f"{totals[4]:.2f}"
        ])
        
        return {
            'header': header,
            'rows': rows
        }
    
    def get_sales_by_product_data(self, from_date, to_date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get sales by product
        cursor.execute("""
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
        """, (from_date, to_date))
        
        product_sales = cursor.fetchall()
        
        # Get totals
        cursor.execute("""
        SELECT 
            SUM(oi.quantity) as quantity,
            SUM(oi.quantity * oi.price) as sales,
            SUM(oi.quantity * oi.price * oi.tax_rate / 100) as tax,
            SUM(o.discount_amount) as discount,
            SUM(o.total_amount - o.discount_amount) as net_sales
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.order_date) BETWEEN ? AND ? AND o.status = 'completed'
        """, (from_date, to_date))
        
        totals = cursor.fetchone()
        conn.close()
        
        # Prepare data
        header = ["Product", "Category", "Quantity", "Sales", "Tax", "Discount", "Net Sales"]
        rows = []
        
        for row in product_sales:
            rows.append([
                row[0],
                row[1] if row[1] else "Uncategorized",
                f"{row[2]:.2f}",
                f"{row[3]:.2f}",
                f"{row[4]:.2f}",
                f"{row[5]:.2f}",
                f"{row[6]:.2f}"
            ])
        
        # Add totals row
        rows.append([
            "TOTAL",
            "",
            f"{totals[0]:.2f}",
            f"{totals[1]:.2f}",
            f"{totals[2]:.2f}",
            f"{totals[3]:.2f}",
            f"{totals[4]:.2f}"
        ])
        
        return {
            'header': header,
            'rows': rows
        }
    
    def get_payment_methods_data(self, from_date, to_date):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get payment methods summary
        cursor.execute("""
        SELECT 
            payment_method,
            COUNT(id) as transactions,
            SUM(total_amount) as amount
        FROM orders
        WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
        GROUP BY payment_method
        ORDER BY amount DESC
        """, (from_date, to_date))
        
        payment_methods = cursor.fetchall()
        
        # Get total amount
        cursor.execute("""
        SELECT SUM(total_amount) as total
        FROM orders
        WHERE DATE(order_date) BETWEEN ? AND ? AND status = 'completed'
        """, (from_date, to_date))
        
        total_amount = cursor.fetchone()[0]
        conn.close()
        
        # Prepare data
        header = ["Payment Method", "Transactions", "Amount", "Percentage"]
        rows = []
        
        for row in payment_methods:
            percentage = (row[2] / total_amount) * 100 if total_amount > 0 else 0
            rows.append([
                row[0],
                row[1],
                f"{row[2]:.2f}",
                f"{percentage:.1f}%"
            ])
        
        # Add totals row
        rows.append([
            "TOTAL",
            "",
            f"{total_amount:.2f}",
            "100%"
        ])
        
        return {
            'header': header,
            'rows': rows
        }
    
    def show_inventory_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top navigation bar
        self.create_navbar(main_container)
        
        # Create content frame
        content_frame = ttk.Frame(main_container, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(content_frame, text="Inventory Management", style="Title.TLabel").pack(pady=10)
        
        # Toolbar
        toolbar = ttk.Frame(content_frame)
        toolbar.pack(fill=tk.X, pady=10)
        
        # Search
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=5)
        search_entry = ttk.Entry(toolbar)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Category filter
        ttk.Label(toolbar, text="Category:").pack(side=tk.LEFT, padx=5)
        category_var = tk.StringVar()
        category_combobox = ttk.Combobox(toolbar, textvariable=category_var, width=15)
        category_combobox.pack(side=tk.LEFT, padx=5)
        
        # Load categories
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_values = ["All"] + [cat[0] for cat in categories]
        category_combobox['values'] = category_values
        category_combobox.current(0)
        
        # Buttons
        add_btn = ttk.Button(toolbar, text="Add Product", command=self.show_add_product_dialog)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        import_btn = ttk.Button(toolbar, text="Import CSV", command=self.import_products_csv)
        import_btn.pack(side=tk.LEFT, padx=5)
        
        export_btn = ttk.Button(toolbar, text="Export CSV", command=self.export_products_csv)
        export_btn.pack(side=tk.LEFT, padx=5)
        
        # Inventory tree
        columns = ("id", "name", "category", "price", "cost", "stock", "min_stock", "status", "actions")
        self.inventory_tree = ttk.Treeview(content_frame, columns=columns, show="headings")
        
        # Define headings
        self.inventory_tree.heading("id", text="ID")
        self.inventory_tree.heading("name", text="Product")
        self.inventory_tree.heading("category", text="Category")
        self.inventory_tree.heading("price", text="Price")
        self.inventory_tree.heading("cost", text="Cost")
        self.inventory_tree.heading("stock", text="Stock")
        self.inventory_tree.heading("min_stock", text="Min Stock")
        self.inventory_tree.heading("status", text="Status")
        self.inventory_tree.heading("actions", text="Actions")
        
        # Define columns
        self.inventory_tree.column("id", width=40, anchor="center")
        self.inventory_tree.column("name", width=150)
        self.inventory_tree.column("category", width=100)
        self.inventory_tree.column("price", width=70, anchor="e")
        self.inventory_tree.column("cost", width=70, anchor="e")
        self.inventory_tree.column("stock", width=70, anchor="e")
        self.inventory_tree.column("min_stock", width=70, anchor="e")
        self.inventory_tree.column("status", width=70, anchor="center")
        self.inventory_tree.column("actions", width=150, anchor="center")
        
        self.inventory_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Load products
        self.load_inventory_products()
        
        # Bind search
        def search_products(event=None):
            search_term = search_entry.get().lower()
            category = category_var.get()
            
            # Clear tree
            for item in self.inventory_tree.get_children():
                self.inventory_tree.delete(item)
            
            # Load products based on search and category
            self.load_inventory_products(search_term, category)
        
        search_entry.bind("<KeyRelease>", search_products)
        category_combobox.bind("<<ComboboxSelected>>", search_products)
    
    def load_inventory_products(self, search_term=None, category=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query based on filters
        query = """
        SELECT p.id, p.name, c.name, p.price, p.cost_price, p.stock, p.min_stock, p.active
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE 1=1
        """
        params = []
        
        if search_term:
            query += " AND (LOWER(p.name) LIKE ? OR LOWER(p.description) LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if category and category != "All":
            query += " AND c.name = ?"
            params.append(category)
        
        query += " ORDER BY p.name"
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        conn.close()
        
        # Add products to tree
        for product in products:
            status = "Active" if product[7] else "Inactive"
            status_color = "green" if product[7] else "red"
            
            # Check if stock is low
            stock_color = "black"
            if product[5] > 0 and product[6] >= product[5]:
                stock_color = "orange"
            elif product[5] == 0:
                stock_color = "red"
            
            item_id = self.inventory_tree.insert(
                "", 
                "end", 
                values=(
                    product[0],
                    product[1],
                    product[2] if product[2] else "Uncategorized",
                    f"₹{product[3]:.2f}",
                    f"₹{product[4]:.2f}" if product[4] else "N/A",
                    product[5],
                    product[6],
                    status,
                    ""  # Actions will be added as buttons
                )
            )
            
            # Add action buttons
            edit_btn = ttk.Button(
                self.inventory_tree, 
                text="Edit", 
                command=lambda p=product[0]: self.show_edit_product_dialog(p)
            )
            
            toggle_btn = ttk.Button(
                self.inventory_tree, 
                text="Disable" if product[7] else "Enable", 
                command=lambda p=product[0], s=product[7]: self.toggle_product_status(p, s)
            )
            
            self.inventory_tree.set(item_id, "actions", "")
            self.inventory_tree.window(item_id, "actions", window=edit_btn)
            self.inventory_tree.window(item_id, "actions", window=toggle_btn)
    
    def show_add_product_dialog(self):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Product")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Add New Product", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(form_frame, text="Name*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Description
        ttk.Label(form_frame, text="Description:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        description_entry = ttk.Entry(form_frame, width=30)
        description_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Category
        ttk.Label(form_frame, text="Category:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        category_var = tk.StringVar()
        category_combobox = ttk.Combobox(form_frame, textvariable=category_var, width=28)
        category_combobox.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # Load categories
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_values = [(cat[0], cat[1]) for cat in categories]
        category_combobox['values'] = [cat[1] for cat in categories]
        if category_values:
            category_combobox.current(0)
        
        # Price
        ttk.Label(form_frame, text="Price*:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        price_entry = ttk.Entry(form_frame, width=30)
        price_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # Cost Price
        ttk.Label(form_frame, text="Cost Price:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        cost_price_entry = ttk.Entry(form_frame, width=30)
        cost_price_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        
        # Stock
        ttk.Label(form_frame, text="Stock*:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        stock_entry = ttk.Entry(form_frame, width=30)
        stock_entry.grid(row=5, column=1, padx=10, pady=10, sticky="ew")
        stock_entry.insert(0, "0")
        
        # Min Stock
        ttk.Label(form_frame, text="Min Stock:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        min_stock_entry = ttk.Entry(form_frame, width=30)
        min_stock_entry.grid(row=6, column=1, padx=10, pady=10, sticky="ew")
        min_stock_entry.insert(0, "0")
        
        # Barcode
        ttk.Label(form_frame, text="Barcode:").grid(row=7, column=0, padx=10, pady=10, sticky="w")
        barcode_entry = ttk.Entry(form_frame, width=30)
        barcode_entry.grid(row=7, column=1, padx=10, pady=10, sticky="ew")
        
        # Tax Rate
        ttk.Label(form_frame, text="Tax Rate (%):").grid(row=8, column=0, padx=10, pady=10, sticky="w")
        tax_rate_entry = ttk.Entry(form_frame, width=30)
        tax_rate_entry.grid(row=8, column=1, padx=10, pady=10, sticky="ew")
        tax_rate_entry.insert(0, "0")
        
        # Active
        active_var = tk.BooleanVar(value=True)
        active_check = ttk.Checkbutton(form_frame, text="Active", variable=active_var)
        active_check.grid(row=9, column=1, padx=10, pady=10, sticky="w")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.save_product(
                name_entry.get(),
                description_entry.get(),
                category_var.get(),
                price_entry.get(),
                cost_price_entry.get(),
                stock_entry.get(),
                min_stock_entry.get(),
                barcode_entry.get(),
                tax_rate_entry.get(),
                active_var.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def save_product(self, name, description, category_name, price, cost_price, stock, min_stock, barcode, tax_rate, active, dialog):
        # Validate required fields
        if not name:
            messagebox.showwarning("Warning", "Product name is required")
            return
        
        try:
            price = float(price)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid price")
            return
        
        try:
            stock = int(stock)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid stock quantity")
            return
        
        try:
            min_stock = int(min_stock)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid minimum stock")
            return
        
        try:
            tax_rate = float(tax_rate)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid tax rate")
            return
        
        # Get category ID
        category_id = None
        if category_name:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            category = cursor.fetchone()
            conn.close()
            
            if category:
                category_id = category[0]
        
        # Save product to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO products (
            name, description, category_id, price, cost_price, stock, 
            min_stock, barcode, tax_rate, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, description, category_id, price, cost_price, stock,
            min_stock, barcode, tax_rate, active
        ))
        
        conn.commit()
        conn.close()
        
        # Close dialog
        dialog.destroy()
        
        # Refresh inventory
        self.load_inventory_products()
        
        # Show success message
        messagebox.showinfo("Success", "Product added successfully")
    
    def show_edit_product_dialog(self, product_id):
        # Get product details
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = ?
        """, (product_id,))
        
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            messagebox.showwarning("Warning", "Product not found")
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Product")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Edit Product", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(form_frame, text="Name*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        name_entry.insert(0, product[1])
        
        # Description
        ttk.Label(form_frame, text="Description:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        description_entry = ttk.Entry(form_frame, width=30)
        description_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        description_entry.insert(0, product[2] or "")
        
        # Category
        ttk.Label(form_frame, text="Category:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        category_var = tk.StringVar()
        category_combobox = ttk.Combobox(form_frame, textvariable=category_var, width=28)
        category_combobox.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # Load categories
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories ORDER BY name")
        categories = cursor.fetchall()
        conn.close()
        
        category_values = [(cat[0], cat[1]) for cat in categories]
        category_combobox['values'] = [cat[1] for cat in categories]
        
        # Set current category
        if product[12]:
            category_var.set(product[12])
        elif category_values:
            category_combobox.current(0)
        
        # Price
        ttk.Label(form_frame, text="Price*:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        price_entry = ttk.Entry(form_frame, width=30)
        price_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        price_entry.insert(0, str(product[3]))
        
        # Cost Price
        ttk.Label(form_frame, text="Cost Price:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        cost_price_entry = ttk.Entry(form_frame, width=30)
        cost_price_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        cost_price_entry.insert(0, str(product[4]) if product[4] else "")
        
        # Stock
        ttk.Label(form_frame, text="Stock*:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        stock_entry = ttk.Entry(form_frame, width=30)
        stock_entry.grid(row=5, column=1, padx=10, pady=10, sticky="ew")
        stock_entry.insert(0, str(product[6]))
        
        # Min Stock
        ttk.Label(form_frame, text="Min Stock:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        min_stock_entry = ttk.Entry(form_frame, width=30)
        min_stock_entry.grid(row=6, column=1, padx=10, pady=10, sticky="ew")
        min_stock_entry.insert(0, str(product[7]))
        
        # Barcode
        ttk.Label(form_frame, text="Barcode:").grid(row=7, column=0, padx=10, pady=10, sticky="w")
        barcode_entry = ttk.Entry(form_frame, width=30)
        barcode_entry.grid(row=7, column=1, padx=10, pady=10, sticky="ew")
        barcode_entry.insert(0, product[8] or "")
        
        # Tax Rate
        ttk.Label(form_frame, text="Tax Rate (%):").grid(row=8, column=0, padx=10, pady=10, sticky="w")
        tax_rate_entry = ttk.Entry(form_frame, width=30)
        tax_rate_entry.grid(row=8, column=1, padx=10, pady=10, sticky="ew")
        tax_rate_entry.insert(0, str(product[11]))
        
        # Active
        active_var = tk.BooleanVar(value=bool(product[12]))
        active_check = ttk.Checkbutton(form_frame, text="Active", variable=active_var)
        active_check.grid(row=9, column=1, padx=10, pady=10, sticky="w")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.update_product(
                product_id,
                name_entry.get(),
                description_entry.get(),
                category_var.get(),
                price_entry.get(),
                cost_price_entry.get(),
                stock_entry.get(),
                min_stock_entry.get(),
                barcode_entry.get(),
                tax_rate_entry.get(),
                active_var.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def update_product(self, product_id, name, description, category_name, price, cost_price, stock, min_stock, barcode, tax_rate, active, dialog):
        # Validate required fields
        if not name:
            messagebox.showwarning("Warning", "Product name is required")
            return
        
        try:
            price = float(price)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid price")
            return
        
        try:
            stock = int(stock)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid stock quantity")
            return
        
        try:
            min_stock = int(min_stock)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid minimum stock")
            return
        
        try:
            tax_rate = float(tax_rate)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid tax rate")
            return
        
        # Get category ID
        category_id = None
        if category_name:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
            category = cursor.fetchone()
            conn.close()
            
            if category:
                category_id = category[0]
        
        # Update product in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE products SET
            name = ?, description = ?, category_id = ?, price = ?, cost_price = ?, 
            stock = ?, min_stock = ?, barcode = ?, tax_rate = ?, active = ?
        WHERE id = ?
        """, (
            name, description, category_id, price, cost_price, stock,
            min_stock, barcode, tax_rate, active, product_id
        ))
        
        conn.commit()
        conn.close()
        
        # Close dialog
        dialog.destroy()
        
        # Refresh inventory
        self.load_inventory_products()
        
        # Show success message
        messagebox.showinfo("Success", "Product updated successfully")
    
    def toggle_product_status(self, product_id, current_status):
        # Toggle product status
        new_status = not current_status
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE products SET active = ? WHERE id = ?
        """, (new_status, product_id))
        
        conn.commit()
        conn.close()
        
        # Refresh inventory
        self.load_inventory_products()
        
        # Show success message
        status_text = "enabled" if new_status else "disabled"
        messagebox.showinfo("Success", f"Product {status_text} successfully")
    
    def import_products_csv(self):
        # Ask for file location
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Import Products"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Get categories
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM categories")
                categories = {cat[1]: cat[0] for cat in cursor.fetchall()}
                
                imported_count = 0
                skipped_count = 0
                
                for row in reader:
                    # Check if product already exists
                    cursor.execute("SELECT id FROM products WHERE name = ?", (row.get('name', ''),))
                    if cursor.fetchone():
                        skipped_count += 1
                        continue
                    
                    # Get category ID
                    category_name = row.get('category', '')
                    category_id = categories.get(category_name) if category_name else None
                    
                    # If category doesn't exist, create it
                    if category_name and not category_id:
                        cursor.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
                        category_id = cursor.lastrowid
                        categories[category_name] = category_id
                    
                    # Insert product
                    cursor.execute("""
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
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo(
                    "Import Complete", 
                    f"Imported {imported_count} products. Skipped {skipped_count} products."
                )
                
                # Refresh inventory
                self.load_inventory_products()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import products: {str(e)}")
    
    def export_products_csv(self):
        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Products"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = [
                    'name', 'description', 'category', 'price', 'cost_price', 
                    'stock', 'min_stock', 'barcode', 'tax_rate', 'active'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                
                # Get products from database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.name
                """)
                
                products = cursor.fetchall()
                conn.close()
                
                for product in products:
                    writer.writerow({
                        'name': product[1],
                        'description': product[2] or '',
                        'category': product[13] or '',
                        'price': product[3],
                        'cost_price': product[4] or '',
                        'stock': product[6],
                        'min_stock': product[7],
                        'barcode': product[8] or '',
                        'tax_rate': product[11],
                        'active': int(product[12])
                    })
            
            messagebox.showinfo("Export Complete", f"Products exported to {file_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export products: {str(e)}")
    
    def show_settings_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top navigation bar
        self.create_navbar(main_container)
        
        # Create content frame
        content_frame = ttk.Frame(main_container, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(content_frame, text="Business Settings", style="Title.TLabel").pack(pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # General settings tab
        general_frame = ttk.Frame(notebook, padding=20)
        notebook.add(general_frame, text="General")
        
        # Get current settings
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM business_settings LIMIT 1")
        settings = cursor.fetchone()
        conn.close()
        
        # Form fields
        form_frame = ttk.Frame(general_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Business name
        ttk.Label(form_frame, text="Business Name*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=40)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        name_entry.insert(0, settings[1])
        
        # Address
        ttk.Label(form_frame, text="Address:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        address_entry = ttk.Entry(form_frame, width=40)
        address_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        address_entry.insert(0, settings[2] or "")
        
        # Phone
        ttk.Label(form_frame, text="Phone:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        phone_entry = ttk.Entry(form_frame, width=40)
        phone_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        phone_entry.insert(0, settings[3] or "")
        
        # Email
        ttk.Label(form_frame, text="Email:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        email_entry = ttk.Entry(form_frame, width=40)
        email_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        email_entry.insert(0, settings[4] or "")
        
        # Tax ID
        ttk.Label(form_frame, text="Tax ID:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        tax_id_entry = ttk.Entry(form_frame, width=40)
        tax_id_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        tax_id_entry.insert(0, settings[5] or "")
        
        # Currency
        ttk.Label(form_frame, text="Currency:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        currency_var = tk.StringVar(value=settings[6])
        currency_combobox = ttk.Combobox(form_frame, textvariable=currency_var, width=10)
        currency_combobox.grid(row=5, column=1, padx=10, pady=10, sticky="w")
        currency_combobox['values'] = ["₹", "$", "€", "£", "¥"]
        
        # Receipt footer
        ttk.Label(form_frame, text="Receipt Footer:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        footer_entry = ttk.Entry(form_frame, width=40)
        footer_entry.grid(row=6, column=1, padx=10, pady=10, sticky="ew")
        footer_entry.insert(0, settings[9] or "")
        
        # Tax inclusive
        tax_inclusive_var = tk.BooleanVar(value=bool(settings[10]))
        tax_inclusive_check = ttk.Checkbutton(
            form_frame, 
            text="Tax Inclusive Pricing", 
            variable=tax_inclusive_var
        )
        tax_inclusive_check.grid(row=7, column=1, padx=10, pady=10, sticky="w")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(general_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save Settings", 
            command=lambda: self.save_business_settings(
                name_entry.get(),
                address_entry.get(),
                phone_entry.get(),
                email_entry.get(),
                tax_id_entry.get(),
                currency_var.get(),
                footer_entry.get(),
                tax_inclusive_var.get()
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Tax settings tab
        tax_frame = ttk.Frame(notebook, padding=20)
        notebook.add(tax_frame, text="Tax Rates")
        
        # Tax rates tree
        columns = ("id", "name", "rate", "actions")
        tax_tree = ttk.Treeview(tax_frame, columns=columns, show="headings")
        
        # Define headings
        tax_tree.heading("id", text="ID")
        tax_tree.heading("name", text="Name")
        tax_tree.heading("rate", text="Rate (%)")
        tax_tree.heading("actions", text="Actions")
        
        # Define columns
        tax_tree.column("id", width=40, anchor="center")
        tax_tree.column("name", width=150)
        tax_tree.column("rate", width=100, anchor="e")
        tax_tree.column("actions", width=150, anchor="center")
        
        tax_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Add tax rate button
        add_tax_btn = ttk.Button(tax_frame, text="Add Tax Rate", command=self.show_add_tax_rate_dialog)
        add_tax_btn.pack(pady=5)
        
        # Load tax rates
        self.load_tax_rates(tax_tree)
    
    def save_business_settings(self, name, address, phone, email, tax_id, currency, footer, tax_inclusive):
        if not name:
            messagebox.showwarning("Warning", "Business name is required")
            return
        
        # Update settings in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE business_settings SET
            name = ?, address = ?, phone = ?, email = ?, tax_id = ?,
            currency = ?, receipt_footer = ?, tax_inclusive = ?
        """, (name, address, phone, email, tax_id, currency, footer, tax_inclusive))
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("Success", "Settings saved successfully")
    
    def load_tax_rates(self, tree):
        # Clear tree
        for item in tree.get_children():
            tree.delete(item)
        
        # For this demo, we'll use hardcoded tax rates
        # In a real implementation, these would be stored in a database table
        tax_rates = [
            (1, "GST 0%", 0),
            (2, "GST 5%", 5),
            (3, "GST 12%", 12),
            (4, "GST 18%", 18),
            (5, "GST 28%", 28)
        ]
        
        # Add tax rates to tree
        for tax in tax_rates:
            item_id = tree.insert(
                "", 
                "end", 
                values=(
                    tax[0],
                    tax[1],
                    f"{tax[2]:.2f}",
                    ""  # Actions will be added as buttons
                )
            )
            
            # Add action buttons
            edit_btn = ttk.Button(
                tree, 
                text="Edit", 
                command=lambda t=tax: self.show_edit_tax_rate_dialog(t)
            )
            
            tree.set(item_id, "actions", "")
            tree.window(item_id, "actions", window=edit_btn)
    
    def show_add_tax_rate_dialog(self):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Tax Rate")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Add Tax Rate", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(form_frame, text="Name*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Rate
        ttk.Label(form_frame, text="Rate (%)*:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        rate_entry = ttk.Entry(form_frame, width=30)
        rate_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.save_tax_rate(
                name_entry.get(),
                rate_entry.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def save_tax_rate(self, name, rate, dialog):
        if not name:
            messagebox.showwarning("Warning", "Tax rate name is required")
            return
        
        try:
            rate = float(rate)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid tax rate")
            return
        
        # In a real implementation, this would save to a database table
        # For this demo, we'll just show a success message
        messagebox.showinfo("Success", "Tax rate added successfully")
        dialog.destroy()
    
    def show_edit_tax_rate_dialog(self, tax_rate):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Tax Rate")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Edit Tax Rate", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Name
        ttk.Label(form_frame, text="Name*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        name_entry.insert(0, tax_rate[1])
        
        # Rate
        ttk.Label(form_frame, text="Rate (%)*:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        rate_entry = ttk.Entry(form_frame, width=30)
        rate_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        rate_entry.insert(0, str(tax_rate[2]))
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.update_tax_rate(
                tax_rate[0],
                name_entry.get(),
                rate_entry.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def update_tax_rate(self, tax_id, name, rate, dialog):
        if not name:
            messagebox.showwarning("Warning", "Tax rate name is required")
            return
        
        try:
            rate = float(rate)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid tax rate")
            return
        
        # In a real implementation, this would update a database table
        # For this demo, we'll just show a success message
        messagebox.showinfo("Success", "Tax rate updated successfully")
        dialog.destroy()
    
    def show_users_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top navigation bar
        self.create_navbar(main_container)
        
        # Create content frame
        content_frame = ttk.Frame(main_container, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(content_frame, text="User Management", style="Title.TLabel").pack(pady=10)
        
        # Toolbar
        toolbar = ttk.Frame(content_frame)
        toolbar.pack(fill=tk.X, pady=10)
        
        add_btn = ttk.Button(toolbar, text="Add User", command=self.show_add_user_dialog)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        # Users tree
        columns = ("id", "username", "name", "role", "email", "phone", "status", "actions")
        self.users_tree = ttk.Treeview(content_frame, columns=columns, show="headings")
        
        # Define headings
        self.users_tree.heading("id", text="ID")
        self.users_tree.heading("username", text="Username")
        self.users_tree.heading("name", text="Name")
        self.users_tree.heading("role", text="Role")
        self.users_tree.heading("email", text="Email")
        self.users_tree.heading("phone", text="Phone")
        self.users_tree.heading("status", text="Status")
        self.users_tree.heading("actions", text="Actions")
        
        # Define columns
        self.users_tree.column("id", width=40, anchor="center")
        self.users_tree.column("username", width=100)
        self.users_tree.column("name", width=100)
        self.users_tree.column("role", width=80, anchor="center")
        self.users_tree.column("email", width=150)
        self.users_tree.column("phone", width=100)
        self.users_tree.column("status", width=70, anchor="center")
        self.users_tree.column("actions", width=150, anchor="center")
        
        self.users_tree.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Load users
        self.load_users()
    
    def load_users(self):
        # Clear tree
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        # Get users from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, name, role, email, phone, active FROM users ORDER BY username")
        users = cursor.fetchall()
        conn.close()
        
        # Add users to tree
        for user in users:
            status = "Active" if user[6] else "Inactive"
            
            item_id = self.users_tree.insert(
                "", 
                "end", 
                values=(
                    user[0],
                    user[1],
                    user[2],
                    user[3],
                    user[4] if user[4] else "",
                    user[5] if user[5] else "",
                    status,
                    ""  # Actions will be added as buttons
                )
            )
            
            # Add action buttons
            edit_btn = ttk.Button(
                self.users_tree, 
                text="Edit", 
                command=lambda u=user[0]: self.show_edit_user_dialog(u)
            )
            
            toggle_btn = ttk.Button(
                self.users_tree, 
                text="Disable" if user[6] else "Enable", 
                command=lambda u=user[0], s=user[6]: self.toggle_user_status(u, s)
            )
            
            reset_btn = ttk.Button(
                self.users_tree, 
                text="Reset Password", 
                command=lambda u=user[0]: self.reset_user_password(u)
            )
            
            self.users_tree.set(item_id, "actions", "")
            self.users_tree.window(item_id, "actions", window=edit_btn)
            self.users_tree.window(item_id, "actions", window=toggle_btn)
            self.users_tree.window(item_id, "actions", window=reset_btn)
    
    def show_add_user_dialog(self):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Add User")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Add New User", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(form_frame, text="Username*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        username_entry = ttk.Entry(form_frame, width=30)
        username_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Password
        ttk.Label(form_frame, text="Password*:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        password_entry = ttk.Entry(form_frame, width=30, show="*")
        password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Confirm Password
        ttk.Label(form_frame, text="Confirm Password*:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        confirm_password_entry = ttk.Entry(form_frame, width=30, show="*")
        confirm_password_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        
        # Name
        ttk.Label(form_frame, text="Name:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        
        # Email
        ttk.Label(form_frame, text="Email:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        email_entry = ttk.Entry(form_frame, width=30)
        email_entry.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        
        # Phone
        ttk.Label(form_frame, text="Phone:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        phone_entry = ttk.Entry(form_frame, width=30)
        phone_entry.grid(row=5, column=1, padx=10, pady=10, sticky="ew")
        
        # Role
        ttk.Label(form_frame, text="Role*:").grid(row=6, column=0, padx=10, pady=10, sticky="w")
        role_var = tk.StringVar()
        role_combobox = ttk.Combobox(form_frame, textvariable=role_var, width=28)
        role_combobox.grid(row=6, column=1, padx=10, pady=10, sticky="ew")
        role_combobox['values'] = ["admin", "manager", "cashier"]
        role_combobox.current(0)
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.save_user(
                username_entry.get(),
                password_entry.get(),
                confirm_password_entry.get(),
                name_entry.get(),
                email_entry.get(),
                phone_entry.get(),
                role_var.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def save_user(self, username, password, confirm_password, name, email, phone, role, dialog):
        # Validate required fields
        if not username:
            messagebox.showwarning("Warning", "Username is required")
            return
        
        if not password:
            messagebox.showwarning("Warning", "Password is required")
            return
        
        if password != confirm_password:
            messagebox.showwarning("Warning", "Passwords do not match")
            return
        
        if not role:
            messagebox.showwarning("Warning", "Role is required")
            return
        
        # Check if username already exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            messagebox.showwarning("Warning", "Username already exists")
            return
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Save user to database
        cursor.execute("""
        INSERT INTO users (username, password, role, name, email, phone)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password_hash, role, name, email, phone))
        
        conn.commit()
        conn.close()
        
        # Close dialog
        dialog.destroy()
        
        # Refresh users
        self.load_users()
        
        # Show success message
        messagebox.showinfo("Success", "User added successfully")
    
    def show_edit_user_dialog(self, user_id):
        # Get user details
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, name, role, email, phone, active FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            messagebox.showwarning("Warning", "User not found")
            return
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit User")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Edit User", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Username
        ttk.Label(form_frame, text="Username*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        username_entry = ttk.Entry(form_frame, width=30)
        username_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        username_entry.insert(0, user[1])
        username_entry.config(state="readonly")
        
        # Name
        ttk.Label(form_frame, text="Name:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(form_frame, width=30)
        name_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        name_entry.insert(0, user[2] or "")
        
        # Email
        ttk.Label(form_frame, text="Email:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        email_entry = ttk.Entry(form_frame, width=30)
        email_entry.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        email_entry.insert(0, user[4] or "")
        
        # Phone
        ttk.Label(form_frame, text="Phone:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        phone_entry = ttk.Entry(form_frame, width=30)
        phone_entry.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        phone_entry.insert(0, user[5] or "")
        
        # Role
        ttk.Label(form_frame, text="Role*:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        role_var = tk.StringVar(value=user[3])
        role_combobox = ttk.Combobox(form_frame, textvariable=role_var, width=28)
        role_combobox.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        role_combobox['values'] = ["admin", "manager", "cashier"]
        
        # Active
        active_var = tk.BooleanVar(value=bool(user[6]))
        active_check = ttk.Checkbutton(form_frame, text="Active", variable=active_var)
        active_check.grid(row=5, column=1, padx=10, pady=10, sticky="w")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Save", 
            command=lambda: self.update_user(
                user_id,
                name_entry.get(),
                email_entry.get(),
                phone_entry.get(),
                role_var.get(),
                active_var.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def update_user(self, user_id, name, email, phone, role, active, dialog):
        # Update user in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users SET
            name = ?, email = ?, phone = ?, role = ?, active = ?
        WHERE id = ?
        """, (name, email, phone, role, active, user_id))
        
        conn.commit()
        conn.close()
        
        # Close dialog
        dialog.destroy()
        
        # Refresh users
        self.load_users()
        
        # Show success message
        messagebox.showinfo("Success", "User updated successfully")
    
    def toggle_user_status(self, user_id, current_status):
        # Toggle user status
        new_status = not current_status
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users SET active = ? WHERE id = ?
        """, (new_status, user_id))
        
        conn.commit()
        conn.close()
        
        # Refresh users
        self.load_users()
        
        # Show success message
        status_text = "enabled" if new_status else "disabled"
        messagebox.showinfo("Success", f"User {status_text} successfully")
    
    def reset_user_password(self, user_id):
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Reset Password")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create frame
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Reset User Password", style="Title.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # New Password
        ttk.Label(form_frame, text="New Password*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        password_entry = ttk.Entry(form_frame, width=30, show="*")
        password_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Confirm Password
        ttk.Label(form_frame, text="Confirm Password*:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        confirm_password_entry = ttk.Entry(form_frame, width=30, show="*")
        confirm_password_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        save_btn = ttk.Button(
            btn_frame, 
            text="Reset Password", 
            command=lambda: self.reset_password(
                user_id,
                password_entry.get(),
                confirm_password_entry.get(),
                dialog
            )
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def reset_password(self, user_id, password, confirm_password, dialog):
        if not password:
            messagebox.showwarning("Warning", "Password is required")
            return
        
        if password != confirm_password:
            messagebox.showwarning("Warning", "Passwords do not match")
            return
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Update password in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users SET password = ? WHERE id = ?
        """, (password_hash, user_id))
        
        conn.commit()
        conn.close()
        
        # Close dialog
        dialog.destroy()
        
        # Show success message
        messagebox.showinfo("Success", "Password reset successfully")
    
    def show_shift_screen(self):
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create top navigation bar
        self.create_navbar(main_container)
        
        # Create content frame
        content_frame = ttk.Frame(main_container, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(content_frame, text="Shift Management", style="Title.TLabel").pack(pady=10)
        
        # Check if there's an open shift
        if self.current_shift:
            # Show close shift screen
            self.show_close_shift_screen(content_frame)
        else:
            # Show open shift screen
            self.show_open_shift_screen(content_frame)
    
    def show_open_shift_screen(self, parent):
        # Create frame
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Open New Shift", style="Header.TLabel").pack(pady=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Opening cash
        ttk.Label(form_frame, text="Opening Cash Amount*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        opening_cash_entry = ttk.Entry(form_frame, width=20)
        opening_cash_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        opening_cash_entry.insert(0, "0")
        
        # Notes
        ttk.Label(form_frame, text="Notes:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        notes_text = tk.Text(form_frame, width=40, height=5)
        notes_text.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        open_btn = ttk.Button(
            btn_frame, 
            text="Open Shift", 
            command=lambda: self.open_shift(
                opening_cash_entry.get(),
                notes_text.get("1.0", tk.END).strip()
            )
        )
        open_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.show_main_screen)
        cancel_btn.pack(side=tk.LEFT, padx=5)
    
    def open_shift(self, opening_cash, notes):
        try:
            opening_cash = float(opening_cash)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid opening cash amount")
            return
        
        # Create shift in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO shifts (
            user_id, start_time, opening_cash, status, notes
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            self.current_user['id'],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            opening_cash,
            'open',
            notes
        ))
        
        shift_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Update current shift
        self.current_shift = {
            'id': shift_id,
            'start_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'opening_cash': opening_cash
        }
        
        # Show success message
        messagebox.showinfo("Success", "Shift opened successfully")
        
        # Return to main screen
        self.show_main_screen()
    
    def show_close_shift_screen(self, parent):
        # Create frame
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(frame, text="Close Current Shift", style="Header.TLabel").pack(pady=10)
        
        # Shift info
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(info_frame, text=f"Shift Started: {self.current_shift['start_time']}").pack(anchor="w", padx=10)
        ttk.Label(info_frame, text=f"Opening Cash: ₹{self.current_shift['opening_cash']:.2f}").pack(anchor="w", padx=10)
        
        # Get shift sales
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT 
            COUNT(id) as orders,
            SUM(total_amount) as sales,
            SUM(CASE WHEN payment_method = 'Cash' THEN total_amount ELSE 0 END) as cash_sales
        FROM orders
        WHERE user_id = ? AND DATE(order_date) = DATE(?) AND status = 'completed'
        """, (self.current_user['id'], self.current_shift['start_time'].split()[0]))
        
        sales_data = cursor.fetchone()
        
        expected_cash = self.current_shift['opening_cash'] + (sales_data[2] or 0)
        
        conn.close()
        
        # Sales info
        sales_frame = ttk.Frame(frame)
        sales_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(sales_frame, text=f"Orders: {sales_data[0] or 0}").pack(anchor="w", padx=10)
        ttk.Label(sales_frame, text=f"Total Sales: ₹{sales_data[1] or 0:.2f}").pack(anchor="w", padx=10)
        ttk.Label(sales_frame, text=f"Cash Sales: ₹{sales_data[2] or 0:.2f}").pack(anchor="w", padx=10)
        ttk.Label(sales_frame, text=f"Expected Cash: ₹{expected_cash:.2f}", font=("Arial", 10, "bold")).pack(anchor="w", padx=10)
        
        # Form fields
        form_frame = ttk.Frame(frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Closing cash
        ttk.Label(form_frame, text="Closing Cash Amount*:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        closing_cash_entry = ttk.Entry(form_frame, width=20)
        closing_cash_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        closing_cash_entry.insert(0, str(expected_cash))
        
        # Difference
        ttk.Label(form_frame, text="Difference:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        difference_label = ttk.Label(form_frame, text="₹0.00")
        difference_label.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Notes
        ttk.Label(form_frame, text="Notes:").grid(row=2, column=0, padx=10, pady=10, sticky="nw")
        notes_text = tk.Text(form_frame, width=40, height=5)
        notes_text.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        
        # Configure column weights
        form_frame.columnconfigure(1, weight=1)
        
        # Calculate difference
        def calculate_difference(event=None):
            try:
                closing_cash = float(closing_cash_entry.get())
                difference = closing_cash - expected_cash
                difference_label.config(text=f"₹{difference:.2f}")
                
                if difference > 0:
                    difference_label.config(foreground="green")
                elif difference < 0:
                    difference_label.config(foreground="red")
                else:
                    difference_label.config(foreground="black")
            except ValueError:
                difference_label.config(text="₹0.00")
        
        closing_cash_entry.bind("<KeyRelease>", calculate_difference)
        calculate_difference()
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        close_btn = ttk.Button(
            btn_frame, 
            text="Close Shift", 
            command=lambda: self.close_shift(
                closing_cash_entry.get(),
                notes_text.get("1.0", tk.END).strip(),
                expected_cash
            )
        )
        close_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.show_main_screen)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Print report button
        print_btn = ttk.Button(
            btn_frame, 
            text="Print Shift Report", 
            command=lambda: self.print_shift_report(
                self.current_shift['start_time'],
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.current_shift['opening_cash'],
                expected_cash,
                closing_cash_entry.get(),
                sales_data[0] or 0,
                sales_data[1] or 0
            )
        )
        print_btn.pack(side=tk.LEFT, padx=5)
    
    def close_shift(self, closing_cash, notes, expected_cash):
        try:
            closing_cash = float(closing_cash)
        except ValueError:
            messagebox.showwarning("Warning", "Invalid closing cash amount")
            return
        
        difference = closing_cash - expected_cash
        
        # Update shift in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
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
            self.current_shift['id']
        ))
        
        conn.commit()
        conn.close()
        
        # Reset current shift
        self.current_shift = None
        
        # Show success message
        messagebox.showinfo("Success", "Shift closed successfully")
        
        # Return to main screen
        self.show_main_screen()
    
    def print_shift_report(self, start_time, end_time, opening_cash, expected_cash, closing_cash, orders, sales):
        try:
            closing_cash = float(closing_cash)
        except ValueError:
            closing_cash = expected_cash
        
        difference = closing_cash - expected_cash
        
        # Get business settings
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM business_settings LIMIT 1")
        business = cursor.fetchone()
        conn.close()
        
        # Create report text
        report = f"{business[1]}\n"
        report += f"SHIFT REPORT\n"
        report += "-" * 30 + "\n"
        report += f"Cashier: {self.current_user['name']}\n"
        report += f"Start: {start_time}\n"
        report += f"End: {end_time}\n"
        report += "-" * 30 + "\n"
        report += f"Opening Cash: ₹{opening_cash:.2f}\n"
        report += f"Total Sales: ₹{sales:.2f}\n"
        report += f"Expected Cash: ₹{expected_cash:.2f}\n"
        report += f"Actual Cash: ₹{closing_cash:.2f}\n"
        report += f"Difference: ₹{difference:.2f}\n"
        report += "-" * 30 + "\n"
        report += f"Orders: {orders}\n"
        report += f"Average Sale: ₹{sales/orders if orders > 0 else 0:.2f}\n"
        report += "-" * 30 + "\n"
        report += f"{business[9]}\n"
        
        # Print report (in a real implementation, this would send to a printer)
        print(report)
        
        # For demo purposes, show report in a message box
        messagebox.showinfo("Shift Report", report)
    
    def logout(self):
        # Check if there's an open shift
        if self.current_shift:
            if messagebox.askyesno("Open Shift", "You have an open shift. Do you want to close it now?"):
                self.show_shift_screen()
                return
        
        # Reset session
        self.current_user = None
        self.current_role = None
        self.current_shift = None
        
        # Show login screen
        self.show_login_screen()

# Main function to run the application
def main():
    root = tk.Tk()
    app = POSApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()