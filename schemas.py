from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExerciseRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "exercise_id": 1,
                "name": "Bench Press",
                "target_muscle": "Chest",
                "description": "Flat barbell press for chest strength.",
            }
        },
    )

    exercise_id: int
    name: str
    target_muscle: str
    description: str | None


class WorkoutCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "workout_date": "2026-07-31",
                "notes": "Upper-body strength session",
            }
        }
    )

    user_id: int = Field(gt=0)
    workout_date: date
    notes: str | None = Field(default=None, max_length=2000)


class WorkoutRead(WorkoutCreate):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "user_id": 1,
                "workout_date": "2026-07-31",
                "notes": "Upper-body strength session",
                "workout_id": 1,
            }
        },
    )

    workout_id: int


class WorkoutExerciseCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "exercise_id": 1,
                "sets": 3,
                "reps": 8,
                "weight_kg": 75.00,
            }
        }
    )

    exercise_id: int = Field(gt=0)
    sets: int = Field(gt=0, le=100)
    reps: int = Field(gt=0, le=1000)
    weight_kg: Decimal = Field(
        ge=0,
        max_digits=6,
        decimal_places=2,
    )


class WorkoutExerciseRead(WorkoutExerciseCreate):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "exercise_id": 1,
                "sets": 3,
                "reps": 8,
                "weight_kg": "75.00",
                "workout_exercise_id": 1,
                "workout_id": 1,
            }
        },
    )

    workout_exercise_id: int
    workout_id: int


class WorkoutExerciseDetail(WorkoutExerciseRead):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "exercise_id": 1,
                "sets": 3,
                "reps": 8,
                "weight_kg": "75.00",
                "workout_exercise_id": 1,
                "workout_id": 1,
                "name": "Bench Press",
                "target_muscle": "Chest",
            }
        },
    )

    name: str
    target_muscle: str


class WorkoutHistory(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workout_id": 1,
                "user_id": 1,
                "workout_date": "2026-07-31",
                "notes": "Upper-body strength session",
                "total_volume_kg": "1800.00",
                "exercises": [
                    {
                        "exercise_id": 1,
                        "sets": 3,
                        "reps": 8,
                        "weight_kg": "75.00",
                        "workout_exercise_id": 1,
                        "workout_id": 1,
                        "name": "Bench Press",
                        "target_muscle": "Chest",
                    }
                ],
            }
        }
    )

    workout_id: int
    user_id: int
    workout_date: date
    notes: str | None
    total_volume_kg: Decimal = Field(ge=0)
    exercises: list[WorkoutExerciseDetail]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    created_at: datetime
