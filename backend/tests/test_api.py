import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db.database import init_db, SessionLocal
from models.models import Project, Asset, Finding


@pytest.fixture
def client():
    """Create Flask test client with fresh test database."""
    app.config["TESTING"] = True
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    init_db()
    with app.test_client() as client:
        # Clear database tables before test
        db = SessionLocal()
        try:
            db.query(Finding).delete()
            db.query(Asset).delete()
            db.query(Project).delete()
            db.commit()
        finally:
            db.close()
        yield client


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
