# CarePulse Backend – Study Guide

This file explains each part of the backend code.
Use it to learn the code and to prepare for your Viva.

---

## 1. What is the backend?

The backend is a **web API**. It is a program that waits for requests from the frontend (React) and sends back data.

The backend does these jobs:

1. It lets staff **log in**.
2. It checks **who** the user is and **what** the user may see.
3. It reads hospital data from **SQL Server**.
4. It calculates **KPIs** (numbers such as admissions, wait time, bed occupancy).
5. It sends the result as **JSON**.

**Technologies used**

| Tool | What it does |
|---|---|
| Python | The programming language. |
| FastAPI | The web framework. It makes the API routes. |
| Uvicorn | The server that runs FastAPI. |
| Pydantic | Checks data shapes (models). Reads settings. |
| SQLAlchemy + pyodbc | Connects Python to SQL Server. |
| python-jose | Creates and checks JWT tokens. |
| bcrypt | Hashes passwords. |
| pytest | Runs the automatic tests. |
| pandas | Used only in scripts and tests. The API does not use it. |

---

## 2. Big picture

A request goes through these layers, from top to bottom:

```
Frontend (React)
     |  HTTP request
     v
Middleware        (CORS, request id, security headers, error handler)
     |
     v
Router            (URL + role check)              router.py
     |
     v
Controller        (connects the parts)            controller.py
     |
     v
Service           (business logic, percentages)   service.py
     |
     v
Repository        (SQL queries)                   sql_repo.py
     |
     v
Database handle  ->  SQL Server
```

**Why layers?** Each layer has one job. This makes the code easy to read, test and change.

**Simple rule to remember for the Viva:**

| Layer | One-line job |
|---|---|
| Router | "Which URL? Who may enter?" |
| Controller | "Call the right functions. Build the response." |
| Service | "Do the math." |
| Repository | "Ask the database." |

---

## 3. Folder map

```
backend/
├── app/
│   ├── main.py            Starts the application
│   ├── config.py          All settings
│   ├── routes.py          Connects all routers
│   ├── core/              Shared rules (constants, errors, JWT, permissions)
│   ├── db/                Database connection and CSV reading
│   ├── middleware/        Code that runs on every request
│   ├── auth/              Login feature
│   ├── users/             User model and roles
│   ├── analytics/         Dashboard data feature
│   ├── health/            "Is the server alive?" checks
│   └── repositories/      SQL queries
├── data/                  Login accounts (users.csv) and the script that makes them
├── scripts/               Helper tools for the database
├── tests/                 Automatic tests
├── requirements.txt       List of Python packages
└── .env.example           Example settings file
```

---

