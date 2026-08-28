import pytest
from unittest.mock import patch, MagicMock
from services.ai_advisor import AIRemediationAdvisor
from models.models import Finding, Asset, Project
from services.finding_correlator import FindingCorrelator

@patch("services.ai_advisor.requests.post")
def test_heuristic_remediation_enhancement(mock_post):
    """Test heuristic AI advisor preserves baseline check recommendations."""
    mock_post.side_effect = Exception("Offline test")
    finding_dict = {
        "title": "Exposed Service: HTTP (Port 80)",
        "severity": "Medium",
        "port": 80,
        "service_name": "HTTP",
        "asset_name": "google.com",
        "exposure": "Internet-Facing"
    }
    asset_dict = {"name": "google.com", "exposure": "Internet-Facing"}
    baseline = "Enforce HTTPS with TLS 1.3"

    rec_text, is_enhanced = AIRemediationAdvisor.enhance_or_generate_remediation(finding_dict, asset_dict, baseline)
    assert is_enhanced is False
    assert "Enforce HTTPS with TLS 1.3" in rec_text

@patch("services.ai_advisor.requests.post")
def test_heuristic_remediation_novel_unseen_finding(mock_post):
    """Test heuristic AI advisor synthesizes fix for unseen findings with no baseline."""
    mock_post.side_effect = Exception("Offline test")
    finding_dict = {
        "title": "Exposed Source Control Subdomain (git.internal.org)",
        "severity": "High",
        "asset_name": "git.internal.org",
        "exposure": "Internal"
    }
    asset_dict = {"name": "git.internal.org", "exposure": "Internal"}

    rec_text, is_enhanced = AIRemediationAdvisor.enhance_or_generate_remediation(finding_dict, asset_dict, baseline_recommendation=None)
    assert is_enhanced is True
    assert "source control" in rec_text.lower() or "git" in rec_text.lower() or "internal" in rec_text.lower()

@patch("services.ai_advisor.requests.post")
def test_gemini_api_call(mock_post, monkeypatch):
    """Test live LLM Gemini API integration when GEMINI_API_KEY is configured."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_mock_key_123")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "1. Isolate port 80 behind WAF.\n2. Mandate HTTP Strict Transport Security."}]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    finding_dict = {"title": "Exposed Port 80", "severity": "Medium", "port": 80}
    rec_text, is_enhanced = AIRemediationAdvisor.enhance_or_generate_remediation(finding_dict)
    
    assert is_enhanced is True
    assert "Isolate port 80" in rec_text
    assert mock_post.called

@patch("services.ai_advisor.requests.post")
def test_openrouter_api_call(mock_post, monkeypatch):
    """Test live LLM OpenRouter API integration with gemma-3-27b-it:free."""
    monkeypatch.setenv("API_KEY", "test_mock_key_999")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "1. Apply strict access control to port 80.\n2. Configure HTTPS certificate."
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    finding_dict = {"title": "Exposed Port 80", "severity": "Medium", "port": 80}
    rec_text, is_enhanced = AIRemediationAdvisor.enhance_or_generate_remediation(finding_dict)
    
    assert is_enhanced is True
    assert "Apply strict access control" in rec_text
    assert mock_post.called

@pytest.fixture
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import db.database as db_module
    
    engine = create_engine("sqlite:///:memory:")
    db_module.Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_finding_correlator_automatic_ai_pipeline(db_session):
    """Test FindingCorrelator automatically processes findings through AI Remediation Advisor."""
    project = Project(name="AI Advisory Scope")
    db_session.add(project)
    db_session.commit()

    asset = Asset(project_id=project.id, name="git.example.com", asset_type="Subdomain", exposure="Internet-Facing")
    db_session.add(asset)
    db_session.commit()

    finding = Finding(
        asset_id=asset.id,
        title="Exposed Source Control Subdomain (git.example.com)",
        severity="High",
        cvss_score=7.5,
        description="Source control portal exposed on internet perimeter."
    )
    db_session.add(finding)
    db_session.commit()

    # Correlate finding
    FindingCorrelator.correlate_and_prioritize_finding(db_session, finding, asset)
    db_session.refresh(finding)

    assert finding.recommendation is not None
    assert len(finding.recommendation) > 15
    assert finding.ai_enhanced is True
