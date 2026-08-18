import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import Base
from models.models import Project, Asset, Service, Technology, Finding, Relationship, Scan


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_project_creation(db_session):
    project = Project(name="Test Assessment", description="UnitTest scope")
    db_session.add(project)
    db_session.commit()

    saved = db_session.query(Project).filter_by(name="Test Assessment").first()
    assert saved is not None
    assert saved.id is not None
    assert saved.description == "UnitTest scope"
    assert saved.to_dict()["asset_count"] == 0


def test_asset_and_service_relationship(db_session):
    project = Project(name="Project Alpha")
    db_session.add(project)
    db_session.commit()

    asset = Asset(
        project_id=project.id,
        name="api.alpha.org",
        asset_type="Domain",
        ip_address="10.0.0.5",
        risk_score=85
    )
    db_session.add(asset)
    db_session.commit()

    service = Service(
        asset_id=asset.id,
        port=443,
        protocol="tcp",
        service_name="HTTPS",
        version="OpenSSL 1.1.1"
    )
    tech = Technology(
        asset_id=asset.id,
        name="Nginx",
        version="1.21.0",
        category="Web Server"
    )
    finding = Finding(
        asset_id=asset.id,
        title="SSL Expiration Warning",
        severity="Medium",
        risk_score=45,
        description="Certificate expires in less than 7 days"
    )
    db_session.add_all([service, tech, finding])
    db_session.commit()

    retrieved = db_session.get(Asset, asset.id)
    assert len(retrieved.services) == 1
    assert retrieved.services[0].port == 443
    assert len(retrieved.technologies) == 1
    assert retrieved.technologies[0].name == "Nginx"
    assert len(retrieved.findings) == 1
    assert retrieved.findings[0].severity == "Medium"
    assert retrieved.to_dict()["risk_score"] == 85


def test_cascade_delete(db_session):
    project = Project(name="Project to Delete")
    db_session.add(project)
    db_session.commit()

    asset = Asset(project_id=project.id, name="doomed.com")
    db_session.add(asset)
    db_session.commit()

    service = Service(asset_id=asset.id, port=80, service_name="HTTP")
    db_session.add(service)
    db_session.commit()

    # Delete project
    db_session.delete(project)
    db_session.commit()

    assert db_session.query(Asset).filter_by(name="doomed.com").first() is None
    assert db_session.query(Service).filter_by(port=80).first() is None
