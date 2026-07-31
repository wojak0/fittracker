from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

import requests


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 8.0,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        parsed_url = urlparse(cleaned_url)

        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ApiError("Enter a valid API URL beginning with http:// or https://.")

        self.base_url = cleaned_url
        self.api_key = api_key.strip()
        self.timeout = timeout

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or response.reason

        detail = payload.get("detail") if isinstance(payload, dict) else payload

        if isinstance(detail, list):
            messages = []
            for item in detail:
                if not isinstance(item, dict):
                    messages.append(str(item))
                    continue

                location = ".".join(str(part) for part in item.get("loc", []))
                message = item.get("msg", "Invalid value")
                messages.append(f"{location}: {message}" if location else message)

            return "; ".join(messages)

        return str(detail or response.reason)

    def request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        protected: bool = False,
    ) -> Any:
        headers = {"Accept": "application/json"}

        if protected:
            headers["X-API-Key"] = self.api_key

        try:
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.Timeout as error:
            raise ApiError(
                f"The API did not respond within {self.timeout:g} seconds."
            ) from error
        except requests.ConnectionError as error:
            raise ApiError(
                "Could not connect to the API. Check the URL and Docker services."
            ) from error
        except requests.RequestException as error:
            raise ApiError(f"API request failed: {error}") from error

        if not response.ok:
            detail = self._error_detail(response)
            raise ApiError(
                f"HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
            )

        if not response.content:
            return None

        try:
            return response.json()
        except ValueError as error:
            raise ApiError("The API returned invalid JSON.") from error

    def get_exercises(self) -> list[dict[str, Any]]:
        return self.request("GET", "/exercises")

    def get_workouts(self, user_id: int) -> list[dict[str, Any]]:
        return self.request("GET", f"/users/{user_id}/workouts")

    def create_workout(
        self,
        user_id: int,
        workout_date: str,
        notes: str,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            "/workouts",
            data={
                "user_id": user_id,
                "workout_date": workout_date,
                "notes": notes or None,
            },
            protected=True,
        )

    def add_exercise(
        self,
        workout_id: int,
        exercise_id: int,
        sets: int,
        reps: int,
        weight: Decimal,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/workouts/{workout_id}/exercises",
            data={
                "exercise_id": exercise_id,
                "sets": sets,
                "reps": reps,
                "weight_kg": str(weight),
            },
            protected=True,
        )
