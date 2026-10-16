# Lume Finance

Lume Finance is a local personal finance web application built with Flask, SQLite, Jinja2, vanilla JavaScript and Chart.js. It includes a public landing page, registration and login, and a separate financial workspace for each user.

The interface uses a dark terracotta-and-black palette, warm amber highlights, cream text, layered gradients and restrained glass effects. Chart.js is bundled locally: no CDN, bank connection, paid service or internet connection is required at runtime.

## What has been built

| Area | Implemented functionality |
| --- | --- |
| Landing page | Application introduction, features, getting-started steps, registration/login links and three journal articles |
| Accounts | Name/email registration, password confirmation, login, POST-based logout and protected private pages |
| User isolation | Separate transactions, budgets, summaries, chart data and preferences for each account |
| Dashboard | Calculated income, expenses, balance, monthly budget remaining, charts and six recent transactions |
| Transactions | Add, edit, delete with confirmation, optional notes, description search, category/type/date filters, date/amount sorting and 15 records per page |
| Budgets | Monthly category limits, update/remove actions, actual spending, remaining amount, percentage used and status bars |
| Analytics | Daily income/expense trends, spending doughnut chart, six-month comparison and ranked category totals |
| Settings | GBP and USD display currencies and compact table spacing, saved per user |
| Reliability | Automatic database initialisation, versioned schema migration, validation, centralised error handling and health endpoint |
| Local demo | Explicitly labelled fictional data, repeatable seeding for a chosen registered account |
| Tests | Isolated pytest coverage of calculations, CRUD, accounts, access controls, APIs and migrations |

The journal includes three complete, publicly accessible articles:

- **A budget you can actually live with**
- **Small expenses. A clearer picture.**
- **Your 15-minute monthly money reset**

These are application content, not an external feed or a blog management system.

## Windows PowerShell setup

Use Python 3.10 or newer. From the project folder:

```powershell
Set-Location "D:\Lume Finance"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For a new installation, create the environment file. Keep an existing `.env` rather than overwriting it:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -c "import secrets; print(secrets.token_hex(32))"
notepad .env
```

Set `SECRET_KEY` to the generated value and save the file. Do not commit or share this secret.

Initialise the database and start the application:

```powershell
python -m flask --app app.py init-db
python app.py
```

Open **http://127.0.0.1:5000**. Stop the server with **Ctrl+C**. Database initialisation also happens automatically on startup; the explicit command preserves existing data.

For subsequent starts:

```powershell
Set-Location "D:\Lume Finance"
.\.venv\Scripts\Activate.ps1
python app.py
```

Restart Flask after changing Python or template files; debug mode and automatic reload are disabled by default. Refresh the browser after restarting. Use Ctrl+F5 if old CSS or JavaScript remains cached.

## First-use flow

1. Visit `/` to see the landing page and journal links.
2. Choose **Create account** and enter a name, email and matching passwords.
3. Use a password between 12 and 128 characters.
4. Registration redirects to the login page; sign in with your new credentials.
5. Login opens `/dashboard`. Add income and expenses, then set category budgets.
6. Use Settings to choose your display currency and table spacing.
7. Choose **Log out** to end the session and return to the landing page.

New accounts start with an empty workspace. Original single-user records and fictional sample data are not automatically given to a newly registered user. Each account sees only its own records, including when accessing record URLs directly.

## Dashboard calculations and chart behaviour

Money is stored as integer minor units: pence, cents or paise. Transaction input must be positive and have no more than two decimal places. Income/expense type determines how an entry affects the balance.

| Display | Calculation or scope |
| --- | --- |
| Total income | All recorded income for the signed-in user, across all dates |
| Total expenses | All recorded expenses for that user, across all dates |
| Current balance | Total income minus total expenses |
| Budget remaining | Selected month's category limits combined, minus **all** expenses in that month |
| Recent transactions | Latest six records across all dates, ordered by date and record ID |
| Daily trend | Income and expenses grouped by transaction date in the selected month |
| Spending mix and top categories | Expense totals by category in the selected month |
| Monthly cash flow | Six calendar months ending in the selected month; missing months show zero |

The month selector changes monthly budgets and chart periods. It does **not** restrict the all-time income, expense and balance cards. Transaction-page filters are independent of this selector.

### One date of data is valid

If every transaction falls on one date, the daily line chart has one point per series and no connecting line. A message explains that another transaction date is needed to show a trend. Hover over the points for exact values.

For example, with income of GBP 10,000 and expenses of GBP 85 on the same date:

- The income point appears at 10,000.
- The expense point appears close to zero because both series share the same scale.
- The balance is GBP 9,915.
- If the expenses are Transport 60 and Food 25, the doughnut and category breakdown reflect those proportions.

