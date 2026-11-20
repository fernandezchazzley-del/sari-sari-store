from datetime import datetime, date
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column("userid", db.Integer, primary_key=True)
    full_name = db.Column("fullname", db.String(80), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column("passwordhash", db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Attendant")
    created_at = db.Column("createdat", db.DateTime, default=datetime.utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def get_id(self): return str(self.id)

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column("categoryid", db.Integer, primary_key=True)
    name = db.Column("categoryname", db.String(40), unique=True, nullable=False)
    products = db.relationship("Product", backref="category", lazy=True)

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column("productid", db.Integer, primary_key=True)
    name = db.Column("productname", db.String(80), nullable=False)
    category_id = db.Column("categoryid", db.Integer, db.ForeignKey("categories.categoryid"), nullable=False)
    unit_cost = db.Column("unitcost", db.Numeric(8,2), nullable=False, default=0)
    unit_price = db.Column("unitprice", db.Numeric(8,2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column("reorderlevel", db.Integer, nullable=False, default=5)

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column("customerid", db.Integer, primary_key=True)
    name = db.Column("customername", db.String(80), nullable=False)
    contact = db.Column("contactno", db.String(15))
    address = db.Column(db.String(150))

class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column("saleid", db.Integer, primary_key=True)
    sale_date = db.Column("saledate", db.DateTime, default=datetime.utcnow, nullable=False)
    payment_type = db.Column("paymenttype", db.String(20), nullable=False)
    due_date = db.Column("duedate", db.Date)
    total_amount = db.Column("totalamount", db.Numeric(10,2), nullable=False)
    customer_id = db.Column("customerid", db.Integer, db.ForeignKey("customers.customerid"))
    user_id = db.Column("userid", db.Integer, db.ForeignKey("users.userid"), nullable=False)
    customer = db.relationship("Customer")
    user = db.relationship("User")
    items = db.relationship("SaleItem", backref="sale", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="sale", cascade="all, delete-orphan")

class SaleItem(db.Model):
    __tablename__ = "sale_items"
    id = db.Column("saleitemid", db.Integer, primary_key=True)
    sale_id = db.Column("saleid", db.Integer, db.ForeignKey("sales.saleid"), nullable=False)
    product_id = db.Column("productid", db.Integer, db.ForeignKey("products.productid"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column("unitprice", db.Numeric(8,2), nullable=False)
    unit_cost = db.Column("unitcost", db.Numeric(8,2), nullable=False)
    product = db.relationship("Product")

class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column("paymentid", db.Integer, primary_key=True)
    sale_id = db.Column("saleid", db.Integer, db.ForeignKey("sales.saleid"), nullable=False)
    payment_date = db.Column("paymentdate", db.DateTime, default=datetime.utcnow, nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    user_id = db.Column("userid", db.Integer, db.ForeignKey("users.userid"), nullable=False)
    user = db.relationship("User")

class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"
    id = db.Column("inventorytransactionid", db.Integer, primary_key=True)
    product_id = db.Column("productid", db.Integer, db.ForeignKey("products.productid"), nullable=False)
    user_id = db.Column("userid", db.Integer, db.ForeignKey("users.userid"), nullable=False)
    transaction_type = db.Column("transactiontype", db.String(20), nullable=False)
    quantity_change = db.Column("quantitychange", db.Integer, nullable=False)
    transaction_date = db.Column("transactiondate", db.DateTime, default=datetime.utcnow, nullable=False)
    remarks = db.Column(db.String(150))
    product = db.relationship("Product")
    user = db.relationship("User")

def outstanding(sale):
    return max(float(sale.total_amount) - sum(float(p.amount) for p in sale.payments), 0)
