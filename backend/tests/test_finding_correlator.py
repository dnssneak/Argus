import pytest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models.models import Project, Target, Asset, Finding, Scan
from services.finding_correlator import FindingCorrelator
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


def test_finding_priority_calculation_keeps_severity_separate(client):
    """Test that original finding severity is NEVER overwritten while calculating contextual priority."""
    db = get_test_db()
    try:
        project = Project(name="Test Security Campaign")
        db.add(project)
        db.commit()

        asset = Asset(
            project_id=project.id,
            name="api.example.com",
            asset_type="Domain",
            exposure="Internet-Facing",
            risk_score=91,
            tags="critical, high"
        )
        db.add(asset)
        db.commit()

        finding = Finding(
            asset_id=asset.id,
            title="Authentication Bypass",
            severity="High",
            cvss_score=8.8,
            risk_score=8,
            port=443,
            service_name="https",
            endpoint="/api/login"
        )
        db.add(finding)
        db.commit()

        # Correlate and calculate priority
        correlated = FindingCorrelator.correlate_and_prioritize_finding(db, finding, asset)

        # Severity MUST remain High
        assert correlated.severity == "High"
        # Contextual priority MUST be CRITICAL
        assert correlated.priority == "CRITICAL"
        assert correlated.priority_score >= 80

        # Verify explanation factors
        factors = json.loads(correlated.priority_explanation)
        assert any("High-severity finding" in f for f in factors)
        assert any("Internet-facing asset" in f for f in factors)
        assert any("Asset Risk Score: 91" in f for f in factors)
        assert any("High asset criticality" in f for f in factors)
        assert any("Affected public service / port: 443" in f for f in factors)
    finally:
        db.close()


def test_finding_lifecycle_across_scans(client):
    """Test finding lifecycle transition from NEW to RECURRING across multiple scans."""
    db = get_test_db()
    try:
        project = Project(name="Lifecycle Test Project")
        db.add(project)
        db.commit()

        asset = Asset(project_id=project.id, name="vpn.example.com", exposure="Internet-Facing")
        db.add(asset)
        db.commit()

        scan1 = Scan(project_id=project.id, target="vpn.example.com", status="completed")
        db.add(scan1)
        db.commit()

        finding = Finding(
            asset_id=asset.id,
            title="Remote Code Execution",
            severity="Critical",
            cvss_score=9.8
        )
        db.add(finding)
        db.commit()

        # First scan correlation pass
        FindingCorrelator.correlate_scan_findings(db, project.id, "vpn.example.com", scan1.id, {})
        db.refresh(finding)

        assert finding.lifecycle_status == "NEW"
        assert finding.first_scan_id == scan1.id
        assert finding.last_scan_id == scan1.id

        # Second scan correlation pass
        scan2 = Scan(project_id=project.id, target="vpn.example.com", status="completed")
        db.add(scan2)
        db.commit()

        FindingCorrelator.correlate_scan_findings(db, project.id, "vpn.example.com", scan2.id, {})
        db.refresh(finding)

        assert finding.lifecycle_status == "RECURRING"
        assert finding.first_scan_id == scan1.id
        assert finding.last_scan_id == scan2.id
    finally:
        db.close()


def test_findings_api_ordering_and_filtering(client):
    """Test GET /api/v1/findings API endpoint orders findings by contextual priority."""
    # Create project via client API
    p_res = client.post("/api/v1/projects", json={"name": "API Test Scope"})
    assert p_res.status_code == 201
    project_id = p_res.get_json()["project"]["id"]

    # Register assets via client API
    a1_res = client.post("/api/v1/assets", json={
        "project_id": project_id,
        "name": "critical.example.com",
        "asset_type": "Domain",
        "risk_score": 90
    })
    asset1_id = a1_res.get_json()["asset"]["id"]

    a2_res = client.post("/api/v1/assets", json={
        "project_id": project_id,
        "name": "internal.example.com",
        "asset_type": "Domain",
        "risk_score": 20
    })
    asset2_id = a2_res.get_json()["asset"]["id"]

    # Add findings via client API
    client.post(f"/api/v1/assets/{asset1_id}/findings", json={
        "title": "Crit Issue",
        "severity": "High",
        "risk_score": 9.0
    })

    client.post(f"/api/v1/assets/{asset2_id}/findings", json={
        "title": "Low Observation",
        "severity": "Low",
        "risk_score": 2.0
    })

    res = client.get(f"/api/v1/findings?project_id={project_id}")
    assert res.status_code == 200
    data = res.get_json()

    assert data["success"] is True
    assert data["count"] == 2

    findings = data["findings"]
    # First returned finding should be highest priority (CRITICAL/HIGH)
    assert findings[0]["title"] == "Crit Issue"
    assert findings[0]["priority"] in ["CRITICAL", "HIGH"]
    assert findings[0]["severity"] == "High"
    assert findings[0]["asset_name"] == "critical.example.com"
    assert len(findings[0]["priority_explanation"]) > 0
