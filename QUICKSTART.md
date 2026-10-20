# CarePulse – Quick Start

**Prerequisites:** Python 3.11–3.13, Node.js 20+, SQL Server, and [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).

## Database (once)

**1. Is SQL Server installed and running?** (PowerShell)
```powershell
Get-Service | Where-Object { $_.Name -like '*SQL*' }
```
- `MSSQLSERVER` running → default instance, use `SERVER=localhost`.
- `MSSQL$SQLEXPRESS` running → named instance, use `SERVER=localhost\SQLEXPRESS`.
- Stopped → start it: `Start-Service 'MSSQL$SQLEXPRESS'` (or `MSSQLSERVER`) in an admin PowerShell.
- Nothing listed → install it (free, dev use):
  ```powershell
  winget install Microsoft.SQLServer.2022.Express
  winget install Microsoft.SQLServerManagementStudio.21   # optional: SSMS GUI
  winget install Microsoft.msodbcsql.18                   # ODBC Driver 18, if not installed
  ```
  Or download manually: [SQL Server Express](https://www.microsoft.com/sql-server/sql-server-downloads) (choose *Basic*; it installs `SQLEXPRESS`). Open a new terminal afterwards so the service and PATH are picked up.

**2. Create the database** (skip if it already exists – it is safe to re-run):
```powershell
sqlcmd -S "localhost\SQLEXPRESS" -E -C -i database/00_create_database.sql
```
Use `-S localhost` for a default instance, or `-U sa -P <password>` instead of `-E` for a SQL login. No `sqlcmd`? Run `database/00_create_database.sql` in SSMS instead.

**3. Verify:** `sqlcmd -S "localhost\SQLEXPRESS" -E -C -Q "SELECT name FROM sys.databases"` should list `CarePulseDB`.

**4. (Optional) Use a SQL user name and password instead of Windows login.**
Skip this if Windows login (`Trusted_Connection=yes`) works for you. Needed for a remote server.
Credentials used throughout this guide and in `backend/.env.example` (option C): user `carepulse`, password `ChangeMe!Str0ngPass`. If you change the password, change it in every place below and in `.env`.

a. Enable mixed-mode authentication: in SSMS, right-click the server → *Properties* → *Security* → select **SQL Server and Windows Authentication mode**, then restart the service:
```powershell
Restart-Service 'MSSQL$SQLEXPRESS'      # or MSSQLSERVER, in an admin PowerShell
```
b. Create a login and give it access to `CarePulseDB` only (change the password; run as an admin Windows login):
```powershell
sqlcmd -S "localhost\SQLEXPRESS" -E -C -Q "CREATE LOGIN carepulse WITH PASSWORD = 'ChangeMe!Str0ngPass', CHECK_POLICY = ON;"
sqlcmd -S "localhost\SQLEXPRESS" -E -C -d CarePulseDB -Q "CREATE USER carepulse FOR LOGIN carepulse; ALTER ROLE db_owner ADD MEMBER carepulse;"
```
`db_owner` lets the loader script create tables. For production, grant only `db_datareader`/`db_datawriter` after the first load.

c. In `backend/.env`, enable option C (it already contains these credentials) and comment out the Windows-login line, so it reads:
```
DATABASE_URL=DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=CarePulseDB;UID=carepulse;PWD=ChangeMe!Str0ngPass;Encrypt=yes;TrustServerCertificate=yes
```
Write it on one line, no quotes. If the password contains `;` or `}`, wrap it in braces: `PWD={pa;ss}}word}` (a literal `}` is doubled). Never commit `.env`.

d. Test: `sqlcmd -S "localhost\SQLEXPRESS" -U carepulse -P "ChangeMe!Str0ngPass" -C -d CarePulseDB -Q "SELECT 1"`. If it fails with *Login failed*, mixed mode isn't on or the service wasn't restarted.

Then set `DATABASE_URL` in `backend/.env` to match your instance (see the options in `.env.example`). A wrong `SERVER` is the usual cause of the *"Named Pipes Provider: Could not open a connection"* error.

## Backend (FastAPI, port 8000)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
```
Edit `backend/.env`: set `JWT_SECRET` (`python -c "import secrets; print(secrets.token_hex(32))"`) and `DATABASE_URL` (the `SERVER=` value must match your instance from the Database step; for `SQLEXPRESS` comment out option A and enable option B).

First run only:
```powershell
python scripts/load_csv_to_sqlserver.py   # load CSV data into SQL Server
python data/create_demo_users.py          # prints login emails/passwords once – save them
```

Start the server:
```powershell
uvicorn app.main:app --reload --port 8000
```
Check: http://localhost:8000/health · http://localhost:8000/health/db · http://localhost:8000/docs

## Frontend (React + Vite, port 5173)
In a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and sign in. Vite proxies `/api` and `/health` to the backend on port 8000, so start the backend first.

See `README.md` for troubleshooting and details.
