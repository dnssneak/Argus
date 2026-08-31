import pytest
from unittest.mock import MagicMock, patch
from web_security import WebSecurityEngine


def test_nikto_output_parsing():
    engine = WebSecurityEngine("https://example.com")
    raw_nikto_output = """
- Nikto v2.1.6
---------------------------------------------------------------------------
+ Target IP:          192.168.1.10
+ Target Hostname:    example.com
+ Target Port:        80
+ Server: Apache/2.4.41 (Ubuntu)
+ The anti-clickjacking X-Frame-Options header is not present.
+ The X-Content-Type-Options header is not set. This could allow the user agent to render the content of the site in a different fashion to the MIME type.
+ Entry '/.env' in web root contains sensitive environment credentials.
---------------------------------------------------------------------------
+ 1 host(s) tested
"""
    parsed = engine.parse_nikto_output(raw_nikto_output)

    assert parsed["server"] == "Apache/2.4.41 (Ubuntu)"
    assert len(parsed["findings"]) == 3

    titles = [f["title"] for f in parsed["findings"]]
    assert "Missing X-Frame-Options Security Header" in titles
    assert "Missing X-Content-Type-Options Security Header" in titles
    assert "Nikto: Potentially Exposed Sensitive Resource (/.env)" in titles

    for f in parsed["findings"]:
        assert f["discovery_source"] == "Nikto"


def test_nikto_fallback_mode():
    engine = WebSecurityEngine("https://example.com")
    fallback_res = engine._run_nikto_fallback("Executable not found")

    assert fallback_res["scan_status"] == "Completed (Integrated Fallback Engine)"
    assert len(fallback_res["observations"]) == 1
    assert "Nikto CLI unavailable" in fallback_res["observations"][0]["details"]