Adding entries on another date in the selected month creates a connecting line. The expense bar in a monthly chart can also look small beside a much larger income bar; tooltips show its exact amount.

### Budget states

Without any category budgets for the selected month, the dashboard and overall budget summary display **Not set**, rather than presenting negative spending as a configured budget balance.

Once a budget exists, overall remaining subtracts all monthly expenses, including expenses in categories without a limit. Each category card separately compares that category's actual spending with its own budget:

- Below 80%: on track, with a green/neutral progress bar.
- From 80% through 100%: near limit, with an amber bar.
- Above 100%: over budget, with a red bar and negative remaining amount.

Save the same category and month again to update its limit. Removing a budget does not delete transactions.

### Currency preferences

GBP and USD are available in Settings and change formatting and labels only. **No currency conversion takes place.** Keep an account's records in one consistent currency. Formatting includes currency symbols and two decimal places. INR is no longer offered or accepted as a new Settings selection. Existing accounts with saved INR preferences keep their original formatting until they explicitly select GBP or USD; amounts are never automatically relabelled. Compact spacing affects transaction tables only.

## Optional fictional sample data

First register an account in the browser. Then, from another PowerShell window with the virtual environment activated:

```powershell
python -m flask --app app.py seed-demo --email "you@example.com"
```

This creates six months of fictional transactions and current-month category budgets for that registered account. Transaction descriptions start with `[Demo]`, with a fictional-data note. Repeating the command does not duplicate the same seeded entries for that account and month; a different account receives its own samples. Samples can be edited or deleted normally.

Skip this command for an empty workspace. If importing the original single-user database, do that before seeding to avoid overlapping samples.

## Existing database migration and original records

SQLite schema versions are tracked with `PRAGMA user_version`. Schema version 2 adds users, transaction/budget ownership, per-user preferences and login-attempt storage while preserving the original records.

Existing single-user transactions and budgets remain unassigned and hidden from every account until the trusted local operator explicitly assigns them:

```powershell
python -m flask --app app.py assign-legacy-data --email "you@example.com"
```

Register the intended account first. This command assigns previously unowned records and imports the original currency/spacing preferences when records are assigned. If a category/month budget conflicts with one already in that account, the import rolls back without changing the records. Remove the conflicting new budget and retry.

This is a trusted local maintenance command, not a web feature. Records are never automatically assigned to the first person who registers.

During the implemented account upgrade, a pre-migration backup was created in `instance/` with a name matching `lume-before-accounts-*.sqlite3`. This was a one-time upgrade backup; startup does not create automatic backups. Back up the configured database with the application stopped before future upgrades, and preserve all account/password-hash data along with financial records. Future schema changes should use ordered, transactional migrations.

## Project structure

```text
Lume Finance/
    app.py                     # Local server entry point and .env loading
    database.py                # SQLite connections and schema migrations
    requirements.txt
    .env.example
    .gitignore
    README.md
    app/
        __init__.py            # Flask factory, security, error handlers, CLI
        auth.py                # Accounts, access guard, public pages, journal
        routes/
            __init__.py        # Dashboard, transactions, budgets, APIs, settings
        services/
            finance_service.py # Validation, money, summaries, charts, seeding
        templates/
            base.html          # Shared navigation, notifications, delete dialog
            _macros.html       # Reusable tables, summaries and chart layout
            landing.html
            auth.html          # Shared registration/login form layout
            article.html
            dashboard.html
            transactions.html
            transaction_form.html
            budgets.html
            analytics.html
            settings.html
            error.html
        static/
            css/style.css
            js/app.js
            js/dashboard.js
            vendor/            # Local Chart.js bundle and license
    instance/                  # Local SQLite database and upgrade backup
    tests/
        conftest.py
        test_application.py
        test_auth.py
```

The virtual environment, `.env`, SQLite databases, instance data and generated caches are excluded from Git.

## Routes and JSON APIs

| Route | Access | Purpose |
| --- | --- | --- |
| `GET /` | Public | Landing page |
| `GET/POST /register` | Public | Account creation |
| `GET/POST /login` | Public | Login |
| `POST /logout` | CSRF-protected | Clear the session |
| `GET /journal/<slug>` | Public | Read an article |
| `GET /dashboard` | Logged in | Financial overview |
| `GET/POST /transactions` | Logged in | List/filter or add a transaction |
| `GET /transactions/new` | Logged in | Add-transaction form |
| `GET/POST /transactions/<id>/edit` | Record owner | View edit form or save changes |
| `POST /transactions/<id>/delete` | Record owner | Delete a transaction |
| `GET/POST /budgets` | Logged in | View or save category limits |
| `POST /budgets/<id>/delete` | Record owner | Remove a limit |
| `GET /analytics` | Logged in | Financial charts and monthly totals |
| `GET/POST /settings` | Logged in | View/save preferences |
| `GET /api/summary?month=YYYY-MM` | Logged in | Summary values in integer minor units |
| `GET /api/charts?month=YYYY-MM` | Logged in | Category, daily and monthly chart datasets |
| `GET /health` | Public | Database connectivity and version check |

