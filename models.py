from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workouts = relationship(
        "Workout", back_populates="user", cascade="all, delete-orphan"
    )


class Exercise(Base):
    __tablename__ = "exercises"

    exercise_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    target_muscle = Column(String(100), nullable=False)
    description = Column(Text)

    workout_entries = relationship(
        "WorkoutExercise", back_populates="exercise", cascade="all, delete-orphan"
    )


class Workout(Base):
    __tablename__ = "workouts"

    workout_id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    workout_date = Column(Date, nullable=False)
    notes = Column(Text)

    user = relationship("User", back_populates="workouts")
    exercise_entries = relationship(
        "WorkoutExercise", back_populates="workout", cascade="all, delete-orphan"
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        CheckConstraint("sets > 0", name="ck_workout_exercises_sets_positive"),
        CheckConstraint("reps > 0", name="ck_workout_exercises_reps_positive"),
        CheckConstraint(
            "weight_kg >= 0", name="ck_workout_exercises_weight_nonnegative"
        ),
        UniqueConstraint(
            "workout_id", "exercise_id", name="uq_workout_exercise_pair"
        ),
    )

    workout_exercise_id = Column(Integer, primary_key=True)
    workout_id = Column(
        Integer,
        ForeignKey("workouts.workout_id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id = Column(
        Integer,
        ForeignKey("exercises.exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    sets = Column(Integer, nullable=False)
    reps = Column(Integer, nullable=False)
    weight_kg = Column(Numeric(6, 2), nullable=False)

    workout = relationship("Workout", back_populates="exercise_entries")
    exercise = relationship("Exercise", back_populates="workout_entries")
