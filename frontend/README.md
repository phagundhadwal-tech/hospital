# CarePulse Frontend

CarePulse is a hospital dashboard. The frontend is the part the user sees in the browser.
It shows charts and numbers about patients, visits and beds.
It gets the data from the backend (a Python API on port 8000).

This file helps you to understand the code and to explain it in a Viva.

---

## 1. Contents

1. [Quick start](#2-quick-start)
2. [Tech stack](#3-tech-stack)
3. [Folder structure](#4-folder-structure)
4. [How the app starts](#5-how-the-app-starts)
5. [Every file explained](#6-every-file-explained)
6. [Data flow (one full example)](#7-data-flow-one-full-example)
7. [Web basics: HTTP, HTTPS, verbs, status codes](#8-web-basics)
8. [React basics](#9-react-basics)
9. [React features used in this project](#10-react-features-used-in-this-project)
10. [Why React? Why not React?](#11-why-react-why-not-react)
11. [Possible Viva questions](#12-possible-viva-questions)

---

## 2. Quick start

```bash
cd frontend
npm install        # install the packages
npm run dev        # start the dev server at http://localhost:5173
npm run build      # make the production files
npm run lint       # check the code for errors
```

The backend must run on port 8000. Vite sends all `/api` requests to the backend (see `vite.config.js`).

---

## 3. Tech stack

| Tool | What it is | Why we use it |
|------|-----------|---------------|
| **React 19** | A library to build user interfaces | Builds the screen from small parts (components) |
| **Vite** | A build tool and dev server | Starts fast and updates the page when you save |
| **React Router** | A routing library | Changes the page without a full reload |
| **Axios** | An HTTP client | Sends requests to the backend |
| **Recharts** | A chart library | Draws bar, line and pie charts |
| **Lucide React** | An icon library | Gives the icons (bed, lock, mail) |
| **Oxlint** | A linter | Finds mistakes in the code |
| **Playwright** | A test tool | Tests the app in a real browser |

---

## 4. Folder structure

```
frontend/
├── index.html              The only HTML page (has <div id="root">)
├── vite.config.js          Vite settings and the /api proxy
├── package.json            List of packages and scripts
├── public/                 Static files (favicon, icons)
└── src/
    ├── main.jsx            Entry point. Starts React.
    ├── App.jsx             Defines all the routes (URLs)
    ├── index.css / App.css Styles
    ├── api/
    │   └── client.js       All backend calls (Axios)
    ├── contexts/
    │   └── AuthContext.jsx Login state and role rules
    ├── components/
    │   ├── layout/         Parts that wrap every page
    │   │   ├── Layout.jsx  Top bar + sidebar + page area
    │   │   └── Sidebar.jsx Navigation menu
    │   └── ui/
    │       └── UI.jsx      Small reusable parts (card, spinner...)
    └── pages/              One file for each screen
        ├── Login.jsx
        ├── Overview.jsx
        ├── PatientFlow.jsx
        ├── BedAvailability.jsx
        └── AccessDenied.jsx
```

**Simple rule:**
- `pages/` = full screens.
- `components/` = small parts that pages use again.
- `api/` = talks to the backend.
- `contexts/` = data that many files share.

---

## 5. How the app starts

```
index.html  →  main.jsx  →  App.jsx  →  Router  →  Page
```

1. The browser opens `index.html`. It has an empty `<div id="root">`.
2. `main.jsx` tells React to draw `<App />` inside that div.
3. `App.jsx` wraps everything in `AuthProvider` (login data) and `BrowserRouter` (URLs).
4. The router looks at the URL and shows the matching page.

---

## 6. Every file explained

### 6.1 `main.jsx` — entry point
- `createRoot(...).render(...)` starts React in the `#root` div.
- `<StrictMode>` finds possible problems in development. It does nothing in production.

### 6.2 `App.jsx` — the route map

| URL | Page shown | Note |
|-----|-----------|------|
| `/login` | `Login` | Public |
| `/access-denied` | `AccessDenied` | Public |
| `/` | Redirects to `/overview` | `<Navigate>` |
| `/overview` | `Overview` | Inside `Layout` |
| `/patient-flow` | `PatientFlow` | Inside `Layout` |
| `/bed-availability` | `BedAvailability` | Inside `Layout` |
| anything else (`*`) | Redirects to `/overview` | Catch-all |

Terms:
- **`<Routes>` / `<Route>`**: match a URL to a component.
- **Nested route**: the three dashboard pages are children of `<Route element={<Layout />}>`. They all get the same top bar and sidebar.
- **`<Navigate>`**: sends the user to another URL.

### 6.3 `api/client.js` — talks to the backend

| Name | Type | What it does |
|------|------|--------------|
| `api` | Axios instance | Base URL is `/api`. All calls use it. |
| Request interceptor | Function | Reads the token from `localStorage`. Adds the header `Authorization: Bearer <token>` to each request. |
| Response interceptor | Function | If the backend returns **401**, it deletes the token and goes to `/login`. It does not do this for the login call itself (a wrong password also returns 401). |
| `authApi.login(email, password)` | Function | `POST /api/auth/login` |
| `authApi.me()` | Function | `GET /api/auth/me` |
| `analyticsApi.kpis(params, signal)` | Function | `GET /api/analytics/kpis` |
| `analyticsApi.monthlyTrend(...)` | Function | `GET /api/analytics/monthly-trend` |
| `analyticsApi.deptActivity(...)` | Function | `GET /api/analytics/dept-activity` |
| `analyticsApi.patientFlow(...)` | Function | `GET /api/analytics/patient-flow` |
| `analyticsApi.bedAvailability(...)` | Function | `GET /api/analytics/bed-availability` |
| `analyticsApi.departments(signal)` | Function | `GET /api/analytics/departments` |
| `isCancelled(err)` | Function | Returns `true` if we cancelled the request on purpose. This is not a real error. |
| `describeError(err, fallback)` | Function | Makes a clear error message. Uses the backend message, or "Cannot reach the API" if the server does not answer, or the fallback text. |

Note: `params` become the query string (for example `?start_date=2025-01-01`). `signal` lets us cancel the request.

### 6.4 `contexts/AuthContext.jsx` — login state

| Name | Type | What it does |
|------|------|--------------|
| `AuthContext` | Context | A shared box of data. |
| `AuthProvider` | Component | Holds the `user` state. Gives `user`, `login`, `logout` to all child components. |
| `login(email, password)` | Function | Calls the API, saves the token and user in `localStorage`, updates the state. |
| `logout()` | Function | Deletes the token and user. Sets `user` to `null`. |
| `useAuth()` | Custom hook | Short way to read the context. Use `const { user } = useAuth()`. |
| `ROLES` | Object | The three roles: `Dean`, `Doctor`, `Nurse`. |
| `PATIENT_FLOW_ROLES` | Set | Roles that can see Patient Flow: Dean, Doctor. |
| `BED_AVAIL_ROLES` | Set | Roles that can see Bed Availability: Dean, Doctor, Nurse. |
| `FULL_ACCESS_ROLES` | Set | Roles with full access: Dean. |

Why `localStorage`? The login stays after a page refresh.

### 6.5 `components/layout/Layout.jsx`
- The frame around the dashboard pages: top bar, sidebar, and page area.
- If there is no `user`, it sends the visitor to `/login`. This is a **route guard**.
- Shows the user's initials, name, role and a logout button.
- `<Outlet />` is the place where the child page appears.
- Uses `useNavigate()` to go to `/login` after logout.

### 6.6 `components/layout/Sidebar.jsx`
- The left navigation menu.
- Uses `NavLink`. It adds the class `active` to the link of the current page.
- Shows each link only if the user's role is in the correct Set. A Nurse does not see "Patient Flow".

### 6.7 `components/ui/UI.jsx` — reusable parts

| Component | Props (inputs) | What it shows |
|-----------|----------------|---------------|
| `Spinner` | `text` | A loading circle with text |
| `ErrorBanner` | `message` | A red warning box |
| `KPICard` | `icon, label, value, sub, color, bgColor, delay` | One number card (for example "Total Beds") |
| `OccBar` | `pct, color` | A progress bar. Red above 80 %, amber above 60 %, otherwise normal. |
| `BreakdownBar` | `label, count, pct, color` | One row with a label, a bar, a count and a percent |

**Props** are the inputs of a component. They work like function arguments.

### 6.8 `pages/Login.jsx`
- A form with email and password.
- State: `email`, `password`, `error`, `loading`.
- `handleSubmit` stops the normal form submit (`e.preventDefault()`), calls `login()`, then goes to `/overview`.
- If the login fails, it shows the error. The `finally` block always sets `loading` to `false`.
- The inputs are **controlled inputs**: React state holds their value.

### 6.9 `pages/Overview.jsx`
- Shows 5 KPI cards, a monthly bar+line chart, and a department bar chart.
- Has filters: start date, end date, department.
- Loads the department list once (`useEffect` with `[]`).
- `fetchAll` sends 3 requests at the same time with `Promise.all`.
- Cancels an old request when a new one starts (`AbortController`).
- Shows `Spinner`, `ErrorBanner` or the data, depending on the state.

### 6.10 `pages/PatientFlow.jsx`
- Only for Dean and Doctor. Other roles see `AccessDenied`.
- Two components: `PatientFlow` (checks the role) and `PatientFlowContent` (loads and shows data).
- Shows 4 KPI cards, a monthly trend, department activity, a **pie chart** (visit type), and a status breakdown.
- Has date filters.

### 6.11 `pages/BedAvailability.jsx`
- For Dean, Doctor and Nurse.
- Shows 5 KPI cards, a status breakdown, an occupancy percentage, and one card for each ward.
- Has a ward-type dropdown. The filter runs in the browser, with no new request.
- `[...new Set(...)]` makes a list of unique ward types.

### 6.12 `pages/AccessDenied.jsx`
- A simple page with a message and a "Back to Overview" button.
- Other pages show it when the role is not allowed.

### 6.13 Config files

| File | Purpose |
|------|---------|
| `vite.config.js` | Enables the React plugin. Sets port 5173. **Proxy**: `/api` and `/health` go to `http://localhost:8000`. This avoids CORS problems in development. |
| `index.html` | The single HTML page. Loads `main.jsx`. |
| `package.json` | Packages and scripts (`dev`, `build`, `lint`, `preview`). |
| `.oxlintrc.json` | Lint rules. |
| `.gitignore` | Files that Git must ignore (for example `node_modules`). |

---

## 7. Data flow (one full example)

**Case: The Dean opens the Overview page.**

1. The user goes to `/overview`. The router shows `Layout`, then `Overview`.
2. `Layout` checks `user`. The user is logged in, so the page loads.
3. `Overview` runs `useEffect`. This calls `fetchAll()`.
4. `fetchAll` sets `loading = true`. The page shows the `Spinner`.
5. Axios sends 3 `GET` requests. The interceptor adds the `Bearer` token.
6. The backend checks the token and the role. It returns JSON.
7. `setKpis`, `setTrend` and `setActivity` save the data in state.
8. React draws the page again. The `Spinner` goes away. Cards and charts appear.

If the token is not valid, the backend returns **401**. The interceptor sends the user to `/login`.

---

## 8. Web basics

### HTTP and HTTPS
- **HTTP** (HyperText Transfer Protocol) is the set of rules for how a browser and a server talk.
- The browser sends a **request**. The server sends a **response**.
- **HTTPS** is HTTP with encryption (TLS). Other people cannot read the data. Use HTTPS in production.
- HTTP is **stateless**. The server does not remember earlier requests. That is why we send the token each time.

### Parts of a request

| Part | Example |
|------|---------|
| Method (verb) | `GET` |
| URL | `/api/analytics/kpis?start_date=2025-01-01` |
| Headers | `Authorization: Bearer eyJ...` |
| Body (not for GET) | `{ "email": "...", "password": "..." }` |

### Request verbs (methods)

| Verb | Meaning | Used here? |
|------|---------|-----------|
| `GET` | Read data | Yes — all dashboard data |
| `POST` | Create data or send a secret | Yes — login |
| `PUT` | Replace data | No |
| `PATCH` | Change part of the data | No |
| `DELETE` | Remove data | No |

### Common status codes

| Code | Name | Meaning |
|------|------|---------|
| 200 | OK | The request worked |
| 201 | Created | A new item was made |
| 400 | Bad Request | The request is wrong |
| 401 | Unauthorized | Not logged in, or the token is not valid |
| 403 | Forbidden | Logged in, but the role is not allowed |
| 404 | Not Found | The URL does not exist |
| 422 | Unprocessable Entity | The data has the wrong format (FastAPI uses this) |
| 500 | Server Error | The backend has a fault |

Groups: **2xx** = success, **4xx** = client error, **5xx** = server error.

### Error types in this project

| Error | Cause | What the app does |
|-------|-------|-------------------|
| Network error (no `response`) | Backend is off, or no internet | Shows "Cannot reach the CarePulse API..." |
| 401 on login | Wrong email or password | Login page shows the message |
| 401 on other calls | Token expired or not valid | Deletes the token, goes to `/login` |
| 403 | Role not allowed | Backend refuses the request |
| `ERR_CANCELED` | We cancelled the request | App ignores it (`isCancelled`) |
| Other 4xx / 5xx | Many causes | `ErrorBanner` shows the message |

### Other basic terms

| Term | Simple meaning |
|------|---------------|
| **API** | A set of URLs the frontend uses to get data |
| **REST** | A style of API. Each URL is a "thing" (resource). The verb is the action. |
| **JSON** | A text format for data: `{ "name": "Anna" }` |
| **JWT** (JSON Web Token) | A signed text string. It proves who the user is. The backend gives it after login. |
| **Bearer token** | The way to send the JWT in the `Authorization` header |
| **Query parameter** | Extra data in the URL after `?` |
| **CORS** | A browser rule that blocks calls to a different origin. The Vite proxy avoids it in development. |
| **Proxy** | A middle server. Vite forwards `/api` to the backend. |
| **localStorage** | Small storage in the browser. Data stays after a refresh. |
| **Authentication** | Check **who** you are (login) |
| **Authorization** | Check **what** you can do (roles) |
| **SPA** (Single Page Application) | One HTML page. JavaScript changes the content. |
| **KPI** | Key Performance Indicator. An important number (for example bed occupancy). |

---

## 9. React basics

**React** is a JavaScript library to build user interfaces. Facebook (Meta) made it.

| Term | Simple meaning |
|------|---------------|
| **Component** | A function that returns a piece of screen. Name starts with a capital letter. |
| **JSX** | HTML-like code inside JavaScript. Example: `<h1>Hello</h1>` |
| **Props** | Inputs to a component. Read-only. |
| **State** | Data that a component remembers. When it changes, React draws the component again. |
| **Hook** | A special function that starts with `use`. It adds features to a component. |
| **Virtual DOM** | A copy of the page in memory. React compares it with the old copy and updates only what changed. |
| **Re-render** | React runs the component function again after a state change. |
| **Declarative** | You say **what** the screen must look like. React decides **how** to do it. |
| **Key** | A unique ID for each item in a list. Helps React track items. |

**Main idea:**  `UI = function(state)`.
When the state changes, the screen changes.

---

## 10. React features used in this project

| Feature | Where | Why |
|---------|-------|-----|
| Function components | All files | Basic building blocks |
| JSX | All files | Write the screen as HTML-like code |
| Props | `KPICard`, `OccBar`, `Spinner`... | Send data into reusable parts |
| `children` prop | `AuthProvider` | Wrap other components |
| `useState` | All pages | Store data, filters, `loading`, `error` |
| `useEffect` | `Overview`, `PatientFlow`, `BedAvailability` | Load data when the page opens or a filter changes. The returned function does cleanup. |
| `useCallback` | Pages, `AuthContext` | Keeps the same function between renders. `useEffect` depends on it. |
| `useRef` | `abortRef` in pages | Keeps the current `AbortController` without a re-render |
| `createContext` + `useContext` | `AuthContext` | Share the user without passing props through every level |
| Custom hook | `useAuth` | Reuse logic |
| Context Provider | `AuthProvider` | Gives the data to all child components |
| Conditional rendering | `{loading && <Spinner />}`, `{error && ...}` | Show parts only when needed |
| List rendering with `.map()` + `key` | Wards, KPI rows, chart cells | Draw many items from an array |
| Controlled inputs | Login, date filters, dropdown | State holds the value of each input |
| Lazy state initialiser | `useState(() => ...)` in `AuthProvider` | Read `localStorage` only once |
| Fragment `<>...</>` | Pages | Group items without an extra `div` |
| Inline `style={{}}` | Many files | Small, single styles |
| React Router: `BrowserRouter`, `Routes`, `Route`, `Navigate`, `NavLink`, `Outlet`, `useNavigate` | `App`, `Layout`, `Sidebar`, `Login`, `AccessDenied` | Navigation |
| `StrictMode` | `main.jsx` | Finds problems in development |

### Browser (non-React) features also used
- `Promise.all` — runs 3 requests together.
- `async` / `await` — write async code in a simple way.
- `AbortController` — cancels a request. This prevents an old, slow answer from replacing a new one (a **race condition**).
- Optional chaining `?.` and nullish `??` — safe access when a value can be empty.
- Spread `...` and `Set` — copy arrays and remove duplicates.

---

## 11. Why React? Why not React?

### Why React (advantages)
- **Components**: build once, use many times (for example `KPICard` is used 14 times).
- **Fast updates**: the Virtual DOM changes only what is different.
- **Large community**: many libraries (Router, Recharts) and many answers online.
- **Easy to learn**: it is plain JavaScript with JSX.
- **Good for dashboards**: the data changes often, and the screen must follow.
- **Same skills for mobile**: React Native uses the same ideas.

### Why not React (disadvantages)
- **Only the view layer**: you must choose Router, state tools and so on.
- **Fast changes**: libraries and best practices change often.
- **Bad for SEO by default**: a SPA sends an empty HTML page. Search engines see less. (Not a problem for a login-only dashboard.)
- **First load is bigger**: the browser must download JavaScript first.
- **Learning curve**: hooks, `useEffect` dependencies and re-renders confuse beginners.
- **Too much for a simple, static site**: plain HTML is enough there.

### Other options
Angular (full framework), Vue (simple and gentle), Svelte (small and fast), Next.js (React with server rendering and SEO).

---

## 12. Possible Viva questions

1. **What is the entry point of the app?**  `index.html` loads `main.jsx`. `main.jsx` renders `<App />`.
2. **What is a component?**  A function that returns JSX. We use it to build the UI in small parts.
3. **What is the difference between props and state?**  Props come from the parent and are read-only. State belongs to the component and can change.
4. **What does `useEffect` do?**  It runs code after the render. We use it to load data from the API.
5. **Why do you use Context?**  To share the logged-in user with all components without passing props down every level.
6. **How does login work?**  `POST /auth/login` returns a JWT. We save it in `localStorage`. An Axios interceptor adds it to each request.
7. **How do you control who sees which page?**  Two checks. The `Sidebar` hides links. The pages show `AccessDenied` if the role is wrong. The backend also checks the role (the frontend check is only for the user's comfort, not for security).
8. **What happens on a 401 error?**  The interceptor deletes the token and goes to `/login`.
9. **Why `AbortController`?**  To cancel an old request when the user changes a filter. This stops old data from replacing new data.
10. **Why `Promise.all`?**  To send the 3 Overview requests at the same time. The page loads faster.
11. **Why a Vite proxy?**  The frontend (port 5173) and backend (port 8000) have different origins. The proxy avoids CORS errors in development.
12. **What is a KPI?**  A number that shows how well the hospital does (admissions, wait time, bed occupancy).
13. **What is JSX?**  A syntax that lets us write HTML-like code in JavaScript. A tool changes it to normal JavaScript.
14. **What is the Virtual DOM?**  A copy of the page in memory. React compares copies and updates only the changed parts of the real DOM.
15. **Is storing a JWT in `localStorage` safe?**  It is simple, but scripts on the page (XSS) can read it. A safer choice is an `HttpOnly` cookie.
