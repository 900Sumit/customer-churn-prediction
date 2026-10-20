# Customer Churn Prediction

ChurnLab is a React/Vite frontend for the existing FastAPI customer churn prediction service. The original `backend/` ML implementation and saved pipelines are preserved.

## Verified backend contract

The inspected backend provides:

- `GET /` and `GET /health`
- `POST /predict` with the 19 fields used by the single-customer form
- `POST /predict-csv-json-to-table` for JSON batch results (this is the actual route in the current source)
- `POST /predict-csv/download` for a CSV download
- `GET /history` and `GET /history/export` for authenticated, user-scoped prediction history
- `GET /analytics` for authenticated persistent analytics derived from prediction history
- `GET /ready` for safe database/authentication readiness status

The backend now includes a minimal CORS configuration for the local Vite origins (`localhost:5173` and `127.0.0.1:5173`). Set `FRONTEND_ORIGINS` to a comma-separated list for deployment.

The backend validates the permitted categorical values, non-negative numeric fields, and required CSV columns. It returns Logistic Regression, CatBoost, ensemble probability, ensemble prediction, risk level, and data-quality warning.

## Windows PowerShell setup

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

In a second PowerShell window:

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open the Vite URL shown in the terminal. Set `VITE_API_BASE_URL` if the API runs elsewhere.

## Clerk and Neon status

The frontend includes Clerk configuration scaffolding. Put a real publishable key in `frontend/.env`; Clerk will be enabled on the next Vite start. No Clerk secret or Neon connection string is exposed to the browser.

The Neon integration is implemented in `backend/database.py`. It loads `DATABASE_URL` from `backend/.env`, requires an SSL PostgreSQL connection, creates a `prediction_history` table on startup when configured, persists authenticated successful single/CSV predictions, and exposes protected user-scoped history and analytics routes. Clerk JWT verification requires the configured JWKS URL and issuer. Standard Clerk session tokens are checked using their authorized-party (`azp`) claim against `FRONTEND_ORIGINS`; `CLERK_AUDIENCE` is additionally enforced when a custom Clerk JWT template with an `aud` claim is used.

Configuration for the implemented integration:

1. Copy `backend/.env.example` to `backend/.env` or set the variables in the shell.
2. Set `DATABASE_URL` to the Neon connection string with `sslmode=require`.
3. In the Clerk Dashboard, inspect the session/JWT configuration used by this frontend. Set `CLERK_JWKS_URL` to that Clerk instance's JWKS endpoint and `CLERK_ISSUER` to the exact token `iss` value. For the standard session token, leave `CLERK_AUDIENCE` unset and keep `FRONTEND_ORIGINS` accurate; if a custom JWT template explicitly emits `aud`, set `CLERK_AUDIENCE` to that exact value. Do not use the publishable key, a secret key, or a guessed URL as the audience.
4. Configure a real `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env` so the browser sends a verified session token.
5. Start FastAPI. The schema is created automatically; successful authenticated predictions populate `/history` and `/analytics`. Use `GET /ready`, `python backend/check_database.py`, and `python backend/check_auth_config.py` to verify readiness without printing credentials.

After changing `backend/.env`, restart FastAPI so dotenv values are loaded. A healthy liveness response does not imply persistence/authentication readiness: `/ready` must return `status: "ready"` before relying on protected history and analytics. The browser should use the existing local URL (`http://localhost:5173`) and the frontend should continue using `VITE_CLERK_PUBLISHABLE_KEY` only.

If Neon or Clerk is not configured, existing public prediction endpoints continue to work, while protected history/analytics return a clear `503` configuration response. A successful prediction includes a safe `persistence_status` field so a database write failure is not hidden.

## Tested locally

- Backend source and schemas inspected; existing ML logic was not modified.
- Frontend source is structured into routes, pages, services, context, reusable components, and styles.
- Single prediction and batch requests target the actual backend routes; CSV uploads are limited to 10 MB and 10,000 rows.
- Run `npm run build` in `frontend` to verify the production bundle after installing dependencies.

## Implemented frontend features

Landing page, responsive dashboard shell, single prediction form with inline validation, CSV upload/drop zone, API-backed result table and download, model information based on verified source, persistent user-scoped history/analytics with filters and export, light/dark/system theme, API health status, Sonner notifications, responsive navigation, settings, and 404 handling.
