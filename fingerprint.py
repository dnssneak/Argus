#!/usr/bin/env python3
"""
Module 4: Website Fingerprinting
Performs passive reconnaissance to identify technologies used by a target website.
"""

import socket
import ssl
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse


class WebsiteFingerprinter:
    """
    Identifies the web server, backend language, CMS, frontend framework,
    CDN, and HTTP protocol version of a target website.
    """

    def __init__(self, target):
        self.raw_target = target.strip()
        self.url = self._normalize_url(self.raw_target)
        self.domain = self._extract_domain(self.url)

    def _normalize_url(self, url):
        # Ensure scheme is present
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return "http://" + url
        return url

    def _extract_domain(self, url):
        try:
            parsed = urlparse(url)
            # Remove www. prefix if present, but keep subdomain if any
            netloc = parsed.netloc or parsed.path.split("/")[0]
            # Strip port if any
            return netloc.split(":")[0]
        except Exception:
            return url

    def collect(self):
        """Runs fingerprinting checks on the target URL."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        
        try:
            # Perform HTTP request
            r = requests.get(self.url, headers=headers, timeout=10, allow_redirects=True)
            html = r.text
            response_headers = r.headers
            cookies = r.cookies
            
            # Update target to final domain in case of redirects
            self.domain = self._extract_domain(r.url)
        except requests.exceptions.Timeout:
            return {
                "target": self.raw_target,
                "error": "Connection timed out. Target host may be down or unreachable."
            }
        except requests.exceptions.ConnectionError:
            return {
                "target": self.raw_target,
                "error": "Connection failed. Host refused connection or DNS resolution failed."
            }
        except Exception as e:
            return {
                "target": self.raw_target,
                "error": f"Failed to retrieve website fingerprint: {str(e)}"
            }

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            soup = None

        web_server = self._detect_web_server(response_headers)
        backend = self._detect_backend(response_headers, cookies, html)
        cms = self._detect_cms(soup, html, response_headers)
        frontend = self._detect_frontend(soup, html)
        cdn = self._detect_cdn(response_headers)
        http_version = self._detect_http_version(self.domain)

        return {
            "target": self.domain,
            "web_server": web_server,
            "backend": backend,
            "cms": cms,
            "frontend": frontend,
            "cdn": cdn,
            "http_version": http_version
        }

    def _detect_web_server(self, headers):
        server = headers.get("Server", "")
        if server:
            return server
        
        # Strip indicator fallbacks or standard server headers
        # E.g. Check for specific Server tokens
        return "Unknown"

    def _detect_backend(self, headers, cookies, html):
        # 1. X-Powered-By
        powered_by = headers.get("X-Powered-By", "")
        if powered_by:
            return powered_by

        # 2. Check standard cookies
        cookie_names = [c.name for c in cookies]
        for name in cookie_names:
            name_lower = name.lower()
            if "phpsessid" in name_lower:
                return "PHP"
            if "jsessionid" in name_lower:
                return "Java"
            if "aspsessionid" in name_lower or "asp.net_sessionid" in name_lower:
                return "ASP.NET"
            if "django" in name_lower:
                return "Python (Django)"
            if "next-auth" in name_lower:
                return "Node.js (Next.js)"

        # 3. Check for specific HTTP headers
        if "X-AspNet-Version" in headers or "X-AspNetMvc-Version" in headers:
            return "ASP.NET"

        # 4. Check HTML structure/signatures
        if "wp-content" in html or "wp-includes" in html:
            return "PHP"
            
        return "Unknown"

    def _detect_cms(self, soup, html, headers):
        html_lower = html.lower()

        # 1. Check meta generator tag
        if soup:
            meta_gen = soup.find("meta", attrs={"name": "generator"})
            if meta_gen:
                content = meta_gen.get("content", "").lower()
                if "wordpress" in content:
                    # Try to extract version
                    v_match = re.search(r"wordpress\s*([\d\.]+)", content)
                    return f"WordPress {v_match.group(1)}" if v_match else "WordPress"
                if "joomla" in content:
                    return "Joomla"
                if "drupal" in content:
                    return "Drupal"
                if "ghost" in content:
                    return "Ghost"
                if "shopify" in content:
                    return "Shopify"

        # 2. Check path signatures
        if "wp-content" in html_lower or "wp-includes" in html_lower:
            return "WordPress"
        if "joomla" in html_lower or "media/system/js" in html_lower:
            return "Joomla"
        if "sites/default" in html_lower or "drupal.js" in html_lower:
            return "Drupal"
        if "cdn.shopify.com" in html_lower or "shopify.theme" in html_lower:
            return "Shopify"

        # 3. Check Shopify response headers
        if "x-shopify-stage" in headers or "x-shopid" in headers:
            return "Shopify"

        return "None Detected"

    def _detect_frontend(self, soup, html):
        detected = []
        html_lower = html.lower()

        # 1. Detect Bootstrap
        if "bootstrap" in html_lower:
            # Extract version from URL paths like ...bootstrap/5.3.0/...
            version_match = re.search(r"bootstrap/(\d+\.\d+\.\d+)", html_lower)
            if version_match:
                detected.append(f"Bootstrap {version_match.group(1)}")
            else:
                detected.append("Bootstrap")

        # 2. Detect jQuery
        if "jquery" in html_lower or "jq" in html_lower:
            version_match = re.search(r"jquery/(\d+\.\d+\.\d+)", html_lower)
            if version_match:
                detected.append(f"jQuery {version_match.group(1)}")
            else:
                detected.append("jQuery")

        # 3. Detect React
        if "data-reactroot" in html_lower or "react.production" in html_lower or "_reactlisten" in html_lower:
            detected.append("React")

        # 4. Detect Angular
        if "ng-version" in html_lower or "ng-app" in html_lower or "ng-controller" in html_lower:
            # Extract version
            v_match = re.search(r"ng-version=\"([^\"]+)\"", html_lower)
            if v_match:
                detected.append(f"Angular {v_match.group(1)}")
            else:
                detected.append("Angular")

        # 5. Detect Vue.js
        if "vue.js" in html_lower or "vue.min.js" in html_lower or "v-bind" in html_lower or "v-out" in html_lower:
            detected.append("Vue.js")

        if not detected:
            return "None Detected"
        return ", ".join(detected)

    def _detect_cdn(self, headers):
        # 1. Cloudflare
        server = headers.get("Server", "").lower()
        if "cf-ray" in headers or server == "cloudflare":
            return "Cloudflare"

        # 2. Amazon CloudFront
        via = headers.get("Via", "").lower()
        if "x-amz-cf-id" in headers or "x-amz-cf-pop" in headers or "cloudfront" in via:
            return "Amazon CloudFront"

        # 3. Akamai
        x_cache = headers.get("X-Cache", "").lower()
        if "akamai" in x_cache or "akamaighost" in server:
            return "Akamai"

        # 4. Fastly
        if "fastly" in x_cache or "x-served-by" in headers:
            return "Fastly"

        return "None Detected"

    def _detect_http_version(self, domain):
        # Negotiate ALPN for SSL HTTP version detection
        try:
            context = ssl.create_default_context()
            context.set_alpn_protocols(["h3", "h2", "http/1.1"])
            
            # Resolve target to an IP address
            ip = socket.gethostbyname(domain)
            with socket.create_connection((ip, 443), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    negotiated = ssock.selected_alpn_protocol()
                    if negotiated == "h2":
                        return "HTTP/2"
                    elif negotiated == "h3":
                        return "HTTP/3"
                    elif negotiated == "http/1.1":
                        return "HTTP/1.1"
        except Exception:
            pass
        return "HTTP/1.1"