Private pages redirect unauthenticated visitors to `/login`; private APIs return HTTP 401 JSON. Missing records and records owned by another user return HTTP 404. Invalid form data returns HTTP 400, throttled login returns HTTP 429, and handled database failures return HTTP 503. State-changing forms require a valid CSRF token.

The chart API includes `unit: "minor"`, plus `categories`, `daily` and `monthly` datasets. Monthly endpoints accept a `YYYY-MM` month and default to the server's current local month. Health returns:

```json
{
  "status": "healthy",
  "application": "Lume Finance",
  "version": "1.0.0"
}
```

`APP_VERSION` controls the returned version.

## Configuration

The entry point loads `.env`; existing process environment variables take precedence.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Random value for each app instance if omitted | Signs sessions and CSRF tokens; configure a stable random secret |
| `PORT` | `5000` | Local listening port |
| `APP_VERSION` | `1.0.0` | Application version returned by health |
| `DATABASE_PATH` | `instance/lume.sqlite3` under Flask's instance directory | Persistent SQLite storage; relative overrides resolve from the working directory |

Without a stable secret, sessions and forms expire when the application restarts, and separate workers would not share a signing key. Debug mode is disabled. The server binds to `0.0.0.0`; use `127.0.0.1` in the browser for local access.

## Security implemented

- Werkzeug scrypt password hashing; plain-text passwords are not stored.
- Registration validation, case-normalised email addresses and duplicate-account checks.
- Generic failed-login messages and a dummy password-hash check for unknown accounts.
- Persistent email-based throttling after eight failed attempts within a 15-minute window.
- Session clearing on login/logout, 12-hour rolling sessions, HttpOnly and SameSite=Lax cookies.
- CSRF protection on state-changing forms, including registration, login and logout.
- Parameterised SQL and ownership checks for reads, edits, deletes and aggregations.
- Server validation of descriptions, amounts, types, category/type matches, dates and notes.
- Jinja escaping of user content and safe text insertion in JavaScript category displays.
- No-store caching for authenticated responses and authentication pages.
- Content-type, frame and referrer security headers; generic storage errors avoid exposing internal diagnostics.

This remains a local development application. See deployment limitations below before exposing it publicly.

## Testing and verification

Run the complete suite:

```powershell
python -m pytest -v
```

**Latest executed result: 63 tests passed.** Coverage includes:

- Main pages, health response and configurable version.
- Income/expense creation, invalid data, editing, deletion and missing records.
- Exact money formatting, dashboard calculations, filtering, sorting and pagination.
- Budget updates, removal, overspending and chart response formats.
- The reviewed GBP 10,000 income / GBP 85 expense screenshot scenario.
- Empty states, invalid API inputs, escaped content and handled database errors.
- Registration validation, password hashing, duplicate emails, login/logout and throttling.
- Authentication requirements, CSRF protection and isolation between two accounts.
- Repeatable per-user seeding and preservation/assignment of legacy records.

Tests create separate temporary SQLite databases and do not modify the local application database. They require no internet or AWS access.

A temporary real Flask server was also checked over HTTP for public pages, journal articles, registration, login, session cookies, authenticated pages/APIs and logout. Its test account existed only in a temporary database. The dashboard screenshots were reviewed for calculations and one-date chart behaviour. No automated browser rendering or interaction suite has been run.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| PowerShell blocks activation | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate; alternatively use `.\.venv\Scripts\python.exe` directly |
| Python or `py` is unavailable | Install Python 3.10+ with the Windows launcher, then reopen PowerShell |
| Missing Python modules | Activate `.venv` and run `python -m pip install -r requirements.txt` |
| Port 5000 is occupied | Set `$env:PORT = "5001"`, run `python app.py`, then open `http://127.0.0.1:5001` |
| Form expired or CSRF error | Refresh and retry; use the same hostname consistently and configure a stable secret |
| Login temporarily blocked | Wait for the 15-minute attempt window to expire before retrying |
| New account has no records | Add transactions, seed that account, or explicitly assign legacy records as appropriate |
| Daily chart has dots but no line | Only one transaction date exists in the selected month; hover for values or add another date |
| Small expenses look almost invisible | Income and expenses share a scale; hover for exact values or use the category breakdown |
| Budget remaining says Not set | Create a category budget for the selected month |
| Charts do not load | Refresh and inspect the browser console/network requests for the local Chart.js file and authenticated chart API |
| Database unavailable | Check the configured path, parent-folder write permission and processes holding long SQLite write locks |
| Changes do not appear | Stop/restart Flask and hard-refresh the browser |

