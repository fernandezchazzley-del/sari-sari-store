# Joyo Family Store — New Local DBMS Project

A fresh Flask + PostgreSQL application based on the revised Joyo Family Store requirements. This folder is independent of the older project; it does not connect to or modify the old database by default.

## Revised credit-account design

- Every cash and credit sale is saved as a `SALE` with one or more `SALE_ITEM` rows.
- `SALE` has `CustomerID` (optional for cash, required by the app for credit) and `UserID`.
- `SALE` has **no DueDate**.
- `PAYMENT` connects to **CUSTOMER and USER**, not SALE. A customer may have several credit sales and make partial payments against the overall customer balance.
- Customer balance = total credit sales for that customer − all payments for that customer.
- The app prevents a payment greater than the current customer balance.
- Product stock is checked and reduced during sale completion; stock-in/adjustments create inventory transaction records.
- Gross profit is calculated from recorded sale-item price and cost. Operating expenses and net profit are not included.

## Included features

Login, dashboard, category and product catalog, cash/credit sale entry, customer accounts and payments, inventory movements, sales/gross-profit reports, and Admin/Attendant user management. Customers do not log in.

## Install on Windows (VS Code)

### 1. Create a separate PostgreSQL database

In pgAdmin 4, connect to your PostgreSQL server, right-click **Databases → Create → Database**. Name it:

`joyo_store_new`

Do not select or drop your older `joyo_store` database.

### 2. Set up this project folder

Extract the ZIP to a new folder, for example:

`C:\Users\YourName\Downloads\joyo_family_store_new`

Open that folder in VS Code. Open **Terminal → New Terminal**, then run:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure PostgreSQL connection

Copy `.env.example` and rename the copy to `.env` in the project root. Open `.env` and replace `CHANGE_ME` with the password for your PostgreSQL `postgres` user. Keep the database name `joyo_store_new`.

Example format (replace the password):

```text
DATABASE_URL=postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/joyo_store_new
SECRET_KEY=use-a-long-random-secret-string
INITIAL_ADMIN_PASSWORD=ChangeMe123!
```

If your PostgreSQL username is not `postgres`, update that part of the URL too. If the password contains URL-reserved characters, URL-encode them.

### 4. Create tables and initial administrator

With `(venv)` active, run:

```powershell
flask --app app init-db
```

The command creates the tables and, if there is no `admin` account yet, creates:

- Username: `admin`
- Initial password: the value of `INITIAL_ADMIN_PASSWORD` in `.env` (default `ChangeMe123!`)

It will not reset an existing admin password.

### 5. Run the application

For development/testing:

```powershell
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

For local serving using Waitress, double-click `run_windows.bat` after the virtual environment and database have been configured.

## Important

- This is a local development project. Keep it on the store computer and do not expose the development server to the public internet.
- Change the initial administrator password after first login and create named family member accounts under **Users**.
- Back up the new database from pgAdmin 4 regularly. This app does not perform automatic cloud backups.
- `schema.sql` is provided as a reference. Prefer `flask --app app init-db` for creating tables in the new empty database.
- The ZIP includes code and setup instructions, not your existing store records or PostgreSQL password.
