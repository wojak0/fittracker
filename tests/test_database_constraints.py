from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

import models


def test_database_rejects_negative_weight(db_session):
    workout = models.Workout(user_id=1, workout_date=date(2026, 7, 31))
    db_session.add(workout)
    db_session.commit()
    db_session.refresh(workout)

    invalid_entry = models.WorkoutExercise(
        workout_id=workout.workout_id,
        exercise_id=1,
        sets=3,
        reps=8,
        weight_kg=-1,
    )
    db_session.add(invalid_entry)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_database_rejects_orphan_workout_exercise(db_session):
    orphan = models.WorkoutExercise(
        workout_id=999,
        exercise_id=1,
        sets=3,
        reps=8,
        weight_kg=50,
    )
    db_session.add(orphan)

    with pytest.raises(IntegrityError):
        db_session.commit()
