-- New database schema for the revised Joyo Family Store application.
-- Run only against a NEW empty database, or use the application's `flask --app app init-db`.
CREATE TABLE users (
  userid SERIAL PRIMARY KEY,
  fullname VARCHAR(80) NOT NULL,
  username VARCHAR(50) NOT NULL UNIQUE,
  passwordhash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL CHECK (role IN ('Admin','Attendant')),
  createdat TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE categories (
  categoryid SERIAL PRIMARY KEY,
  categoryname VARCHAR(40) NOT NULL UNIQUE
);
CREATE TABLE products (
  productid SERIAL PRIMARY KEY,
  productname VARCHAR(80) NOT NULL,
  categoryid INTEGER NOT NULL REFERENCES categories(categoryid),
  unitcost DECIMAL(8,2) NOT NULL CHECK (unitcost >= 0),
  unitprice DECIMAL(8,2) NOT NULL CHECK (unitprice > 0),
  stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
  reorderlevel INTEGER NOT NULL DEFAULT 5 CHECK (reorderlevel >= 0)
);
CREATE TABLE customers (
  customerid SERIAL PRIMARY KEY,
  customername VARCHAR(80) NOT NULL,
  contactno VARCHAR(15),
  address VARCHAR(150)
);
CREATE TABLE sales (
  saleid SERIAL PRIMARY KEY,
  saledate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  paymenttype VARCHAR(20) NOT NULL CHECK (paymenttype IN ('Cash','Credit')),
  totalamount DECIMAL(10,2) NOT NULL CHECK (totalamount > 0),
  customerid INTEGER REFERENCES customers(customerid),
  userid INTEGER NOT NULL REFERENCES users(userid)
  -- DueDate intentionally omitted in revised design.
);
CREATE TABLE sale_items (
  saleitemid SERIAL PRIMARY KEY,
  saleid INTEGER NOT NULL REFERENCES sales(saleid),
  productid INTEGER NOT NULL REFERENCES products(productid),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  unitprice DECIMAL(8,2) NOT NULL CHECK (unitprice > 0),
  unitcost DECIMAL(8,2) NOT NULL CHECK (unitcost >= 0)
);
CREATE TABLE payments (
  paymentid SERIAL PRIMARY KEY,
  customerid INTEGER NOT NULL REFERENCES customers(customerid),
  paymentdate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
  userid INTEGER NOT NULL REFERENCES users(userid)
  -- Customer-account payment: no SaleID in revised design.
);
CREATE TABLE inventory_transactions (
  inventorytransactionid SERIAL PRIMARY KEY,
  productid INTEGER NOT NULL REFERENCES products(productid),
  userid INTEGER NOT NULL REFERENCES users(userid),
  transactiontype VARCHAR(20) NOT NULL CHECK (transactiontype IN ('Stock In','Sale','Adjustment')),
  quantitychange INTEGER NOT NULL CHECK (quantitychange <> 0),
  transactiondate TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  remarks VARCHAR(150)
);
