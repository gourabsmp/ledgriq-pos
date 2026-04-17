import os
import json
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ledgriq_super_secret_key_2026")

# ==========================================
# 🛑 MOCK DATABASE (Local-First Prototype) 🛑
# ==========================================
MOCK_DB = {
    "products": [
        {"name": "Mechanical Keyboard", "sku": "KB-001", "price": 4500.00, "stock_quantity": 15},
        {"name": "Wireless Mouse", "sku": "MS-099", "price": 1200.00, "stock_quantity": 5},
        {"name": "USB-C Hub", "sku": "USB-002", "price": 800.00, "stock_quantity": 0}
    ],
    "customers": [
        {"phone": "9876543210", "name": "Rajesh Kumar", "total_due": 500.00} 
    ],
    "transactions": [],
    "total_revenue": 0.0
}
# ==========================================

@app.route('/')
def home():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dev')
def dev_login():
    session['user_id'] = 'local-dev-user'
    session['shop_name'] = 'Ledgriq Prototype Store'
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['POST'])
def login():
    session['user_id'] = 'mock-user'
    session['shop_name'] = 'Ledgriq Prototype Store'
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['POST'])
def register():
    shop_name = request.form.get('shop_name', 'My New Store')
    session['user_id'] = 'mock-user-new'
    session['shop_name'] = shop_name
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template('dashboard.html', 
                           shop_name=session.get('shop_name'),
                           revenue=MOCK_DB.get("total_revenue", 0.0),
                           count=len(MOCK_DB.get("products", [])),
                           sales=MOCK_DB.get("transactions", []))

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session: return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form.get('name')
        price_str = request.form.get('price')
        sku = request.form.get('sku', '')
        stock_str = request.form.get('stock', '0')
        if name and price_str:
            try:
                MOCK_DB["products"].insert(0, {
                    "name": str(name), "sku": str(sku), 
                    "price": float(price_str), "stock_quantity": int(stock_str)
                })
            except ValueError:
                pass
        return redirect(url_for('inventory'))
    return render_template('inventory.html', shop_name=session.get('shop_name'), products=MOCK_DB["products"])

# --- NEW: MODERN POS TERMINAL ---
@app.route('/pos')
def pos():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template('pos.html', shop_name=session.get('shop_name'), products=MOCK_DB["products"])

# --- NEW: CUSTOMERS CRM ---
@app.route('/customers')
def customers():
    if 'user_id' not in session: return redirect(url_for('home'))
    return render_template('customers.html', shop_name=session.get('shop_name'), customers=MOCK_DB["customers"])

# --- API: EDIT CUSTOMER ---
@app.route('/edit_customer', methods=['POST'])
def edit_customer():
    if 'user_id' not in session: return redirect(url_for('home'))

    # Get the data from the edit form
    old_phone = request.form.get('old_phone')
    new_phone = request.form.get('phone')
    new_name = request.form.get('name')
    new_due_str = request.form.get('total_due', '0')

    # Find the specific customer in the mock database
    customer = next((c for c in MOCK_DB["customers"] if c["phone"] == old_phone), None)

    if customer:
        # Update their details
        customer['phone'] = new_phone
        customer['name'] = new_name
        try:
            # Safely update the ledger balance
            customer['total_due'] = float(new_due_str)
        except ValueError:
            pass

    return redirect(url_for('customers'))

# --- API: CUSTOMER LOOKUP ---
@app.route('/get_customer/<phone>')
def get_customer(phone):
    customer = next((c for c in MOCK_DB["customers"] if c["phone"] == phone), None)
    if customer: return customer
    return {"name": "", "total_due": 0.0, "is_new": True}

# --- API: MASTER CHECKOUT ---
@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.json
    cart = data.get('cart')
    customer_info = data.get('customer')
    
    sale_total = 0.0
    items_sold = 0
    
    # 1. Deduct Stock & Calculate Bill
    for sku, item_data in cart.items():
        qty_purchased = item_data['qty']
        price_sold = item_data['price'] # Use the edited price from the POS!
        
        for product in MOCK_DB["products"]:
            if product["sku"] == sku and product["stock_quantity"] >= qty_purchased:
                product["stock_quantity"] -= qty_purchased
                sale_total += (price_sold * qty_purchased)
                items_sold += qty_purchased
                break

    grand_total = sale_total * 1.18 # Add 18% GST
    
    # 2. Process Ledger
    phone = customer_info.get('phone', '0000000000')
    amount_paid = float(customer_info.get('amount_paid', 0))
    customer = next((c for c in MOCK_DB["customers"] if c["phone"] == phone), None)
    
    if not customer:
        customer = {"phone": phone, "name": customer_info.get('name', 'Walk-in'), "total_due": 0.0}
        MOCK_DB["customers"].append(customer)
    else:
        customer["name"] = customer_info.get('name', customer["name"])

    previous_due = customer["total_due"]
    new_total_due = previous_due + grand_total - amount_paid
    customer["total_due"] = new_total_due
    MOCK_DB["total_revenue"] += amount_paid
    
    # 3. Log Transaction
    MOCK_DB["transactions"].insert(0, {
        "items": items_sold,
        "total": grand_total,
        "status": "Paid" if amount_paid >= grand_total else "Partial/Due"
    })

    return {"status": "success"}, 200

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)