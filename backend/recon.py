#!/usr/bin/env python3
"""
Module 1: System Information
Module 2: Information Gathering
"""

import platform
import socket
import getpass
import re
import ipaddress

import psutil
import requests
import dns.resolver
import whois


class SystemInfo:
    """Module 1: Gathers information about the local machine."""

    def collect(self):
        return {
            "operating_system": self._get_os(),
            "hostname": self._get_hostname(),
            "current_user": self._get_user(),
            "local_ip": self._get_local_ip(),
            "public_ip": self._get_public_ip(),
            "network_interfaces": self._get_interfaces(),
        }

    def _get_os(self):
        try:
            os_name = platform.system()
            os_version = platform.release()
            if os_name == "Linux":
                try:
                    distro = platform.freedesktop_os_release().get("NAME", "")
                    if distro:
                        return f"{distro} {os_version}"
                except (AttributeError, FileNotFoundError):
                    pass
            return f"{os_name} {os_version}"
        except Exception:
            return "Unknown"

    def _get_hostname(self):
        try:
            return socket.gethostname()
        except Exception:
            return "Unknown"

    def _get_user(self):
        try:
            return getpass.getuser()
        except Exception:
            return "Unknown"

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unavailable"

    def _get_public_ip(self):
        try:
            r = requests.get("https://api.ipify.org?format=json", timeout=5)
            r.raise_for_status()
            return r.json().get("ip", "Unavailable")
        except Exception:
            return "Unavailable"

    def _get_interfaces(self):
        interfaces = []
        try:
            for name, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interfaces.append({"name": name, "ip": addr.address})
                        break
        except Exception:
            pass
        return interfaces


class TargetRecon:
    """Module 2: Gathers publicly available information about a target."""

    def __init__(self, target):
        self.raw_target = target.strip()
        self.target = self.raw_target.lower()
        self.is_ip = self._is_ip_address(self.target)
        self.domain = self._extract_domain(self.target)

    def _is_ip_address(self, value):
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def _extract_domain(self, value):
        clean = re.sub(r"^https?://", "", value)
        clean = clean.split("/")[0]
        clean = clean.split(":")[0]
        return clean

    def collect(self):
        return {
            "target": self.raw_target,
            "whois": self._get_whois(),
            "dns": self._get_dns(),
            "reverse_dns": self._get_reverse_dns(),
            "http_headers": self._get_http_headers(),
            "ip_geolocation": self._get_ip_geolocation(),
        }

    def _get_ip_geolocation(self):
        resolved_ip = None
        if self.is_ip:
            resolved_ip = self.target
        else:
            try:
                resolved_ip = socket.gethostbyname(self.domain)
            except Exception:
                return {
                    "applicable": True,
                    "error": f"Failed to resolve domain name '{self.domain}' to an IP address."
                }

        try:
            r = requests.get(f"http://ip-api.com/json/{resolved_ip}", timeout=10)
            r.raise_for_status()
            data = r.json()
            if data.get("status") == "success":
                return {
                    "applicable": True,
                    "ip_address": resolved_ip,
                    "country": data.get("country", "Not Available"),
                    "region": data.get("regionName", "Not Available"),
                    "city": data.get("city", "Not Available"),
                    "isp": data.get("isp", "Not Available"),
                    "org": data.get("org", "Not Available"),
                    "timezone": data.get("timezone", "Not Available"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
            else:
                return {
                    "applicable": True,
                    "error": f"GeoIP API error: {data.get('message', 'Unknown failure')}"
                }
        except Exception as e:
            return {
                "applicable": True,
                "error": f"Failed to retrieve geolocation data: {str(e)}"
            }

    def _get_whois(self):
        if self.is_ip:
            return {
                "applicable": False,
                "message": "WHOIS not applicable for IP addresses"
            }

        try:
            w = whois.whois(self.domain)
            return {
                "applicable": True,
                "registrar": w.registrar or "Not Available",
                "creation_date": self._format_date(w.creation_date),
                "expiration_date": self._format_date(w.expiration_date),
                "updated_date": self._format_date(w.updated_date),
                "status": w.status or "Not Available",
            }
        except Exception:
            return {
                "applicable": True,
                "error": "WHOIS lookup failed. Domain may not be registered or rate-limited."
            }

    def _format_date(self, date_value):
        if date_value is None:
            return "Not Available"
        if isinstance(date_value, list):
            date_value = date_value[0]
        if hasattr(date_value, "strftime"):
            return date_value.strftime("%Y-%m-%d")
        return str(date_value)

    def _get_dns(self):
        if self.is_ip:
            return {
                "applicable": False,
                "message": "DNS lookup not applicable for IP addresses"
            }

        records = {"a": [], "mx": [], "ns": [], "txt": []}

        try:
            answers = dns.resolver.resolve(self.domain, "A")
            records["a"] = [str(rdata) for rdata in answers]
        except Exception:
            pass

        try:
            answers = dns.resolver.resolve(self.domain, "MX")
            records["mx"] = [str(rdata.exchange) for rdata in answers]
        except Exception:
            pass

        try:
            answers = dns.resolver.resolve(self.domain, "NS")
            records["ns"] = [str(rdata) for rdata in answers]
        except Exception:
            pass

        try:
            answers = dns.resolver.resolve(self.domain, "TXT")
            records["txt"] = [str(rdata).strip('"') for rdata in answers]
        except Exception:
            pass

        return {
            "applicable": True,
            "records": records
        }

    def _get_reverse_dns(self):
        if not self.is_ip:
            return {
                "applicable": False,
                "message": "Reverse DNS only applicable for IP addresses"
            }

        try:
            hostname, _, _ = socket.gethostbyaddr(self.target)
            return {
                "applicable": True,
                "hostname": hostname
            }
        except Exception:
            return {
                "applicable": True,
                "error": "No reverse DNS record found"
            }

    def _get_http_headers(self):
        if self.is_ip:
            url = f"http://{self.target}"
        else:
            url = f"http://{self.domain}"

        try:
            r = requests.get(url, timeout=10, allow_redirects=True)
            headers = dict(r.headers)

            security_headers = {
                "X-Frame-Options": headers.get("X-Frame-Options", "Not Present"),
                "Content-Security-Policy": headers.get("Content-Security-Policy", "Not Present"),
                "Strict-Transport-Security": headers.get("Strict-Transport-Security", "Not Present"),
                "X-Content-Type-Options": headers.get("X-Content-Type-Options", "Not Present"),
                "X-XSS-Protection": headers.get("X-XSS-Protection", "Not Present"),
            }

            return {
                "applicable": True,
                "status_code": f"{r.status_code} {r.reason}",
                "server": headers.get("Server", "Not Present"),
                "content_type": headers.get("Content-Type", "Not Present"),
                "content_length": headers.get("Content-Length", "Not Present"),
                "security_headers": security_headers,
            }
        except requests.exceptions.Timeout:
            return {
                "applicable": True,
                "error": "Connection timed out. Host may not be reachable or does not accept HTTP connections."
            }
        except requests.exceptions.ConnectionError:
            return {
                "applicable": True,
                "error": "Connection failed. Host refused connection or is unreachable."
            }
        except Exception:
            return {
                "applicable": True,
                "error": "HTTP request failed. Host may not have a web server running."
            }