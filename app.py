from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from sqlalchemy import func

from config import Config
from models import (
    db, User, Category, Product, Customer,
    Sale, SaleItem, Payment, InventoryTransaction,
    outstanding
)


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ADMIN ACCESS CONTROL
def admin_required(function):
    @wraps(function)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "Admin":
            flash("Administrator access is required.", "danger")
            return redirect(url_for("dashboard"))
        return function(*args, **kwargs)
    return wrapper


def money(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal("0.00")


# HOME
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# LOGIN
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
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "success")
    return redirect(url_for("login"))


# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()

    today_sales = db.session.query(
        func.coalesce(func.sum(Sale.total_amount), 0)
    ).filter(
        func.date(Sale.sale_date) == today
    ).scalar()

    total_products = Product.query.count()
    total_customers = Customer.query.count()
    low_stock = Product.query.filter(
        Product.stock <= Product.reorder_level
    ).count()

    recent_sales = Sale.query.order_by(
        Sale.sale_date.desc()
    ).limit(5).all()

    return render_template(
        "dashboard.html",
        today_sales=today_sales,
        total_products=total_products,
        total_customers=total_customers,
        low_stock=low_stock,
        recent_sales=recent_sales
    )


# CATEGORIES
@app.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash("Category name is required.", "danger")
        elif Category.query.filter_by(name=name).first():
            flash("Category already exists.", "danger")
        else:
            db.session.add(Category(name=name))
            db.session.commit()
            flash("Category added successfully.", "success")

        return redirect(url_for("categories"))

    all_categories = Category.query.order_by(Category.name).all()

    return render_template(
        "categories.html",
        categories=all_categories
    )


@app.route("/categories/delete/<int:category_id>", methods=["POST"])
@admin_required
def delete_category(category_id):
    category = db.session.get(Category, category_id)

    if not category:
        flash("Category not found.", "danger")
    elif category.products:
        flash("Cannot delete a category that has products.", "danger")
    else:
        db.session.delete(category)
        db.session.commit()
        flash("Category deleted.", "success")

    return redirect(url_for("categories"))


# PRODUCTS
@app.route("/products", methods=["GET", "POST"])
@login_required
def products():
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            category_id = int(request.form.get("category_id"))
            unit_cost = money(request.form.get("unit_cost"))
            unit_price = money(request.form.get("unit_price"))
            stock = int(request.form.get("stock", 0))
            reorder_level = int(request.form.get("reorder_level", 5))

            category = db.session.get(Category, category_id)

            if not name or not category:
                raise ValueError("Enter a product name and valid category.")

            if unit_cost < 0 or unit_price <= 0:
                raise ValueError("Invalid product cost or selling price.")

            if stock < 0 or reorder_level < 0:
                raise ValueError("Stock and reorder level cannot be negative.")

            product = Product(
                name=name,
                category_id=category_id,
                unit_cost=unit_cost,
                unit_price=unit_price,
                stock=stock,
                reorder_level=reorder_level
            )

            db.session.add(product)
            db.session.flush()

            if stock > 0:
                db.session.add(InventoryTransaction(
                    product_id=product.id,
                    user_id=current_user.id,
                    transaction_type="Stock In",
                    quantity_change=stock,
                    remarks="Initial stock"
                ))

            db.session.commit()
            flash("Product added successfully.", "success")

        except (ValueError, TypeError, InvalidOperation) as error:
            db.session.rollback()
            flash(str(error), "danger")

        return redirect(url_for("products"))

    all_products = Product.query.order_by(Product.name).all()
    all_categories = Category.query.order_by(Category.name).all()

    return render_template(
        "products.html",
        products=all_products,
        categories=all_categories
    )