## Remaining limitations and future deployment

- No email verification, password recovery, MFA, account deletion or account administration UI.
- No banking integration, exchange-rate conversion, recurring transactions or transaction import/export.
- Journal articles are maintained in source code; there is no CMS.
- SQLite remains the database. Native `python app.py` uses the Flask development server; Docker uses Gunicorn.
- Public deployment still needs HTTPS, Secure cookies, broader abuse controls, operational monitoring and scheduled backups. Docker now supplies a production WSGI server.
- Docker packaging is implemented below. A first-stage GitHub Actions CI workflow is prepared under `.github/workflows/ci.yml`; its first successful GitHub run is still pending. Amazon ECR and AWS EC2 deployment have **not** been implemented.

The application uses configurable ports/version/storage, binds to `0.0.0.0` and exposes `/health`. Docker packaging prepares it for future deployment; it does not complete the CI/CD pipeline.

## Docker Containerisation

### Architecture and files

The existing application runs unchanged in a Linux container using the official `python:3.13.16-slim-bookworm` base and Gunicorn 26.2.0. Gunicorn calls the actual application factory, `app:create_app()`, rather than assuming that the `app` package exports an application instance. Two synchronous workers serve requests. Preloading initialises/migrates SQLite once in the master before workers start, and the existing factory closes its initialisation connection before the fork.

The service runs as UID/GID **10001:10001**, listens on `0.0.0.0:5000` by default, and uses `/data/lume.sqlite3`. The recommended named volume persists `/data` on Docker's host storage independently of container replacements. No host database, development secret, virtual environment or test source is copied into the image. Runtime needs no external network; image builds do need access to Docker Hub and Python package downloads.

| File | Purpose |
| --- | --- |
| `Dockerfile` | Python runtime, dependencies, non-root user, runtime-only copies, SIGTERM and health probe |
| `.dockerignore` | Allowlisted build context plus explicit exclusions for secrets, databases, backups and caches |
| `gunicorn.conf.py` | Port, required external secret, workers, preload, stdout/stderr logs and graceful shutdown |
| `docker/healthcheck.py` | Python-standard-library probe of the existing `/health` endpoint |
| `scripts/verify_docker.py` | Optional isolated container verification; never uses the local database |
| `requirements.txt` | Adds pinned Gunicorn only on non-Windows systems; native Windows startup is unchanged |
| `.gitignore` | Adds `.env.*` and `backups/`, while retaining `.env.example` |
| `README.md` | Container setup, persistence, verification and recovery instructions |

Business logic, frontend, existing tests, database schema and health endpoint were not changed for Docker. Dependencies retain the project's existing compatible ranges, with Gunicorn pinned; builds are not fully locked across every transitive dependency. The Python patch tag is pinned, but an image digest/dependency lock can be added when preparing release promotion.

### Prerequisites and build

Install/start Docker Desktop using the **Linux containers** engine and WSL 2 backend. From PowerShell:

```powershell
Set-Location "D:\Lume Finance"
docker version
docker build --tag lume-finance:local .
docker volume create lume-data
```

`docker version` should show both Client and Server. Creating the same named volume again reuses it. An empty volume mounted at `/data` inherits the image directory's ownership, so the non-root application can initialise SQLite. Existing volumes must already permit UID 10001 to write their database and parent directory.

### External configuration and first start

Create a dedicated Docker environment file once. This is separate from your native `.env` and is ignored by Git and the build context:

```powershell
if (-not (Test-Path .env.docker)) {
    $lumeSecret = python -c "import secrets; print(secrets.token_hex(32))"
    @(
        "SECRET_KEY=$lumeSecret"
        "PORT=5000"
        "APP_VERSION=1.0.0"
        "DATABASE_PATH=/data/lume.sqlite3"
    ) | Set-Content -Encoding ascii .env.docker
    Remove-Variable lumeSecret
}
```

This generates a secret without printing its value or placing it literally in a Docker command. Keep `.env.docker` private and retain it across replacements. Changing `SECRET_KEY` invalidates existing sessions and CSRF tokens. The container refuses to start with an absent, short or example secret. Environment variables remain visible to trusted Docker administrators; do not share full `docker inspect` output containing environment values.

