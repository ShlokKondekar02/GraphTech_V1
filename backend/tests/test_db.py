"""
DB integration tests: write and read `users` and `diagram_requests` rows
against the real schema (using in-memory SQLite via conftest fixtures).
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.users import User
from app.models.diagram_requests import DiagramRequest


class TestUsersTable:
    def test_create_and_read_user(self, db_session: Session):
        """Can write a User row and read it back by email."""
        user = User(
            id=uuid.uuid4(),
            google_id="google-db-test-001",
            email="db_test@example.com",
            name="DB Test User",
            avatar_url="https://example.com/pic.png",
        )
        db_session.add(user)
        db_session.commit()

        fetched = db_session.query(User).filter(User.email == "db_test@example.com").first()
        assert fetched is not None
        assert fetched.name == "DB Test User"
        assert fetched.google_id == "google-db-test-001"
        assert fetched.avatar_url == "https://example.com/pic.png"

    def test_email_uniqueness_enforced(self, db_session: Session):
        """Inserting two users with the same email raises an integrity error."""
        from sqlalchemy.exc import IntegrityError

        u1 = User(id=uuid.uuid4(), email="unique@example.com", name="First")
        u2 = User(id=uuid.uuid4(), email="unique@example.com", name="Second")
        db_session.add(u1)
        db_session.commit()

        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_google_id_uniqueness_enforced(self, db_session: Session):
        """Inserting two users with the same google_id raises an integrity error."""
        from sqlalchemy.exc import IntegrityError

        u1 = User(id=uuid.uuid4(), email="user1@example.com", google_id="shared-gid")
        u2 = User(id=uuid.uuid4(), email="user2@example.com", google_id="shared-gid")
        db_session.add(u1)
        db_session.commit()

        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestDiagramRequestsTable:
    def _make_user(self, db: Session) -> User:
        user = User(id=uuid.uuid4(), email=f"dr_test_{uuid.uuid4().hex[:6]}@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_create_and_read_diagram_request(self, db_session: Session):
        """Can write a DiagramRequest row linked to a user and read it back."""
        user = self._make_user(db_session)

        dr = DiagramRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            prompt="Design a microservices architecture for an e-commerce platform",
            status="pending",
            diagram_type="system",
            complexity="moderate",
            renderer="mermaid",
        )
        db_session.add(dr)
        db_session.commit()

        fetched = db_session.query(DiagramRequest).filter(DiagramRequest.user_id == user.id).first()
        assert fetched is not None
        assert fetched.prompt == "Design a microservices architecture for an e-commerce platform"
        assert fetched.status == "pending"
        assert fetched.diagram_type == "system"

    def test_diagram_request_cascade_delete(self, db_session: Session):
        """Deleting a user cascades and removes their diagram_requests."""
        user = self._make_user(db_session)

        dr = DiagramRequest(
            id=uuid.uuid4(),
            user_id=user.id,
            prompt="Cascade delete test",
            status="pending",
        )
        db_session.add(dr)
        db_session.commit()

        # Verify it exists
        assert db_session.query(DiagramRequest).filter(DiagramRequest.user_id == user.id).count() == 1

        # Delete user — cascade should remove diagram_requests
        db_session.delete(user)
        db_session.commit()

        assert db_session.query(DiagramRequest).filter(DiagramRequest.user_id == user.id).count() == 0

    def test_diagram_request_nullable_user(self, db_session: Session):
        """DiagramRequest.user_id is nullable — anonymous request is valid."""
        dr = DiagramRequest(
            id=uuid.uuid4(),
            prompt="Anonymous diagram request",
            status="pending",
        )
        db_session.add(dr)
        db_session.commit()

        fetched = db_session.query(DiagramRequest).filter(DiagramRequest.user_id == None).first()  # noqa: E711
        assert fetched is not None
        assert fetched.prompt == "Anonymous diagram request"
