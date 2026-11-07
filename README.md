# Ridehail Daily Close

Every morning, finance closes the books for the previous day. The ride platform exports trips as CSV files, one file per day. You build the pipeline that loads those files into PostgreSQL and produces three reports per business day:

- revenue per city,
- payout per driver,
- a driver leaderboard per city.

It is two containers: `db` (PostgreSQL 16) and `pipeline` (your Python code).

- Python reads, validates and loads the files.
- SQL does every transformation and produces every number in the reports.
- Docker makes it run the same way on every machine.
- Git records how you built it.

## Step 1

**1. Make it your repository.** Unzip the starter, then:

```bash
cd ridehail-close
git init -b main
git add .
git commit -m "Initial commit"
```

Create an empty repository on GitHub called `ridehail-close`, with no README and no .gitignore, since you already have both. Then:

```bash
git remote add origin git@github.com:<your-user>/ridehail-close.git
git push -u origin main
```

**2. Configure.**

```bash
cp .env.example .env                  # PowerShell: Copy-Item .env.example .env
```

`.env` holds the database credentials. Git ignores it and you must never commit it. Committing it and deleting it later does not help, because Git history is permanent.

**3. Run.**

```bash
docker compose up --build --exit-code-from pipeline
```

Lines starting with `db-1` are PostgreSQL starting up; ignore them unless something fails. You should see:

```
pipeline-1  | connected to ridehail@db (PostgreSQL 16.x)
pipeline-1  | schema    1 file applied
pipeline-1  | TODO      reference data, trip files, reports
pipeline-1 exited with code 0
```

When the pipeline exits, Compose stops the database too. The data stays in the `pgdata` volume.

## How it runs

```
 your machine                              containers
 ------------                              ----------
 ./data/       --- mounted read-only --->  /data      \
 ./reports/    <-- mounted -------------   /reports    |  pipeline
 ./ridehail/   --- copied into the image   /app        |  python -m ridehail close
 ./sql/            at build time -------->             /    |
                                                            | DATABASE_URL -> db:5432
 localhost:5433 ------------------------------------>  db  (PostgreSQL 16, volume: pgdata)
```

The pipeline is a batch job, not a service. It starts, does the whole close, and exits.

- Code and SQL are copied into the image when it is built. After changing either, the image must be rebuilt. `--build` does that.
- Data is mounted, not copied. To process new files, put them in `data/incoming/` and run the same command again.
- The database lives in the named volume `pgdata`. It survives `up`/`down` and is deleted only by `docker compose down -v`.
- Hosts differ inside and outside. Inside the containers, the database is host `db`, port `5432`. From your machine, it is `localhost:5433`.

## Commands

| What | How |
|---|---|
| Run the pipeline | `docker compose up --build --exit-code-from pipeline` |
| Run one command | `docker compose run --rm --build pipeline load /data/incoming/trips_2026-10-19.csv` (or `report`) |
| Open a SQL prompt | `docker compose up -d db`, then `docker compose exec db psql -U ridehail -d ridehail` |
| Use a GUI client | `docker compose up -d db`, then connect DBeaver/DataGrip to `localhost:5433`, user/password/database from `.env` |
| Stop the database | `docker compose stop` |
| Start from an empty database | `docker compose down -v` |

Paths given to `load` are container paths (`/data/...`), not paths on your machine.

## Repository layout

```
ridehail-close/
├── compose.yaml
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
├── requirements.txt
├── README.md
├── ridehail/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              TODO
│   ├── db.py               the database adapter
│   ├── validate.py         TODO
│   ├── load.py             TODO
│   └── report.py           TODO
├── sql/
│   ├── 01_schemas.sql
│   ├── 02_raw.sql          TODO
│   ├── 03_core.sql         TODO
│   └── 04_marts.sql        TODO
├── data/
│   ├── reference/
│   └── incoming/
└── reports/                output, ignored by Git
```

Don't rename the service names, the variables in `.env.example`, the CLI commands, and the database objects listed below.

You can add files, functions, tables and views.

## The database adapter: `ridehail/db.py`

