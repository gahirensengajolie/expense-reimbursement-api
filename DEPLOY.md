# Hosting Passbook on Render (free demo setup)

## 0. Before you start
- Push the project to GitHub (`.env` and `*.db` are already git-ignored: keep it that way).
- Render free web service sleeps after ~15 min idle (first request then takes about a minute).
- Render's free Postgres expires after 30 days and has no backups. Use a free
  Postgres from Neon or Supabase instead if you want it to last (check their current limits).

## 1. Create a database
Create a Postgres database and copy its **connection string** (starts with `postgres://` or `postgresql://`).

## 2. Create the web service
Render dashboard -> New -> Blueprint -> pick your GitHub repo (it reads `render.yaml`).
When asked for `DATABASE_URL`, paste the connection string.
`SECRET_KEY` is generated for you. Render builds the Dockerfile and starts the app.
Check `https://YOUR-APP.onrender.com/health` returns `{"status":"ok",...}`.

## 3. Make yourself the first admin
Register your account on the live site, then from your own computer
(use the database's EXTERNAL connection string):

    cd ~/projects/expense-api
    DATABASE_URL='postgresql://...' PYTHONPATH=. python3 scripts/set_role.py you@example.com admin

Sign out and in. Use People & roles in the app to promote managers from then on.

## Notes
- Do not set ENVIRONMENT=production without a real SECRET_KEY: the app refuses to start (on purpose).
- Tables are created automatically on first start. Later column changes need a migration (Alembic).
