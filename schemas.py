from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExerciseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    name: str
    target_muscle: str
    description: str | None


class WorkoutCreate(BaseModel):
    user_id: int = Field(gt=0)
    workout_date: date
    notes: str | None = Field(default=None, max_length=2000)


class WorkoutRead(WorkoutCreate):
    model_config = ConfigDict(from_attributes=True)

    workout_id: int


class WorkoutExerciseCreate(BaseModel):
    exercise_id: int = Field(gt=0)
    sets: int = Field(gt=0, le=100)
    reps: int = Field(gt=0, le=1000)
    weight_kg: Decimal = Field(ge=0, max_digits=6, decimal_places=2)


class WorkoutExerciseRead(WorkoutExerciseCreate):
    model_config = ConfigDict(from_attributes=True)

    workout_exercise_id: int
    workout_id: int


class WorkoutExerciseDetail(WorkoutExerciseRead):
    name: str
    target_muscle: str


class WorkoutHistory(BaseModel):
    workout_id: int
    user_id: int
    workout_date: date
    notes: str | None
    total_volume_kg: Decimal
    exercises: list[WorkoutExerciseDetail]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    created_at: datetime
