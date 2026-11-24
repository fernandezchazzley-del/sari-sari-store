import os
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from models import db, User, Category, Product, Customer, Sale, SaleItem, Payment, InventoryTransaction

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "replace-this-local-secret-before-use")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:CHANGE_ME@localhost:5432/joyo_store_new")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access the store system."

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "Admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def customer_balance(customer_id):
    credit_total = db.session.query(func.coalesce(func.sum(Sale.totalamount), 0)).filter(
        Sale.customerid == customer_id, Sale.paymenttype == "Credit"
    ).scalar()
    paid_total = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
        Payment.customerid == customer_id
    ).scalar()
    return money(credit_total) - money(paid_total)


@app.template_filter("currency")
def currency(value):
    return f"₱{money(value):,.2f}"


@app.cli.command("init-db")
def init_db_command():
    """Create tables and an initial admin only if one doesn't already exist."""
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(fullname="Store Owner / Administrator", username="admin", role="Admin")
        admin.set_password(os.getenv("INITIAL_ADMIN_PASSWORD", "ChangeMe123!"))
        db.session.add(admin)
        db.session.commit()
        print("Database tables created. Initial admin: admin / ChangeMe123! (change it after login).")
    else:
        print("Database tables checked. Existing admin account was not changed.")


@app.route("/")
def index():
    return redirect(url_for("dashboard" if current_user.is_authenticated else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    today_total = db.session.query(func.coalesce(func.sum(Sale.totalamount), 0)).filter(
        func.date(Sale.saledate) == today
    ).scalar()
    products_count = Product.query.count()
    customers_count = Customer.query.count()
    low_stock = Product.query.filter(Product.stock <= Product.reorderlevel).order_by(Product.stock).limit(8).all()
    recent_sales = Sale.query.order_by(Sale.saledate.desc()).limit(8).all()
    total_credit = db.session.query(func.coalesce(func.sum(Sale.totalamount), 0)).filter(Sale.paymenttype == "Credit").scalar()
    total_payments = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    return render_template("dashboard.html", today_total=today_total, products_count=products_count,
                           customers_count=customers_count, low_stock=low_stock, recent_sales=recent_sales,
                           total_outstanding=money(total_credit)-money(total_payments))


@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        try:
            name = request.form.get("productname", "").strip()
            categoryid = int(request.form.get("categoryid", ""))
            cost = money(request.form.get("unitcost"))
            price = money(request.form.get("unitprice"))
            stock = int(request.form.get("stock", "0"))
            reorder = int(request.form.get("reorderlevel", "5"))
            if not name or cost < 0 or price <= 0 or stock < 0 or reorder < 0:
                raise ValueError
            product = Product(productname=name, categoryid=categoryid, unitcost=cost, unitprice=price, stock=stock, reorderlevel=reorder)
            db.session.add(product)
            db.session.flush()
            if stock:
                db.session.add(InventoryTransaction(productid=product.productid, userid=current_user.userid,
                    transactiontype="Stock In", quantitychange=stock, remarks="Opening stock"))
            db.session.commit()
            flash("Product added.", "success")
            return redirect(url_for("products"))
        except (ValueError, TypeError):
            db.session.rollback(); flash("Check the product fields and enter valid values.", "error")
        except IntegrityError:
            db.session.rollback(); flash("Could not save product. Check its category.", "error")
    category_list = Category.query.order_by(Category.categoryname).all()
    product_list = Product.query.order_by(Product.productname).all()
    return render_template("products.html", categories=category_list, products=product_list)


@app.post("/products/<int:product_id>/update")
@login_required
def update_product(product_id):
    p = db.get_or_404(Product, product_id)
    try:
        p.productname = request.form.get("productname", "").strip()
        p.categoryid = int(request.form.get("categoryid", ""))
        p.unitcost = money(request.form.get("unitcost")); p.unitprice = money(request.form.get("unitprice"))
        p.reorderlevel = int(request.form.get("reorderlevel", "5"))
        if not p.productname or p.unitcost < 0 or p.unitprice <= 0 or p.reorderlevel < 0: raise ValueError
        db.session.commit(); flash("Product updated.", "success")
    except (ValueError, TypeError, IntegrityError):
        db.session.rollback(); flash("Could not update product. Check the values.", "error")
    return redirect(url_for("products"))


@app.post("/products/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    p = db.get_or_404(Product, product_id)
    if p.sale_items or p.inventory_transactions:
        flash("This product has transaction history and cannot be deleted. You can leave it in the catalog.", "error")
    else:
        db.session.delete(p); db.session.commit(); flash("Product deleted.", "success")
    return redirect(url_for("products"))


@app.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("categoryname", "").strip()
        if name:
            db.session.add(Category(categoryname=name))
            try: db.session.commit(); flash("Category added.", "success")
            except IntegrityError: db.session.rollback(); flash("Category already exists.", "error")
        return redirect(url_for("categories"))
    return render_template("categories.html", categories=Category.query.order_by(Category.categoryname).all())


@app.post("/categories/<int:category_id>/delete")
@admin_required
def delete_category(category_id):
    c = db.get_or_404(Category, category_id)
    if c.products: flash("Cannot delete a category that contains products.", "error")
    else: db.session.delete(c); db.session.commit(); flash("Category deleted.", "success")
    return redirect(url_for("categories"))


@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    if request.method == "POST":
        name = request.form.get("customername", "").strip()
        if name:
            db.session.add(Customer(customername=name, contactno=request.form.get("contactno", "").strip() or None,
                                  address=request.form.get("address", "").strip() or None))
            db.session.commit(); flash("Customer added.", "success")
        return redirect(url_for("customers"))
    customer_list = Customer.query.order_by(Customer.customername).all()
    balances = {c.customerid: customer_balance(c.customerid) for c in customer_list}
    return render_template("customers.html", customers=customer_list, balances=balances)


@app.route("/customers/<int:customer_id>", methods=["GET", "POST"])
@login_required
def customer_account(customer_id):
    customer = db.get_or_404(Customer, customer_id)
    if request.method == "POST":
        amount = money(request.form.get("amount"))
        balance = customer_balance(customer.customerid)
        if amount <= 0 or amount > balance:
            flash(f"Payment must be greater than zero and no more than the outstanding balance ({balance:,.2f}).", "error")
        else:
            db.session.add(Payment(customerid=customer.customerid, amount=amount, userid=current_user.userid))
            db.session.commit(); flash("Customer payment recorded.", "success")
        return redirect(url_for("customer_account", customer_id=customer_id))
    credit_sales = Sale.query.filter_by(customerid=customer_id, paymenttype="Credit").order_by(Sale.saledate.desc()).all()
    payments = Payment.query.filter_by(customerid=customer_id).order_by(Payment.paymentdate.desc()).all()
    return render_template("customer_account.html", customer=customer, balance=customer_balance(customer_id),
                          credit_sales=credit_sales, payments=payments)


@app.route("/sales")
@login_required
def sales():
    sale_list = Sale.query.order_by(Sale.saledate.desc()).limit(300).all()
    return render_template("sales.html", sales=sale_list)


@app.route("/sales/new", methods=["GET", "POST"])
@login_required
def new_sale():
    product_list = Product.query.filter(Product.stock > 0).order_by(Product.productname).all()
    customer_list = Customer.query.order_by(Customer.customername).all()
    if request.method == "POST":
        paymenttype = request.form.get("paymenttype")
        customerid_raw = request.form.get("customerid", "").strip()
        customerid = int(customerid_raw) if customerid_raw else None
        if paymenttype not in ("Cash", "Credit") or (paymenttype == "Credit" and not customerid):
            flash("Credit sales require a customer. Choose Cash or Credit.", "error")
            return render_template("new_sale.html", products=product_list, customers=customer_list)
        raw_ids = request.form.getlist("productid")
        raw_qtys = request.form.getlist("quantity")
        grouped = {}
        try:
            for raw_id, raw_qty in zip(raw_ids, raw_qtys):
                if not raw_id or not raw_qty: continue
                pid, qty = int(raw_id), int(raw_qty)
                if qty <= 0: raise ValueError
                grouped[pid] = grouped.get(pid, 0) + qty
            if not grouped: raise ValueError
            if customerid and not db.session.get(Customer, customerid): raise ValueError
            items = []
            total = Decimal("0.00")
            for pid, qty in grouped.items():
                product = db.session.get(Product, pid)
                if not product or product.stock < qty: raise ValueError(f"Not enough stock for {product.productname if product else 'selected product'}.")
                subtotal = money(product.unitprice * qty); total += subtotal
                items.append((product, qty))
            sale = Sale(paymenttype=paymenttype, totalamount=money(total), customerid=customerid if paymenttype == "Credit" else customerid,
                        userid=current_user.userid)
            db.session.add(sale); db.session.flush()
            for product, qty in items:
                product.stock -= qty
                db.session.add(SaleItem(saleid=sale.saleid, productid=product.productid, quantity=qty,
                                        unitprice=product.unitprice, unitcost=product.unitcost))
                db.session.add(InventoryTransaction(productid=product.productid, userid=current_user.userid,
                    transactiontype="Sale", quantitychange=-qty, remarks=f"Sale #{sale.saleid}"))
            db.session.commit(); flash(f"Sale #{sale.saleid} recorded.", "success")
            return redirect(url_for("sales"))
        except ValueError as e:
            db.session.rollback(); flash(str(e) or "Enter valid products and quantities.", "error")
        except Exception:
            db.session.rollback(); flash("Sale could not be saved. Check product stock and customer selection.", "error")
    return render_template("new_sale.html", products=product_list, customers=customer_list)


@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    if request.method == "POST":
        try:
            productid = int(request.form.get("productid", "")); quantity = int(request.form.get("quantity", ""))
            kind = request.form.get("transactiontype")
            product = db.get_or_404(Product, productid)
            if kind not in ("Stock In", "Adjustment") or quantity <= 0: raise ValueError
            if kind == "Stock In": change = quantity
            else:
                direction = request.form.get("direction")
                change = quantity if direction == "increase" else -quantity if direction == "decrease" else 0
            if change == 0 or product.stock + change < 0: raise ValueError
            product.stock += change
            db.session.add(InventoryTransaction(productid=productid, userid=current_user.userid,
                transactiontype=kind, quantitychange=change, remarks=request.form.get("remarks", "").strip() or None))
            db.session.commit(); flash("Inventory updated.", "success")
        except (ValueError, TypeError):
            db.session.rollback(); flash("Enter a valid quantity and adjustment. Stock cannot become negative.", "error")
        return redirect(url_for("inventory"))
    products_list = Product.query.order_by(Product.productname).all()
    movements = InventoryTransaction.query.order_by(InventoryTransaction.transactiondate.desc()).limit(100).all()
    return render_template("inventory.html", products=products_list, movements=movements)


@app.route("/reports")
@login_required
def reports():
    period = request.args.get("period", "month")
    today = date.today()
    if period == "today": start = today
    elif period == "year": start = date(today.year, 1, 1)
    else: period = "month"; start = date(today.year, today.month, 1)
    sales_rows = Sale.query.filter(func.date(Sale.saledate) >= start).order_by(Sale.saledate.desc()).all()
    revenue = sum((money(s.totalamount) for s in sales_rows), Decimal("0.00"))
    cogs = sum((money(item.unitcost * item.quantity) for s in sales_rows for item in s.items), Decimal("0.00"))
    return render_template("reports.html", period=period, sales=sales_rows, revenue=revenue, cogs=cogs,
                          gross_profit=revenue-cogs)


@app.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip(); username = request.form.get("username", "").strip()
        password = request.form.get("password", ""); role = request.form.get("role", "Attendant")
        if not fullname or not username or len(password) < 8 or role not in ("Admin", "Attendant"):
            flash("Enter a name, username, valid role, and password of at least 8 characters.", "error")
        else:
            user = User(fullname=fullname, username=username, role=role); user.set_password(password); db.session.add(user)
            try: db.session.commit(); flash("User account created.", "success")
            except IntegrityError: db.session.rollback(); flash("That username already exists.", "error")
        return redirect(url_for("users"))
    return render_template("users.html", users=User.query.order_by(User.fullname).all())


@app.post("/users/<int:user_id>/reset-password")
@admin_required
def reset_password(user_id):
    user = db.get_or_404(User, user_id)
    password = request.form.get("password", "")
    if len(password) < 8: flash("Password must be at least 8 characters.", "error")
    else: user.set_password(password); db.session.commit(); flash("Password updated.", "success")
    return redirect(url_for("users"))


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The requested page or record was not found."), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
