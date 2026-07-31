#!/usr/bin/env python3
"""
Module 6: Report Generation
Compiles scan results into downloadable TXT and HTML reports.
"""

import os
from datetime import datetime


class ReportGenerator:
    """
    Generates structured reports from system info, recon, and scan data.
    """

    def __init__(self, system_info=None, recon_data=None, scan_data=None, fingerprint_data=None, subdomain_data=None):
        self.system_info = system_info or {}
        self.recon_data = recon_data or {}
        self.scan_data = scan_data or {}
        self.fingerprint_data = fingerprint_data or {}
        self.subdomain_data = subdomain_data or {}
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.report_dir = os.path.join(os.path.dirname(__file__), "reports")
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
        width = 65

        # Header Block
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append("|" + "ARGUS SECURITY ASSESSMENT".center(width - 2) + "|")
        lines.append("|" + f"Generated: {self.timestamp}".center(width - 2) + "|")
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append("")

        # Target Information
        target = self.scan_data.get("target") or self.recon_data.get("target") or "N/A"
        lines.append("[ REPORT TARGET ]")
        lines.append(f"  Target Host : {target}")
        lines.append(f"  Report Time : {self.timestamp}")
        lines.append("")

        # System Information Section
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

        # Information Gathering Section
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
                
                # Security Headers
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

        # Network Scan Section
        lines.append("[ 3. NETWORK SCAN (NMAP) ]")
        lines.append("=" * width)
        if self.scan_data:
            lines.append(f"  Host Status : {self.scan_data.get('host_status', 'N/A')}")
            lines.append(f"  Scan Status : {self.scan_data.get('scan_status', 'N/A')}")
            lines.append("")

            open_ports = self.scan_data.get("open_ports", [])
            services = self.scan_data.get("services", [])

            # Map services by (port, protocol)
            services_map = {}
            for svc in services:
                port_proto = (svc.get("port"), svc.get("protocol"))
                services_map[port_proto] = svc

            if open_ports:
                lines.append("  Open Ports & Services:")
                lines.append("    " + "-" * 57)
                lines.append(f"    {'PORT':<10} {'STATE':<10} {'SERVICE':<15} {'VERSION'}")
                lines.append("    " + "-" * 57)
                for port in open_ports:
                    p_num = port.get('port', 'N/A')
                    proto = port.get('protocol', 'N/A')
                    port_str = f"{p_num}/{proto}"
                    state = port.get('state', 'N/A')
                    
                    svc = services_map.get((p_num, proto), {})
                    svc_name = svc.get('name', 'N/A')
                    svc_version = svc.get('version', '')
                    
                    lines.append(f"    {port_str:<10} {state:<10} {svc_name:<15} {svc_version or 'N/A'}")
                lines.append("    " + "-" * 57)
            else:
                lines.append("  Open Ports: None found")
            lines.append("")
            lines.append(f"  Total Open Ports: {len(open_ports)}")
        else:
            lines.append("  No network scan data available.")
        lines.append("")

        # Website Fingerprinting Section
        lines.append("[ 4. WEBSITE FINGERPRINTING & SCRAPING ]")
        lines.append("=" * width)
        if self.fingerprint_data and not self.fingerprint_data.get("error"):
            fp = self.fingerprint_data
            ts = fp.get("tech_stack") or {}
            meta = fp.get("metadata") or {}
            contacts = fp.get("contacts_and_links") or {}
            forms = fp.get("forms_summary") or {}
            assets = fp.get("assets") or {}

            # Tech Stack
            lines.append("  Technology Stack:")
            lines.append(f"    {'Web Server':<24} : {ts.get('web_server') or fp.get('web_server', 'Unknown')}")
            lines.append(f"    {'Backend Tech':<24} : {ts.get('backend') or fp.get('backend', 'Unknown')}")
            lines.append(f"    {'CMS':<24} : {ts.get('cms') or fp.get('cms', 'None Detected')}")
            lines.append(f"    {'Frontend Frameworks':<24} : {ts.get('frontend_frameworks') or fp.get('frontend', 'None Detected')}")
            lines.append(f"    {'CSS Frameworks':<24} : {ts.get('css_frameworks', 'None Detected')}")
            lines.append(f"    {'CDN / Security':<24} : {ts.get('cdn_security') or fp.get('cdn', 'None Detected')}")
            lines.append(f"    {'HTTP Protocol':<24} : {ts.get('http_version') or fp.get('http_version', 'HTTP/1.1')}")
            lines.append("")

            # Scraped Metadata
            if meta:
                lines.append("  Scraped Web Metadata:")
                lines.append(f"    {'Page Title':<24} : {meta.get('title', 'N/A')}")
                lines.append(f"    {'Meta Description':<24} : {meta.get('description', 'N/A')}")
                lines.append(f"    {'Language':<24} : {meta.get('lang', 'N/A')}")
                lines.append("")

            # Links & Contacts
            if contacts:
                lines.append("  Links & Contacts Scraped:")
                lines.append(f"    Internal Links Count     : {contacts.get('internal_links_count', 0)}")
                lines.append(f"    External Links Count     : {contacts.get('external_links_count', 0)}")
                emails = contacts.get("emails", [])
                if emails:
                    lines.append(f"    Scraped Emails           : {', '.join(emails)}")
                lines.append("")

            # Assets & Forms
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

        # Subdomain Finder Section
        lines.append("[ 5. SUBDOMAIN FINDER ]")
        lines.append("=" * width)
        if self.subdomain_data and not self.subdomain_data.get("error"):
            sub_list = self.subdomain_data.get("subdomains", [])
            if sub_list:
                lines.append(f"    Total Subdomains Found : {self.subdomain_data.get('total_found', 0)}")
                lines.append("")
                lines.append(f"    {'Subdomain':<38} {'Status':<10} {'IP Address'}")
                lines.append("    " + "-" * (width - 6))
                for s in sub_list:
                    lines.append(f"    {s.get('subdomain'):<38} {s.get('status'):<10} {s.get('ip_address')}")
            else:
                lines.append("    No subdomains found.")
        elif self.subdomain_data and self.subdomain_data.get("error"):
            lines.append(f"    Error: {self.subdomain_data.get('error')}")
        else:
            lines.append("    No subdomain data available.")
        lines.append("")

        # Summary Section
        lines.append("[ 6. EXECUTIVE SUMMARY ]")
        lines.append("=" * width)
        if self.scan_data:
            lines.append(f"  Scan Status       : {self.scan_data.get('scan_status', 'N/A')}")
            lines.append(f"  Open Ports Found  : {len(self.scan_data.get('open_ports', []))}")
            outcome = "Scan completed successfully." if self.scan_data.get("scan_status") == "Completed" else "Scan encountered issues."
            lines.append(f"  Overall Outcome   : {outcome}")
        else:
            lines.append("  No scan data available for summary.")
        lines.append("")

        # Footer Block
        lines.append("+" + "-" * (width - 2) + "+")
        lines.append("|" + "END OF REPORT".center(width - 2) + "|")
        lines.append("+" + "-" * (width - 2) + "+")

        return "\n".join(lines)

    def _build_html_content(self):
        """Build HTML report content."""
        target = self.scan_data.get("target") or self.recon_data.get("target") or "N/A"

        # Build sections
        system_section = self._build_system_html()
        recon_section = self._build_recon_html()
        scan_section = self._build_scan_html()
        fingerprint_section = self._build_fingerprint_html()
        subdomain_section = self._build_subdomain_html()
        summary_section = self._build_summary_html()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Argus Report - {target}</title>
    <style>
        body {{
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0a0a0f;
            color: #f1f0f5;
            line-height: 1.6;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            color: #a855f7;
            text-align: center;
            border-bottom: 2px solid #2d2d44;
            padding-bottom: 15px;
        }}
        h2 {{
            color: #8b5cf6;
            margin-top: 30px;
            padding-bottom: 8px;
            border-bottom: 1px solid #2d2d44;
        }}
        h3 {{
            color: #d946ef;
            margin-top: 20px;
        }}
        .meta {{
            background-color: #1a1a2e;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #2d2d44;
        }}
        .meta-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }}
        .meta-label {{
            color: #a8a5b8;
        }}
        .meta-value {{
            color: #f1f0f5;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
        }}
        .section {{
            background-color: #12121a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #a855f7;
            border-top: 1px solid #2d2d44;
            border-right: 1px solid #2d2d44;
            border-bottom: 1px solid #2d2d44;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #2d2d44;
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .label {{
            color: #a8a5b8;
            font-weight: 500;
        }}
        .value {{
            color: #f1f0f5;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
        }}
        .status-open {{
            color: #4ade80;
            font-weight: 600;
        }}
        .status-down {{
            color: #f87171;
        }}
        .no-data {{
            color: #6b6680;
            font-style: italic;
        }}
        .error {{
            color: #f87171;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #2d2d44;
        }}
        th {{
            color: #a8a5b8;
            text-transform: uppercase;
            font-size: 0.85rem;
            background-color: #0a0a0f;
        }}
        td {{
            color: #f1f0f5;
        }}
        .summary-box {{
            background-color: #0a0a0f;
            padding: 15px;
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
            color: #6b6680;
        }}
    </style>
</head>
<body>
    <h1>Argus Report</h1>

    <div class="meta">
        <div class="meta-item">
            <span class="meta-label">Scan Date</span>
            <span class="meta-value">{self.timestamp}</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Target</span>
            <span class="meta-value">{target}</span>
        </div>
    </div>

    {system_section}
    {recon_section}
    {scan_section}
    {fingerprint_section}
    {subdomain_section}
    {summary_section}

    <div class="footer">
        <p>Generated by Argus</p>
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
                f'<div class="info-row"><span class="label">{iface.get("name", "N/A")}</span><span class="value">{iface.get("ip", "N/A")}</span></div>'
                for iface in interfaces
            ])
            iface_html = f'<h3>Network Interfaces</h3>{iface_rows}'
        else:
            iface_html = '<p class="no-data">No network interfaces found.</p>'

        return f"""<div class="section">
            <h2>System Information</h2>
            <div class="info-row">
                <span class="label">Operating System</span>
                <span class="value">{self.system_info.get('operating_system', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="label">Hostname</span>
                <span class="value">{self.system_info.get('hostname', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="label">Current User</span>
                <span class="value">{self.system_info.get('current_user', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="label">Local IP Address</span>
                <span class="value">{self.system_info.get('local_ip', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="label">Public IP Address</span>
                <span class="value">{self.system_info.get('public_ip', 'N/A')}</span>
            </div>
            {iface_html}
        </div>"""

    def _build_recon_html(self):
        """Build Information Gathering HTML section."""
        if not self.recon_data:
            return '<div class="section"><h2>Information Gathering</h2><p class="no-data">No reconnaissance data available.</p></div>'

        # WHOIS
        whois = self.recon_data.get("whois", {})
        if whois.get("applicable") and not whois.get("error"):
            whois_html = f"""<div class="info-row"><span class="label">Registrar</span><span class="value">{whois.get('registrar', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Creation Date</span><span class="value">{whois.get('creation_date', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Expiration Date</span><span class="value">{whois.get('expiration_date', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Updated Date</span><span class="value">{whois.get('updated_date', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Status</span><span class="value">{whois.get('status', 'N/A')}</span></div>"""
        elif not whois.get("applicable"):
            whois_html = f'<p class="no-data">{whois.get("message", "N/A")}</p>'
        else:
            whois_html = f'<p class="error">{whois.get("error", "Lookup failed")}</p>'

        # DNS
        dns = self.recon_data.get("dns", {})
        if dns.get("applicable"):
            records = dns.get("records", {})
            dns_rows = ""
            for rtype in ["a", "mx", "ns", "txt"]:
                values = records.get(rtype, [])
                if values:
                    val_str = ", ".join(values)
                else:
                    val_str = "None found"
                dns_rows += f'<div class="info-row"><span class="label">{rtype.upper()} Records</span><span class="value">{val_str}</span></div>'
            dns_html = dns_rows
        else:
            dns_html = f'<p class="no-data">{dns.get("message", "N/A")}</p>'

        # Reverse DNS
        reverse = self.recon_data.get("reverse_dns", {})
        if reverse.get("applicable") and not reverse.get("error"):
            reverse_html = f'<div class="info-row"><span class="label">Hostname</span><span class="value">{reverse.get("hostname", "N/A")}</span></div>'
        elif not reverse.get("applicable"):
            reverse_html = f'<p class="no-data">{reverse.get("message", "N/A")}</p>'
        else:
            reverse_html = f'<p class="no-data">{reverse.get("error", "Lookup failed")}</p>'

        # IP Geolocation
        geo = self.recon_data.get("ip_geolocation", {})
        if geo.get("applicable") and not geo.get("error"):
            geo_html = f"""<div class="info-row"><span class="label">Target IP</span><span class="value">{geo.get('ip_address', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Country</span><span class="value">{geo.get('country', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Region/State</span><span class="value">{geo.get('region', 'N/A')}</span></div>
            <div class="info-row"><span class="label">City</span><span class="value">{geo.get('city', 'N/A')}</span></div>
            <div class="info-row"><span class="label">ISP</span><span class="value">{geo.get('isp', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Organization</span><span class="value">{geo.get('org', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Time Zone</span><span class="value">{geo.get('timezone', 'N/A')}</span></div>"""
            if geo.get("latitude") and geo.get("longitude"):
                geo_html += f'<div class="info-row"><span class="label">Coordinates</span><span class="value">{geo.get("latitude")}, {geo.get("longitude")}</span></div>'
        elif not geo.get("applicable"):
            geo_html = f'<p class="no-data">{geo.get("message", "N/A")}</p>'
        else:
            geo_html = f'<p class="error">{geo.get("error", "Lookup failed")}</p>'

        # HTTP Headers
        headers = self.recon_data.get("http_headers", {})
        if not headers.get("error"):
            sec_headers = headers.get("security_headers", {})
            sec_rows = "".join([
                f'<div class="info-row"><span class="label">{h}</span><span class="value">{v}</span></div>'
                for h, v in sec_headers.items()
            ])
            headers_html = f"""<div class="info-row"><span class="label">Status Code</span><span class="value">{headers.get('status_code', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Server</span><span class="value">{headers.get('server', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Content-Type</span><span class="value">{headers.get('content_type', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Content-Length</span><span class="value">{headers.get('content_length', 'N/A')}</span></div>
            <h3>Security Headers</h3>{sec_rows}"""
        else:
            headers_html = f'<p class="error">{headers.get("error", "Request failed")}</p>'

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
                f'<tr><td>{s.get("port", "N/A")}/{s.get("protocol", "N/A")}</td><td>{s.get("name", "N/A")}</td><td>{s.get("version", "Unknown")}</td></tr>'
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
                <span class="value {'status-open' if self.scan_data.get('host_status') == 'Up' else 'status-down'}">{self.scan_data.get('host_status', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="label">Scan Status</span>
                <span class="value">{self.scan_data.get('scan_status', 'N/A')}</span>
            </div>
            <h3>Open Ports</h3>{ports_html}
            <h3>Services</h3>{services_html}
            <p><strong>Total Open Ports:</strong> {len(open_ports)}</p>
        </div>"""

    def _build_summary_html(self):
        """Build Summary HTML section."""
        if not self.scan_data:
            return '<div class="section"><h2>Summary</h2><p class="no-data">No scan data available for summary.</p></div>'

        total_ports = len(self.scan_data.get("open_ports", []))
        status = self.scan_data.get("scan_status", "N/A")
        outcome = "Scan completed successfully" if status == "Completed" else "Scan encountered issues"

        return f"""<div class="section">
            <h2>Summary</h2>
            <div class="summary-box">
                <div class="info-row">
                    <span class="label">Scan Completion Status</span>
                    <span class="value">{status}</span>
                </div>
                <div class="info-row">
                    <span class="label">Total Open Ports</span>
                    <span class="value">{total_ports}</span>
                </div>
                <div class="info-row">
                    <span class="label">Overall Outcome</span>
                    <span class="value">{outcome}</span>
                </div>
            </div>
        </div>"""

    def _build_fingerprint_html(self):
        """Build Website Fingerprinting HTML section."""
        if not self.fingerprint_data:
            return '<div class="section"><h2>Website Fingerprinting</h2><p class="no-data">No website fingerprinting data available.</p></div>'

        if self.fingerprint_data.get("error"):
            return f'<div class="section"><h2>Website Fingerprinting</h2><p class="error">{self.fingerprint_data.get("error")}</p></div>'

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
            <div class="info-row"><span class="label">Title</span><span class="value">{meta.get('title', 'N/A')}</span></div>
            <div class="info-row"><span class="label">Description</span><span class="value">{meta.get('description', 'N/A')}</span></div>"""

        contacts_html = ""
        if contacts:
            emails = ", ".join(contacts.get("emails", [])) or "None Detected"
            contacts_html = f"""<h3>Links & Scraped Contacts</h3>
            <div class="info-row"><span class="label">Discovered Links</span><span class="value">{contacts.get('internal_links_count', 0)} Internal | {contacts.get('external_links_count', 0)} External</span></div>
            <div class="info-row"><span class="label">Scraped Emails</span><span class="value">{emails}</span></div>"""

        return f"""<div class="section">
            <h2>Website Fingerprinting & Scraping</h2>
            <h3>Technology Stack</h3>
            <div class="info-row"><span class="label">Web Server</span><span class="value">{web_server}</span></div>
            <div class="info-row"><span class="label">Backend Technology</span><span class="value">{backend}</span></div>
            <div class="info-row"><span class="label">Content Management System</span><span class="value">{cms}</span></div>
            <div class="info-row"><span class="label">Frontend Frameworks</span><span class="value">{frontend}</span></div>
            <div class="info-row"><span class="label">CSS Frameworks</span><span class="value">{css}</span></div>
            <div class="info-row"><span class="label">CDN / Security</span><span class="value">{cdn}</span></div>
            <div class="info-row"><span class="label">HTTP Protocol</span><span class="value">{http_ver}</span></div>
            {meta_html}
            {contacts_html}
        </div>"""

    def _build_subdomain_html(self):
        """Build Subdomain Finder HTML section."""
        if not self.subdomain_data:
            return '<div class="section"><h2>Subdomain Finder</h2><p class="no-data">No subdomain data available.</p></div>'

        if self.subdomain_data.get("error"):
            return f'<div class="section"><h2>Subdomain Finder</h2><p class="error">{self.subdomain_data.get("error")}</p></div>'

        sub_list = self.subdomain_data.get("subdomains", [])
        if sub_list:
            rows = "".join([
                f'<tr><td>{s.get("subdomain")}</td><td class="{"status-open" if s.get("status") == "Active" else "status-down"}">{s.get("status")}</td><td>{s.get("ip_address")}</td></tr>'
                for s in sub_list
            ])
            table_html = f"""<table>
                <tr><th>Subdomain</th><th>Status</th><th>IP Address</th></tr>
                {rows}
            </table>
            <p style="margin-top: 10px;"><strong>Total Subdomains Found:</strong> {self.subdomain_data.get('total_found', 0)}</p>"""
        else:
            table_html = '<p class="no-data">No subdomains found.</p>'

        return f"""<div class="section">
            <h2>Subdomain Finder</h2>
            {table_html}
        </div>"""