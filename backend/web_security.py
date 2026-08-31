#!/usr/bin/env python3
"""
Phase 5: Dedicated Web Security Engine
Performs deep web security analysis:
- Security Header Analysis
- SSL/TLS Analysis
- Cookie Security Analysis
- CORS Analysis
- HTTP Methods Analysis
- Directory / Endpoint Discovery
- Expanded Web Fingerprinting
Integrates results and findings with Argus Assets, Findings, Scans, and Risk Engine.
"""

import socket
import ssl
import re
import urllib.parse
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup


class WebSecurityEngine:
    """
    Central Web Security Engine for Argus 2.0.
    Executes comprehensive security auditing modules against a target host/URL.
    """

    COMMON_PATHS = [
        "/admin", "/login", "/api", "/docs", "/uploads", "/backup",
        "/.env", "/.git", "/config", "/swagger", "/dashboard", "/actuator"
    ]

    SECURITY_HEADER_SPECS = {
        "Content-Security-Policy": {
            "name": "Content-Security-Policy",
            "missing_severity": "Medium",
            "cvss_score": 5.3,
            "desc": "Mitigates Cross-Site Scripting (XSS) and data injection attacks by restricting resources.",
            "rec": "Implement a strong Content-Security-Policy header defining trusted script, style, and frame sources."
        },
        "Strict-Transport-Security": {
            "name": "Strict-Transport-Security",
            "missing_severity": "Medium",
            "cvss_score": 5.3,
            "desc": "Enforces HTTPS connections and prevents SSL stripping attacks.",
            "rec": "Enable HSTS header: 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload'."
        },
        "X-Content-Type-Options": {
            "name": "X-Content-Type-Options",
            "missing_severity": "Low",
            "cvss_score": 2.0,
            "desc": "Prevents MIME-type sniffing attacks.",
            "rec": "Set 'X-Content-Type-Options: nosniff'."
        },
        "X-Frame-Options": {
            "name": "X-Frame-Options",
            "missing_severity": "Low",
            "cvss_score": 3.1,
            "desc": "Protects against clickjacking attacks.",
            "rec": "Set 'X-Frame-Options: DENY' or 'SAMEORIGIN'."
        },
        "Referrer-Policy": {
            "name": "Referrer-Policy",
            "missing_severity": "Low",
            "cvss_score": 2.0,
            "desc": "Controls information sent in the Referer header.",
            "rec": "Set 'Referrer-Policy: strict-origin-when-cross-origin'."
        },
        "Permissions-Policy": {
            "name": "Permissions-Policy",
            "missing_severity": "Low",
            "cvss_score": 2.0,
            "desc": "Restricts browser features like camera, microphone, and geolocation.",
            "rec": "Implement Permissions-Policy header restricting unused browser capabilities."
        }
    }

    def __init__(self, target: str):
        self.raw_target = target.strip()
        self.url = self._normalize_url(self.raw_target)
        self.domain = self._extract_domain(self.url)

    def _normalize_url(self, url: str) -> str:
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return f"http://{url}"
        return url

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc or parsed.path.split("/")[0]
            return netloc.split(":")[0]
        except Exception:
            return url

    def collect(self) -> dict:
        """
        Executes all web security analysis modules and returns consolidated structured data and findings.
        """
        results = {
            "target": self.domain,
            "url": self.url,
            "final_url": self.url,
            "status_code": None,
            "security_headers": {},
            "ssl": {},
            "cookies": [],
            "cors": {},
            "http_methods": {},
            "directory_discovery": [],
            "technologies": [],
            "endpoints": [],
            "findings": []
        }

        # Shared session & initial request
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36 Argus/2.0 WebSecurityEngine"
            )
        }

        try:
            r = requests.get(self.url, headers=headers, timeout=10, allow_redirects=True)
            results["final_url"] = r.url
            results["status_code"] = r.status_code
            resp_headers = dict(r.headers)
            html = r.text
            cookies_obj = r.cookies
            self.domain = self._extract_domain(r.url)
        except requests.exceptions.Timeout:
            results["error"] = "Connection timed out during web security analysis."
            return results
        except requests.exceptions.ConnectionError:
            results["error"] = "Connection failed. Host unreachable or refused HTTP connection."
            return results
        except Exception as e:
            results["error"] = f"Web Security Analysis failed: {str(e)}"
            return results

        soup = None
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            pass

        # 1. Security Header Analysis
        sec_headers_data, header_findings = self.analyze_security_headers(resp_headers, r.url)
        results["security_headers"] = sec_headers_data
        results["findings"].extend(header_findings)

        # 2. SSL/TLS Analysis
        ssl_data, ssl_findings = self.analyze_ssl_tls(self.domain, r.url)
        results["ssl"] = ssl_data
        results["findings"].extend(ssl_findings)

        # 3. Cookie Security Analysis
        cookie_data, cookie_findings = self.analyze_cookies(cookies_obj, resp_headers)
        results["cookies"] = cookie_data
        results["findings"].extend(cookie_findings)

        # 4. CORS Analysis
        cors_data, cors_findings = self.analyze_cors(self.url, resp_headers)
        results["cors"] = cors_data
        results["findings"].extend(cors_findings)

        # 5. HTTP Methods Analysis
        methods_data, methods_findings = self.analyze_http_methods(self.url)
        results["http_methods"] = methods_data
        results["findings"].extend(methods_findings)

        # 6. Directory / Endpoint Discovery
        dir_data, dir_endpoints, dir_findings = self.discover_directories(self.url)
        results["directory_discovery"] = dir_data
        results["endpoints"].extend(dir_endpoints)
        results["findings"].extend(dir_findings)

        # 7. Expanded Web Fingerprinting
        tech_list = self.expand_web_fingerprint(soup, html, resp_headers, cookies_obj)
        results["technologies"] = tech_list

        return results

    # --- 1. Security Header Analysis ---
    def analyze_security_headers(self, headers: dict, current_url: str) -> tuple:
        sec_results = {}
        findings = []
        is_https = current_url.lower().startswith("https://")

        # Standardize header lookup (case-insensitive)
        headers_lower = {k.lower(): v for k, v in headers.items()}

        for header_name, spec in self.SECURITY_HEADER_SPECS.items():
            h_key = header_name.lower()
            val = headers_lower.get(h_key)

            if not val:
                # If non-HTTPS, missing HSTS is expected, otherwise low/medium
                if header_name == "Strict-Transport-Security" and not is_https:
                    sec_results[header_name] = {
                        "status": "Not Applicable",
                        "value": None,
                        "details": "HSTS requires HTTPS"
                    }
                else:
                    sec_results[header_name] = {
                        "status": "Missing",
                        "value": None,
                        "details": f"{header_name} header is not configured"
                    }
                    findings.append({
                        "title": f"Missing {header_name} Security Header",
                        "severity": spec["missing_severity"],
                        "cvss_score": spec.get("cvss_score", 5.3 if spec["missing_severity"] == "Medium" else 2.0),
                        "risk_score": 30 if spec["missing_severity"] == "Medium" else 15,
                        "description": f"The HTTP response does not include the `{header_name}` security header. {spec['desc']}",
                        "evidence": f"Target URL: {current_url}\nResponse Headers:\n" + "\n".join(f"{k}: {v}" for k, v in headers.items()),
                        "recommendation": spec["rec"]
                    })
            else:
                # Check for weak configurations
                status = "Present"
                details = f"Configured: {val}"

                if header_name == "Content-Security-Policy" and ("unsafe-inline" in val or "unsafe-eval" in val or "*" in val):
                    status = "Weak / Misconfigured"
                    details = "CSP includes weak directives (unsafe-inline, unsafe-eval, or wildcard)"
                    findings.append({
                        "title": "Weak Content-Security-Policy Directive Detected",
                        "severity": "Low",
                        "risk_score": 20,
                        "description": "Content-Security-Policy is present but contains permissive directives like `unsafe-inline` or wildcard origins.",
                        "evidence": f"Content-Security-Policy: {val}",
                        "recommendation": "Remove `unsafe-inline` and `unsafe-eval` from CSP. Restrict resource origins to specific trusted domains."
                    })
                elif header_name == "X-Frame-Options" and val.upper() not in ["DENY", "SAMEORIGIN"]:
                    status = "Weak / Misconfigured"
                    details = f"Non-standard or permissive setting: {val}"

                sec_results[header_name] = {
                    "status": status,
                    "value": val,
                    "details": details
                }

        return sec_results, findings

    # --- 2. SSL/TLS Analysis ---
    def analyze_ssl_tls(self, domain: str, current_url: str) -> tuple:
        ssl_res = {
            "https_available": False,
            "http_to_https_redirect": False,
            "certificate_valid": False,
            "subject": "N/A",
            "issuer": "N/A",
            "expiration": "N/A",
            "sans": [],
            "hostname_match": False,
            "tls_versions": [],
            "ciphers": "N/A"
        }
        findings = []

        # Check HTTP -> HTTPS Redirect
        try:
            http_r = requests.get(f"http://{domain}", timeout=5, allow_redirects=False)
            if http_r.status_code in (301, 302, 307, 308):
                loc = http_r.headers.get("Location", "")
                if loc.lower().startswith("https://"):
                    ssl_res["http_to_https_redirect"] = True
        except Exception:
            pass

        if not ssl_res["http_to_https_redirect"] and not current_url.startswith("https://"):
            findings.append({
                "title": "HTTP to HTTPS Automatic Redirect Missing",
                "severity": "Low",
                "risk_score": 15,
                "description": "The web application allows unencrypted HTTP access without automatically redirecting clients to HTTPS.",
                "evidence": f"HTTP request to http://{domain} returned status {http_r.status_code if 'http_r' in locals() else 'No Response'}",
                "recommendation": "Configure 301 Permanent Redirect from HTTP (port 80) to HTTPS (port 443)."
            })

        # Connect SSL Socket to inspect Certificate and TLS Protocols
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    ssl_res["https_available"] = True
                    ssl_res["certificate_valid"] = True
                    ssl_res["hostname_match"] = True

                    # Subject & Issuer
                    subject_dict = dict(x[0] for x in cert.get("subject", []))
                    issuer_dict = dict(x[0] for x in cert.get("issuer", []))
                    ssl_res["subject"] = subject_dict.get("commonName") or subject_dict.get("organizationName") or domain
                    ssl_res["issuer"] = issuer_dict.get("organizationName") or issuer_dict.get("commonName") or "Unknown Issuer"

                    # Expiration
                    not_after = cert.get("notAfter")
                    if not_after:
                        exp_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                        ssl_res["expiration"] = exp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        if exp_dt < datetime.now(timezone.utc):
                            ssl_res["certificate_valid"] = False
                            findings.append({
                                "title": "SSL/TLS Certificate Expired",
                                "severity": "High",
                                "risk_score": 70,
                                "description": "The SSL/TLS certificate presented by the target server has expired.",
                                "evidence": f"Certificate Expiration: {ssl_res['expiration']}",
                                "recommendation": "Renew and re-install a valid SSL/TLS certificate immediately."
                            })

                    # SANs
                    sans = [item[1] for item in cert.get("subjectAltName", []) if item[0] == "DNS"]
                    ssl_res["sans"] = sans

                    # Negotiated Protocol & Cipher
                    cipher_info = ssock.cipher()
                    if cipher_info:
                        ssl_res["ciphers"] = f"{cipher_info[0]} ({cipher_info[1]})"
                        ssl_res["tls_versions"].append(ssock.version())

        except ssl.SSLCertVerificationError as cert_err:
            ssl_res["https_available"] = True
            ssl_res["certificate_valid"] = False
            findings.append({
                "title": "SSL/TLS Certificate Validation Failed",
                "severity": "Medium",
                "risk_score": 50,
                "description": f"The SSL/TLS certificate presented by the server failed validation: {str(cert_err)}",
                "evidence": f"Target Domain: {domain}\nError: {str(cert_err)}",
                "recommendation": "Replace self-signed or invalid certificates with a trusted CA-signed certificate."
            })
        except Exception:
            ssl_res["https_available"] = False

        # Protocol version checks (TLS 1.0, 1.1 legacy check)
        for prot_name, prot_const in [("TLSv1.0", ssl.TLSVersion.TLSv1), ("TLSv1.1", ssl.TLSVersion.TLSv1_1)]:
            try:
                legacy_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                legacy_ctx.check_hostname = False
                legacy_ctx.verify_mode = ssl.CERT_NONE
                legacy_ctx.minimum_version = prot_const
                legacy_ctx.maximum_version = prot_const
                with socket.create_connection((domain, 443), timeout=3) as sock:
                    with legacy_ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                        if prot_name not in ssl_res["tls_versions"]:
                            ssl_res["tls_versions"].append(prot_name)
                        findings.append({
                            "title": f"Deprecated {prot_name} Protocol Supported",
                            "severity": "Medium",
                            "risk_score": 40,
                            "description": f"The server supports legacy protocol `{prot_name}`, which contains known cryptographic weaknesses.",
                            "evidence": f"Successfully established TLS handshake using protocol `{prot_name}`",
                            "recommendation": "Disable TLS 1.0 and TLS 1.1 on web server. Enforce TLS 1.2 and TLS 1.3 only."
                        })
            except Exception:
                pass

        return ssl_res, findings

    # --- 3. Cookie Security Analysis ---
    def analyze_cookies(self, cookies_obj, headers: dict) -> tuple:
        cookie_list = []
        findings = []

        # Parse raw Set-Cookie headers for accurate flag inspection
        raw_set_cookies = []
        for k, v in headers.items():
            if k.lower() == "set-cookie":
                raw_set_cookies.append(v)

        for c in cookies_obj:
            c_name = c.name
            c_value = c.value
            is_secure = c.secure
            is_httponly = c.has_nonstandard_attr("HttpOnly") or c.has_nonstandard_attr("httponly")
            
            # Fallback to Set-Cookie header text parsing
            raw_match = next((raw for raw in raw_set_cookies if f"{c_name}=" in raw), "")
            if raw_match:
                if "httponly" in raw_match.lower():
                    is_httponly = True
                if "secure" in raw_match.lower():
                    is_secure = True

            samesite = c.get_nonstandard_attr("SameSite") or c.get_nonstandard_attr("samesite")
            if not samesite and raw_match and "samesite=" in raw_match.lower():
                m = re.search(r"samesite=([a-zA-Z]+)", raw_match, re.I)
                if m:
                    samesite = m.group(1)

            c_info = {
                "name": c_name,
                "domain": c.domain or self.domain,
                "path": c.path or "/",
                "secure": is_secure,
                "httponly": is_httponly,
                "samesite": samesite or "Not Set",
                "expires": str(c.expires) if c.expires else "Session"
            }
            cookie_list.append(c_info)

            # Security Findings for missing flags on sensitive/session cookies
            missing_flags = []
            if not is_httponly:
                missing_flags.append("HttpOnly")
            if not is_secure and self.url.startswith("https://"):
                missing_flags.append("Secure")

            if missing_flags:
                is_session_cookie = any(kw in c_name.lower() for kw in ["sess", "auth", "token", "jwt", "id", "user"])
                sev = "Medium" if is_session_cookie else "Low"
                findings.append({
                    "title": f"Cookie '{c_name}' Missing {', '.join(missing_flags)} Attribute",
                    "severity": sev,
                    "risk_score": 35 if sev == "Medium" else 15,
                    "description": f"The cookie `{c_name}` is set without the required security attribute(s): {', '.join(missing_flags)}.",
                    "evidence": f"Cookie Name: {c_name}\nAttributes: Secure={is_secure}, HttpOnly={is_httponly}, SameSite={c_info['samesite']}",
                    "recommendation": f"Configure Set-Cookie directive for `{c_name}` to include `HttpOnly`, `Secure`, and `SameSite=Lax` or `Strict`."
                })

        return cookie_list, findings

    # --- 4. CORS Analysis ---
    def analyze_cors(self, url: str, headers: dict) -> tuple:
        cors_info = {
            "allow_origin": "Not Set",
            "allow_credentials": False,
            "allow_methods": "Not Set",
            "allow_headers": "Not Set",
            "status": "Configured / Safe"
        }
        findings = []

        headers_lower = {k.lower(): v for k, v in headers.items()}
        allow_origin = headers_lower.get("access-control-allow-origin")
        allow_credentials = headers_lower.get("access-control-allow-credentials", "").lower() == "true"
        allow_methods = headers_lower.get("access-control-allow-methods")
        allow_headers = headers_lower.get("access-control-allow-headers")

        if allow_origin:
            cors_info["allow_origin"] = allow_origin
            cors_info["allow_credentials"] = allow_credentials
            cors_info["allow_methods"] = allow_methods or "Default"
            cors_info["allow_headers"] = allow_headers or "Default"

            # Check wildcard + credentials insecure combo
            if allow_origin == "*" and allow_credentials:
                cors_info["status"] = "Insecure Wildcard with Credentials"
                findings.append({
                    "title": "Insecure CORS Configuration: Wildcard Origin with Credentials",
                    "severity": "High",
                    "risk_score": 60,
                    "description": "The server specifies `Access-Control-Allow-Origin: *` while allowing credentials (`Access-Control-Allow-Credentials: true`).",
                    "evidence": f"Access-Control-Allow-Origin: {allow_origin}\nAccess-Control-Allow-Credentials: true",
                    "recommendation": "Remove wildcard origin when credentials are enabled. Specify an explicit whitelist of trusted origins."
                })

        # Active Probe: Send untrusted Origin header to detect dynamic origin reflection
        try:
            evil_origin = "https://evil-untrusted-domain.com"
            probe_r = requests.get(url, headers={"Origin": evil_origin}, timeout=5)
            probe_origin = probe_r.headers.get("Access-Control-Allow-Origin", "")
            probe_creds = probe_r.headers.get("Access-Control-Allow-Credentials", "").lower() == "true"

            if probe_origin == evil_origin:
                cors_info["status"] = "Reflects Arbitrary Origins"
                sev = "High" if probe_creds else "Medium"
                findings.append({
                    "title": "CORS Arbitrary Origin Reflection Detected",
                    "severity": sev,
                    "risk_score": 65 if probe_creds else 40,
                    "description": "The server reflects untrusted arbitrary `Origin` HTTP headers back in `Access-Control-Allow-Origin`.",
                    "evidence": f"Sent Origin: {evil_origin}\nReceived Access-Control-Allow-Origin: {probe_origin}\nAccess-Control-Allow-Credentials: {probe_creds}",
                    "recommendation": "Validate `Origin` headers against a strict server-side whitelist before reflecting origin access control headers."
                })
        except Exception:
            pass

        return cors_info, findings

    # --- 5. HTTP Methods Analysis ---
    def analyze_http_methods(self, url: str) -> tuple:
        methods_info = {
            "supported": [],
            "potentially_risky": [],
            "restricted": []
        }
        findings = []

        all_methods = ["GET", "POST", "HEAD", "OPTIONS", "PUT", "DELETE", "PATCH", "TRACE"]
        risky_methods = ["PUT", "DELETE", "TRACE"]

        # Step 1: Query OPTIONS header
        try:
            opt_r = requests.options(url, timeout=5)
            allow_hdr = opt_r.headers.get("Allow", "") or opt_r.headers.get("Public", "")
            if allow_hdr:
                declared_methods = [m.strip().upper() for m in allow_hdr.split(",") if m.strip()]
                for m in declared_methods:
                    if m in risky_methods:
                        methods_info["potentially_risky"].append(m)
                    else:
                        methods_info["supported"].append(m)
        except Exception:
            pass

        # Step 2: Direct probe for risky methods if OPTIONS wasn't authoritative
        for method in risky_methods:
            if method in methods_info["potentially_risky"]:
                continue
            try:
                r = requests.request(method, url, timeout=4, allow_redirects=False)
                if r.status_code in (200, 201, 204):
                    methods_info["potentially_risky"].append(method)
                elif r.status_code in (401, 403, 405):
                    methods_info["restricted"].append(method)
            except Exception:
                pass

        if "TRACE" in methods_info["potentially_risky"]:
            findings.append({
                "title": "HTTP TRACE Method Enabled",
                "severity": "Medium",
                "risk_score": 45,
                "description": "The HTTP TRACE method is enabled on the server, exposing the application to Cross-Site Tracing (XST) attacks.",
                "evidence": "Server responded successfully to HTTP TRACE probe request.",
                "recommendation": "Disable the HTTP TRACE method in web server configuration."
            })
        if "PUT" in methods_info["potentially_risky"] or "DELETE" in methods_info["potentially_risky"]:
            exposed = [m for m in ["PUT", "DELETE"] if m in methods_info["potentially_risky"]]
            findings.append({
                "title": f"Potentially Unsafe HTTP Method Enabled ({', '.join(exposed)})",
                "severity": "Medium",
                "risk_score": 40,
                "description": f"The web application exposes dangerous HTTP method(s): {', '.join(exposed)} without mandatory authentication.",
                "evidence": f"Methods accessible without authentication: {', '.join(exposed)}",
                "recommendation": "Restrict PUT and DELETE HTTP methods or require authentication/authorization."
            })

        return methods_info, findings

    # --- 6. Directory / Endpoint Discovery ---
    def discover_directories(self, base_url: str) -> tuple:
        discovered_paths = []
        endpoints = []
        findings = []

        parsed = urllib.parse.urlparse(base_url)
        base_prefix = f"{parsed.scheme}://{parsed.netloc}"

        sensitive_paths = ["/.env", "/.git", "/backup", "/config", "/actuator"]

        for path in self.COMMON_PATHS:
            target_path_url = urllib.parse.urljoin(base_prefix, path)
            try:
                r = requests.get(target_path_url, timeout=4, allow_redirects=False)
                st_code = r.status_code
                content_type = r.headers.get("Content-Type", "Unknown").split(";")[0]
                resp_size = len(r.content)

                # Ignore general 404 Not Found
                if st_code == 404:
                    continue

                res_entry = {
                    "path": path,
                    "status_code": st_code,
                    "content_type": content_type,
                    "response_size": resp_size,
                    "redirect": r.headers.get("Location") if st_code in (301, 302, 307, 308) else None
                }
                discovered_paths.append(res_entry)

                endpoints.append({
                    "method": "GET",
                    "path": path,
                    "status_code": st_code,
                    "discovery_source": "Web Security Engine"
                })

                # Check for sensitive exposed files returning 200 OK
                if st_code == 200 and path in sensitive_paths:
                    findings.append({
                        "title": f"Potentially Sensitive File Exposed ({path})",
                        "severity": "High",
                        "risk_score": 75,
                        "description": f"Publicly accessible sensitive endpoint or file discovered at `{path}`.",
                        "evidence": f"URL: {target_path_url}\nStatus Code: 200 OK\nContent-Type: {content_type}\nSize: {resp_size} bytes",
                        "recommendation": f"Restrict access or remove the sensitive file/endpoint `{path}` from production web root."
                    })
            except Exception:
                pass

        return discovered_paths, endpoints, findings

    # --- 7. Expanded Web Fingerprinting ---
    def expand_web_fingerprint(self, soup, html: str, headers: dict, cookies_obj) -> list:
        tech_map = {}

        def add_tech(name: str, version: str = None, category: str = "Web Stack"):
            if name not in tech_map:
                tech_map[name] = {"name": name, "version": version, "category": category}
            elif version and not tech_map[name]["version"]:
                tech_map[name]["version"] = version

        html_lower = (html or "").lower()

        # Web Server
        server_hdr = headers.get("Server", "").strip()
        if server_hdr:
            s_parts = server_hdr.split("/")
            s_name = s_parts[0]
            s_ver = s_parts[1].split()[0] if len(s_parts) > 1 else None
            add_tech(s_name, s_ver, "Web Server")

        # Reverse Proxy / CDN / WAF
        if "cf-ray" in headers or server_hdr.lower() == "cloudflare":
            add_tech("Cloudflare WAF/CDN", None, "CDN/WAF")
        if "x-amz-cf-id" in headers or "cloudfront" in headers.get("Via", "").lower():
            add_tech("Amazon CloudFront", None, "CDN")
        if "akamai" in headers.get("X-Cache", "").lower() or "akamaighost" in server_hdr.lower():
            add_tech("Akamai CDN", None, "CDN")

        # Backend Framework / Language
        powered_by = headers.get("X-Powered-By", "")
        if powered_by:
            pb_parts = powered_by.split("/")
            add_tech(pb_parts[0], pb_parts[1] if len(pb_parts) > 1 else None, "Backend Framework")

        cookie_names = [c.name.lower() for c in cookies_obj]
        for name in cookie_names:
            if "phpsessid" in name:
                add_tech("PHP", None, "Programming Language")
            elif "jsessionid" in name:
                add_tech("Java (J2EE)", None, "Programming Language")
            elif "aspsessionid" in name or "asp.net" in name:
                add_tech("ASP.NET", None, "Framework")
            elif "django" in name:
                add_tech("Python (Django)", None, "Framework")
            elif "laravel_session" in name:
                add_tech("PHP (Laravel)", None, "Framework")

        # CMS Detection
        if not soup and html:
            try:
                soup = BeautifulSoup(html, "html.parser")
            except Exception:
                soup = None

        if soup:
            meta_gen = soup.find("meta", attrs={"name": re.compile(r"^generator$", re.I)})
            if meta_gen and meta_gen.get("content"):
                gen_str = meta_gen.get("content").strip()
                v_match = re.search(r"([\w\.]+)\s*([\d\.]+)", gen_str)
                if v_match:
                    add_tech(v_match.group(1), v_match.group(2), "CMS")
                else:
                    add_tech(gen_str, None, "CMS")

        if "wp-content" in html_lower or "wp-includes" in html_lower:
            add_tech("WordPress", None, "CMS")
        elif "sites/default" in html_lower or "drupal.js" in html_lower:
            add_tech("Drupal", None, "CMS")

        # Frontend JS & CSS Frameworks
        jq_match = re.search(r"jquery[.-]?(\d+\.\d+\.\d+)", html_lower)
        if jq_match:
            add_tech("jQuery", jq_match.group(1), "JavaScript Library")
        elif "jquery" in html_lower:
            add_tech("jQuery", None, "JavaScript Library")

        if "__next" in html_lower or "_next/static" in html_lower:
            add_tech("Next.js", None, "JavaScript Framework")
        elif "data-reactroot" in html_lower or "react" in html_lower:
            add_tech("React", None, "JavaScript Framework")

        if "__nuxt" in html_lower or "vue.js" in html_lower:
            add_tech("Vue.js", None, "JavaScript Framework")

        bs_match = re.search(r"bootstrap[.-]?(\d+\.\d+\.\d+)", html_lower)
        if bs_match:
            add_tech("Bootstrap", bs_match.group(1), "CSS Framework")
        elif "bootstrap" in html_lower:
            add_tech("Bootstrap", None, "CSS Framework")

        if "tailwind" in html_lower:
            add_tech("Tailwind CSS", None, "CSS Framework")

        return list(tech_map.values())
