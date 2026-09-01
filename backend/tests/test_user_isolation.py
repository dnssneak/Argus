import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import db.database as db_module
from models.models import User, Project, Asset, Finding, Scan, Target


@pytest.fixture
def client():
    """Create Flask test client with an isolated in-memory database."""
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


def test_user_data_isolation(client):
    # 1. Signup User A
    res_a = client.post("/api/v1/auth/signup", json={
        "name": "User Alpha",
        "email": "alpha@security.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res_a.status_code == 201
    token_a = res_a.get_json()["token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Signup User B
    res_b = client.post("/api/v1/auth/signup", json={
        "name": "User Beta",
        "email": "beta@security.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert res_b.status_code == 201
    token_b = res_b.get_json()["token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates Project A
    res_pa = client.post("/api/v1/projects", json={"name": "Alpha Defense Scope"}, headers=headers_a)
    assert res_pa.status_code == 201
    proj_a_id = res_pa.get_json()["project"]["id"]

    # 4. User B creates Project B
    res_pb = client.post("/api/v1/projects", json={"name": "Beta Audit Scope"}, headers=headers_b)
    assert res_pb.status_code == 201
    proj_b_id = res_pb.get_json()["project"]["id"]

    # 5. User A creates Asset A inside Project A
    res_aa = client.post("/api/v1/assets", json={
        "name": "alpha-server.com",
        "asset_type": "Domain",
        "project_id": proj_a_id
    }, headers=headers_a)
    assert res_aa.status_code == 201
    asset_a_id = res_aa.get_json()["asset"]["id"]

    # 6. User B creates Asset B inside Project B
    res_ab = client.post("/api/v1/assets", json={
        "name": "beta-vault.com",
        "asset_type": "Domain",
        "project_id": proj_b_id
    }, headers=headers_b)
    assert res_ab.status_code == 201
    asset_b_id = res_ab.get_json()["asset"]["id"]

    # --- VERIFY PROJECT LIST ISOLATION ---
    projects_a = client.get("/api/v1/projects", headers=headers_a).get_json()["projects"]
    projects_b = client.get("/api/v1/projects", headers=headers_b).get_json()["projects"]
    
    assert len(projects_a) == 1
    assert projects_a[0]["name"] == "Alpha Defense Scope"

    assert len(projects_b) == 1
    assert projects_b[0]["name"] == "Beta Audit Scope"

    # --- VERIFY CROSS-USER PROJECT ACCESS DENIED (404) ---
    res_cross_p = client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_b)
    assert res_cross_p.status_code == 404

    res_cross_dash = client.get(f"/api/v1/projects/{proj_a_id}/dashboard", headers=headers_b)
    assert res_cross_dash.status_code == 404

    # --- VERIFY ASSET LIST & DETAIL ISOLATION ---
    assets_a = client.get("/api/v1/assets", headers=headers_a).get_json()["assets"]
    assets_b = client.get("/api/v1/assets", headers=headers_b).get_json()["assets"]

    assert len(assets_a) == 1
    assert assets_a[0]["name"] == "alpha-server.com"

    assert len(assets_b) == 1
    assert assets_b[0]["name"] == "beta-vault.com"

    res_cross_asset = client.get(f"/api/v1/assets/{asset_a_id}", headers=headers_b)
    assert res_cross_asset.status_code == 404

    # --- VERIFY STATS ISOLATION ---
    stats_a = client.get("/api/v1/stats", headers=headers_a).get_json()["stats"]
    stats_b = client.get("/api/v1/stats", headers=headers_b).get_json()["stats"]

    assert stats_a["total_assets"] == 1
    assert stats_b["total_assets"] == 1

    # --- VERIFY DELETION ISOLATION ---
    res_del_cross = client.delete(f"/api/v1/projects/{proj_a_id}?force=true", headers=headers_b)
    assert res_del_cross.status_code == 404

    # Project A still exists for User A
    res_check_a = client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_a)
    assert res_check_a.status_code == 200
