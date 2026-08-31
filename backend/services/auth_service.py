# pyrefly: ignore [missing-import]
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from werkzeug.security import generate_password_hash, check_password_hash
# pyrefly: ignore [missing-import]
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

try:
    from models.models import User
except ImportError:
    from backend.models.models import User

SECRET_KEY = os.environ.get("SECRET_KEY", "argus-cyber-security-secret-key-2026-v2")
SECURITY_SALT = os.environ.get("SECURITY_SALT", "argus-auth-salt-token-protection")

serializer = URLSafeTimedSerializer(SECRET_KEY, salt=SECURITY_SALT)
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AuthService:

    @staticmethod
    def register_user(db, name: str, email: str, password: str, confirm_password: str = None):
        """Register a new user with secure password hashing."""
        name = (name or "").strip()
        email = (email or "").strip().lower()

        if not name or len(name) < 2:
            raise ValueError("Full name must be at least 2 characters long.")

        if not email or not EMAIL_REGEX.match(email):
            raise ValueError("A valid email address is required.")

        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        if confirm_password is not None and confirm_password != password:
            raise ValueError("Passwords do not match.")

        # Check for existing user
        existing_user = db.query(User).filter(func.lower(User.email) == email).first()
        if existing_user:
            raise ValueError("An account with this email address already exists.")

        # Hash password securely
        try:
            password_hash = generate_password_hash(password, method="scrypt")
        except Exception:
            password_hash = generate_password_hash(password, method="pbkdf2:sha256")

        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db, email: str, password: str):
        """Authenticate user against stored password hash."""
        email = (email or "").strip().lower()
        if not email or not password:
            raise ValueError("Email and password are required.")

        user = db.query(User).filter(func.lower(User.email) == email).first()
        if not user:
            raise ValueError("Invalid email or password.")

        if not check_password_hash(user.password_hash, password):
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Account is disabled. Please contact your administrator.")

        return user

    @staticmethod
    def generate_token(user, max_age: int = 86400) -> str:
        """Generate a cryptographically signed token for user session authentication."""
        payload = {
            "user_id": user.id,
            "email": user.email
        }
        return serializer.dumps(payload)

    @staticmethod
    def verify_token(db, token: str, max_age: int = 86400):
        """Verify authentication token and return corresponding user."""
        if not token:
            return None

        try:
            payload = serializer.loads(token, max_age=max_age)
            user_id = payload.get("user_id")
            if not user_id:
                return None
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active:
                return user
            return None
        except (SignatureExpired, BadSignature, Exception):
            return None
