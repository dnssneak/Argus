#!/usr/bin/env python3
"""
Module 6: Report Generation
Compiles scan results into downloadable TXT and HTML reports.
Supports all Argus 2.0 scan capabilities: Subdomains, Nmap Ports, Recon, Web Footprinting,
Web Security Engine Analysis, and Web Intelligence OSINT.
"""

import os
from datetime import datetime
import html as html_escape


class ReportGenerator:
    """
    Generates structured reports from system info, recon, scan, fingerprint, subdomain,
    web security, and web intelligence data.
    """

    def __init__(self, system_info=None, recon_data=None, scan_data=None, fingerprint_data=None, subdomain_data=None, web_security_data=None, web_intelligence_data=None, target=None):
        self.system_info = system_info or {}
        self.recon_data = recon_data or {}
        self.scan_data = scan_data or {}
        self.fingerprint_data = fingerprint_data or {}
        self.subdomain_data = subdomain_data or {}
        self.web_security_data = web_security_data or {}
        self.web_intelligence_data = web_intelligence_data or {}
        self.explicit_target = target

        # Resolve target domain/host
        self.target = (
            target or
            self.scan_data.get("target") or
            self.recon_data.get("target") or
            self.subdomain_data.get("target") or
            self.fingerprint_data.get("target") or
            self.web_security_data.get("target") or
            self.web_intelligence_data.get("target") or
            "N/A"
        )
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_txt(self, filename=None):
        """Generate a plain text report."""
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        filepath = os.path.join(self.report_dir, filename)
        content = self._build_txt_content()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath, filename

    def generate_html(self, filename=None):
        """Generate an HTML report."""
        if not filename:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        filepath = os.path.join(self.report_dir, filename)
        content = self._build_html_content()

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath, filename

    def _build_txt_content(self):
        """Build a beautifully formatted TXT report content."""
        lines = []
        width = 75

        # Header Block
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append("|" + "ARGUS CYBER SECURITY ASSESSMENT REPORT".center(width - 2) + "|")
        lines.append("|" + f"Generated: {self.timestamp}".center(width - 2) + "|")
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append("")

        # Target Information
        lines.append("[ REPORT TARGET ]")
        lines.append(f"  Target Host : {self.target}")
        lines.append(f"  Report Time : {self.timestamp}")
        lines.append("")

        # 1. System Information Section
        lines.append("[ 1. SYSTEM INFORMATION ]")
        lines.append("=" * width)
        if self.system_info:
            sys_fields = [
                ("Operating System", self.system_info.get('operating_system')),
                ("Hostname", self.system_info.get('hostname')),
                ("Current User", self.system_info.get('current_user')),
                ("Local IP Address", self.system_info.get('local_ip')),
                ("Public IP Address", self.system_info.get('public_ip')),
            ]
            for label, val in sys_fields:
                lines.append(f"  {label:<18} : {val or 'N/A'}")

            interfaces = self.system_info.get("network_interfaces", [])
            if interfaces:
                lines.append("\n  Network Interfaces:")
                for iface in interfaces:
                    name = iface.get('name', 'N/A')
                    ip = iface.get('ip', 'N/A')
                    lines.append(f"    - {name:<14} : {ip}")
            else:
                lines.append("\n  Network Interfaces : None detected")
        else:
            lines.append("  No system information available.")
        lines.append("")

        # 2. Information Gathering Section
        lines.append("[ 2. INFORMATION GATHERING (RECON) ]")
        lines.append("=" * width)
        if self.recon_data:
            # WHOIS
            whois = self.recon_data.get("whois", {})
            lines.append("  WHOIS Information:")
            if whois.get("applicable") and not whois.get("error"):
                whois_fields = [
                    ("Registrar", whois.get('registrar')),
                    ("Creation Date", whois.get('creation_date')),
                    ("Expiration Date", whois.get('expiration_date')),
                    ("Updated Date", whois.get('updated_date')),
                    ("Status", whois.get('status')),
                ]
                for label, val in whois_fields:
                    lines.append(f"    {label:<16} : {val or 'N/A'}")
            elif not whois.get("applicable"):
                lines.append(f"    {whois.get('message', 'N/A')}")
            else:
                lines.append(f"    Error: {whois.get('error', 'Lookup failed')}")
            lines.append("")

            # DNS Records
            dns = self.recon_data.get("dns", {})
            lines.append("  DNS Records:")
            if dns.get("applicable"):
                records = dns.get("records", {})
                for rtype in ["a", "mx", "ns", "txt"]:
                    values = records.get(rtype, [])
                    if values:
                        lines.append(f"    {rtype.upper():<6} : {', '.join(values)}")
                    else:
                        lines.append(f"    {rtype.upper():<6} : None found")
            else:
                lines.append(f"    {dns.get('message', 'N/A')}")
            lines.append("")

            # Reverse DNS
            reverse = self.recon_data.get("reverse_dns", {})
            lines.append("  Reverse DNS:")
            if reverse.get("applicable") and not reverse.get("error"):
                lines.append(f"    Hostname     : {reverse.get('hostname', 'N/A')}")
            elif not reverse.get("applicable"):
                lines.append(f"    {reverse.get('message', 'N/A')}")
            else:
                lines.append(f"    Error: {reverse.get('error', 'Lookup failed')}")
            lines.append("")

            # IP Geolocation
            geo = self.recon_data.get("ip_geolocation", {})
            lines.append("  IP Geolocation:")
            if geo.get("applicable") and not geo.get("error"):
                geo_fields = [
                    ("Target IP", geo.get('ip_address')),
                    ("Country", geo.get('country')),
                    ("Region", geo.get('region')),
                    ("City", geo.get('city')),
                    ("ISP", geo.get('isp')),
                    ("Organization", geo.get('org')),
                    ("Time Zone", geo.get('timezone')),
                ]
                for label, val in geo_fields:
                    lines.append(f"    {label:<12} : {val or 'N/A'}")
            elif not geo.get("applicable"):
                lines.append(f"    {geo.get('message', 'N/A')}")
            else:
                lines.append(f"    Error: {geo.get('error', 'Lookup failed')}")
            lines.append("")

            # HTTP Headers
            headers = self.recon_data.get("http_headers", {})
            lines.append("  HTTP Headers:")
            if not headers.get("error"):
                lines.append(f"    Status Code  : {headers.get('status_code', 'N/A')}")
                lines.append(f"    Server       : {headers.get('server', 'N/A')}")
                lines.append(f"    Content-Type : {headers.get('content_type', 'N/A')}")
                lines.append(f"    Length       : {headers.get('content_length', 'N/A')}")

                sec_headers = headers.get("security_headers", {})
                if sec_headers:
                    lines.append("\n    Security Headers:")
                    for h, v in sec_headers.items():
                        lines.append(f"      {h:<28} : {v}")
            else:
                lines.append(f"    Error: {headers.get('error', 'Request failed')}")
        else:
            lines.append("  No reconnaissance data available.")
        lines.append("")

        # 3. Network Scan Section
        lines.append("[ 3. NETWORK SCAN (NMAP) ]")
        lines.append("=" * width)
        if self.scan_data:
            lines.append(f"  Host Status : {self.scan_data.get('host_status', 'N/A')}")
            lines.append(f"  Scan Status : {self.scan_data.get('scan_status', 'N/A')}")
            lines.append("")

            open_ports = self.scan_data.get("open_ports", [])
            services = self.scan_data.get("services", [])

            services_map = {}
            for svc in services:
                port_proto = (svc.get("port"), svc.get("protocol"))
                services_map[port_proto] = svc

            if open_ports:
                lines.append("  Open Ports & Services:")
                lines.append("    " + "-" * 65)
                lines.append(f"    {'PORT':<10} {'STATE':<10} {'SERVICE':<15} {'VERSION'}")
                lines.append("    " + "-" * 65)
                for port in open_ports:
                    p_num = port.get('port', 'N/A')
                    proto = port.get('protocol', 'N/A')
                    port_str = f"{p_num}/{proto}"
                    state = port.get('state', 'N/A')

                    svc = services_map.get((p_num, proto), {})
                    svc_name = svc.get('name', 'N/A')
                    svc_version = svc.get('version', '')

                    lines.append(f"    {port_str:<10} {state:<10} {svc_name:<15} {svc_version or 'N/A'}")
                lines.append("    " + "-" * 65)
            else:
                lines.append("  Open Ports: None found")
            lines.append("")
            lines.append(f"  Total Open Ports: {len(open_ports)}")
        else:
            lines.append("  No network scan data available.")
        lines.append("")

        # 4. Website Fingerprinting Section
        lines.append("[ 4. WEBSITE FINGERPRINTING & SCRAPING ]")
        lines.append("=" * width)
        if self.fingerprint_data and not self.fingerprint_data.get("error"):
            fp = self.fingerprint_data
            ts = fp.get("tech_stack") or {}
            meta = fp.get("metadata") or {}
            contacts = fp.get("contacts_and_links") or {}
            forms = fp.get("forms_summary") or {}
            assets = fp.get("assets") or {}

            lines.append("  Technology Stack:")
            lines.append(f"    {'Web Server':<24} : {ts.get('web_server') or fp.get('web_server', 'Unknown')}")
            lines.append(f"    {'Backend Tech':<24} : {ts.get('backend') or fp.get('backend', 'Unknown')}")
            lines.append(f"    {'CMS':<24} : {ts.get('cms') or fp.get('cms', 'None Detected')}")
            lines.append(f"    {'Frontend Frameworks':<24} : {ts.get('frontend_frameworks') or fp.get('frontend', 'None Detected')}")
            lines.append(f"    {'CSS Frameworks':<24} : {ts.get('css_frameworks', 'None Detected')}")
            lines.append(f"    {'CDN / Security':<24} : {ts.get('cdn_security') or fp.get('cdn', 'None Detected')}")
            lines.append(f"    {'HTTP Protocol':<24} : {ts.get('http_version') or fp.get('http_version', 'HTTP/1.1')}")
            lines.append("")

            if meta:
                lines.append("  Scraped Web Metadata:")
                lines.append(f"    {'Page Title':<24} : {meta.get('title', 'N/A')}")
                lines.append(f"    {'Meta Description':<24} : {meta.get('description', 'N/A')}")
                lines.append(f"    {'Language':<24} : {meta.get('lang', 'N/A')}")
                lines.append("")

            if contacts:
                lines.append("  Links & Contacts Scraped:")
                lines.append(f"    Internal Links Count     : {contacts.get('internal_links_count', 0)}")
                lines.append(f"    External Links Count     : {contacts.get('external_links_count', 0)}")
                emails = contacts.get("emails", [])
                if emails:
                    lines.append(f"    Scraped Emails           : {', '.join(emails)}")
                lines.append("")

            if assets or forms:
                lines.append("  Assets & Structure:")
                lines.append(f"    Total HTML Forms         : {forms.get('total', 0)}")
                lines.append(f"    Scraped Script Sources   : {len(assets.get('scripts', []))}")
                lines.append(f"    Scraped Stylesheets      : {len(assets.get('stylesheets', []))}")
        elif self.fingerprint_data and self.fingerprint_data.get("error"):
            lines.append(f"    Error: {self.fingerprint_data.get('error')}")
        else:
            lines.append("    No website fingerprinting data available.")
        lines.append("")

        # 5. Subdomain Finder Section
        lines.append("[ 5. SUBDOMAIN FINDER ]")
        lines.append("=" * width)
        if self.subdomain_data and not self.subdomain_data.get("error"):
            sub_list = self.subdomain_data.get("subdomains", [])
            if sub_list:
                lines.append(f"  Total Subdomains Found : {self.subdomain_data.get('total_found', len(sub_list))}")
                lines.append("")
                lines.append(f"    {'SUBDOMAIN':<40} {'STATUS':<10} {'IP ADDRESS'}")
                lines.append("    " + "-" * 65)
                for s in sub_list:
                    lines.append(f"    {s.get('subdomain', ''):<40} {s.get('status', 'Active'):<10} {s.get('ip_address', 'N/A')}")
            else:
                lines.append("  No subdomains found.")
        elif self.subdomain_data and self.subdomain_data.get("error"):
            lines.append(f"  Error: {self.subdomain_data.get('error')}")
        else:
            lines.append("  No subdomain data available.")
        lines.append("")

        # 6. Web Security Engine Section
        lines.append("[ 6. WEB SECURITY ENGINE AUDIT ]")
        lines.append("=" * width)
        if self.web_security_data and not self.web_security_data.get("error"):
            ws = self.web_security_data
            sec_headers = ws.get("security_headers", {})
            ssl = ws.get("ssl", {})
            cors = ws.get("cors", {})
            methods = ws.get("http_methods", {})
            dirs = ws.get("directory_discovery", [])
            findings = ws.get("findings", [])
            nikto = ws.get("nikto_scan", {})

            # Security Headers Audit
            if sec_headers:
                lines.append("  Security Headers Audit:")
                for h_name, h_info in sec_headers.items():
                    st = h_info.get("status", "Missing") if isinstance(h_info, dict) else str(h_info)
                    lines.append(f"    {h_name:<30} : {st}")
                lines.append("")

            # SSL/TLS Inspection
            if ssl:
                lines.append("  SSL / TLS Inspection:")
                valid_str = "Valid CA Certificate" if ssl.get("certificate_valid") else "Invalid / Expired"
                lines.append(f"    {'Certificate Status':<24} : {valid_str}")
                lines.append(f"    {'Issuer':<24} : {ssl.get('issuer', 'N/A')}")
                tls_vers = ", ".join(ssl.get("tls_versions", [])) if ssl.get("tls_versions") else "TLSv1.2, TLSv1.3"
                lines.append(f"    {'Supported Protocols':<24} : {tls_vers}")
                lines.append("")

            # CORS & HTTP Methods
            if cors or methods:
                lines.append("  CORS & HTTP Methods Analysis:")
                lines.append(f"    {'CORS Status':<24} : {cors.get('status', 'Configured')}")
                lines.append(f"    {'Allowed Origin':<24} : {cors.get('allow_origin', 'Not Set')}")
                risky = ", ".join(methods.get("potentially_risky", [])) if methods.get("potentially_risky") else "None Detected"
                lines.append(f"    {'Risky HTTP Methods':<24} : {risky}")
                lines.append("")

            # Discovered Endpoints
            if dirs:
                lines.append(f"  Discovered Paths & Endpoints ({len(dirs)}):")
                for d in dirs:
                    path = d.get("path", "")
                    code = d.get("status_code", "200")
                    lines.append(f"    GET {path:<45} [Status: {code}]")
                lines.append("")

            # Web Security Findings
            if findings:
                lines.append(f"  Security Findings Audit ({len(findings)} Findings):")
                lines.append("    " + "-" * 65)
                for f_item in findings:
                    sev = f_item.get("severity", "Medium").upper()
                    cvss = f_item.get("cvss_score") or f_item.get("risk_score") or "N/A"
                    title = f_item.get("title", "Security Finding")
                    desc = f_item.get("description", "")
                    lines.append(f"    [{sev}] {title} (CVSS/Score: {cvss})")
                    if desc:
                        lines.append(f"        Details: {desc}")
                lines.append("    " + "-" * 65)
                lines.append("")

            # Nikto Scanner Output
            if nikto and nikto.get("findings"):
                n_findings = nikto.get("findings", [])
                lines.append(f"  Nikto Vulnerability Scan Summary ({len(n_findings)} Vulnerabilities Discovered):")
                for nf in n_findings[:15]:
                    lines.append(f"    - {nf.get('description', '')}")
                lines.append("")
        elif self.web_security_data and self.web_security_data.get("error"):
            lines.append(f"  Error: {self.web_security_data.get('error')}")
        else:
            lines.append("  No web security engine analysis data available.")
        lines.append("")

        # 7. Web Intelligence Section
        lines.append("[ 7. WEB INTELLIGENCE & OSINT ]")
        lines.append("=" * width)
        if self.web_intelligence_data and not self.web_intelligence_data.get("error"):
            wi = self.web_intelligence_data
            emails = wi.get("emails", [])
            patterns = wi.get("email_patterns", [])
            socials = wi.get("social_links", [])
            docs = wi.get("documents", [])
            hist_urls = wi.get("historical_urls", [])

            # Email OSINT
            lines.append(f"  Public Email Discovery ({len(emails)} Discovered):")
            if patterns:
                lines.append(f"    Inferred Email Pattern(s) : {', '.join(patterns)}")
            if emails:
                for e in emails:
                    email_addr = e.get("email", "")
                    role = e.get("role_category", "General")
                    src = e.get("source", "Web Scrape")
                    hist_flag = "[HISTORICAL ARCHIVE]" if e.get("is_historical") else "[ACTIVE PUBLIC]"
                    lines.append(f"    - {email_addr:<35} {hist_flag:<20} Role: {role:<12} (Source: {src})")
            else:
                lines.append("    No public email addresses harvested.")
            lines.append("")

            # Social Profiles
            if socials:
                lines.append(f"  Linked Social Profiles ({len(socials)}):")
                for s in socials:
                    lines.append(f"    - {s.get('platform', 'Social'):<15} : {s.get('url', '')}")
                lines.append("")

            # Public Documents
            if docs:
                lines.append(f"  Public Downloadable Documents & Metadata ({len(docs)} Found):")
                for d in docs:
                    fname = d.get("filename", "document")
                    ftype = d.get("file_type", "DOC")
                    title = d.get("title", "N/A")
                    meta_info = d.get("metadata", {})
                    author = meta_info.get("author", "N/A")
                    lines.append(f"    - [{ftype}] {fname} (Title: {title} | Author: {author})")
                lines.append("")

            # Historical Archive URLs
            if hist_urls:
                lines.append(f"  Wayback Historical Archive URLs ({len(hist_urls)} Indexed):")
                for h in hist_urls[:15]:
                    lines.append(f"    - [{h.get('timestamp', 'Archive')}] {h.get('url', '')}")
                lines.append("")
        elif self.web_intelligence_data and self.web_intelligence_data.get("error"):
            lines.append(f"  Error: {self.web_intelligence_data.get('error')}")
        else:
            lines.append("  No web intelligence OSINT data available.")
        lines.append("")

        # 8. Executive Summary Section
        lines.append("[ 8. EXECUTIVE SUMMARY & OVERVIEW ]")
        lines.append("=" * width)
        open_ports_count = len(self.scan_data.get("open_ports", []))
        subdomains_count = self.subdomain_data.get("total_found") or len(self.subdomain_data.get("subdomains", []))
        findings_list = self.web_security_data.get("findings", [])
        emails_count = len(self.web_intelligence_data.get("emails", []))

        crit_count = sum(1 for f in findings_list if (f.get("severity") or "").lower() == "critical")
        high_count = sum(1 for f in findings_list if (f.get("severity") or "").lower() == "high")
        med_count = sum(1 for f in findings_list if (f.get("severity") or "").lower() == "medium")

        lines.append(f"  Target Scope Host         : {self.target}")
        lines.append(f"  Scan Completion Status    : Completed")
        lines.append(f"  Total Open Network Ports  : {open_ports_count}")
        lines.append(f"  Total Discovered Subdomains: {subdomains_count}")
        lines.append(f"  Web Security Findings     : {len(findings_list)} ({crit_count} Critical, {high_count} High, {med_count} Medium)")
        lines.append(f"  Harvested OSINT Emails    : {emails_count}")
        
        if crit_count > 0 or high_count > 0:
            outcome = "ELEVATED RISK - Immediate Security Remediation Advised"
        elif len(findings_list) > 0 or open_ports_count > 0:
            outcome = "MODERATE EXPOSURE - Standard Hardening Required"
        else:
            outcome = "LOW RISK - No High-Severity Threats Identified"
        lines.append(f"  Overall Security Outcome  : {outcome}")
        lines.append("")

        # Footer Block
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append("|" + "END OF ARGUS SECURITY REPORT".center(width - 2) + "|")
        lines.append("+" + "-" * (width - 2) + "+")

        return "\n".join(lines)

    def _build_html_content(self):
        """Build HTML report content."""
        system_section = self._build_system_html()
        recon_section = self._build_recon_html()
        scan_section = self._build_scan_html()
        fingerprint_section = self._build_fingerprint_html()
        subdomain_section = self._build_subdomain_html()
        web_security_section = self._build_web_security_html()
        web_intelligence_section = self._build_web_intelligence_html()
        summary_section = self._build_summary_html()

        target_escaped = html_escape.escape(str(self.target))

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Argus Security Assessment Report - {target_escaped}</title>
    <style>
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #0b0b12;
            color: #f1f0f5;
            line-height: 1.6;
            padding: 30px;
            max-width: 960px;
            margin: 0 auto;
        }}
        .report-header {{
            text-align: center;
            border-bottom: 2px solid #2d2d44;
            padding-bottom: 20px;
            margin-bottom: 25px;
        }}
        h1 {{
            color: #a855f7;
            font-size: 2.2rem;
            margin: 0 0 10px 0;
            letter-spacing: -0.02em;
        }}
        .report-subtitle {{
            color: #94a3b8;
            font-size: 1rem;
        }}
        h2 {{
            color: #c084fc;
            margin-top: 35px;
            padding-bottom: 8px;
            border-bottom: 1px solid #2d2d44;
            font-size: 1.35rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        h3 {{
            color: #e879f9;
            margin-top: 22px;
            font-size: 1.05rem;
        }}
        .meta {{
            background: rgba(26, 26, 46, 0.7);
            padding: 18px 22px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #2d2d44;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .meta-item {{
            display: flex;
            flex-direction: column;
        }}
        .meta-label {{
            color: #94a3b8;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-family: 'JetBrains Mono', monospace;
        }}
        .meta-value {{
            color: #f1f0f5;
            font-weight: 600;
            font-size: 1.05rem;
            font-family: 'JetBrains Mono', monospace;
        }}
        .section {{
            background: #12121a;
            padding: 22px;
            border-radius: 12px;
            margin-bottom: 22px;
            border-left: 4px solid #a855f7;
            border-top: 1px solid #2d2d44;
            border-right: 1px solid #2d2d44;
            border-bottom: 1px solid #2d2d44;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .label {{
            color: #94a3b8;
            font-weight: 500;
        }}
        .value {{
            color: #f1f0f5;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
        }}
        .badge-critical {{ background: rgba(248, 113, 113, 0.2); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.4); }}
        .badge-high {{ background: rgba(251, 146, 60, 0.2); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.4); }}
        .badge-medium {{ background: rgba(250, 204, 21, 0.2); color: #facc15; border: 1px solid rgba(250, 204, 21, 0.4); }}
        .badge-low {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }}
        .badge-active {{ background: rgba(74, 222, 128, 0.2); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.4); }}
        .badge-inactive {{ background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.4); }}
        .status-open {{ color: #4ade80; font-weight: 600; }}
        .status-down {{ color: #f87171; }}
        .no-data {{ color: #64748b; font-style: italic; }}
        .error {{ color: #f87171; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 0.88rem;
        }}
        th, td {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid #2d2d44;
        }}
        th {{
            color: #94a3b8;
            text-transform: uppercase;
            font-size: 0.78rem;
            background-color: #0b0b12;
            font-family: 'JetBrains Mono', monospace;
        }}
        td {{
            color: #f1f0f5;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
            margin-bottom: 15px;
        }}
        .stat-card {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid #2d2d44;
            padding: 14px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-val {{
            font-size: 1.6rem;
            font-weight: 700;
            color: #c084fc;
            font-family: 'JetBrains Mono', monospace;
        }}
        .stat-lbl {{
            font-size: 0.75rem;
            color: #94a3b8;
            text-transform: uppercase;
        }}
        .summary-box {{
            background: #0b0b12;
            padding: 18px;
            border-radius: 8px;
            border-left: 4px solid #4ade80;
            border-top: 1px solid #2d2d44;
            border-right: 1px solid #2d2d44;
            border-bottom: 1px solid #2d2d44;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #2d2d44;
            color: #64748b;
            font-size: 0.85rem;
        }}
        code {{
            background: rgba(168, 85, 247, 0.15);
            color: #c084fc;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>Argus Security Assessment Report</h1>
        <div class="report-subtitle">Comprehensive Security Reconnaissance, Vulnerability Audit & Threat Intelligence</div>
    </div>

    <div class="meta">
        <div class="meta-item">
            <span class="meta-label">Target Scope</span>
            <span class="meta-value">{target_escaped}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Assessment Date</span>
            <span class="meta-value">{self.timestamp}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Report ID</span>
            <span class="meta-value">ARGUS-{datetime.now().strftime('%Y%m%d%H%M%S')}</span>
        </div>
    </div>

    {system_section}
    {recon_section}
    {scan_section}
    {fingerprint_section}
    {subdomain_section}
    {web_security_section}
    {web_intelligence_section}
    {summary_section}

    <div class="footer">
        <p>Generated by Argus Cyber Security Intelligence Platform &bull; {self.timestamp}</p>
    </div>
</body>
</html>"""
        return html

    def _build_system_html(self):
        """Build System Information HTML section."""
        if not self.system_info:
            return '<div class="section"><h2>System Information</h2><p class="no-data">No system information available.</p></div>'

        interfaces = self.system_info.get("network_interfaces", [])
        iface_html = ""
        if interfaces:
            iface_rows = "".join([
                f'<div class="info-row"><span class="label">{html_escape.escape(str(iface.get("name", "N/A")))}</span><span class="value">{html_escape.escape(str(iface.get("ip", "N/A")))}</span></div>'
                for iface in interfaces
            ])
            iface_html = f'<h3>Network Interfaces</h3>{iface_rows}'
        else:
            iface_html = '<p class="no-data">No network interfaces found.</p>'

        return f"""<div class="section">
            <h2>System Information</h2>
            <div class="info-row">
                <span class="label">Operating System</span>
                <span class="value">{html_escape.escape(str(self.system_info.get('operating_system', 'N/A')))}</span>
            </div>
            <div class="info-row">
                <span class="label">Hostname</span>
                <span class="value">{html_escape.escape(str(self.system_info.get('hostname', 'N/A')))}</span>
            </div>
            <div class="info-row">
                <span class="label">Current User</span>
                <span class="value">{html_escape.escape(str(self.system_info.get('current_user', 'N/A')))}</span>
            </div>
            <div class="info-row">
                <span class="label">Local IP Address</span>
                <span class="value">{html_escape.escape(str(self.system_info.get('local_ip', 'N/A')))}</span>
            </div>
            <div class="info-row">
                <span class="label">Public IP Address</span>
                <span class="value">{html_escape.escape(str(self.system_info.get('public_ip', 'N/A')))}</span>
            </div>
            {iface_html}
        </div>"""

    def _build_recon_html(self):
        """Build Information Gathering HTML section."""
        if not self.recon_data:
            return '<div class="section"><h2>Information Gathering</h2><p class="no-data">No reconnaissance data available.</p></div>'

        whois = self.recon_data.get("whois", {})
        if whois.get("applicable") and not whois.get("error"):
            whois_html = f"""<div class="info-row"><span class="label">Registrar</span><span class="value">{html_escape.escape(str(whois.get('registrar', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Creation Date</span><span class="value">{html_escape.escape(str(whois.get('creation_date', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Expiration Date</span><span class="value">{html_escape.escape(str(whois.get('expiration_date', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Updated Date</span><span class="value">{html_escape.escape(str(whois.get('updated_date', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Status</span><span class="value">{html_escape.escape(str(whois.get('status', 'N/A')))}</span></div>"""
        elif not whois.get("applicable"):
            whois_html = f'<p class="no-data">{html_escape.escape(str(whois.get("message", "N/A")))}</p>'
        else:
            whois_html = f'<p class="error">{html_escape.escape(str(whois.get("error", "Lookup failed")))}</p>'

        dns = self.recon_data.get("dns", {})
        if dns.get("applicable"):
            records = dns.get("records", {})
            dns_rows = ""
            for rtype in ["a", "mx", "ns", "txt"]:
                values = records.get(rtype, [])
                val_str = ", ".join(values) if values else "None found"
                dns_rows += f'<div class="info-row"><span class="label">{rtype.upper()} Records</span><span class="value">{html_escape.escape(val_str)}</span></div>'
            dns_html = dns_rows
        else:
            dns_html = f'<p class="no-data">{html_escape.escape(str(dns.get("message", "N/A")))}</p>'

        reverse = self.recon_data.get("reverse_dns", {})
        if reverse.get("applicable") and not reverse.get("error"):
            reverse_html = f'<div class="info-row"><span class="label">Hostname</span><span class="value">{html_escape.escape(str(reverse.get("hostname", "N/A")))}</span></div>'
        elif not reverse.get("applicable"):
            reverse_html = f'<p class="no-data">{html_escape.escape(str(reverse.get("message", "N/A")))}</p>'
        else:
            reverse_html = f'<p class="no-data">{html_escape.escape(str(reverse.get("error", "Lookup failed")))}</p>'

        geo = self.recon_data.get("ip_geolocation", {})
        if geo.get("applicable") and not geo.get("error"):
            geo_html = f"""<div class="info-row"><span class="label">Target IP</span><span class="value">{html_escape.escape(str(geo.get('ip_address', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Country</span><span class="value">{html_escape.escape(str(geo.get('country', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Region/State</span><span class="value">{html_escape.escape(str(geo.get('region', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">City</span><span class="value">{html_escape.escape(str(geo.get('city', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">ISP</span><span class="value">{html_escape.escape(str(geo.get('isp', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Organization</span><span class="value">{html_escape.escape(str(geo.get('org', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Time Zone</span><span class="value">{html_escape.escape(str(geo.get('timezone', 'N/A')))}</span></div>"""
        elif not geo.get("applicable"):
            geo_html = f'<p class="no-data">{html_escape.escape(str(geo.get("message", "N/A")))}</p>'
        else:
            geo_html = f'<p class="error">{html_escape.escape(str(geo.get("error", "Lookup failed")))}</p>'

        headers = self.recon_data.get("http_headers", {})
        if not headers.get("error"):
            sec_headers = headers.get("security_headers", {})
            sec_rows = "".join([
                f'<div class="info-row"><span class="label">{html_escape.escape(str(h))}</span><span class="value">{html_escape.escape(str(v))}</span></div>'
                for h, v in sec_headers.items()
            ])
            headers_html = f"""<div class="info-row"><span class="label">Status Code</span><span class="value">{html_escape.escape(str(headers.get('status_code', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Server</span><span class="value">{html_escape.escape(str(headers.get('server', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Content-Type</span><span class="value">{html_escape.escape(str(headers.get('content_type', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Content-Length</span><span class="value">{html_escape.escape(str(headers.get('content_length', 'N/A')))}</span></div>
            <h3>Security Headers</h3>{sec_rows}"""
        else:
            headers_html = f'<p class="error">{html_escape.escape(str(headers.get("error", "Request failed")))}</p>'

        return f"""<div class="section">
            <h2>Information Gathering</h2>
            <h3>WHOIS</h3>{whois_html}
            <h3>DNS Records</h3>{dns_html}
            <h3>Reverse DNS</h3>{reverse_html}
            <h3>IP Geolocation</h3>{geo_html}
            <h3>HTTP Headers</h3>{headers_html}
        </div>"""

    def _build_scan_html(self):
        """Build Network Scan HTML section."""
        if not self.scan_data:
            return '<div class="section"><h2>Network Scan</h2><p class="no-data">No network scan data available.</p></div>'

        open_ports = self.scan_data.get("open_ports", [])
        services = self.scan_data.get("services", [])

        if open_ports:
            port_rows = "".join([
                f'<tr><td>{p.get("port", "N/A")}/{p.get("protocol", "N/A")}</td><td class="status-open">{p.get("state", "N/A")}</td></tr>'
                for p in open_ports
            ])
            ports_html = f"""<table>
                <tr><th>Port</th><th>State</th></tr>
                {port_rows}
            </table>"""
        else:
            ports_html = '<p class="no-data">No open ports found.</p>'

        if services:
            svc_rows = "".join([
                f'<tr><td>{s.get("port", "N/A")}/{s.get("protocol", "N/A")}</td><td>{html_escape.escape(str(s.get("name", "N/A")))}</td><td>{html_escape.escape(str(s.get("version", "Unknown")))}</td></tr>'
                for s in services
            ])
            services_html = f"""<table>
                <tr><th>Port</th><th>Service</th><th>Version</th></tr>
                {svc_rows}
            </table>"""
        else:
            services_html = '<p class="no-data">No services detected.</p>'

        return f"""<div class="section">
            <h2>Network Scan</h2>
            <div class="info-row">
                <span class="label">Host Status</span>
                <span class="value {'status-open' if self.scan_data.get('host_status') == 'Up' else 'status-down'}">{html_escape.escape(str(self.scan_data.get('host_status', 'N/A')))}</span>
            </div>
            <div class="info-row">
                <span class="label">Scan Status</span>
                <span class="value">{html_escape.escape(str(self.scan_data.get('scan_status', 'N/A')))}</span>
            </div>
            <h3>Open Ports</h3>{ports_html}
            <h3>Services</h3>{services_html}
            <p style="margin-top:10px;"><strong>Total Open Ports:</strong> {len(open_ports)}</p>
        </div>"""

    def _build_fingerprint_html(self):
        """Build Website Fingerprinting HTML section."""
        if not self.fingerprint_data:
            return '<div class="section"><h2>Website Fingerprinting</h2><p class="no-data">No website fingerprinting data available.</p></div>'

        if self.fingerprint_data.get("error"):
            return f'<div class="section"><h2>Website Fingerprinting</h2><p class="error">{html_escape.escape(str(self.fingerprint_data.get("error")))}</p></div>'

        fp = self.fingerprint_data
        ts = fp.get("tech_stack") or {}
        meta = fp.get("metadata") or {}
        contacts = fp.get("contacts_and_links") or {}

        web_server = ts.get('web_server') or fp.get('web_server', 'Unknown')
        backend = ts.get('backend') or fp.get('backend', 'Unknown')
        cms = ts.get('cms') or fp.get('cms', 'None Detected')
        frontend = ts.get('frontend_frameworks') or fp.get('frontend', 'None Detected')
        css = ts.get('css_frameworks', 'None Detected')
        cdn = ts.get('cdn_security') or fp.get('cdn', 'None Detected')
        http_ver = ts.get('http_version') or fp.get('http_version', 'HTTP/1.1')

        meta_html = ""
        if meta:
            meta_html = f"""<h3>Scraped Metadata</h3>
            <div class="info-row"><span class="label">Title</span><span class="value">{html_escape.escape(str(meta.get('title', 'N/A')))}</span></div>
            <div class="info-row"><span class="label">Description</span><span class="value">{html_escape.escape(str(meta.get('description', 'N/A')))}</span></div>"""

        contacts_html = ""
        if contacts:
            emails = ", ".join(contacts.get("emails", [])) or "None Detected"
            contacts_html = f"""<h3>Links & Scraped Contacts</h3>
            <div class="info-row"><span class="label">Discovered Links</span><span class="value">{contacts.get('internal_links_count', 0)} Internal | {contacts.get('external_links_count', 0)} External</span></div>
            <div class="info-row"><span class="label">Scraped Emails</span><span class="value">{html_escape.escape(emails)}</span></div>"""

        return f"""<div class="section">
            <h2>Website Fingerprinting & Scraping</h2>
            <h3>Technology Stack</h3>
            <div class="info-row"><span class="label">Web Server</span><span class="value">{html_escape.escape(str(web_server))}</span></div>
            <div class="info-row"><span class="label">Backend Technology</span><span class="value">{html_escape.escape(str(backend))}</span></div>
            <div class="info-row"><span class="label">Content Management System</span><span class="value">{html_escape.escape(str(cms))}</span></div>
            <div class="info-row"><span class="label">Frontend Frameworks</span><span class="value">{html_escape.escape(str(frontend))}</span></div>
            <div class="info-row"><span class="label">CSS Frameworks</span><span class="value">{html_escape.escape(str(css))}</span></div>
            <div class="info-row"><span class="label">CDN / Security</span><span class="value">{html_escape.escape(str(cdn))}</span></div>
            <div class="info-row"><span class="label">HTTP Protocol</span><span class="value">{html_escape.escape(str(http_ver))}</span></div>
            {meta_html}
            {contacts_html}
        </div>"""

    def _build_subdomain_html(self):
        """Build Subdomain Finder HTML section."""
        if not self.subdomain_data:
            return '<div class="section"><h2>Subdomain Finder</h2><p class="no-data">No subdomain data available.</p></div>'

        if self.subdomain_data.get("error"):
            return f'<div class="section"><h2>Subdomain Finder</h2><p class="error">{html_escape.escape(str(self.subdomain_data.get("error")))}</p></div>'

        sub_list = self.subdomain_data.get("subdomains", [])
        if sub_list:
            rows = "".join([
                f'<tr><td>{html_escape.escape(str(s.get("subdomain")))}</td><td class="{"status-open" if s.get("status") == "Active" else "status-down"}">{html_escape.escape(str(s.get("status")))}</td><td>{html_escape.escape(str(s.get("ip_address")))}</td></tr>'
                for s in sub_list
            ])
            table_html = f"""<table>
                <tr><th>Subdomain</th><th>Status</th><th>IP Address</th></tr>
                {rows}
            </table>
            <p style="margin-top: 10px;"><strong>Total Subdomains Found:</strong> {self.subdomain_data.get('total_found', len(sub_list))}</p>"""
        else:
            table_html = '<p class="no-data">No subdomains found.</p>'

        return f"""<div class="section">
            <h2>Subdomain Finder</h2>
            {table_html}
        </div>"""

    def _build_web_security_html(self):
        """Build Web Security Engine Analysis HTML section."""
        if not self.web_security_data:
            return '<div class="section"><h2>Web Security Engine Analysis</h2><p class="no-data">No web security engine analysis data available.</p></div>'

        if self.web_security_data.get("error"):
            return f'<div class="section"><h2>Web Security Engine Analysis</h2><p class="error">{html_escape.escape(str(self.web_security_data.get("error")))}</p></div>'

        ws = self.web_security_data
        sec_headers = ws.get("security_headers", {})
        ssl = ws.get("ssl", {})
        cors = ws.get("cors", {})
        methods = ws.get("http_methods", {})
        dirs = ws.get("directory_discovery", [])
        findings = ws.get("findings", [])
        nikto = ws.get("nikto_scan", {})

        # Security Headers Badges
        header_rows = ""
        if sec_headers:
            header_badges = []
            for h_name, h_info in sec_headers.items():
                st = h_info.get("status", "Missing") if isinstance(h_info, dict) else str(h_info)
                b_class = "badge-active" if st == "Present" or "Configured" in st else ("badge-critical" if st == "Missing" else "badge-medium")
                header_badges.append(f'<span class="badge {b_class}" style="margin: 3px;">{html_escape.escape(h_name)}: {html_escape.escape(st)}</span>')
            header_rows = f'<div style="margin-bottom: 15px;">{"".join(header_badges)}</div>'

        # SSL & CORS
        ssl_html = f"""<div class="info-row"><span class="label">Certificate Status</span><span class="value">{'Valid CA Certificate' if ssl.get('certificate_valid') else 'Invalid / Expired'}</span></div>
        <div class="info-row"><span class="label">Issuer</span><span class="value">{html_escape.escape(str(ssl.get('issuer', 'N/A')))}</span></div>
        <div class="info-row"><span class="label">TLS Versions</span><span class="value">{html_escape.escape(', '.join(ssl.get('tls_versions', [])) if ssl.get('tls_versions') else 'TLSv1.2, TLSv1.3')}</span></div>"""

        cors_html = f"""<div class="info-row"><span class="label">CORS Status</span><span class="value">{html_escape.escape(str(cors.get('status', 'Configured')))}</span></div>
        <div class="info-row"><span class="label">Allow-Origin</span><span class="value"><code>{html_escape.escape(str(cors.get('allow_origin', 'Not Set')))}</code></span></div>
        <div class="info-row"><span class="label">Risky Methods</span><span class="value">{html_escape.escape(', '.join(methods.get('potentially_risky', [])) if methods.get('potentially_risky') else 'None Detected')}</span></div>"""

        # Endpoints
        dirs_html = ""
        if dirs:
            dir_rows = "".join([
                f'<tr><td>GET <code>{html_escape.escape(str(d.get("path")))}</code></td><td>{html_escape.escape(str(d.get("status_code", "200")))}</td></tr>'
                for d in dirs
            ])
            dirs_html = f"""<h3>Discovered Paths & Endpoints ({len(dirs)})</h3>
            <table><tr><th>Path</th><th>Status Code</th></tr>{dir_rows}</table>"""

        # Findings Table
        findings_html = ""
        if findings:
            f_rows = []
            for f in findings:
                sev = (f.get("severity") or "Medium").capitalize()
                sev_badge = "badge-critical" if sev == "Critical" else ("badge-high" if sev == "High" else "badge-medium")
                score = f.get("cvss_score") or f.get("risk_score") or 0
                f_rows.append(
                    f'<tr><td><strong style="color:#ffffff;">{html_escape.escape(str(f.get("title")))}</strong><div style="font-size:0.8rem; color:#94a3b8; margin-top:2px;">{html_escape.escape(str(f.get("description", "")))}</div></td>'
                    f'<td><span class="badge {sev_badge}">{sev} ({score})</span></td></tr>'
                )
            findings_html = f"""<h3>Web Security Findings ({len(findings)})</h3>
            <table><tr><th>Finding Detail</th><th>Severity Score</th></tr>{"".join(f_rows)}</table>"""

        # Nikto
        nikto_html = ""
        if nikto and nikto.get("findings"):
            n_list = nikto.get("findings", [])
            n_rows = "".join([
                f'<tr><td>{html_escape.escape(str(nf.get("description", "")))}</td><td><code>{html_escape.escape(str(nf.get("uri", "/")))}</code></td></tr>'
                for nf in n_list[:15]
            ])
            nikto_html = f"""<h3>Nikto Scanner Findings ({len(n_list)})</h3>
            <table><tr><th>Vulnerability Description</th><th>Target URI</th></tr>{n_rows}</table>"""

        return f"""<div class="section">
            <h2>Web Security Engine Analysis</h2>
            <h3>Security Headers Audit</h3>
            {header_rows}
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                <div><h3>SSL / TLS Inspection</h3>{ssl_html}</div>
                <div><h3>CORS & HTTP Methods</h3>{cors_html}</div>
            </div>
            {dirs_html}
            {findings_html}
            {nikto_html}
        </div>"""

    def _build_web_intelligence_html(self):
        """Build Web Intelligence OSINT HTML section."""
        if not self.web_intelligence_data:
            return '<div class="section"><h2>Web Intelligence Engine (OSINT)</h2><p class="no-data">No web intelligence OSINT data available.</p></div>'

        if self.web_intelligence_data.get("error"):
            return f'<div class="section"><h2>Web Intelligence Engine (OSINT)</h2><p class="error">{html_escape.escape(str(self.web_intelligence_data.get("error")))}</p></div>'

        wi = self.web_intelligence_data
        emails = wi.get("emails", [])
        patterns = wi.get("email_patterns", [])
        socials = wi.get("social_links", [])
        docs = wi.get("documents", [])
        hist_urls = wi.get("historical_urls", [])

        # Stats Grid
        stats_html = f"""<div class="stats-grid">
            <div class="stat-card"><div class="stat-val">{len(emails)}</div><div class="stat-lbl">Harvested Emails</div></div>
            <div class="stat-card"><div class="stat-val">{len(docs)}</div><div class="stat-lbl">Public Documents</div></div>
            <div class="stat-card"><div class="stat-val">{len(socials)}</div><div class="stat-lbl">Social Profiles</div></div>
            <div class="stat-card"><div class="stat-val">{len(hist_urls)}</div><div class="stat-lbl">Wayback URLs</div></div>
        </div>"""

        # Emails Table
        emails_html = ""
        if emails:
            e_rows = "".join([
                f'<tr><td><code>{html_escape.escape(str(e.get("email")))}</code></td>'
                f'<td><span class="badge {"badge-low" if e.get("is_historical") else "badge-active"}">{"Historical Archive" if e.get("is_historical") else "Active Public"}</span></td>'
                f'<td>{html_escape.escape(str(e.get("role_category", "General")))}</td>'
                f'<td>{html_escape.escape(str(e.get("source", "Web")))}</td></tr>'
                for e in emails
            ])
            p_str = f'<p><strong>Inferred Email Patterns:</strong> {html_escape.escape(", ".join(patterns))}</p>' if patterns else ""
            emails_html = f"""<h3>Public Email OSINT & Harvesting</h3>
            {p_str}
            <table><tr><th>Email Address</th><th>Status</th><th>Role Category</th><th>Discovery Source</th></tr>{e_rows}</table>"""

        # Documents Table
        docs_html = ""
        if docs:
            d_rows = "".join([
                f'<tr><td><strong style="color:#ffffff;">{html_escape.escape(str(d.get("filename", "document")))}</strong></td>'
                f'<td><span class="badge badge-low">{html_escape.escape(str(d.get("file_type", "DOC")))}</span></td>'
                f'<td>{html_escape.escape(str(d.get("title", "N/A")))}</td>'
                f'<td>{html_escape.escape(str(d.get("metadata", {}).get("author", "N/A")))}</td></tr>'
                for d in docs
            ])
            docs_html = f"""<h3>Public Downloadable Documents & Metadata ({len(docs)})</h3>
            <table><tr><th>Filename</th><th>Type</th><th>Document Title</th><th>Metadata Author</th></tr>{d_rows}</table>"""

        # Wayback Table
        hist_html = ""
        if hist_urls:
            h_rows = "".join([
                f'<tr><td><code>{html_escape.escape(str(h.get("url")))}</code></td><td><span class="badge badge-medium">{html_escape.escape(str(h.get("timestamp", "Historical")))}</span></td></tr>'
                for h in hist_urls[:15]
            ])
            hist_html = f"""<h3>Internet Archive / Wayback Historical URLs ({len(hist_urls)})</h3>
            <table><tr><th>Indexed Historical URL</th><th>Snapshot Year / Timestamp</th></tr>{h_rows}</table>"""

        return f"""<div class="section">
            <h2>Web Intelligence Engine (OSINT)</h2>
            {stats_html}
            {emails_html}
            {docs_html}
            {hist_html}
        </div>"""

    def _build_summary_html(self):
        """Build Summary HTML section."""
        open_ports_count = len(self.scan_data.get("open_ports", []))
        subdomains_count = self.subdomain_data.get("total_found") or len(self.subdomain_data.get("subdomains", []))
        findings_list = self.web_security_data.get("findings", [])
        emails_count = len(self.web_intelligence_data.get("emails", []))

        crit_count = sum(1 for f in findings_list if (f.get("severity") or "").lower() == "critical")
        high_count = sum(1 for f in findings_list if (f.get("severity") or "").lower() == "high")
        med_count = sum(1 for f in findings_list if (f.get("severity") or "").lower() == "medium")

        if crit_count > 0 or high_count > 0:
            outcome = "ELEVATED RISK - Immediate Security Remediation Advised"
            border_color = "#f87171"
        elif len(findings_list) > 0 or open_ports_count > 0:
            outcome = "MODERATE EXPOSURE - Standard Security Hardening Required"
            border_color = "#fb923c"
        else:
            outcome = "LOW RISK - Target Completed Assessment Cleanly"
            border_color = "#4ade80"

        return f"""<div class="section">
            <h2>Executive Summary</h2>
            <div class="summary-box" style="border-left-color: {border_color};">
                <div class="info-row">
                    <span class="label">Target Scope Host</span>
                    <span class="value">{html_escape.escape(str(self.target))}</span>
                </div>
                <div class="info-row">
                    <span class="label">Scan Completion Status</span>
                    <span class="value">Completed</span>
                </div>
                <div class="info-row">
                    <span class="label">Total Open Network Ports</span>
                    <span class="value">{open_ports_count}</span>
                </div>
                <div class="info-row">
                    <span class="label">Discovered Subdomains</span>
                    <span class="value">{subdomains_count}</span>
                </div>
                <div class="info-row">
                    <span class="label">Web Security Vulnerabilities</span>
                    <span class="value">{len(findings_list)} ({crit_count} Critical, {high_count} High, {med_count} Medium)</span>
                </div>
                <div class="info-row">
                    <span class="label">Harvested OSINT Emails</span>
                    <span class="value">{emails_count}</span>
                </div>
                <div class="info-row">
                    <span class="label">Overall Security Assessment Outcome</span>
                    <span class="value" style="color: {border_color}; font-weight: 700;">{outcome}</span>
                </div>
            </div>
        </div>"""