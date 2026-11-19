"""Tests for the Mergington High School Activities API.

All tests follow the AAA (Arrange-Act-Assert) pattern.
"""

import copy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_activities():
    """Snapshot the in-memory activities database and restore it after each test."""
    # Arrange (shared): preserve original state so mutations don't leak between tests
    snapshot = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(snapshot)


class TestRoot:
    def test_root_redirects_to_static_index(self):
        # Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code in (302, 307)
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    def test_returns_all_activities(self):
        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == set(activities.keys())

    def test_activities_have_expected_structure(self):
        # Act
        response = client.get("/activities")

        # Assert
        data = response.json()
        for activity in data.values():
            assert set(activity.keys()) == {
                "description",
                "schedule",
                "max_participants",
                "participants",
            }
            assert isinstance(activity["participants"], list)


class TestSignup:
    def test_signup_success_adds_participant(self):
        # Arrange
        activity_name = "Basketball Team"
        email = "newstudent@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup", params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == {
            "message": f"Signed up {email} for {activity_name}"
        }
        assert email in activities[activity_name]["participants"]

    def test_signup_unknown_activity_returns_404(self):
        # Arrange
        email = "student@mergington.edu"

        # Act
        response = client.post(
            "/activities/Nonexistent Club/signup", params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_returns_400(self):
        # Arrange
        activity_name = "Chess Club"
        email = activities[activity_name]["participants"][0]

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup", params={"email": email}
        )

        # Assert
        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "Student already signed up for this activity"
        )

    def test_signup_full_activity_returns_400(self):
        # Arrange
        activity_name = "Chess Club"
        activity = activities[activity_name]
        activity["participants"] = [
            f"student{i}@mergington.edu"
            for i in range(activity["max_participants"])
        ]

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "latecomer@mergington.edu"},
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["detail"] == "Activity is full"


class TestUnregister:
    def test_unregister_success_removes_participant(self):
        # Arrange
        activity_name = "Chess Club"
        email = activities[activity_name]["participants"][0]

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants", params={"email": email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == {
            "message": f"Unregistered {email} from {activity_name}"
        }
        assert email not in activities[activity_name]["participants"]

    def test_unregister_unknown_activity_returns_404(self):
        # Arrange
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            "/activities/Nonexistent Club/participants", params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_not_signed_up_returns_404(self):
        # Arrange
        activity_name = "Chess Club"
        email = "notsignedup@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/participants", params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Student not signed up for this activity"
        )
