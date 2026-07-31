from decimal import Decimal


API_HEADERS = {"X-API-Key": "test-api-key"}


def create_workout(client):
    return client.post(
        "/workouts",
        headers=API_HEADERS,
        json={
            "user_id": 1,
            "workout_date": "2026-07-31",
            "notes": "Chest session",
        },
    )


def test_get_exercise_dictionary(client):
    response = client.get("/exercises")

    assert response.status_code == 200
    assert [exercise["name"] for exercise in response.json()] == [
        "Bench Press",
        "Squat",
    ]


def test_write_endpoints_require_api_key(client):
    response = client.post(
        "/workouts",
        json={"user_id": 1, "workout_date": "2026-07-31", "notes": None},
    )

    assert response.status_code == 401


def test_create_workout_and_return_joined_history(client):
    workout_response = create_workout(client)
    assert workout_response.status_code == 201
    workout_id = workout_response.json()["workout_id"]

    entry_response = client.post(
        f"/workouts/{workout_id}/exercises",
        headers=API_HEADERS,
        json={"exercise_id": 1, "sets": 3, "reps": 8, "weight_kg": "75.00"},
    )
    assert entry_response.status_code == 201

    history_response = client.get("/users/1/workouts")
    assert history_response.status_code == 200

    history = history_response.json()
    assert len(history) == 1
    assert history[0]["notes"] == "Chest session"
    assert Decimal(history[0]["total_volume_kg"]) == Decimal("1800.00")
    assert history[0]["exercises"][0]["name"] == "Bench Press"
    assert history[0]["exercises"][0]["sets"] == 3


def test_negative_weight_is_rejected(client):
    workout_id = create_workout(client).json()["workout_id"]

    response = client.post(
        f"/workouts/{workout_id}/exercises",
        headers=API_HEADERS,
        json={"exercise_id": 1, "sets": 3, "reps": 8, "weight_kg": -1},
    )

    assert response.status_code == 422


def test_unknown_user_returns_not_found(client):
    response = client.get("/users/999/workouts")

    assert response.status_code == 404


def test_duplicate_exercise_in_workout_returns_conflict(client):
    workout_id = create_workout(client).json()["workout_id"]
    payload = {"exercise_id": 1, "sets": 3, "reps": 8, "weight_kg": 75}

    first = client.post(
        f"/workouts/{workout_id}/exercises", headers=API_HEADERS, json=payload
    )
    second = client.post(
        f"/workouts/{workout_id}/exercises", headers=API_HEADERS, json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 409
