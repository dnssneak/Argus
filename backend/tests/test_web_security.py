import pytest
from unittest.mock import MagicMock, patch
from web_security import WebSecurityEngine


def test_web_security_headers_missing():
    engine = WebSecurityEngine("example.com")
    headers = {"Server": "nginx", "Content-Type": "text/html"}
    sec_data, findings = engine.analyze_security_headers(headers, "https://example.com")

    assert sec_data["Content-Security-Policy"]["status"] == "Missing"
    assert sec_data["Strict-Transport-Security"]["status"] == "Missing"
    assert sec_data["X-Content-Type-Options"]["status"] == "Missing"
    assert len(findings) >= 5


def test_web_security_headers_present():
    engine = WebSecurityEngine("example.com")
    headers = {
        "Content-Security-Policy": "default-src 'self'",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=()"
    }
    sec_data, findings = engine.analyze_security_headers(headers, "https://example.com")

    assert sec_data["Content-Security-Policy"]["status"] == "Present"
    assert sec_data["Strict-Transport-Security"]["status"] == "Present"
    assert sec_data["X-Frame-Options"]["status"] == "Present"
    # No missing header findings should be created
    assert len(findings) == 0


def test_cookie_security_analysis():
    engine = WebSecurityEngine("example.com")

    mock_cookie = MagicMock()
    mock_cookie.name = "session_id"
    mock_cookie.value = "abc123secret"
    mock_cookie.secure = False
    mock_cookie.has_nonstandard_attr.return_value = False
    mock_cookie.get_nonstandard_attr.return_value = None
    mock_cookie.domain = "example.com"
    mock_cookie.path = "/"
    mock_cookie.expires = None

    cookies_list, findings = engine.analyze_cookies([mock_cookie], {})
    assert len(cookies_list) == 1
    assert cookies_list[0]["name"] == "session_id"
    assert cookies_list[0]["secure"] is False
    assert cookies_list[0]["httponly"] is False

    # Should produce missing HttpOnly / Secure findings
    assert len(findings) >= 1
    assert "Missing" in findings[0]["title"]


def test_cors_analysis_wildcard_credentials():
    engine = WebSecurityEngine("example.com")
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true"
    }

    with patch("requests.get") as mock_get:
        mock_r = MagicMock()
        mock_r.headers = {}
        mock_get.return_value = mock_r

        cors_info, findings = engine.analyze_cors("https://example.com", headers)
        assert cors_info["allow_origin"] == "*"
        assert cors_info["allow_credentials"] is True
        assert any("Wildcard" in f["title"] for f in findings)


def test_expanded_web_fingerprint():
    engine = WebSecurityEngine("example.com")
    headers = {"Server": "nginx/1.20.1", "X-Powered-By": "Express"}
    html = "<html><head><meta name='generator' content='WordPress 6.2'></head><body><div id='__next'></div></body></html>"

    techs = engine.expand_web_fingerprint(None, html, headers, [])
    tech_names = [t["name"] for t in techs]

    assert "nginx" in tech_names
    assert "WordPress" in tech_names
    assert "Next.js" in tech_names
