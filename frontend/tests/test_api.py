import json
from decimal import Decimal

import pytest
import requests

from fittracker_frontend.api import ApiClient, ApiError


def make_response(status_code, payload):
    response = requests.Response()
    response.status_code = status_code
    response.reason = "Test response"
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(payload).encode("utf-8")
    return response


def test_rejects_invalid_base_url():
    with pytest.raises(ApiError, match="valid API URL"):
        ApiClient("localhost:8888", "test-key")


def test_get_exercises_is_public(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return make_response(
            200,
            [
                {
                    "exercise_id": 1,
                    "name": "Bench Press",
                    "target_muscle": "Chest",
                    "description": "Test exercise",
                }
            ],
        )

    monkeypatch.setattr(requests, "request", fake_request)

    client = ApiClient("http://localhost:8888/", "test-key")
    result = client.get_exercises()

    assert result[0]["name"] == "Bench Press"
    assert captured["method"] == "GET"
    assert captured["url"] == "http://localhost:8888/exercises"
    assert "X-API-Key" not in captured["headers"]
    assert captured["timeout"] == 8.0


def test_create_workout_sends_api_key_and_json(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return make_response(
            201,
            {
                "workout_id": 7,
                "user_id": 1,
                "workout_date": "2026-07-31",
                "notes": "Test",
            },
        )

    monkeypatch.setattr(requests, "request", fake_request)

    client = ApiClient("http://localhost:8888", "secret-key")
    result = client.create_workout(
        user_id=1,
        workout_date="2026-07-31",
        notes="Test",
    )

    assert result["workout_id"] == 7
    assert captured["method"] == "POST"
    assert captured["headers"]["X-API-Key"] == "secret-key"
    assert captured["json"]["user_id"] == 1
    assert captured["json"]["notes"] == "Test"


def test_add_exercise_serializes_decimal_weight(monkeypatch):
    captured = {}

    def fake_request(**kwargs):
        captured.update(kwargs)
        return make_response(
            201,
            {
                "workout_exercise_id": 3,
                "workout_id": 7,
                "exercise_id": 1,
                "sets": 3,
                "reps": 8,
                "weight_kg": "75.25",
            },
        )

    monkeypatch.setattr(requests, "request", fake_request)

    client = ApiClient("http://localhost:8888", "secret-key")
    client.add_exercise(
        workout_id=7,
        exercise_id=1,
        sets=3,
        reps=8,
        weight=Decimal("75.25"),
    )

    assert captured["url"].endswith("/workouts/7/exercises")
    assert captured["json"]["weight_kg"] == "75.25"
    assert captured["headers"]["X-API-Key"] == "secret-key"


def test_http_error_contains_status_and_detail(monkeypatch):
    def fake_request(**_kwargs):
        return make_response(
            401,
            {"detail": "Invalid or missing API key"},
        )

    monkeypatch.setattr(requests, "request", fake_request)

    client = ApiClient("http://localhost:8888", "wrong-key")

    with pytest.raises(
        ApiError,
        match="HTTP 401: Invalid or missing API key",
    ) as error:
        client.create_workout(
            user_id=1,
            workout_date="2026-07-31",
            notes="Test",
        )

    assert error.value.status_code == 401


def test_connection_error_is_user_friendly(monkeypatch):
    def fake_request(**_kwargs):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "request", fake_request)

    client = ApiClient("http://localhost:8888", "test-key")

    with pytest.raises(ApiError, match="Could not connect to the API"):
        client.get_exercises()
