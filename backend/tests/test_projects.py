import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db.database import init_db, SessionLocal
from models.models import Project, Target, Asset, Finding, Scan
from services.project_service import ProjectService


@pytest.fixture
def db():
    """Create fresh database session for unit testing."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    init_db()
    session = SessionLocal()
    # Clear tables
    session.query(Finding).delete()
    session.query(Asset).delete()
    session.query(Scan).delete()
    session.query(Target).delete()
    session.query(Project).delete()
    session.commit()
    yield session
    session.close()


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    init_db()
    with app.test_client() as client:
        yield client


def test_project_validation_and_creation(db):
    # Test empty name validation
    with pytest.raises(ValueError, match="name is required"):
        ProjectService.create_project(db, name="")

    # Test valid creation
    project = ProjectService.create_project(
        db=db,
        name="ACME Security Assessment",
        description="External attack surface assessment",
        status="ACTIVE",
        owner_id="user-123"
    )
    assert project.id is not None
    assert project.name == "ACME Security Assessment"
    assert project.status == "ACTIVE"
    assert project.owner_id == "user-123"
    assert any(a.action == "Project Created" for a in project.activities)


def test_project_search_and_status_filtering(db):
    p1 = ProjectService.create_project(db, name="Alpha Engagement", status="ACTIVE")
    p2 = ProjectService.create_project(db, name="Beta Audit", status="ARCHIVED")
    p3 = ProjectService.create_project(db, name="Gamma Infrastructure", status="ACTIVE")

    # Search filter
    results = ProjectService.list_projects(db, search="Beta")
    assert len(results) == 1
    assert results[0].name == "Beta Audit"

    # Status filter ACTIVE
    active_projects = ProjectService.list_projects(db, status="ACTIVE")
    assert len(active_projects) == 2

    # Status filter ARCHIVED
    archived_projects = ProjectService.list_projects(db, status="ARCHIVED")
    assert len(archived_projects) == 1
    assert archived_projects[0].name == "Beta Audit"


def test_project_target_relationship(db):
    project = ProjectService.create_project(db, name="Target Test Project")
    target1 = ProjectService.add_target(db, project.id, "example.com", "Domain")
    target2 = ProjectService.add_target(db, project.id, "192.168.10.0/24", "CIDR")

    assert target1.id is not None
    assert target2.target_type == "CIDR"

    dashboard_data = ProjectService.get_project_dashboard(db, project.id)
    assert dashboard_data["stats"]["targets"] == 2
    assert len(dashboard_data["targets"]) == 2


def test_project_update_and_archive(db):
    project = ProjectService.create_project(db, name="Update Test")
    updated = ProjectService.update_project(db, project.id, name="Renamed Assessment", description="New details")
    assert updated.name == "Renamed Assessment"

    archived = ProjectService.archive_project(db, project.id)
    assert archived.status == "ARCHIVED"


def test_delete_protection(db):
    project = ProjectService.create_project(db, name="Protected Project")
    ProjectService.add_target(db, project.id, "target.org")

    # Attempt deletion without force
    success, msg, counts = ProjectService.delete_project(db, project.id, force=False)
    assert success is False
    assert "Delete Protection Active" in msg
    assert counts["targets"] == 1

    # Force deletion
    success, msg, counts = ProjectService.delete_project(db, project.id, force=True)
    assert success is True
    assert db.get(Project, project.id) is None


def test_project_api_endpoints(client):
    # Test POST /api/v1/projects
    res = client.post("/api/v1/projects", json={
        "name": "API Scope Test",
        "description": "API test details",
        "status": "ACTIVE"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    project_id = data["project"]["id"]

    # Test POST add target
    res_t = client.post(f"/api/v1/projects/{project_id}/targets", json={
        "target": "api.test.org",
        "target_type": "Subdomain"
    })
    assert res_t.status_code == 201
    assert res_t.get_json()["target"]["target"] == "api.test.org"

    # Test GET project dashboard
    res_dash = client.get(f"/api/v1/projects/{project_id}/dashboard")
    assert res_dash.status_code == 200
    dash_data = res_dash.get_json()["data"]
    assert dash_data["stats"]["targets"] == 1

    # Test POST archive
    res_arc = client.post(f"/api/v1/projects/{project_id}/archive")
    assert res_arc.status_code == 200
    assert res_arc.get_json()["project"]["status"] == "ARCHIVED"
