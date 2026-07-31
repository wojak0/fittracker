# Fit Tracker

Fit Tracker is a small database-backed strength-training application for the
THGA *Introduction to Database Management Systems* term project.

## Architecture

- PostgreSQL stores users, exercises, workouts, and exercise performances.
- FastAPI exposes exactly two read and two write endpoints.
- Docker Compose runs only the PostgreSQL and FastAPI backend services.
- The planned Tkinter frontend will run outside Docker and be delivered as a
  Debian package.

## API

| Method | Path | API key | Purpose |
| --- | --- | --- | --- |
| `GET` | `/exercises` | No | Read the exercise dictionary |
| `GET` | `/users/{user_id}/workouts` | No | Read joined workout history and total volume |
| `POST` | `/workouts` | Yes | Create a workout session |
| `POST` | `/workouts/{workout_id}/exercises` | Yes | Log sets, reps, and weight |

Write requests must include the header `X-API-Key`.

## Start the backend

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Replace both placeholder secrets in `.env`.
3. Build and start the services:

   ```bash
   docker compose up -d --build
   ```

4. Open the interactive API documentation at
   `http://localhost:8888/docs`.

The initial database contains user `1` (`demo_user`) and five exercises.
PostgreSQL executes `init.sql` only when its data volume is first created.

## Example requests

Create a workout:

```bash
curl -X POST http://localhost:8888/workouts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_KEY' \
  -d '{"user_id":1,"workout_date":"2026-07-31","notes":"Chest session"}'
```

Log bench press for workout `1`:

```bash
curl -X POST http://localhost:8888/workouts/1/exercises \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_KEY' \
  -d '{"exercise_id":1,"sets":3,"reps":8,"weight_kg":75}'
```

Read the complete history:

```bash
curl http://localhost:8888/users/1/workouts
```

## Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

The test suite covers API-key rejection, endpoint happy paths, JOIN and
aggregation results, validation errors, duplicate entries, foreign keys, and
database check constraints.

## Documentation material

- `Pdf files/Proposal.pdf`: submitted Fit Tracker proposal
- `src/dbms_10.tex`: original assignment
- `proposal-template/`: proposal source material
- `example-documentation/`: lecturer's documentation example
- `style/thga-db.sty`: THGA LaTeX style

The HTML file in `frontend/` is an early prototype only. The final frontend will
be replaced by the required Tkinter desktop application and `.deb` package.