Start the application:

```powershell
docker run --detach --name lume-finance `
    --restart unless-stopped `
    --stop-timeout 40 `
    --publish 127.0.0.1:5000:5000 `
    --env-file .env.docker `
    --mount type=volume,source=lume-data,target=/data `
    lume-finance:local
```

Open **http://127.0.0.1:5000** and register/login normally. Stop any native Flask process using port 5000 first. Alternatively publish `127.0.0.1:5001:5000` and browse port 5001; the container's `PORT` can stay 5000.

The Docker defaults are `PORT=5000`, `APP_VERSION=1.0.0` and `DATABASE_PATH=/data/lume.sqlite3`. Override them with the environment file or `--env`. If changing the internal `PORT`, change the right-hand publish port too. Keep `DATABASE_PATH` beneath the mounted `/data`; a different unmounted path could create a new, disposable database. Native defaults remain unchanged.

Do not copy your native `.env` directly into Docker configuration without checking `DATABASE_PATH`: a Windows path or `instance/` override is inappropriate for container persistence. The original Windows database is not automatically imported. Accounts begin empty in a new volume; register new accounts, seed explicitly, or intentionally restore a backup.

### Docker Desktop startup and the SECRET_KEY error

Running the image directly from Docker Desktop's Images screen does not automatically load the project's `.env` or `.env.docker` file. Without an externally supplied valid secret, Gunicorn intentionally exits with:

```text
Failed to read config file: gunicorn.conf.py
RuntimeError: Supply a stable, random SECRET_KEY of at least 32 characters.
```

Despite the first line, this error means the configuration file was found and rejected a missing, short or example secret. It does not mean that Gunicorn's configuration file is absent. No image rebuild is required.

To resolve it:

1. Create `.env.docker` using the first-start commands above. If the file already exists with an invalid secret, generate a replacement locally and set `SECRET_KEY` in that file; retain `PORT=5000`, `APP_VERSION=1.0.0` and `DATABASE_PATH=/data/lume.sqlite3`.
2. Create the container with the documented `docker run` command, including **`--env-file .env.docker`**, the localhost port mapping and the `lume-data` volume mount.
3. Open `http://127.0.0.1:5000` and check `/health` or the Docker health status.

A stopped container created without the required environment retains that original configuration. Clicking Start on it does not load a newly created environment file. Create a correctly configured container instead; if reusing the same container name, stop/remove the old container first while preserving its named volume. Once the configured `lume-finance` container exists, Docker Desktop's Start/Stop controls can manage it normally.

For a working installation, keep `.env.docker` and its secret unchanged. Editing an environment file does not update an existing container: deliberate environment changes require container recreation with the same data volume. Secret rotation invalidates sessions and CSRF tokens.

### Status, health, logs and commands

```powershell
docker ps --filter name=lume-finance
docker inspect --format '{{.State.Health.Status}}' lume-finance
docker inspect --format '{{json .State.Health}}' lume-finance
Invoke-RestMethod http://127.0.0.1:5000/health
docker logs --tail 100 lume-finance
docker logs --follow lume-finance
```

Ctrl+C stops log following without stopping the application. The health probe runs every 30 seconds, has a 5-second Docker timeout, allows a 30-second start period and marks unhealthy after three consecutive failures. It uses Python, not curl/wget. It checks both HTTP 200 and `status: healthy`; it prints neither response diagnostics nor secrets. Existing database failures return HTTP 503. An unhealthy status alone does not automatically restart a container; `unless-stopped` restarts exited processes.

Check the non-root identity and configured database path without printing secrets:

```powershell
docker exec lume-finance id
docker exec lume-finance python -c "import os; print(os.environ['DATABASE_PATH'])"
```

Expected UID/GID: 10001. No tests or demo seeding run during production startup. Existing automatic schema initialisation/migration remains active. To seed a registered account deliberately:

```powershell
docker exec lume-finance python -m flask --app app.py seed-demo --email "you@example.com"
```

### Stop, restart and replace without losing data

```powershell
docker stop --time 40 lume-finance
docker start lume-finance
```

Gunicorn receives SIGTERM directly as PID 1 and has 30 seconds to finish requests. Use a Docker stop allowance of 40 seconds so it can exit gracefully.

To replace the container after rebuilding:

```powershell
docker stop --time 40 lume-finance
docker rm lume-finance
docker build --tag lume-finance:local .
```

Then repeat the first-start `docker run` command with the **same `lume-data` volume and `.env.docker` file**. `docker rm` removes the container, not the named volume. Do not remove/prune the data volume unless intentionally deleting its financial data. Back up before an application upgrade that may migrate the schema.

