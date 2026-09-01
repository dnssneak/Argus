#!/usr/bin/env python3
"""
Unit tests for ReportGenerator (Module 6) and Report API Endpoints.
Verifies report creation, target formatting, section rendering, and HTTP download endpoints.
"""

import os
import pytest
from report import ReportGenerator


@pytest.fixture
def mock_full_scan_data():
    return {
        "target": "example.com",
        "system_info": {
            "operating_system": "Windows 11 Security Edition",
            "hostname": "ARGUS-NODE-01",
            "current_user": "analyst",
            "local_ip": "192.168.1.50",
            "public_ip": "203.0.113.10",
            "network_interfaces": [{"name": "eth0", "ip": "192.168.1.50"}]
        },
        "recon_data": {
            "target": "example.com",
            "whois": {"applicable": True, "registrar": "Example Registrar LLC", "creation_date": "2020-01-01"},
            "dns": {"applicable": True, "records": {"a": ["93.184.216.34"], "mx": ["mail.example.com"]}},
            "reverse_dns": {"applicable": True, "hostname": "example.com"},
            "ip_geolocation": {"applicable": True, "ip_address": "93.184.216.34", "country": "United States"},
            "http_headers": {"status_code": 200, "server": "nginx/1.18.0", "security_headers": {"Strict-Transport-Security": "max-age=31536000"}}
        },
        "scan_data": {
            "target": "example.com",
            "host_status": "Up",
            "scan_status": "Completed",
            "open_ports": [{"port": 80, "protocol": "TCP", "state": "Open"}, {"port": 443, "protocol": "TCP", "state": "Open"}],
            "services": [{"port": 80, "protocol": "TCP", "name": "http", "version": "nginx/1.18.0"}, {"port": 443, "protocol": "TCP", "name": "https", "version": "OpenSSL 1.1.1"}]
        },
        "fingerprint_data": {
            "target": "example.com",
            "tech_stack": {"web_server": "nginx", "backend": "Python/Flask", "frontend_frameworks": "Bootstrap 5"},
            "metadata": {"title": "Example Domain", "description": "Illustrative domain"},
            "contacts_and_links": {"emails": ["contact@example.com"], "internal_links_count": 12, "external_links_count": 4}
        },
        "subdomain_data": {
            "target": "example.com",
            "total_found": 3,
            "subdomains": [
                {"subdomain": "api.example.com", "status": "Active", "ip_address": "93.184.216.35"},
                {"subdomain": "dev.example.com", "status": "Active", "ip_address": "93.184.216.36"},
                {"subdomain": "stage.example.com", "status": "Inactive", "ip_address": "Not Resolved"}
            ]
        },
        "web_security_data": {
            "target": "example.com",
            "security_headers": {"Content-Security-Policy": {"status": "Missing"}, "X-Frame-Options": {"status": "Present"}},
            "ssl": {"certificate_valid": True, "issuer": "Let's Encrypt Authority X3", "tls_versions": ["TLSv1.2", "TLSv1.3"]},
            "cors": {"status": "Wildcard Allowed", "allow_origin": "*"},
            "http_methods": {"potentially_risky": ["PUT", "DELETE"]},
            "directory_discovery": [{"path": "/admin", "status_code": 403}, {"path": "/.git/HEAD", "status_code": 200}],
            "findings": [
                {"title": "Exposed Git Repository", "severity": "Critical", "cvss_score": 9.8, "description": "Public access to /.git directory"},
                {"title": "Wildcard CORS Policy", "severity": "Medium", "cvss_score": 5.3, "description": "Access-Control-Allow-Origin: *"}
            ],
            "nikto_scan": {"findings": [{"description": "Server leaks inode info", "uri": "/"}]}
        },
        "web_intelligence_data": {
            "target": "example.com",
            "emails": [
                {"email": "admin@example.com", "role_category": "IT / Admin", "source": "Web Scrape", "is_historical": False},
                {"email": "support@example.com", "role_category": "Support", "source": "Wayback Archive", "is_historical": True}
            ],
            "email_patterns": ["{first}.{last}@example.com"],
            "social_links": [{"platform": "Twitter", "url": "https://twitter.com/example"}],
            "documents": [{"filename": "security-policy.pdf", "file_type": "PDF", "title": "Security Policy", "metadata": {"author": "SecTeam"}}],
            "historical_urls": [{"url": "https://example.com/old-portal", "timestamp": "2021"}]
        }
    }


