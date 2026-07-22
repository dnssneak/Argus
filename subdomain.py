#!/usr/bin/env python3
"""
Module 5: Subdomain Finder
Enumerates subdomains passively using CT logs and a common wordlist lookup, resolving IPs.
"""

import socket
import re
import requests


class SubdomainFinder:
    """
    Finds and resolves subdomains of a target domain passively.
    """

    DEFAULT_SUBDOMAINS = [
        "www", "mail", "api", "dev", "blog", "admin", "test", "vpn", "status",
        "stage", "portal", "secure", "shop", "git", "webmail", "support", "billing"
    ]

    def __init__(self, target):
        self.raw_target = target.strip()
        self.domain = self._sanitize_domain(self.raw_target)

    def _sanitize_domain(self, value):
        # Remove schemes and subdomains/paths if provided
        clean = re.sub(r"^https?://", "", value, flags=re.IGNORECASE)
        clean = clean.split("/")[0]
        clean = clean.split(":")[0]
        # Remove 'www.' prefix if entered by user to perform clean enumeration on the root domain
        if clean.lower().startswith("www."):
            clean = clean[4:]
        return clean.lower()

    def collect(self):
        """Discovers subdomains and resolves status & IPs."""
        if not self.domain:
            return {
                "target": self.raw_target,
                "error": "Invalid target domain format."
            }

        subdomains = set()

        # 1. Query crt.sh passively (CT Logs)
        try:
            # Short timeout to keep the app responsive if crt.sh is slow/rate-limited
            url = f"https://crt.sh/?q=%.{self.domain}&output=json"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for item in data:
                    name_value = item.get("name_value", "")
                    # name_value can contain multiple subdomains split by newlines
                    for name in name_value.split("\n"):
                        name = name.strip().lower()
                        # Filter out wildcards and check if it is a valid subdomain of target domain
                        if name and not name.startswith("*.") and name.endswith(f".{self.domain}"):
                            subdomains.add(name)
        except Exception:
            # If crt.sh fails or times out, proceed to wordlist fallback
            pass

        # 2. Add local fallback common subdomains to scan list
        for sub in self.DEFAULT_SUBDOMAINS:
            subdomains.add(f"{sub}.{self.domain}")

        # Add the base domain itself
        subdomains.add(self.domain)

        # 3. Resolve and verify subdomains
        results = []
        for sub in sorted(list(subdomains)):
            try:
                ip = socket.gethostbyname(sub)
                status = "Active"
            except Exception:
                ip = "Not Resolved"
                status = "Inactive"
            
            results.append({
                "subdomain": sub,
                "status": status,
                "ip_address": ip
            })

        return {
            "target": self.domain,
            "subdomains": results,
            "total_found": len(results)
        }