All database access goes through it. You pass in SQL and parameters; you get back plain Python values. Connections, cursors and transactions stay inside `db.py`, and nothing else in the project imports the database driver. You should not need to change it.

```python
from ridehail import db

db.apply_schema()                         # runs sql/*.sql in name order, all-or-nothing

n = db.execute("DELETE FROM raw.x WHERE a = %s", (a,))              # one statement, committed at once

rows = db.fetch_all("SELECT a, b FROM raw.x WHERE b > %s", (10,))   # list of dicts
row = db.fetch_one("SELECT a FROM raw.x WHERE a = %s", (a,))         # dict or None

counts = db.run_in_transaction([          # everything gets put in the database or nothing does
    db.many("INSERT INTO raw.x (a, b) VALUES (%s, %s)", list_of_tuples),
    db.once("INSERT INTO raw.y (name) VALUES (%s)", (name,)),
])
```

- Values always go in as parameters. Write `%s` in the SQL and pass a tuple, or write `%(name)s` and pass a dict. Never build SQL out of data with f-strings or `+`.
- `execute` commits immediately. Anything that must be all-or-nothing goes into one `run_in_transaction` call:
  - `db.many(sql, rows)` runs the statement once per row; an empty `rows` runs it zero times.
  - `db.once(sql, params)` runs it once.
- Rows come back as dicts keyed by column name. NUMERIC comes back as `Decimal`, `timestamptz` as a timezone-aware `datetime` in UTC, and `date` as `date`.
- Failures raise `db.QueryError` (a statement failed), `db.SchemaError` (a file in `sql/` failed), `db.ConnectionFailed` or `db.ConfigError`. All four are `db.DatabaseError`; `cli.py` prints the message and exits with 1.
- `apply_schema` runs on every start. Everything in `sql/` must be safe to run again on a database that already has it, eg. `CREATE TABLE IF NOT EXISTS`.

## Input data

All files are UTF-8 CSV with a header row.

`data/reference/cities.csv`: `city,voivodeship`

`data/reference/drivers.csv`: `driver_id,name,home_city,commission_rate,joined_at`
- `commission_rate` is a fraction, e.g. `0.20`.
- `joined_at` is a date, `YYYY-MM-DD`.

`data/incoming/trips_YYYY-MM-DD.csv`: `trip_id,driver_id,city,requested_at,completed_at,updated_at,distance_km,fare_pln,status`
- Timestamps are ISO-8601 in UTC, e.g. `2026-10-19T21:47:05Z`.
- `distance_km` and `fare_pln` are decimals with a dot, e.g. `12.40`.
- `status` is `completed`, `cancelled` or `refunded`.
- Cancelled trips: `completed_at`, `distance_km` and `fare_pln` are empty.

## Rules

### Loading

1. Load order. `close` loads `cities.csv` and `drivers.csv`, then every `data/incoming/trips_*.csv` in file-name order. Loading the reference files again must not create duplicates.
2. Skip loaded files. A trip file whose content (SHA-256) is already recorded in `raw.loaded_files` is skipped.
3. One transaction per file. Each trip file loads in a single transaction. Either all of its rows land (in `raw.trips` or `raw.rejected`) and the file is recorded in `raw.loaded_files`, or nothing from it does.
4. Reject rules. A row is rejected if and only if one of these holds:
   - A required field is empty. `trip_id, driver_id, city, requested_at, updated_at, status` are always required. `completed_at, distance_km, fare_pln` are required unless the status is `cancelled`.
   - A timestamp can't be parsed.
   - `distance_km` or `fare_pln` is not a valid decimal, or is negative.
   - `status` is not one of the three allowed values.
   - `city` is not in `cities.csv`.

   Rejected rows go to `raw.rejected` with a human-readable reason. They never stop the load.
5. Reconciliation line. After each file, print exactly one line:
   ```
   trips_2026-10-19.csv  lines=<N>  loaded=<N>  rejected=<N>
   trips_2026-10-19.csv  skipped (already loaded)
   ```
   `lines` counts data lines, not the header. `lines = loaded + rejected`, always.
6. Running `close` again with no new files changes nothing, in the database or in the reports.

### Current state of a trip

