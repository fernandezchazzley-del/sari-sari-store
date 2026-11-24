from datetime import datetime
from decimal import Decimal
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import CheckConstraint, UniqueConstraint


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    userid = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(50), nullable=False, unique=True)
    passwordhash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="Attendant")
    createdat = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (CheckConstraint("role IN ('Admin', 'Attendant')", name="ck_users_role"),)

    sales = db.relationship("Sale", back_populates="user")
    payments = db.relationship("Payment", back_populates="user")
    inventory_transactions = db.relationship("InventoryTransaction", back_populates="user")

    def get_id(self):
        return str(self.userid)

    def set_password(self, password):
        self.passwordhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passwordhash, password)


class Category(db.Model):
    __tablename__ = "categories"
    categoryid = db.Column(db.Integer, primary_key=True)
    categoryname = db.Column(db.String(40), nullable=False, unique=True)
    products = db.relationship("Product", back_populates="category")


class Product(db.Model):
    __tablename__ = "products"
    productid = db.Column(db.Integer, primary_key=True)
    productname = db.Column(db.String(80), nullable=False)
    categoryid = db.Column(db.Integer, db.ForeignKey("categories.categoryid"), nullable=False)
    unitcost = db.Column(db.Numeric(8, 2), nullable=False)
    unitprice = db.Column(db.Numeric(8, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    reorderlevel = db.Column(db.Integer, nullable=False, default=5)
    __table_args__ = (
        CheckConstraint("unitcost >= 0", name="ck_products_unitcost_nonnegative"),
        CheckConstraint("unitprice > 0", name="ck_products_unitprice_positive"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonnegative"),
        CheckConstraint("reorderlevel >= 0", name="ck_products_reorder_nonnegative"),
    )
    category = db.relationship("Category", back_populates="products")
    sale_items = db.relationship("SaleItem", back_populates="product")
    inventory_transactions = db.relationship("InventoryTransaction", back_populates="product")


class Customer(db.Model):
    __tablename__ = "customers"
    customerid = db.Column(db.Integer, primary_key=True)
    customername = db.Column(db.String(80), nullable=False)
    contactno = db.Column(db.String(15))
    address = db.Column(db.String(150))
    sales = db.relationship("Sale", back_populates="customer")
    payments = db.relationship("Payment", back_populates="customer")


class Sale(db.Model):
    __tablename__ = "sales"
    saleid = db.Column(db.Integer, primary_key=True)
    saledate = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    paymenttype = db.Column(db.String(20), nullable=False)
    totalamount = db.Column(db.Numeric(10, 2), nullable=False)
    customerid = db.Column(db.Integer, db.ForeignKey("customers.customerid"))
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)
    __table_args__ = (
        CheckConstraint("paymenttype IN ('Cash', 'Credit')", name="ck_sales_paymenttype"),
        CheckConstraint("totalamount > 0", name="ck_sales_total_positive"),
    )
    customer = db.relationship("Customer", back_populates="sales")
    user = db.relationship("User", back_populates="sales")
    items = db.relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")


class SaleItem(db.Model):
    __tablename__ = "sale_items"
    saleitemid = db.Column(db.Integer, primary_key=True)
    saleid = db.Column(db.Integer, db.ForeignKey("sales.saleid"), nullable=False)
    productid = db.Column(db.Integer, db.ForeignKey("products.productid"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unitprice = db.Column(db.Numeric(8, 2), nullable=False)
    unitcost = db.Column(db.Numeric(8, 2), nullable=False)
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_saleitems_quantity_positive"),
        CheckConstraint("unitprice > 0", name="ck_saleitems_price_positive"),
        CheckConstraint("unitcost >= 0", name="ck_saleitems_cost_nonnegative"),
    )
    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product", back_populates="sale_items")


class Payment(db.Model):
    """Customer-account payment. Intentionally has no SaleID or DueDate."""
    __tablename__ = "payments"
    paymentid = db.Column(db.Integer, primary_key=True)
    customerid = db.Column(db.Integer, db.ForeignKey("customers.customerid"), nullable=False)
    paymentdate = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_amount_positive"),)
    customer = db.relationship("Customer", back_populates="payments")
    user = db.relationship("User", back_populates="payments")


class InventoryTransaction(db.Model):
    __tablename__ = "inventory_transactions"
    inventorytransactionid = db.Column(db.Integer, primary_key=True)
    productid = db.Column(db.Integer, db.ForeignKey("products.productid"), nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey("users.userid"), nullable=False)
    transactiontype = db.Column(db.String(20), nullable=False)
    quantitychange = db.Column(db.Integer, nullable=False)
    transactiondate = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    remarks = db.Column(db.String(150))
    __table_args__ = (
        CheckConstraint("transactiontype IN ('Stock In', 'Sale', 'Adjustment')", name="ck_inventory_type"),
        CheckConstraint("quantitychange <> 0", name="ck_inventory_quantity_nonzero"),
    )
    product = db.relationship("Product", back_populates="inventory_transactions")
    user = db.relationship("User", back_populates="inventory_transactions")
