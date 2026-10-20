# CarePulse – Quick Start

**Prerequisites:** Python 3.11–3.13, Node.js 20+, SQL Server, and [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server).

## Database (once)
Run `database/00_create_database.sql` in SSMS to create `CarePulseDB`.

## Backend (FastAPI, port 8000)
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env
```
Edit `backend/.env`: set `JWT_SECRET` (`python -c "import secrets; print(secrets.token_hex(32))"`) and `DATABASE_URL`.

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