## 4. How to run it

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
copy .env.example .env              # then edit .env
python scripts/load_csv_to_sqlserver.py
python scripts/check_db.py
python data/create_demo_users.py    # prints the passwords. Save them.
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` to see the Swagger page. It lists all endpoints.

Run the tests:

```bash
pytest
```

---

## 5. All endpoints

| Method | URL | Who may use it | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | Everyone | Log in. Get a JWT. |
| GET | `/api/auth/me` | Any logged-in user | Show own profile. |
| GET | `/api/analytics/kpis` | All roles | KPI cards. |
| GET | `/api/analytics/monthly-trend` | All roles | Admissions and discharges per month. |
| GET | `/api/analytics/dept-activity` | All roles | Visits and admissions per department. |
| GET | `/api/analytics/patient-flow` | Dean, Admin, Ops Manager, Dept Head, Doctor | Patient Flow page. |
| GET | `/api/analytics/bed-availability` | Dean, Admin, Ops Manager, Dept Head, Doctor, Nurse | Bed page. |
| GET | `/api/analytics/departments` | All roles | List for dropdowns. |
| GET | `/api/analytics/data-quality` | Dean, Admin, Ops Manager | Data problem report. |
| GET | `/health` | Everyone | Is the server alive? |
| GET | `/health/db` | Everyone | Can the server reach SQL Server? |

**Query filters** (optional): `start_date`, `end_date`, `department_id`, `visit_type`, `visit_status`.

---

## 6. File-by-file explanation

### 6.1 `app/main.py` – Application start

| Item | Explanation |
|---|---|
| `create_app()` | **Factory function.** It makes the FastAPI app. It adds middleware and routes. |
| `app` | The ready app. Uvicorn uses this object. |

**Why a factory?** Tests can make a new, clean app. Startup code stays in one place.

---

### 6.2 `app/config.py` – Settings

| Item | Explanation |
|---|---|
| `Settings` (class) | Holds all settings. Reads them from environment variables or `backend/.env`. Based on Pydantic `BaseSettings`. |
| `get_settings()` | Returns the `Settings` object. It uses `@lru_cache`, so it creates the object only once. |
| `cors_origins` (property) | Changes the text list of allowed websites into a Python list. |
| `users_csv_file` (property) | Gives the full path of `users.csv`. |
| `jwt_secret_must_be_strong` | **Validator.** Stops the app if `JWT_SECRET` has fewer than 32 characters. |
| `identifiers_must_be_safe` | **Validator.** Allows only letters, digits and `_` in `DB_SCHEMA` and `DB_TABLE_SUFFIX`. This stops SQL injection through settings. |

**Important settings**

| Setting | Meaning |
|---|---|
| `JWT_SECRET` | Secret key to sign tokens. **Required.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token life. Default 60. |
| `DATABASE_URL` | How to connect to SQL Server. |
| `DB_SCHEMA`, `DB_TABLE_SUFFIX` | Schema and table-name ending (for example `_V6`). |
| `CORS_ORIGINS` | Websites that may call the API. |
| `BCRYPT_ROUNDS` | Password hash strength. Default 12. |

**Why use settings?** No password or secret lives in the source code.

---

### 6.3 `app/routes.py` – Route registration

| Item | Explanation |
|---|---|
| `register_routes(app, settings)` | Mounts the auth router and the analytics router under `/api`. Mounts the health router with no prefix. |

---

### 6.4 `app/core/` – Shared rules

#### `constants.py`

Fixed values used by many files.

| Constant | Meaning |
|---|---|
| `T_VISITS`, `T_BEDS`, … | **Logical** table names used in code. |
| `DEFAULT_TABLE_NAMES` | Map from logical name to real table name. |
| `STATUS_ONGOING` | Visit status text `"Ongoing"`. |
| `BED_OCCUPIED`, `BED_AVAILABLE`, `BED_MAINTENANCE`, `BED_RESERVED` | The four bed statuses. |
| `UNASSIGNED_DEPARTMENT` | Label for a ward with no department. |
| `PERCENT_DECIMALS` | Decimal places for percentages. |

#### `exceptions.py`

Custom errors. The service code raises them. The error handler changes them into HTTP answers.

| Class | HTTP code | Use |
|---|---|---|
| `CarePulseError` | – | **Base class.** Holds `status_code` and `detail`. |
| `NotFoundError` | 404 | Item not found. |
| `ForbiddenError` | 403 | User has no permission. |
| `UnauthorizedError` | 401 | User is not logged in. |
| `BadRequestError` | 400 | Wrong input (for example a bad date). |
| `DatabaseUnavailableError` | 503 | Cannot reach SQL Server. |
| `DatabaseQueryError` | 500 | The SQL query failed. |

| Function | Explanation |
|---|---|
| `carepulse_error_handler()` | Changes a `CarePulseError` into JSON: `{"detail": "..."}`. |

**Why custom errors?** Business code does not need to know about HTTP.

#### `security.py` – JWT

**JWT** = JSON Web Token. It is a signed text with three parts: `header.payload.signature`.
The server signs it at login. The client sends it back on each request. The server checks the signature.

| Item | Explanation |
|---|---|
| `oauth2_scheme` | `HTTPBearer`. Reads the `Authorization: Bearer <token>` header. |
| `create_access_token(data, expires_delta)` | Adds an expiry time (`exp`) and signs the token with `JWT_SECRET` (HS256). |
| `_decode_raw(token)` | Checks the signature and expiry. Raises 401 if the token is bad or old. |
| `get_current_user()` | **FastAPI dependency.** Reads the token. Returns a `TokenUser`. Raises 401 if the token is missing or has missing fields. |

**Why HS256?** One server makes and checks tokens. One shared secret is enough.

#### `permissions.py` – Who may see what

| Item | Explanation |
|---|---|
| `FULL_ACCESS_ROLES` | Dean, Hospital Admin, Operations Manager. They see all departments. |
| `OVERVIEW_ROLES` | All roles. |
| `PATIENT_FLOW_ROLES` | Dean, Admin, Ops Manager, Department Head, Doctor. |
| `BED_AVAILABILITY_ROLES` | The roles above plus Nurse. |
| `require_roles(*allowed)` | **Dependency factory.** Makes a check that gives 403 if the role is not allowed. |
| `get_department_scope()` | Returns `None` for full-access roles. Returns the user's own `department_id` for other roles. |

**Two layers of protection:**

1. **Route layer** – `require_roles` blocks a role that has no access.
2. **Data layer** – `get_department_scope` limits the data to the user's department.

The scope comes from the token. The frontend cannot change it.

| Role | Overview | Patient Flow | Bed Availability | Departments |
|---|---|---|---|---|
| Dean / Hospital Admin / Ops Manager | Yes | Yes | Yes | All |
| Department Head | Yes | Yes | Yes | Own only |
| Doctor | Yes | Yes | Yes | Own only |
| Nurse | Yes | No | Yes | Own only |
| Receptionist | Yes | No | No | Own only |

> Note: the text in the `permissions.py` comment says "6 roles". The code has **7** roles, because `Dean` is also a role.

---

### 6.5 `app/users/models.py` – User models

| Class | Explanation |
|---|---|
| `UserRole` | **Enum** of the 7 roles: Dean, Hospital Admin, Operations Manager, Department Head, Doctor, Nurse, Receptionist. It inherits from `str`, so JSON shows `"Doctor"`. |
| `TokenUser` | **Pydantic model.** Holds `staff_id`, `email`, `role`, `department_id`, `department_name`. It is built from the token. No database read is needed. |

**Why an enum?** A typo in a role name is caught early. The code is safer.

---

### 6.6 `app/db/` – Database

#### `database.py`

| Item | Explanation |
|---|---|
| `build_engine_url(raw)` | Accepts a SQLAlchemy URL (`mssql+pyodbc://…`) or an ODBC string (`DRIVER=…`). Raises an error if `DATABASE_URL` is empty or wrong. |
| `SQLAlchemyDatabase` (class) | The production database handle. |
| ↳ `table(name)` | Gives the full table name, for example `[dbo].[patient_visits]`. |
| ↳ `query(sql, params)` | Runs SQL with **bound parameters**. Returns a list of dicts. Changes database errors to 503 or 500. |
| `get_database()` | Makes the engine one time (`@lru_cache`). Sets up the **connection pool**. |
| `get_db()` | **FastAPI dependency.** Tests replace it with a fake database. |