### Database backup

Stop the only application container writing this volume before copying database files. Archive the **entire `/data` directory**, including any SQLite sidecar files, rather than copying a live database file. The helper uses Python already in the image and does not initialise the application.

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null
$lumeBackupDir = (Resolve-Path .\backups).Path
$lumeBackupFile = "lume-data-$(Get-Date -Format 'yyyyMMdd-HHmmss').tar.gz"
docker stop --time 40 lume-finance

docker run --rm --network none `
    --mount type=volume,source=lume-data,target=/data,readonly `
    --mount "type=bind,source=$lumeBackupDir,target=/backup" `
    --env "BACKUP_FILE=$lumeBackupFile" `
    --entrypoint python lume-finance:local `
    -c "import os,tarfile; archive=tarfile.open('/backup/'+os.environ['BACKUP_FILE'],'x:gz'); archive.add('/data',arcname='.'); archive.close()"

if ($LASTEXITCODE -ne 0) { throw 'Backup failed. Check storage/permissions before continuing.' }
docker start lume-finance
Get-Item (Join-Path $lumeBackupDir $lumeBackupFile)
```

The backup contains accounts, password hashes, transactions, budgets, settings and migration metadata. Protect it as personal financial data. The environment-file secret is not included in `/data`; retain it securely separately. The application does not schedule backups automatically.

### Restore safely to a new volume

Restore a trusted archive into a **new empty** volume so the original remains available for rollback. Stop the current application before switching storage. Set the example backup filename to your actual archive name:

```powershell
$lumeBackupDir = (Resolve-Path .\backups).Path
$lumeBackupFile = 'lume-data-YYYYMMDD-HHMMSS.tar.gz'
if (-not (Test-Path (Join-Path $lumeBackupDir $lumeBackupFile))) { throw 'Backup not found.' }
docker stop --time 40 lume-finance
docker volume create lume-data-restored

docker run --rm --network none `
    --mount type=volume,source=lume-data-restored,target=/data `
    --mount "type=bind,source=$lumeBackupDir,target=/backup,readonly" `
    --env "BACKUP_FILE=$lumeBackupFile" `
    --entrypoint python lume-finance:local `
    -c "import os,tarfile; from pathlib import Path; assert not any(Path('/data').iterdir()), 'Restore volume must be empty'; archive=tarfile.open('/backup/'+os.environ['BACKUP_FILE'],'r:gz'); archive.extractall('/data',filter='data'); archive.close()"

