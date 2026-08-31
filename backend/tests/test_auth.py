# pyrefly: ignore [missing-import]
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker
import db.database as db_module
from services.auth_service import AuthService


@pytest.fixture
def client():
    """Create Flask test client with isolated in-memory test database."""
    app.config["TESTING"] = True
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db_module.Base.metadata.create_all(bind=test_engine)

    orig_engine = db_module.engine
    orig_sessionmaker = db_module.SessionLocal

    db_module.engine = test_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with app.test_client() as client:
        yield client

    db_module.engine = orig_engine
    db_module.SessionLocal = orig_sessionmaker


def test_user_signup_success(client):
    payload = {
        "name": "Alice Security Analyst",
        "email": "alice@argus-sec.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }
    res = client.post("/api/v1/auth/signup", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["email"] == "alice@argus-sec.com"
    assert data["user"]["name"] == "Alice Security Analyst"
    assert "password_hash" not in data["user"]


def test_user_signup_duplicate_email(client):
    payload = {
        "name": "Bob Analyst",
        "email": "bob@argus-sec.com",
        "password": "SecurePassword123!"
    }
    res1 = client.post("/api/v1/auth/signup", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate signup
    res2 = client.post("/api/v1/auth/signup", json=payload)
    assert res2.status_code == 400
    data2 = res2.get_json()
    assert data2["success"] is False
    assert "already exists" in data2["error"].lower()


def test_user_signup_invalid_input(client):
    # Short password
    res = client.post("/api/v1/auth/signup", json={
        "name": "Charlie",
        "email": "charlie@argus.com",
        "password": "short"
    })
    assert res.status_code == 400
    assert "at least 8 characters" in res.get_json()["error"]

    # Mismatched confirm password
    res_mismatch = client.post("/api/v1/auth/signup", json={
        "name": "Charlie",
        "email": "charlie2@argus.com",
        "password": "Password123!",
        "confirm_password": "DifferentPassword123!"
    })
    assert res_mismatch.status_code == 400
    assert "do not match" in res_mismatch.get_json()["error"]


def test_user_login_success(client):
    # Register user first
    signup_data = {
        "name": "Dave Operator",
        "email": "dave@argus-sec.com",
        "password": "MySuperSecretPassword123!"
    }
    client.post("/api/v1/auth/signup", json=signup_data)

    # Login
    login_data = {
        "email": "dave@argus-sec.com",
        "password": "MySuperSecretPassword123!"
    }
    res = client.post("/api/v1/auth/login", json=login_data)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data
    assert data["user"]["email"] == "dave@argus-sec.com"


def test_user_login_wrong_password(client):
    signup_data = {
        "name": "Eve Tester",
        "email": "eve@argus-sec.com",
        "password": "CorrectPassword123!"
    }
    client.post("/api/v1/auth/signup", json=signup_data)

    # Wrong password
    res = client.post("/api/v1/auth/login", json={
        "email": "eve@argus-sec.com",
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False
    assert "invalid email or password" in data["error"].lower()


def test_auth_me_protected_endpoint(client):
    # Unauthenticated request
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401
    assert res_unauth.get_json()["success"] is False

    # Sign up and get token
    signup_res = client.post("/api/v1/auth/signup", json={
        "name": "Frank Officer",
        "email": "frank@argus-sec.com",
        "password": "FrankPassword123!"
    })
    token = signup_res.get_json()["token"]

    # Authenticated request with Bearer token
    res_auth = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_auth.status_code == 200
    data = res_auth.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "frank@argus-sec.com"


def test_auth_logout(client):
    signup_res = client.post("/api/v1/auth/signup", json={
        "name": "Grace Engineer",
        "email": "grace@argus-sec.com",
        "password": "GracePassword123!"
    })
    assert signup_res.status_code == 201

    res_logout = client.post("/api/v1/auth/logout")
    assert res_logout.status_code == 200
    assert res_logout.get_json()["success"] is True
