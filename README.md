# Joyo Family Sari-Sari Store Management System

A Flask + PostgreSQL starter application based on the group's project paper.

## Included
- Login with Admin and Attendant roles
- Dashboard with today's sales, product count, low-stock alerts, and outstanding credit
- Product and category management
- Customer records
- Cash and credit sales with multiple products per sale
- Stock deduction when a sale is completed
- Stock-in and adjustment records
- Partial credit payments with balance validation
- Daily/monthly sales and gross-profit reports
- Admin user-account creation

## Important scope alignment
The paper says operating expenses and net profit are outside the current scope, so this app does not include an EXPENSE table or net-profit report. It calculates gross profit only. Customers are not application users.

## Setup (Windows / VS Code)

1. Install Python 3.11+ and PostgreSQL.
2. In pgAdmin 4, create a database named `joyo_store`.
3. Open this project folder in VS Code.
4. Open Terminal and create a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\activate
   ```

5. Install packages:

   ```powershell
   pip install -r requirements.txt
   ```

6. Copy `.env.example` to `.env` and update the PostgreSQL username/password and secret key.
7. Initialize the database and first admin:

   ```powershell
   flask --app app init-db
   ```

8. Run the app:

   ```powershell
   flask --app app run --debug
   ```

9. Open http://127.0.0.1:5000

## First login
- Username: `admin`
- Password: `ChangeMe123!`

Change this password immediately after first login. Do not deploy this starter with the default secret key or default password.

## Notes before real use
This is a classroom MVP/starter, not a production-hardened point-of-sale system. Test with sample data first. Before real deployment, add password-change/reset, CSRF protection, stronger role/permission enforcement, database migrations, audit logs, backups, and automated tests. For production, run with a production WSGI server and disable Flask debug mode.