if ($LASTEXITCODE -ne 0) { throw 'Restore failed. Do not switch the application volume.' }
docker rm lume-finance
```

Repeat the `docker run` command using `source=lume-data-restored` instead of `source=lume-data`, with the same environment file. Verify `/health`, login and transaction totals before adopting the restored copy. Keep the original volume until recovery is confirmed. For later backups/replacements, use the restored volume name consistently. Never start two application containers against the same SQLite volume during migrations.

### Verification

After building the image, run the optional host-side procedure:

```powershell
python scripts/verify_docker.py
python -m pytest -v
```

The Docker procedure creates a uniquely named disposable volume and container, generates a stable test secret for that run, registers a fictional account, adds an income transaction, checks CSRF and authenticated pages/APIs, checks the non-root UID and local assets, restarts the container, replaces it using the same volume, and verifies that the account/transaction persist. It checks health and logs, confirms a graceful shutdown, archives/restores test data into a fresh volume and removes only its own test resources. It runs with `--network none` and no published ports, demonstrating that the application can work without external networking. Your Windows database and normal `lume-data` volume are not used.

The following checks were actually executed for this implementation:

- Docker image build succeeded on Docker Desktop's Linux engine.
- All 63 existing pytest tests passed unchanged in the native development environment.
- The disposable verification procedure passed registration, CSRF, login/logout, transaction creation, restart/replacement persistence and backup/restore.
- Docker health reached healthy, `/health` returned HTTP 200, and the runtime UID was 10001.
- The application and local chart assets worked with `--network none`.
- Test logs contained neither the test secret nor test password; the image excluded host secrets and local SQLite files.
- Graceful SIGTERM shutdown exited with code 0; startup without an external secret was rejected.
- A separate temporary database failure returned generic HTTP 503 without internal database diagnostics.
- Windows PowerShell localhost port publishing, custom `PORT=5050`, configurable `APP_VERSION` and homepage HTTP 200 were verified using another disposable volume.

No verification migrations ran against the real Windows application database. Test containers and volumes were removed after verification; the built `lume-finance:local` image remains available. The automated verification did not leave a normal application container running.

### Successful local Docker Desktop run

On **15 October 2026**, the user confirmed that the normal application container was running correctly after supplying its Docker environment configuration. The supplied Docker Desktop screenshots show:

- The `lume-finance:local` image and a running container named `lume-finance`.
- Port mapping `5000:5000`.
- Requests for login, the dashboard, static assets and the chart API in the application logs.
- Repeated `/health` requests from the container health probe.

This records the user's successful local run separately from the isolated automated checks above. The screenshots alone do not verify the mount source or show every health response status; use the inspection and health commands in this README to check those details when needed. The initial missing-secret startup error was resolved through external configuration, without rebuilding the image. The first-stage GitHub Actions CI configuration is documented below; registry publishing and AWS deployment remain future work.

For everyday operation, reuse the configured container:

```powershell
docker start lume-finance
docker logs --tail 100 lume-finance
docker inspect --format '{{.State.Health.Status}}' lume-finance
Invoke-RestMethod http://127.0.0.1:5000/health
```

Open **http://127.0.0.1:5000**. If it is already running, there is no need to create another container. Stop it when required with `docker stop --time 40 lume-finance`; retain the named volume and `.env.docker` for the next start.

### Windows and storage troubleshooting

| Problem | Resolution |
| --- | --- |
| Docker reports a missing `dockerDesktopLinuxEngine` pipe | Start Docker Desktop, enable the Linux/WSL 2 engine and wait for `docker version` to show Server information |
| Docker API access denied | Ensure your Windows account can access Docker Desktop; restart the terminal/session after Docker access changes |
| Windows-container/image platform mismatch | Switch Docker Desktop to Linux containers |
| Build cannot fetch base image/packages | Check Docker Desktop network/proxy access; downloads are required at build time only |
| Port already allocated | Stop the native Flask server or map host port 5001 to container port 5000 |
| Container exits immediately | Inspect logs; supply a stable generated secret, valid port and writable database directory |
| `Supply a stable, random SECRET_KEY of at least 32 characters` | Supply a valid secret through `--env-file .env.docker` when creating the container; starting the previously misconfigured container does not apply the new file |
| `Permission denied` / SQLite cannot open database | Confirm `/data` is mounted and UID 10001 can write its parent directory; prefer a fresh named volume over a Windows bind mount |
| Existing named volume is owned by root | Stop its writer, back up first, then have the operator correct ownership for UID/GID 10001; do not solve this by running the main service as root or using chmod 777 |
| Backup bind mount cannot be written | Check Docker Desktop host-folder sharing/access and Windows folder permissions; use a local writable folder outside protected locations |
| Empty workspace after replacement | Check volume name and `DATABASE_PATH`; the original data may still be in the old volume or native database |
| CSRF/session fails across requests/restarts | Reuse the same secret across workers and replacements; keep one consistent browser hostname |
| Health remains starting | Allow the startup window, inspect logs and verify `/health`; failed migrations or inaccessible storage must be resolved first |

The Docker volume lives in Docker Desktop-managed Linux storage, not automatically in the Windows `instance/` folder. A named volume survives container removal but not intentional volume deletion or Docker Desktop data reset.

### Deployment boundary and references

This packaging can later be tagged/pushed to ECR and run on EC2, but no registry push, AWS resource or reverse proxy has been created. The first-stage GitHub Actions workflow below only tests and builds the image. Keep one application container per SQLite volume, mount persistent local storage, supply secrets externally, and configure HTTPS/proxy/session security before public exposure. Multi-host SQLite sharing and automatic scaling are outside this implementation.

References: [Official Python image](https://hub.docker.com/_/python), [Docker volume persistence](https://docs.docker.com/engine/storage/volumes/), [Gunicorn settings](https://gunicorn.org/reference/settings/), and [Gunicorn termination signals](https://gunicorn.org/signals/).

## GitHub Actions CI: stage 1

Repository: [shalihjkr/lume-finance](https://github.com/shalihjkr/lume-finance).

The workflow is defined in `.github/workflows/ci.yml`. It triggers on pushes to `main` and pull requests targeting `main`, using a GitHub-hosted `ubuntu-24.04` runner.

One job, **Tests and Docker build**, performs these steps in order:

1. Check out the triggering commit with persisted Git credentials disabled.
2. Set up Python 3.13, matching the Docker image's Python minor version, and cache pip downloads using `requirements.txt` as the cache key input.
3. Upgrade pip and install `requirements.txt`, which already contains pytest and all application/testing dependencies. The existing non-Windows Gunicorn dependency is also installed on Ubuntu.
4. Run the existing command `python -m pytest -v`.
5. Only after all previous steps pass, configure Docker Buildx.
6. Build the existing Dockerfile with `docker buildx build --file Dockerfile --tag lume-finance:ci --load .`.

Normal GitHub Actions success gating stops subsequent steps on failure. There is no `continue-on-error`, `always()` build override, registry login, image push, container deployment or AWS step. The image is loaded into the temporary runner's Docker engine and disappears when that runner is discarded. This stage does not run the optional Docker HTTP/persistence verification script automatically.

The workflow has a 20-minute timeout and read-only `contents` permissions. Third-party actions are pinned to verified full commit SHAs, with version comments for maintenance. Update those pins deliberately when upgrading actions.

### Test storage and secrets

`tests/conftest.py` remains unchanged: each test receives a separate pytest `tmp_path` SQLite database with a fixture-owned test account. Migration and seeding tests also use temporary storage. The pytest step sets a fallback `DATABASE_PATH` under the runner's temporary directory; explicit test configuration takes precedence. The workflow does not import the native application's entry point to initialise your real database, run demo seeding against your workspace or mount a production volume.

No GitHub repository secrets, production `SECRET_KEY`, Docker credentials or AWS credentials are required for this stage. Tests supply test-only secrets through their fixtures. Docker only builds the image; it does not start Gunicorn, so the container startup requirement for an external secret does not apply to the build.

The existing `.dockerignore` still controls the local-path build context, excluding environment files, personal databases, backups and other local artifacts. Existing tests and Docker configuration are unchanged. One portability fix in `app/services/finance_service.py` replaces the month validator's OS-dependent `strftime` comparison with `date.isoformat()[:7]`. The original early-year API test reproduced a failure on Linux before the fix; Windows and Linux now apply the same ISO month validation. No financial calculation or database schema was changed.

### Repository data review

On 16 October 2026, the public repository's `main` branch matched local commit `ef3d45813bccf1b103591253e631b96b4aacec44`. At review time, the public repository had one branch, one commit and no tags.

The tracked files and reachable Git history were reviewed for sensitive filenames, SQLite file signatures, private-key/provider-token patterns, and matches for the local deployment secrets without printing secret values. No findings were detected. `.env`, `.env.docker`, the local SQLite database and its backup are excluded; `.env.example` remains tracked as a placeholder-only setup example. Fictional demo records and test-only credentials in tests are intentional.

This is a scoped review, not a guarantee that every possible secret format can be detected. `.gitignore` prevents new untracked files from being added normally; it does not remove files already committed. If a real credential is ever published, revoke/rotate it and address repository history as well as the current file.

### Commit, push and check the first run

Review and publish only the intended workflow and documentation changes from the existing `main` branch:

```powershell
Set-Location "D:\Lume Finance"
git branch --show-current
git status --short
git add .github/workflows/ci.yml app/services/finance_service.py README.md
git diff --cached --check
git diff --cached
git commit -m "Add CI tests and Docker build workflow"
git push origin main
```

If GitHub requires pull requests, commit on a feature branch and open a pull request targeting `main`; the pull-request trigger runs the same checks. No force push is needed.

After pushing, open [repository Actions](https://github.com/shalihjkr/lume-finance/actions), choose **Lume Finance CI**, and open the run for the pushed commit. Confirm that **Run pytest** passes before **Set up Docker Buildx** and **Build image without publishing** run. A green overall result for that commit is the evidence that this workflow succeeded on GitHub. For a failure, inspect the failing step and fix its error before treating the stage as working. If no run appears, check the branch, workflow path and repository Actions settings.

To require this result before merging, the repository owner can later add **Tests and Docker build** as a required check in the `main` branch rules. This workflow does not change repository rules automatically.

### Validation status

- Existing test suite rerun on native Windows and in the Linux Python 3.13.16 container: **63 passed on each**, without modifying tests or the real application database.
- Workflow validated with checksum-verified **actionlint v1.7.12**: no errors.
- The exact workflow Buildx command completed locally with tag `lume-finance:ci`, including the Linux date fix; no registry push was performed.
- The public repository had **zero GitHub Actions runs** when inspected before publishing this workflow.
- **GitHub execution is pending**: the workflow is prepared locally and has not been committed or pushed by the implementation agent. A local lint/test/build result is not a successful hosted Actions run.

References: [GitHub Python CI](https://docs.github.com/en/actions/tutorials/build-and-test-code/python), [actions/checkout](https://github.com/actions/checkout), [actions/setup-python](https://github.com/actions/setup-python), and [Docker Buildx action](https://github.com/docker/setup-buildx-action).
