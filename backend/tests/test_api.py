import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db.database import init_db, SessionLocal
from models.models import Project, Asset, Finding


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import db.database as db_module

@pytest.fixture
def client():
    """Create Flask test client with isolated in-memory test database."""
    app.config["TESTING"] = True
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    db_module.Base.metadata.create_all(bind=test_engine)
    
    # Store original engine and SessionLocal
    orig_engine = db_module.engine
    orig_sessionmaker = db_module.SessionLocal

    # Rebind db module to test engine
    db_module.engine = test_engine
    db_module.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with app.test_client() as client:
        yield client

    # Restore original engine
    db_module.engine = orig_engine
    db_module.SessionLocal = orig_sessionmaker


def test_list_and_create_projects(client):
    # Test GET empty projects
    res = client.get("/api/v1/projects")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    # Test POST create project
    payload = {"name": "Audit 2026", "description": "Enterprise audit scope"}
    res = client.post("/api/v1/projects", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["project"]["name"] == "Audit 2026"
    project_id = data["project"]["id"]

    # Test GET single project detail
    res = client.get(f"/api/v1/projects/{project_id}")
    assert res.status_code == 200
    assert res.get_json()["project"]["name"] == "Audit 2026"


def test_create_and_query_assets(client):
    # Create project first
    res_p = client.post("/api/v1/projects", json={"name": "Network Scope"})
    project_id = res_p.get_json()["project"]["id"]

    # Register Asset
    asset_data = {
        "name": "vpn.company.com",
        "asset_type": "Domain",
        "ip_address": "192.168.100.1",
        "risk_score": 90,
        "project_id": project_id
    }
    res_a = client.post("/api/v1/assets", json=asset_data)
    assert res_a.status_code == 201
    asset_id = res_a.get_json()["asset"]["id"]

    # List Assets
    res_list = client.get(f"/api/v1/assets?project_id={project_id}")
    assert res_list.status_code == 200
    data = res_list.get_json()
    assert data["count"] == 1
    assert data["assets"][0]["name"] == "vpn.company.com"

    # Detail Asset
    res_detail = client.get(f"/api/v1/assets/{asset_id}")
    assert res_detail.status_code == 200
    assert res_detail.get_json()["asset"]["ip_address"] == "192.168.100.1"


def test_security_stats_api(client):
    # Query stats endpoint
    res = client.get("/api/v1/stats")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "total_assets" in data["stats"]
    assert "findings_summary" in data["stats"]
