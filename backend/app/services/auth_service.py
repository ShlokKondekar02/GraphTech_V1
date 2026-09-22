"""Authentication service for Google OAuth and session management (Sprint 1+)."""

class AuthService:
    def __init__(self):
        pass

    async def verify_google_token(self, token: str) -> dict:
        """Stub for Google token verification."""
        raise NotImplementedError("Google token verification will be implemented in the Auth sprint.")

    async def get_or_create_user(self, email: str, name: str, avatar_url: str = None):
        """Stub for user provisioning."""
        raise NotImplementedError("User management will be implemented in the Auth sprint.")


auth_service = AuthService()
