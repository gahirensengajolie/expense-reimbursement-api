# Hosting Passbook (Render example)

## 0. Before you start
- Push the project to GitHub (`.env` and `*.db` are git-ignored: keep it that way).
- Render's free web service sleeps after ~15 minutes idle (first visit then takes about a minute),
  and its free Postgres expires after 30 days with no backups. Fine for a demo; for the company use a
  paid always-on web service and a paid database (or any Postgres with backups). Check current prices.

## 1. Create a database
Create a Postgres database and copy its **connection string** (`postgres://...` or `postgresql://...`).

## 2. Create the web service
Render dashboard -> New -> Blueprint -> pick your GitHub repo (it reads `render.yaml`).
Fill in when asked:
- `DATABASE_URL`: the connection string from step 1
- `FIRST_ADMIN_EMAIL`: the first administrator's email
- `FIRST_ADMIN_PASSWORD`: a temporary password (8+ characters). They must change it at first sign-in.

`SECRET_KEY` is generated for you and `ALLOW_SELF_REGISTRATION` is already `false`
(nobody can create their own account; the admin adds people in the app).

Check `https://YOUR-APP.onrender.com/health` returns `{"status":"ok",...}`.

## 3. First sign-in
Open the site and sign in with `FIRST_ADMIN_EMAIL` and the temporary password. You are asked to
choose your own password. Then: People -> Add person, to create managers and employees
and assign each employee to a manager. See `ADMIN_GUIDE.md`.

After that you can delete `FIRST_ADMIN_PASSWORD` from the host settings (it is only used when
the system has no admin yet).

## Notes
- The app refuses to start with `ENVIRONMENT=production` and a weak `SECRET_KEY` (on purpose).
- Tables are created automatically on first start. If you change the database tables later,
  add a migration (Alembic) rather than editing a live database by hand.
- Back up the database regularly (your host's backup feature, or `pg_dump`).

## Database is required in production
With `ENVIRONMENT=production` the app **refuses to start on SQLite** (the server's disk is erased on every deploy).
Set `DATABASE_URL` to a Postgres connection string. Take regular backups of that database.

## Logs
Every request is logged as `METHOD /path -> status (ms)`; bodies, tokens and query strings are never logged.
Set `LOG_LEVEL=DEBUG` or `WARNING` to change the detail. View logs in the Render dashboard.