`trip_id` identifies a trip. If the same `trip_id` is delivered more than once, the row with the latest `updated_at` is its current state. `core.trips` holds exactly one row per `trip_id`: its current state.

### Report rules

- Business date: the calendar date in Europe/Warsaw of the trip's `completed_at`.
- Which trips count: only trips whose current status is `completed`, in every report.
- Revenue: `revenue_pln` and `gross_pln` are the sum of `fare_pln`.
- Per-trip payout: `round(fare_pln * (1 - commission_rate), 2)`, using PostgreSQL `round()` on numeric. `commission_rate` comes from `drivers.csv`. A driver who is not in `drivers.csv` has a `commission_rate` of `0.25`.
- Driver payout: `payout_pln` is the sum of per-trip payouts.
- Rank: `rank_in_city` gives rank 1 to the highest `payout_pln` within a `business_date` and `city`. Equal payouts share a rank, and the next rank is skipped (1, 2, 2, 4).

### Required database objects

You may add columns, tables and views. These must exist, with these names:

| Object | Required columns |
|---|---|
| `raw.loaded_files` | `file_name`, `sha256`, `loaded_at` |
| `raw.trips` | `source_file`, `line_no`, plus the nine trip columns, typed |
| `raw.rejected` | `source_file`, `line_no`, `reason`, `raw_row` |
| `core.cities` | `city`, `voivodeship` |
| `core.drivers` | `driver_id`, `name`, `home_city`, `commission_rate`, `joined_at` |
| `core.trips` | the nine trip columns, typed; one row per `trip_id` |
| `mart.daily_city_revenue` (view) | `business_date`, `city`, `completed_trips`, `revenue_pln` |
| `mart.driver_payouts` (view) | `business_date`, `driver_id`, `completed_trips`, `gross_pln`, `payout_pln` |
| `mart.driver_leaderboard` (view) | `business_date`, `city`, `driver_id`, `payout_pln`, `rank_in_city` |

Column details:
- `line_no` is the line number in the file, where the header is line 1.
- `raw_row` is the row as received, in any readable form.
- Money columns in `raw.trips` and `core.trips` are `NUMERIC(10,2)`. Timestamps are `timestamptz`.
- Each mart view has one row per key combination that has at least one completed trip.

### Reports

`report`, and the end of `close`, write each view in full to `reports/`, with a header row, overwriting the previous files:

| File | Order by |
|---|---|
| `daily_city_revenue.csv` | `business_date, city` |
| `driver_payouts.csv` | `business_date, driver_id` |
| `driver_leaderboard.csv` | `business_date, city, rank_in_city, driver_id` |

### Exit codes

- `0`: success, including runs with rejected rows.
- `1`: the run could not complete, e.g. the database is unreachable, a file is unreadable, or a SQL file is broken.

## Milestones and Git workflow

**Git rules:**
- After the initial commit, `main` only changes through merged pull requests.
- Use one branch and one PR per milestone, named as below.
- Commit messages say what changed ("Load drivers.csv into core.drivers"), not "fix", "wip" or "dupdupa".
- Each PR description says what it does and how you checked it.

| Branch | Done when |
|---|---|
| `m0-setup` | Starter runs with exit code 0; batch 1 committed under `data/`; PR merged |
| `m1-load-raw` | Reference data and all trip files land in `raw.*` / `core.cities` / `core.drivers`; reconciliation lines printed |
| `m2-rerun` | A second `close` changes nothing; `load <path>` works under the same rules as `close` |
| `m3-core-marts` | `core.trips` holds current state; the three views exist. Batch 2 arrives: commit it in this branch and run `close` on top of your existing database, without `down -v` |
| `m4-reports` | `report` and `close` write the three CSVs; the fresh-clone check passes; `v1.0` tagged |

Do this before tagging, outside your working copy, with your working copy's database stopped:

```bash
git clone <your-repo-url> fresh-check && cd fresh-check
cp .env.example .env
docker compose up --build --exit-code-from pipeline
docker compose down -v                     # clean up afterwards
```

**Submit:**

```bash
git tag v1.0
git push origin v1.0
```
