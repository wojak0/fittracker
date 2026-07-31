-- Fit Tracker analytical SQL queries
-- These queries use the seeded demo user with user_id = 1.


-- Query 1: List the exercise dictionary alphabetically.

SELECT exercise_id,
       name,
       target_muscle,
       description
FROM exercises
ORDER BY name;


-- Query 2: Workout history and total training volume for user 1.
-- LEFT JOIN keeps workouts that do not yet contain an exercise.
-- Training volume = sets * repetitions * weight in kilograms.

SELECT w.workout_id,
       w.user_id,
       w.workout_date,
       w.notes,
       COALESCE(
           SUM(
               we.sets
               * we.reps
               * we.weight_kg
           ),
           0
       ) AS total_volume_kg
FROM workouts AS w
LEFT JOIN workout_exercises AS we
       ON we.workout_id = w.workout_id
WHERE w.user_id = 1
GROUP BY
       w.workout_id,
       w.user_id,
       w.workout_date,
       w.notes
ORDER BY
       w.workout_date DESC,
       w.workout_id DESC;


-- Query 3: Exercise details belonging to every workout.

SELECT w.workout_id,
       w.workout_date,
       e.exercise_id,
       e.name AS exercise_name,
       e.target_muscle,
       we.sets,
       we.reps,
       we.weight_kg,
       we.sets * we.reps * we.weight_kg AS exercise_volume_kg
FROM workouts AS w
JOIN workout_exercises AS we
     ON we.workout_id = w.workout_id
JOIN exercises AS e
     ON e.exercise_id = we.exercise_id
WHERE w.user_id = 1
ORDER BY
     w.workout_date DESC,
     w.workout_id DESC,
     we.workout_exercise_id;


-- Query 4: Exercises that have never been logged in a workout.

SELECT e.exercise_id,
       e.name,
       e.target_muscle
FROM exercises AS e
WHERE NOT EXISTS (
    SELECT 1
    FROM workout_exercises AS we
    WHERE we.exercise_id = e.exercise_id
)
ORDER BY e.name;


-- Query 5: Number of workouts and total volume for every user.
-- LEFT JOIN keeps users who have not recorded a workout.

SELECT u.user_id,
       u.username,
       COUNT(DISTINCT w.workout_id) AS workout_count,
       COALESCE(
           SUM(
               we.sets
               * we.reps
               * we.weight_kg
           ),
           0
       ) AS total_volume_kg
FROM users AS u
LEFT JOIN workouts AS w
       ON w.user_id = u.user_id
LEFT JOIN workout_exercises AS we
       ON we.workout_id = w.workout_id
GROUP BY
       u.user_id,
       u.username
ORDER BY u.username;
