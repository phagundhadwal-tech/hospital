# CarePulse – Hospital Operations Dashboard (React + FastAPI + SQL Server)

The original dashboard (login, sidebar, KPI cards, charts, ward cards) is unchanged visually.
Every number now comes from **Microsoft SQL Server**. No mock data, no CSV reading at runtime.

```
CarePulse_Project/
├── database/                 00_create_database.sql, 01_schema.sql, data/*_V6.csv  (your dataset)
├── backend/                  FastAPI + SQLAlchemy + pyodbc
│   ├── app/                  api, auth, db layer, SQL repository
│   ├── scripts/              load_csv_to_sqlserver.py, check_db.py, verify_database.py
│   ├── data/create_demo_users.py
│   └── tests/
├── frontend/                 React + Vite (your existing UI)
└── docs/METRICS.md           every KPI formula, filters, data-quality findings
```

## 0. Install once (Windows, macOS or Linux)
1. **Python 3.11 – 3.13**, **Node.js 20+**
2. **Microsoft ODBC Driver 18 for SQL Server** – https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server  
   (If you already use SSMS you still need this driver for Python.)
3. A running **SQL Server** (Express is fine) and **SSMS**.

## 1. Create the database in SSMS
Open `database/00_create_database.sql` in SSMS and press **Execute** (creates an empty `CarePulseDB`; skip if it exists).
* **Your data is only in the CSV files (default):** the loader in step 4 creates the tables and loads them.
* **You already imported the tables into SQL Server with SSMS:** skip the loader. In `.env` set `DATABASE_URL` to that database; if your tables are named like `PATIENT_VISITS_V6` set `DB_TABLE_SUFFIX=_V6`; if they are not in `dbo` set `DB_SCHEMA`. `python scripts/check_db.py` then tells you exactly what is missing. Date columns must be real `datetime`/`datetime2` (not text).

## 2. Backend setup
Open a terminal in the `backend` folder:

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):   .venv\Scripts\Activate.ps1
# Windows (cmd):          .venv\Scripts\activate.bat
# macOS / Linux:          source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure the connection (`.env`)
```bash
# Windows:  copy .env.example .env        macOS/Linux:  cp .env.example .env
```
Open `backend/.env` and set:
* `JWT_SECRET` – run `python -c "import secrets; print(secrets.token_hex(32))"` and paste the result.
* `DATABASE_URL` – choose the example that matches how you log in to SSMS (Windows login / SQL login / named instance such as `SERVER=localhost\SQLEXPRESS`).  
  `TrustServerCertificate=yes` is for a development PC with a self-signed certificate only – remove it on a production server that has a real certificate.

## 4. Load + verify the database (backend folder, venv active)
```bash
python scripts/load_csv_to_sqlserver.py    # only if the data is not in SQL Server yet; safe to re-run (never duplicates or deletes)
python scripts/check_db.py                 # connection, tables, column types, KPIs, data-quality report
python scripts/verify_database.py          # SQL results vs independent pandas calculation (expects "ALL CHECKS PASSED")
```

## 5. Create the login accounts
```bash
python data/create_demo_users.py
```
It prints one e-mail + random password per role **once** – note them down (only hashes are stored in `data/users.csv`).
`admin@carepulse.local` sees every department; the other roles are limited to their department.

## 6. Run the backend
```bash
uvicorn app.main:app --reload --port 8000
```
* http://localhost:8000/health → API is up  
* http://localhost:8000/health/db → SQL Server reachable  
* http://localhost:8000/docs → interactive API docs

## 7. Run the frontend (second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173** and sign in with an account from step 5.

## Filters & what changed in the UI
Same layout, colours, charts and routes. Small data-driven edits only:
* Date and department filters now reach the database (the department filter previously only trimmed one chart). Reset restores everything.
* “—” is shown for average wait when no valid visits exist; empty charts show a short “no data for these filters” message.
* Bed percentages use *operational beds* (all beds − maintenance) as the one denominator; KPI sub-labels say so.
* Stale responses are cancelled (a slow older request cannot overwrite a newer filter result). Failed requests show a clear error – never fake data.
* Ward-type pill colours for the new ward types (Emergency / Pediatric / Private).

## API (all require a login token; role/department rules unchanged)
`POST /api/auth/login`, `GET /api/auth/me`, and under `/api/analytics`: `kpis`, `monthly-trend`, `dept-activity`, `patient-flow`, `bed-availability`, `departments`, `data-quality` (admin roles).
Filters: `start_date`, `end_date`, `department_id`, `visit_type`, `visit_status`.
No patient-identifying fields are returned by any endpoint.

## Tests
```bash
cd backend
python -m pytest -q
```
`test_sql_metrics.py` compares the SQL with pandas on the CSV data (no SQL Server needed – uses an in-memory SQLite copy and the same repository code); `test_api.py` / `test_auth.py` cover login, roles, department scoping, filters and the database-outage message.

## Troubleshooting
| Message | Fix |
|---|---|
| `Can't open lib 'ODBC Driver 18 for SQL Server'` | Install the ODBC driver (step 0) or change `DRIVER={...}` to the version you have (`ODBC Driver 17 for SQL Server`). |
| `certificate verify failed` / SSL error | Dev PC: add `TrustServerCertificate=yes`. Production: install a trusted certificate instead. |
| `Login failed` | Windows login: keep `Trusted_Connection=yes`. SQL login: use `UID=...;PWD=...` and make sure SQL authentication is enabled. |
| `Cannot open database "CarePulseDB"` | Run `database/00_create_database.sql` in SSMS. |
| Dashboard says “Cannot reach the CarePulse API” | Backend not running on port 8000 (step 6). |
| Dashboard says “Cannot connect to SQL Server” | Open `/health/db`, fix `DATABASE_URL`, restart uvicorn. |
| Login says wrong password after rebuilding | Re-run `python data/create_demo_users.py` and use the newly printed passwords. |
| “Your account is linked to an invalid department” | `users.csv` was created for the old dataset – re-run `create_demo_users.py`. |
