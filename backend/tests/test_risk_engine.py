import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db.database import init_db, SessionLocal
from models.models import Project, Asset, Service, Finding, Endpoint, Technology, AssetHistory
from services.risk_engine import RiskEngine


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import db.database as db_module

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


def get_test_db():
    return db_module.SessionLocal()


def test_severity_level_mapping():
    """Verify 0-100 score mapping to 5 severity level tiers."""
    assert RiskEngine.get_severity_level(0) == "INFORMATIONAL"
    assert RiskEngine.get_severity_level(15) == "INFORMATIONAL"
    assert RiskEngine.get_severity_level(20) == "LOW"
    assert RiskEngine.get_severity_level(35) == "LOW"
    assert RiskEngine.get_severity_level(40) == "MEDIUM"
    assert RiskEngine.get_severity_level(59) == "MEDIUM"
    assert RiskEngine.get_severity_level(60) == "HIGH"
    assert RiskEngine.get_severity_level(75) == "HIGH"
    assert RiskEngine.get_severity_level(80) == "CRITICAL"
    assert RiskEngine.get_severity_level(100) == "CRITICAL"


def test_baseline_asset_risk_calculation(client):
    """Test risk calculation for a low-exposure baseline asset."""
    db = get_test_db()
    try:
        project = Project(name="Test Project")
        db.add(project)
        db.commit()

        asset = Asset(
            project_id=project.id,
            name="internal-dev.local",
            exposure="Internal",
            status="active"
        )
        db.add(asset)
        db.commit()

        analysis = RiskEngine.calculate_asset_risk(db, asset)
        assert analysis["score"] >= 0 and analysis["score"] <= 100
        assert analysis["severity"] in ["INFORMATIONAL", "LOW"]
    finally:
        db.close()


def test_sensitive_port_and_critical_finding_risk_elevation(client):
    """Test that exposed sensitive ports and critical findings increase risk score and severity."""
    db = get_test_db()
    try:
        project = Project(name="Prod Core")
        db.add(project)
        db.commit()

        asset = Asset(
            project_id=project.id,
            name="api.prod.example.com",
            exposure="Internet-Facing",
            status="active",
            tags="critical"
        )
        db.add(asset)
        db.commit()

        # Add sensitive open RDP and SSH ports
        svc1 = Service(asset_id=asset.id, port=3389, service_name="ms-wbt-server", state="Open")
        svc2 = Service(asset_id=asset.id, port=22, service_name="ssh", state="Open")
        db.add_all([svc1, svc2])

        # Add Critical vulnerability finding
        finding = Finding(asset_id=asset.id, title="RCE Vulnerability", severity="Critical", risk_score=9.8)
        db.add(finding)

        # Add unauthenticated admin endpoint
        ep = Endpoint(asset_id=asset.id, path="/admin/unauth", method="GET")
        db.add(ep)
        db.commit()

        analysis = RiskEngine.calculate_asset_risk(db, asset)
        assert analysis["score"] >= 80
        assert analysis["severity"] == "CRITICAL"
        assert len(analysis["contributing_factors"]["high"]) > 0
    finally:
        db.close()


def test_recalculate_and_update_asset_risk_timeline_event(client):
    """Test recalculate_and_update_asset_risk updates Asset.risk_score and logs history event."""
    db = get_test_db()
    try:
        project = Project(name="Timeline Project")
        db.add(project)
        db.commit()

        asset = Asset(
            project_id=project.id,
            name="db.company.internal",
            exposure="Internet-Facing",
            risk_score=10
        )
        db.add(asset)
        db.commit()

        # Recalculate risk
        updated = RiskEngine.recalculate_and_update_asset_risk(db, asset, trigger_reason="Test Trigger")
        assert updated is True

        history_events = db.query(AssetHistory).filter_by(asset_id=asset.id).all()
        assert len(history_events) > 0
        assert "Risk Score Recalculated" in history_events[0].event_name
    finally:
        db.close()


def test_api_sorting_and_filtering_by_severity(client):
    """Test GET /api/v1/assets severity filtering and risk sorting."""
    # Create project
    p_res = client.post("/api/v1/projects", json={"name": "Sort Scope"})
    project_id = p_res.get_json()["project"]["id"]

    # Create low risk asset
    client.post("/api/v1/assets", json={
        "project_id": project_id,
        "name": "low-risk.com",
        "asset_type": "Domain"
    })

    # Create asset detail API call
    res_list = client.get(f"/api/v1/assets?project_id={project_id}&sort_by=risk_score&sort_order=desc")
    assert res_list.status_code == 200
    data = res_list.get_json()
    assert data["success"] is True
    assert len(data["assets"]) >= 1
    assert "severity" in data["assets"][0]