**Why bound parameters?** Values go in separately (`:dept`), never inside the SQL text. This **stops SQL injection**.

**Why a connection pool?** The app re-uses open connections. This is faster.

#### `dialect.py`

SQL Server and SQLite use different functions for dates. SQLite is used only in tests.

| Function | Explanation |
|---|---|
| `minutes_between(dialect, start, end)` | SQL text for "minutes from start to end". |
| `year_month(dialect, col)` | SQL text for the `YYYY-MM` label of a date. |

#### `csv_data.py`

Reads the CSV files into Python rows with the correct types.

| Item | Explanation |
|---|---|
| `TABLE_FILES` | Table name → CSV file name. |
| `LOAD_ORDER` | The order in which tables load. Parents first (foreign keys). |
| `COLUMNS` | The columns and types of each table. |
| `parse_datetime(text)` | Tries several date formats. Raises an error if none fits. |
| `_convert(value, kind)` | Changes text to `int`, `date`, `datetime` or `str`. Empty text becomes `None`. |
| `read_table(table, data_dir)` | Reads one CSV. Gives a clear error with file, line and column if the data is wrong. |

---

### 6.7 `app/middleware/` – Code that runs on every request

| File / Class | Explanation |
|---|---|
| `__init__.py` → `register_middleware()` | Adds all middleware in the correct order: CORS → request context → security headers. |
| `request_context.py` → `RequestContextMiddleware` | Gives each request an id (`X-Request-ID`). Writes one log line: method, path, status, time. |
| `security_headers.py` → `SecurityHeadersMiddleware` | Adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`. Adds `Cache-Control: no-store` for `/api` answers. |
| `error_handlers.py` → `unhandled_error_handler()` | Catches all other errors. Sends a general 500 message. Writes the full error in the log. The client never sees the details. |
| `error_handlers.py` → `register_exception_handlers()` | Connects the two error handlers to the app. |

**What is CORS?** A browser rule. It lets the frontend (port 5173) call the backend (port 8000). Only the websites in `CORS_ORIGINS` are allowed.

**What is middleware?** Code that wraps every request and every response.

---

### 6.8 `app/auth/` – Login feature

| File | Item | Explanation |
|---|---|---|
| `models.py` | `LoginRequest` | Input of login: `email`, `password`. |
| | `TokenResponse` | Output of login: `access_token`, `token_type`, `role`, `department_id`, `department_name`, `staff_id`, `full_name`. |
| | `MeResponse` | Output of `/me`: profile from the token. |
| `service.py` | `verify_password()` | Compares a password with a bcrypt hash. |
| | `hash_password()` | Makes a bcrypt hash. |
| | `_load_users()` | Reads `users.csv`. |
| | `authenticate_user(email, password)` | Finds the user, checks `Is_Active`, checks the password. Returns the user or `None`. |
| `controller.py` | `login(body)` | Checks the credentials. Makes the JWT with role and department inside. Returns `TokenResponse`. |
| | `me(current_user)` | Builds `MeResponse`. |
| `router.py` | `POST /auth/login`, `GET /auth/me` | The two URLs. |

**Login steps:**

1. The user sends email and password.
2. `authenticate_user` finds the user in `users.csv`.
3. `bcrypt` compares the password with the stored hash.
4. The controller makes a JWT.
5. The frontend keeps the token and sends it in every next request.

**Security points to say in the Viva:**

- The system stores **hashes only**, never plain passwords.
- A wrong email and a wrong password give the **same** error. An attacker cannot learn which emails exist.
- `bcrypt.checkpw` takes a constant time. This stops timing attacks.
- The token has an expiry time.

---

### 6.9 `app/analytics/` – Dashboard data feature

This is the main feature.

#### `filters.py`

| Item | Explanation |
|---|---|
| `Filters` (frozen dataclass) | Holds checked filter values: `start`, `end_exclusive`, `department_id`, `visit_type`, `visit_status`. It cannot change after creation. |
| `_parse_date()` | Changes `YYYY-MM-DD` text to a date. Gives 400 if wrong. |
| `_parse_dept()` | Changes text to a number. Gives 400 if wrong. |
| `_clean_text()` | Removes spaces. Rejects long text (more than 40 characters). |
| `_hint()` | Makes a friendly format hint for error messages. |
| `build_filters(...)` | Does all checks and makes the `Filters` object. |

**Date rules:**

- `start_date` includes that whole day.
- `end_date` includes that whole day too. The code uses `< end_date + 1 day`. So the last day is never lost.

**Department rule:** If the user has a department scope, the server uses it. A `department_id` in the URL cannot widen it.

#### `dependencies.py`

| Function | Explanation |
|---|---|
| `get_filters()` | Reads query parameters. Adds the user's department scope. Returns `Filters`. |
| `get_scope_filters()` | Returns `Filters` with only the department scope. Used for the department list. |

#### `models.py` – Response shapes (Pydantic)

| Class | Used for |
|---|---|
| `DepartmentInfo` | Department id and name. |
| `KPIResponse` | KPI cards: `admissions`, `discharges`, `avg_wait_minutes`, `bed_occupancy_pct`, `current_admissions`, `wait_samples`. |
| `MonthlyPoint`, `MonthlyTrendResponse` | Monthly trend. |
| `DeptActivityPoint`, `DeptActivityResponse` | Department bars. |
| `VisitTypeBreakdown`, `StatusBreakdown` | Count and percentage per type or status. |
| `PatientFlowResponse` | Full Patient Flow page. |
| `BedStatusBreakdown` | Count and percentage per bed status. |
| `WardOccupancy` | One ward: beds, occupied, available, percentage. |
| `BedAvailabilityResponse` | Full Bed page. |
| `DataQualityCheck`, `DataQualityResponse` | Data problem report. |

**Why response models?** FastAPI checks the output, makes the docs, and removes extra fields.

#### `service.py` – Business logic

| Function | Explanation |
|---|---|
| `pct(part, total)` | Percentage with 1 decimal. Returns `0.0` if total is 0 (no divide-by-zero error). |
| `occupancy_pct(occupied, total, maintenance)` | Occupied ÷ (total − maintenance) × 100. |
| `kpis(db, f)` | Joins visit KPIs and bed occupancy. |
| `monthly_trend(db, f)` | Calls the repository. |
| `dept_activity(db, f)` | Calls the repository. |
| `_with_pct(rows, key)` | Adds a percentage to each row. |
| `patient_flow(db, f)` | Collects all Patient Flow data. |
| `bed_availability(db, department_id)` | Calculates ward and total bed numbers. Sorts wards by highest occupancy. |

#### `controller.py`

| Function | Explanation |
|---|---|
| `get_kpis` | Calls `svc.kpis`. Returns `KPIResponse`. |
| `get_monthly_trend` | Returns `MonthlyTrendResponse`. |
| `get_dept_activity` | Returns `DeptActivityResponse`. |
| `get_patient_flow` | Returns `PatientFlowResponse`. |
| `get_bed_availability` | Returns `BedAvailabilityResponse`. |
| `get_departments` | Returns a list of `{Department_ID, Department_Name}`. |
| `get_data_quality` | Returns `DataQualityResponse`. |

#### `router.py`

Declares the 7 analytics URLs. Each route has these parts:

1. `require_roles(...)` – role check.
2. `get_filters` – filters and scope.
3. `get_db` – database.
4. A call to the controller.

---

### 6.10 `app/repositories/` – SQL queries

#### `sql_repo.py`

All SQL is here. Each function gets `db` and `Filters`. Each returns plain Python data.

**Helper functions**

| Function | Explanation |
|---|---|
| `_and(*conds)` | Joins conditions with `AND`. Skips empty ones. |
| `_in_range(col, f)` | Makes the date range condition. |
| `_visit_base(f, alias, include_dept)` | Makes the condition for department, type and status. |
| `_params(f)` | Makes the dict of bound parameters. |
| `_i(v)` | Changes `None` to `0`. |

**Query functions**

| Function | What it returns |
|---|---|
| `departments()` | List of departments. |
| `visit_kpis()` | Total visits, admissions, discharges, average wait, wait samples, current admissions. One SQL query with `SUM(CASE WHEN …)`. |
| `monthly_trend()` | Admissions and discharges per month (`UNION ALL`). |
| `dept_activity()` | Visits and admissions per department (`LEFT JOIN`). |
| `_visit_breakdown()` | Count per column value. |
| `visit_type_counts()` | Count per visit type. |
| `visit_status_counts()` | Count per visit status. |
| `ward_bed_rows()` | Per ward: total, occupied, available, maintenance, reserved. |
| `bed_status_counts()` | Count per bed status. |
| `data_quality()` | Nine read-only checks (for example "discharge before admission"). |

**KPI rules (also in `docs/METRICS.md`):**

| KPI | Rule |
|---|---|
| Admissions | Visits with `Admission_Time`, counted by that date. |
| Discharges | Visits with `Discharge_Time`, counted by that date. |
| Wait time | `Consultation_Start_Time − Registration_Time` in minutes. Only when both exist and result ≥ 0. |
| Bed occupancy | Occupied ÷ (all beds − Maintenance beds) × 100. It is a **snapshot** of now. |
| Current admissions | Status `Ongoing`, has `Admission_Time`, no `Discharge_Time`. |

#### `base.py`

| Class | Explanation |
|---|---|
| `BaseRepository` (abstract) | An interface with `get_all()` and `get_by_id()`. **The code does not use it now.** It is kept for future use. |

---

### 6.11 `app/health/` – Health checks

| File | Item | Explanation |
|---|---|---|
| `controller.py` | `liveness()` | Returns `{"status": "ok"}`. |
| | `database_status(db)` | Runs `SELECT 1`. Proves the database answers. |
| `router.py` | `GET /health`, `GET /health/db` | No login needed. Used by monitoring tools. |

---

## 7. Data folder and scripts

### `data/create_demo_users.py`

Makes `data/users.csv` with **three** demo accounts: Dean, Doctor (Emergency), Nurse (Orthopedics).

| Item | Explanation |
|---|---|
| `DEMO_ACCOUNTS` | The three accounts. |
| `FIELDNAMES` | CSV column names. |
| `main()` | Makes a random password for each account. Hashes it with bcrypt. Prints the password once. Saves only the hash. |

### `scripts/`

| File | Explanation |
|---|---|
| `_common.py` | Shared helpers. `read_env()` reads `.env`. `make_database()` builds a database handle. `explain_connection_error()` prints help text. |
| `load_csv_to_sqlserver.py` | Creates the tables from `database/01_schema.sql`. Loads the 7 CSV files. It **skips** tables that already have rows. Option `--drop-and-reload` deletes all (you must type YES). |
| `check_db.py` | **Read-only.** Checks connection, tables, columns and date types. Prints KPIs and the data-quality report. |
| `csv_expected.py` | Calculates the same metrics with **pandas**. It shares no code with the SQL layer. |
| `verify_database.py` | Compares SQL results with `csv_expected.py`. Prints `ALL CHECKS PASSED` when they match. |

**Why two calculations?** If SQL and pandas give the same number, the number is very likely correct.

---

## 8. Tests (`tests/`)

Run with `pytest`. The tests do **not** need SQL Server. They use an in-memory SQLite database.

| File | Explanation |
|---|---|
| `conftest.py` | Sets test settings **before** the app is imported. Makes a temporary `users.csv` with one user per role. Gives the `client` and `test_credentials` fixtures. |
| `helpers.py` | `Sqlite3Database` – a fake database with the same interface as the real one. Loads the CSV files. |
| `test_auth.py` | Login success, login failure, `/me`, token content, health check. |
| `test_api.py` | Login required, KPIs match the CSV, date filter, department scope, role limits, bad filters (400), database down (503). |
| `test_sql_metrics.py` | SQL results match pandas. Maintenance beds are not "available". Negative waits are excluded. No divide-by-zero. SQL-injection text is treated as a plain value. |

**Key words:**

- **Fixture** – a ready-made helper object for tests (for example `client`).
- **TestClient** – calls the API without starting a real server.
- **Dependency override** – replaces `get_db` with the SQLite fake.

---

## 9. Example: follow one request

The user (Nurse, Orthopedics) opens the Bed page.

1. The browser calls `GET /api/analytics/bed-availability` with `Authorization: Bearer <token>`.
2. Middleware gives the request an id and adds security headers.
3. `get_current_user` checks the token. It builds a `TokenUser`.
4. `require_roles(*BED_AVAILABILITY_ROLES)` allows `Nurse`.
5. `get_department_scope` returns `"4"` (Orthopedics).
6. `build_filters` makes `Filters(department_id=4)`.
7. The controller calls `service.bed_availability`.
8. The service calls `sql_repo.ward_bed_rows` and `bed_status_counts`.
9. The repository runs SQL with `:dept = 4`.
10. The service calculates the percentages.
11. FastAPI checks the result against `BedAvailabilityResponse` and sends JSON.

---

## 10. Viva question bank

**Q: What is FastAPI?**
A Python web framework. It makes APIs fast. It checks input with Pydantic. It makes Swagger docs by itself.

**Q: Why do you use layers (router, controller, service, repository)?**
Each layer has one job. It is easier to read, test and change.

**Q: What is a JWT? Why use it?**
A signed token. It holds the user's role and department. The server needs no database read on each request.

**Q: How do you keep passwords safe?**
We store only bcrypt hashes. bcrypt is slow on purpose and uses a random salt.

**Q: How do you stop SQL injection?**
Every user value is a bound parameter (`:dept`). Only table names from validated settings are put in the SQL text.

**Q: How does role-based access work?**
Two steps. `require_roles` checks the role. `get_department_scope` limits the data to the user's department. Both use the token.

**Q: Can a Doctor see another department by changing the URL?**
No. The server uses the department from the token. The URL value is ignored for scoped roles.

**Q: How is bed occupancy calculated?**
Occupied beds ÷ (all beds − beds in maintenance) × 100.

**Q: How is wait time calculated?**
`Consultation_Start_Time − Registration_Time` in minutes. Negative values are excluded.

**Q: Why does `end_date` add one day?**
So the whole last day is included. The code uses `< end_date + 1 day`.

**Q: What does middleware do here?**
It adds CORS, a request id with logging, and security headers. It also handles errors.

**Q: Why do the tests use SQLite?**
Tests then run anywhere and need no SQL Server. `dialect.py` handles the small SQL differences.

**Q: How do you know the numbers are correct?**
`verify_database.py` compares the SQL results with an independent pandas calculation.

**Q: What is `lru_cache` used for?**
It makes `get_settings()` and `get_database()` run only once. The app re-uses the same object.

**Q: What does `get_db` do and why is it a dependency?**
It gives the database to each route. Tests can replace it with a fake.

**Q: What happens when SQL Server is off?**
`SQLAlchemyDatabase.query` raises `DatabaseUnavailableError`. The client gets HTTP 503 with a clear message.

---

## 11. Known limits (be honest in the Viva)

- Users live in `users.csv`, not in the database. This is simple but not for a large production system.
- `users.csv` is read from disk at each login.
- `create_demo_users.py` makes only 3 accounts (Dean, Doctor, Nurse). The tests create all roles by themselves.
- Bed availability is a **current snapshot**. Date filters do not change it.
- `BaseRepository` in `base.py` is not used.
- Some code raises FastAPI `HTTPException`; other code raises the custom `CarePulseError`. Both give the same JSON shape.

---

## 12. Quick glossary

| Word | Simple meaning |
|---|---|
| API | A way for programs to talk to each other. |
| Endpoint | One URL of the API. |
| Router | Connects a URL to a function. |
| Dependency | A function that FastAPI runs before the route function. |
| Middleware | Code that runs on every request. |
| Pydantic model | A class that checks the shape of data. |
| JWT | A signed token that proves who the user is. |
| bcrypt | A password hash method. |
| CORS | A browser rule for calls between different websites. |
| KPI | A key number (for example average wait time). |
| Repository | Code that talks to the database. |
| Bound parameter | A value sent separately from the SQL text. |
| Connection pool | A set of open database connections that the app re-uses. |
| Fixture | A ready-made object for a test. |