def test_txt_report_generation(mock_full_scan_data):
    generator = ReportGenerator(
        system_info=mock_full_scan_data["system_info"],
        recon_data=mock_full_scan_data["recon_data"],
        scan_data=mock_full_scan_data["scan_data"],
        fingerprint_data=mock_full_scan_data["fingerprint_data"],
        subdomain_data=mock_full_scan_data["subdomain_data"],
        web_security_data=mock_full_scan_data["web_security_data"],
        web_intelligence_data=mock_full_scan_data["web_intelligence_data"],
        target=mock_full_scan_data["target"]
    )

    filepath, filename = generator.generate_txt()
    assert os.path.exists(filepath)
    assert filename.endswith(".txt")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Target Host : example.com" in content
    assert "[ 1. SYSTEM INFORMATION ]" in content
    assert "[ 2. INFORMATION GATHERING (RECON) ]" in content
    assert "[ 3. NETWORK SCAN (NMAP) ]" in content
    assert "[ 4. WEBSITE FINGERPRINTING & SCRAPING ]" in content
    assert "[ 5. SUBDOMAIN FINDER ]" in content
    assert "[ 6. WEB SECURITY ENGINE AUDIT ]" in content
    assert "[ 7. WEB INTELLIGENCE & OSINT ]" in content
    assert "[ 8. EXECUTIVE SUMMARY & OVERVIEW ]" in content
    assert "Exposed Git Repository" in content
    assert "admin@example.com" in content
    assert "api.example.com" in content

    # Cleanup
    os.remove(filepath)


def test_html_report_generation(mock_full_scan_data):
    generator = ReportGenerator(
        system_info=mock_full_scan_data["system_info"],
        recon_data=mock_full_scan_data["recon_data"],
        scan_data=mock_full_scan_data["scan_data"],
        fingerprint_data=mock_full_scan_data["fingerprint_data"],
        subdomain_data=mock_full_scan_data["subdomain_data"],
        web_security_data=mock_full_scan_data["web_security_data"],
        web_intelligence_data=mock_full_scan_data["web_intelligence_data"],
        target=mock_full_scan_data["target"]
    )

    filepath, filename = generator.generate_html()
    assert os.path.exists(filepath)
    assert filename.endswith(".html")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "<title>Argus Security Assessment Report - example.com</title>" in content
    assert "System Information" in content
    assert "Information Gathering" in content
    assert "Network Scan" in content
    assert "Website Fingerprinting & Scraping" in content
    assert "Subdomain Finder" in content
    assert "Web Security Engine Analysis" in content
    assert "Web Intelligence Engine (OSINT)" in content
    assert "Executive Summary" in content
    assert "Exposed Git Repository" in content
    assert "admin@example.com" in content
    assert "api.example.com" in content

    # Cleanup
    os.remove(filepath)


def test_report_generation_with_minimal_data():
    """Test report generation when only subdomain and explicit target are provided."""
    sub_data = {
        "target": "targetdomain.org",
        "total_found": 1,
        "subdomains": [{"subdomain": "sub.targetdomain.org", "status": "Active", "ip_address": "1.2.3.4"}]
    }

    generator = ReportGenerator(
        subdomain_data=sub_data,
        target="targetdomain.org"
    )

    filepath, filename = generator.generate_html()
    assert os.path.exists(filepath)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert "targetdomain.org" in content
    assert "Subdomain Finder" in content

    os.remove(filepath)


def test_download_report_endpoint_with_client():
    """Test the Flask API download endpoint to ensure file is served with status 200."""
    from app import app
    from db.database import SessionLocal
    from models.models import Project, Scan

    client = app.test_client()
    db = SessionLocal()

    try:
        # Create test project and scan
        proj = Project(name="Test Report Project", owner_id="local-user")
        db.add(proj)
        db.commit()
        db.refresh(proj)

        scan = Scan(project_id=proj.id, target="download-test.com", scan_type="Full", status="completed")
        db.add(scan)
        db.commit()
        db.refresh(scan)

        # Generate report file using ReportGenerator
        gen = ReportGenerator(target="download-test.com")
        filepath, filename = gen.generate_html(filename="test_download_file.html")

        # Request download via API endpoint
        response = client.get(f"/api/v1/projects/{proj.id}/scans/{scan.id}/download-report?filename={filename}")
        assert response.status_code == 200
        assert b"Argus Security Assessment Report" in response.data

        # Cleanup created test records
        response.close()
        db.delete(scan)
        db.delete(proj)
        db.commit()
    finally:
        db.close()
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