@app.route("/products/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = db.session.get(Product, product_id)

    if not product:
        flash("Product not found.", "danger")
    elif SaleItem.query.filter_by(product_id=product_id).first():
        flash("This product has sales history and cannot be deleted.", "danger")
    elif InventoryTransaction.query.filter_by(product_id=product_id).first():
        flash("This product has inventory history and cannot be deleted.", "danger")
    else:
        db.session.delete(product)
        db.session.commit()
        flash("Product deleted.", "success")

    return redirect(url_for("products"))


# CUSTOMERS
@app.route("/customers", methods=["GET", "POST"])
@login_required
def customers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        contact = request.form.get("contact", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Customer name is required.", "danger")
        else:
            customer = Customer(
                name=name,
                contact=contact or None,
                address=address or None
            )
            db.session.add(customer)
            db.session.commit()
            flash("Customer added successfully.", "success")

        return redirect(url_for("customers"))

    all_customers = Customer.query.order_by(Customer.name).all()

    return render_template(
        "customers.html",
        customers=all_customers
    )


# INVENTORY
@app.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    if request.method == "POST":
        try:
            product_id = int(request.form.get("product_id"))
            quantity = int(request.form.get("quantity"))
            transaction_type = request.form.get("transaction_type")
            remarks = request.form.get("remarks", "").strip()

            product = db.session.get(Product, product_id)

            if not product:
                raise ValueError("Product not found.")

            if quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")

            if transaction_type not in ["Stock In", "Adjustment"]:
                raise ValueError("Invalid inventory transaction type.")

            change = quantity if transaction_type == "Stock In" else quantity

            if transaction_type == "Adjustment":
                change = int(request.form.get("quantity_change"))

            if change == 0:
                raise ValueError("Adjustment cannot be zero.")

            if product.stock + change < 0:
                raise ValueError("Insufficient stock for this adjustment.")

            product.stock += change

            db.session.add(InventoryTransaction(
                product_id=product.id,
                user_id=current_user.id,
                transaction_type=transaction_type,
                quantity_change=change,
                remarks=remarks or None
            ))

            db.session.commit()
            flash("Inventory updated successfully.", "success")

        except (ValueError, TypeError) as error:
            db.session.rollback()
            flash(str(error), "danger")

        return redirect(url_for("inventory"))

    all_products = Product.query.order_by(Product.name).all()

    transactions = InventoryTransaction.query.order_by(
        InventoryTransaction.transaction_date.desc()
    ).limit(50).all()

    return render_template(
        "inventory.html",
        products=all_products,
        transactions=transactions
    )


# SALES
@app.route("/sales", methods=["GET", "POST"])
@login_required
def sales():
    if request.method == "POST":
        try:
            payment_type = request.form.get("payment_type")
            customer_id = request.form.get("customer_id")
            due_date_text = request.form.get("due_date")

            if payment_type not in ["Cash", "Credit"]:
                raise ValueError("Select Cash or Credit.")

            customer = None

            if customer_id:
                customer = db.session.get(Customer, int(customer_id))

                if not customer:
                    raise ValueError("Invalid customer.")

            if payment_type == "Credit" and not customer:
                raise ValueError("A customer is required for credit sales.")

            due_date = None

            if payment_type == "Credit":
                if due_date_text:
                    due_date = datetime.strptime(
                        due_date_text, "%Y-%m-%d"
                    ).date()

            product_ids = request.form.getlist("product_id")
            quantities = request.form.getlist("quantity")

            if not product_ids:
                raise ValueError("A sale must contain at least one product.")

            sale = Sale(
                payment_type=payment_type,
                customer_id=customer.id if customer else None,
                due_date=due_date,
                total_amount=Decimal("0.00"),
                user_id=current_user.id
            )

            db.session.add(sale)
            db.session.flush()

            total = Decimal("0.00")

            for product_id, quantity_text in zip(product_ids, quantities):
                product = db.session.get(Product, int(product_id))
                quantity = int(quantity_text)

                if not product:
                    raise ValueError("A selected product does not exist.")

                if quantity <= 0:
                    raise ValueError("Quantity must be greater than zero.")

                if product.stock < quantity:
                    raise ValueError(
                        f"Insufficient stock for {product.name}."
                    )

                subtotal = product.unit_price * quantity
                total += subtotal

                db.session.add(SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.unit_price,
                    unit_cost=product.unit_cost
                ))

                product.stock -= quantity

                db.session.add(InventoryTransaction(
                    product_id=product.id,
                    user_id=current_user.id,
                    transaction_type="Sale",
                    quantity_change=-quantity,
                    remarks=f"Sale #{sale.id}"
                ))

            if total <= 0:
                raise ValueError("Sale total must be greater than zero.")

            sale.total_amount = total

            db.session.commit()
            flash(f"Sale #{sale.id} recorded successfully.", "success")

        except (ValueError, TypeError, InvalidOperation) as error:
            db.session.rollback()
            flash(str(error), "danger")

        return redirect(url_for("sales"))

    all_sales = Sale.query.order_by(Sale.sale_date.desc()).all()
    all_products = Product.query.order_by(Product.name).all()
    all_customers = Customer.query.order_by(Customer.name).all()

    return render_template(
        "sales.html",
        sales=all_sales,
        products=all_products,
        customers=all_customers,
        outstanding=outstanding
    )


# CREDIT PAYMENTS
@app.route("/payments/<int:sale_id>", methods=["POST"])
@login_required
def add_payment(sale_id):
    try:
        sale = db.session.get(Sale, sale_id)

        if not sale or sale.payment_type != "Credit":
            raise ValueError("Credit sale not found.")

        amount = money(request.form.get("amount"))

        if amount <= 0:
            raise ValueError("Payment must be greater than zero.")

        balance = Decimal(str(outstanding(sale)))

        if amount > balance:
            raise ValueError("Payment cannot exceed the outstanding balance.")

        payment = Payment(
            sale_id=sale.id,
            amount=amount,
            user_id=current_user.id
        )

        db.session.add(payment)
        db.session.commit()

        flash("Payment recorded successfully.", "success")

    except (ValueError, TypeError, InvalidOperation) as error:
        db.session.rollback()
        flash(str(error), "danger")

    return redirect(url_for("sales"))


# REPORTS
@app.route("/reports")
@login_required
def reports():
    start_text = request.args.get("start")
    end_text = request.args.get("end")

    try:
        start_date = (
            datetime.strptime(start_text, "%Y-%m-%d").date()
            if start_text else date.today().replace(day=1)
        )

        end_date = (
            datetime.strptime(end_text, "%Y-%m-%d").date()
            if end_text else date.today()
        )

        if start_date > end_date:
            raise ValueError()

    except ValueError:
        flash("Invalid report date range.", "danger")
        return redirect(url_for("reports"))

    report_sales = Sale.query.filter(
        func.date(Sale.sale_date) >= start_date,
        func.date(Sale.sale_date) <= end_date
    ).order_by(Sale.sale_date.desc()).all()

    total_sales = sum(
        (Decimal(str(s.total_amount)) for s in report_sales),
        Decimal("0.00")
    )

    gross_profit = Decimal("0.00")

    for sale in report_sales:
        for item in sale.items:
            gross_profit += (
                (Decimal(str(item.unit_price)) -
                 Decimal(str(item.unit_cost))) * item.quantity
            )

    return render_template(
        "reports.html",
        sales=report_sales,
        total_sales=total_sales,
        gross_profit=gross_profit,
        start_date=start_date,
        end_date=end_date
    )


# USER MANAGEMENT
@app.route("/users", methods=["GET", "POST"])
@admin_required
def users():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "Attendant")

        if not full_name or not username or not password:
            flash("All required fields must be completed.", "danger")

        elif role not in ["Admin", "Attendant"]:
            flash("Invalid user role.", "danger")

        elif User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")

        else:
            user = User(
                full_name=full_name,
                username=username,
                role=role
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("User created successfully.", "success")

        return redirect(url_for("users"))

    all_users = User.query.order_by(User.full_name).all()

    return render_template("users.html", users=all_users)


# DATABASE INITIALIZATION
with app.app_context():
    db.create_all()

    # Create the first administrator if no users exist.
    if User.query.count() == 0:
        admin = User(
            full_name="Store Administrator",
            username="admin",
            role="Admin"
        )

        admin.set_password("Admin123!")

        db.session.add(admin)
        db.session.commit()

        print("Initial administrator created.")
        print("Username: admin")
        print("Password: Admin123!")
        print("Change this password after your first login.")


if __name__ == "__main__":
    app.run(debug=True)