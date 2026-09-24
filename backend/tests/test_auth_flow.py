"""
Integration tests: auth flow — session establishment + protected route gating.

Tests:
1. No session cookie → GET /api/me → 401
2. Valid JWT cookie set on client → GET /api/me → 200 with correct user data
3. GET /api/auth/session with no cookie → 401
4. GET /api/auth/session with valid cookie → 200 with user data
5. Tampered JWT → 401
6. POST /api/auth/logout → 200
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.users import User


def _create_test_user(db: Session) -> User:
    """Helper: insert a User row and return it."""
    user = User(
        id=uuid.uuid4(),
        google_id="google-test-id-123",
        email="testuser@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestProtectedRoute:
    def test_get_me_without_session_returns_401(self, client):
        """No cookie → /api/me must return 401, not a user object."""
        response = client.get("/api/me")
        assert response.status_code == 401, (
            f"Expected 401 without auth cookie, got {response.status_code}: {response.text}"
        )

    def test_get_me_with_valid_session_returns_200(self, client, db_session):
        """Valid JWT cookie → /api/me returns 200 with the authenticated user."""
        user = _create_test_user(db_session)
        token = create_access_token(data={"sub": str(user.id)})

        # Set cookie on the client instance (not per-request)
        client.cookies.set("access_token", token)
        response = client.get("/api/me")
        client.cookies.clear()

        assert response.status_code == 200, (
            f"Expected 200 with valid auth cookie, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["name"] == "Test User"
        assert str(user.id) == data["id"]

    def test_get_me_with_tampered_jwt_returns_401(self, client, db_session):
        """Tampered JWT → /api/me must return 401."""
        _create_test_user(db_session)
        client.cookies.set("access_token", "this.is.not.a.valid.jwt")
        response = client.get("/api/me")
        client.cookies.clear()
        assert response.status_code == 401


class TestSessionEndpoint:
    def test_session_without_cookie_returns_401(self, client):
        """No cookie → /api/auth/session must return 401."""
        response = client.get("/api/auth/session")
        assert response.status_code == 401

    def test_session_with_valid_cookie_returns_user(self, client, db_session):
        """Valid JWT cookie → /api/auth/session returns user profile."""
        user = _create_test_user(db_session)
        token = create_access_token(data={"sub": str(user.id)})

        client.cookies.set("access_token", token)
        response = client.get("/api/auth/session")
        client.cookies.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
        assert data["google_id"] == user.google_id

    def test_logout_returns_200(self, client):
        """POST /api/auth/logout → 200 with success message."""
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json().get("message") == "Logged out successfully"
