# Fit Tracker – DBMS Term Project

**Author:** Ahmad Hoteit  
**Module:** Introduction to Database Management Systems  
**Lecturer:** Stephan Bökelmann  
**Institution:** Technische Hochschule Georg Agricola (THGA), Bochum  
**Semester:** Summer Term 2026  

Fit Tracker is a database-backed strength-training application developed as the
term project for the Introduction to Database Management Systems module.

It allows gym users to create workout sessions, select exercises from an
exercise dictionary, record sets, repetitions and weight, and review their
training history.

## Architecture

```text
Tkinter frontend installed as .deb
              |
              | HTTP + X-API-Key
              v
       FastAPI container
              |
              v
      PostgreSQL container
```

Docker Compose operates only the backend services:

- `postgres`: PostgreSQL database
- `api`: FastAPI REST API

The planned Tkinter frontend runs outside Docker and communicates exclusively
with the FastAPI backend.

## Database model

The system contains exactly four relational tables:

| Table | Purpose |
| --- | --- |
| `users` | Stores application users |
| `exercises` | Stores the exercise dictionary |
| `workouts` | Stores workout sessions belonging to users |
| `workout_exercises` | Resolves the N:M relationship between workouts and exercises |

Relationship structure:

```text
users 1 ── N workouts 1 ── N workout_exercises N ── 1 exercises
```

The schema includes primary keys, foreign keys, unique constraints, `NOT NULL`
constraints and checks for positive sets and repetitions and non-negative
weights.

## REST API

The API provides exactly two read and two write endpoints:

| Method | Endpoint | API key | Purpose |
| --- | --- | --- | --- |
| `GET` | `/exercises` | No | Read the exercise dictionary |
| `GET` | `/users/{user_id}/workouts` | No | Read joined workout history and total volume |
| `POST` | `/workouts` | Yes | Create a workout session |
| `POST` | `/workouts/{workout_id}/exercises` | Yes | Log sets, repetitions and weight |

The workout-history endpoint performs JOIN and aggregation operations. Training
volume is calculated as:

```text
sets × repetitions × weight
```

Write requests require the following HTTP header:

```text
X-API-Key: configured-api-key
```

## Requirements

- Linux or Debian-based system
- Docker
- Docker Compose
- Git
- Python 3.11 or newer for local testing

## Starting the backend

Copy the environment template:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder password and API key:

```bash
nano .env
```

Build and start PostgreSQL and FastAPI:

```bash
docker compose up -d --build
```

Check the services:

```bash
docker compose ps
```

Both services should be running, and PostgreSQL should report `healthy`.

The interactive FastAPI documentation is available at:

```text
http://localhost:8888/docs
```

## Initial data

When PostgreSQL creates a new database volume, `init.sql` creates the schema and
inserts:

- Demo user with `user_id = 1`
- Bench Press
- Squat
- Deadlift
- Overhead Press
- Triceps Pushdown

PostgreSQL executes `init.sql` only when the database volume is initialized for
the first time.

## Example API usage

Create a workout:

```bash
curl -X POST http://localhost:8888/workouts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "user_id": 1,
    "workout_date": "2026-07-31",
    "notes": "Chest session"
  }'
```

Log an exercise:

```bash
curl -X POST http://localhost:8888/workouts/1/exercises \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "exercise_id": 1,
    "sets": 3,
    "reps": 8,
    "weight_kg": 75
  }'
```

Read workout history:

```bash
curl http://localhost:8888/users/1/workouts
```

For three sets of eight repetitions with 75 kg, the returned total volume is:

```text
3 × 8 × 75 kg = 1800 kg
```

## Automated tests

Create a Python environment and install the development dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

Run the tests:

```bash
.venv/bin/pytest -q
```

Alternatively:

```bash
make test
```

The current test suite covers:

- Exercise dictionary retrieval
- Workout creation
- Exercise logging
- Joined workout history
- Volume aggregation
- Missing API-key rejection
- Invalid weight validation
- Duplicate exercise rejection
- Foreign-key constraints
- Database check constraints

## Useful commands

```bash
make up       # Build and start the backend
make down     # Stop the backend
make logs     # Display API and PostgreSQL logs
make test     # Run automated tests
make docs     # Build the LaTeX documents
```

## Repository structure

```text
.
├── database.py
├── main.py
├── models.py
├── schemas.py
├── init.sql
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
├── tests/
├── frontend/
├── Pdf files/
│   └── Proposal.pdf
├── proposal-template/
├── example-documentation/
├── src/
├── style/
├── Makefile
└── README.md
```

The HTML file currently inside `frontend/` is an early prototype only. It is not
part of the final application. The final frontend will be implemented using
Python and Tkinter and packaged as a Debian `.deb` installer.

## Security

Database credentials and the API key are stored in `.env`.

The real `.env` file is excluded from Git. Only `.env.example`, containing
placeholder values, is committed.

Never commit real passwords or API keys.

## Current status

Completed:

- PostgreSQL schema and seed data
- Four SQLAlchemy models
- Four required FastAPI endpoints
- X-API-Key authentication
- Docker and Docker Compose configuration
- JOIN and volume aggregation
- Automated backend tests
- Successful Docker test on Ubuntu

Remaining:

- Tkinter desktop frontend
- Debian `.deb` packaging
- GitHub Actions
- Final technical documentation
- Complete Debian installation test
- 8–10 minute demonstration video

## Sources and reuse

The project structure and Docker/FastAPI patterns are based on the examples from
the DBMS lectures and exercises, particularly DBMS_08, DBMS_09 and lecture 10.
The THGA LaTeX style and documentation templates originate from the provided
DBMS_10 course repository.
