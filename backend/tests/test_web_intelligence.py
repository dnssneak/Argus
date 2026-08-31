import pytest
from unittest.mock import MagicMock, patch
from web_intelligence import WebIntelligenceEngine


def test_web_intelligence_initialization():
    engine = WebIntelligenceEngine("https://example.com/about")
    assert engine.domain == "example.com"
    assert engine.url.startswith("https://example.com")


def test_email_pattern_detection_and_classification():
    engine = WebIntelligenceEngine("example.com")
    active_emails = [
        {"email": "john.doe@example.com", "source": "https://example.com/team", "module": "Web Scraping"},
        {"email": "jane.smith@example.com", "source": "https://example.com/about", "module": "Web Scraping"},
        {"email": "support@example.com", "source": "https://example.com/contact", "module": "Web Scraping"},
        {"email": "security@example.com", "source": "https://example.com/security", "module": "Web Scraping"},
    ]
    historical_emails = [
        {"email": "old.contact@example.com", "source": "Historical Archive (2021)", "module": "Historical Archive Intelligence", "is_historical": True}
    ]

    analyzed, patterns = engine._analyze_emails(active_emails, historical_emails)

    # Check pattern detection
    assert "first.last@example.com" in patterns

    # Check email classification
    email_dict = {e["email"]: e for e in analyzed}
    assert email_dict["support@example.com"]["category"] == "Role-Based Address"
    assert email_dict["support@example.com"]["role_category"] == "Support"
    assert email_dict["security@example.com"]["role_category"] == "Security"
    assert email_dict["john.doe@example.com"]["category"] == "Personal / Employee Address"

    # Check source tracking & historical flag
    assert email_dict["old.contact@example.com"]["is_historical"] is True
    assert "Historical Archive" in email_dict["old.contact@example.com"]["source"]
    assert email_dict["john.doe@example.com"]["is_historical"] is False


def test_document_metadata_extraction():
    engine = WebIntelligenceEngine("example.com")
    docs = [
        {
            "filename": "annual-report.pdf",
            "file_type": "PDF",
            "url": "https://example.com/docs/annual-report.pdf",
            "title": "Annual Report 2024",
            "source": "https://example.com/docs"
        }
    ]

    with patch("requests.head") as mock_head:
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.headers = {
            "Last-Modified": "Wed, 15 May 2024 10:00:00 GMT",
            "Server": "Apache/2.4.41"
        }
        mock_head.return_value = mock_r

        docs_with_meta = engine._extract_document_metadata(docs)
        assert len(docs_with_meta) == 1
        doc = docs_with_meta[0]
        assert doc["filename"] == "annual-report.pdf"
        assert doc["file_type"] == "PDF"
        assert doc["metadata"]["created"] == "Wed, 15 May 2024 10:00:00 GMT"
        assert doc["metadata"]["software"] == "Apache/2.4.41"
        assert doc["source"] == "https://example.com/docs"


def test_archive_intelligence_parsing():
    engine = WebIntelligenceEngine("example.com")

    mock_cdx_data = [
        ["original", "timestamp", "mimetype", "statuscode"],
        ["https://old.example.com/admin", "20210510120000", "text/html", "200"],
        ["https://example.com/mailto:legacy@example.com", "20220301000000", "text/html", "200"]
    ]

    with patch("requests.get") as mock_get:
        mock_r = MagicMock()
        mock_r.status_code = 200
        mock_r.json.return_value = mock_cdx_data
        mock_get.return_value = mock_r

        archive_res = engine._archive_intelligence()
        assert len(archive_res["historical_urls"]) == 2
        assert len(archive_res["subdomains"]) >= 1
        subdom_names = [s["subdomain"] for s in archive_res["subdomains"]]
        assert "old.example.com" in subdom_names
        assert any(h["is_historical"] for h in archive_res["historical_urls"])
