import os
import secrets
from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db


API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not configured. Copy .env.example to .env and set it.")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
app = FastAPI(
    title="Fit Tracker API",
    description="REST API for strength-training sessions.",
    version="0.1.0",
)


def require_api_key(api_key: str | None = Security(api_key_header)) -> str:
    if api_key is None or not secrets.compare_digest(api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


@app.get("/exercises", response_model=list[schemas.ExerciseRead])
def get_exercises(db: Session = Depends(get_db)):
    return db.query(models.Exercise).order_by(models.Exercise.name).all()


@app.get(
    "/users/{user_id}/workouts",
    response_model=list[schemas.WorkoutHistory],
)
def get_user_workouts(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    volume_expression = func.coalesce(
        func.sum(
            models.WorkoutExercise.sets
            * models.WorkoutExercise.reps
            * models.WorkoutExercise.weight_kg
        ),
        0,
    )

    workout_rows = (
        db.query(models.Workout, volume_expression.label("total_volume_kg"))
        .outerjoin(
            models.WorkoutExercise,
            models.Workout.workout_id == models.WorkoutExercise.workout_id,
        )
        .filter(models.Workout.user_id == user_id)
        .group_by(models.Workout.workout_id)
        .order_by(models.Workout.workout_date.desc(), models.Workout.workout_id.desc())
        .all()
    )

    history = []
    for workout, total_volume in workout_rows:
        entry_rows = (
            db.query(models.WorkoutExercise, models.Exercise)
            .join(
                models.Exercise,
                models.WorkoutExercise.exercise_id == models.Exercise.exercise_id,
            )
            .filter(models.WorkoutExercise.workout_id == workout.workout_id)
            .order_by(models.WorkoutExercise.workout_exercise_id)
            .all()
        )

        exercises = [
            schemas.WorkoutExerciseDetail(
                workout_exercise_id=entry.workout_exercise_id,
                workout_id=entry.workout_id,
                exercise_id=entry.exercise_id,
                name=exercise.name,
                target_muscle=exercise.target_muscle,
                sets=entry.sets,
                reps=entry.reps,
                weight_kg=entry.weight_kg,
            )
            for entry, exercise in entry_rows
        ]

        history.append(
            schemas.WorkoutHistory(
                workout_id=workout.workout_id,
                user_id=workout.user_id,
                workout_date=workout.workout_date,
                notes=workout.notes,
                total_volume_kg=Decimal(str(total_volume or 0)),
                exercises=exercises,
            )
        )

    return history


@app.post(
    "/workouts",
    response_model=schemas.WorkoutRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_workout(workout: schemas.WorkoutCreate, db: Session = Depends(get_db)):
    if db.get(models.User, workout.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    new_workout = models.Workout(**workout.model_dump())
    db.add(new_workout)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Workout could not be created") from exc

    db.refresh(new_workout)
    return new_workout


@app.post(
    "/workouts/{workout_id}/exercises",
    response_model=schemas.WorkoutExerciseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def add_exercise_to_workout(
    workout_id: int,
    entry: schemas.WorkoutExerciseCreate,
    db: Session = Depends(get_db),
):
    if db.get(models.Workout, workout_id) is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    if db.get(models.Exercise, entry.exercise_id) is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    existing = (
        db.query(models.WorkoutExercise)
        .filter(
            models.WorkoutExercise.workout_id == workout_id,
            models.WorkoutExercise.exercise_id == entry.exercise_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Exercise is already logged for this workout",
        )

    new_entry = models.WorkoutExercise(workout_id=workout_id, **entry.model_dump())
    db.add(new_entry)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Exercise performance could not be logged"
        ) from exc

    db.refresh(new_entry)
    return new_entry
