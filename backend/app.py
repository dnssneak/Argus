#!/usr/bin/env python3
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, send_from_directory

from recon import SystemInfo, TargetRecon
from scanner import NetworkScanner
from report import ReportGenerator
from fingerprint import WebsiteFingerprinter
from subdomain import SubdomainFinder

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')


@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """System info dashboard with module navigation."""
    sys_info = SystemInfo()
    system_data = sys_info.collect()
    return render_template("dashboard.html", system=system_data)


@app.route("/recon", methods=["GET", "POST"])
def recon():
    """Dedicated reconnaissance page."""
    if request.method == "POST":
        target = request.form.get("target", "").strip()
        if not target:
            return render_template("recon.html", error="Please enter a target.")

        recon = TargetRecon(target)
        recon_data = recon.collect()
        return render_template("recon.html", recon=recon_data)

    return render_template("recon.html")


@app.route("/fingerprint", methods=["GET", "POST"])
def fingerprint():
    """Website fingerprinting page."""
    if request.method == "POST":
        target = request.form.get("target", "").strip()
        if not target:
            return render_template("fingerprint.html", error="Please enter a URL or domain.")

        printer = WebsiteFingerprinter(target)
        fingerprint_data = printer.collect()
        return render_template("fingerprint.html", fingerprint=fingerprint_data)

    return render_template("fingerprint.html")


@app.route("/subdomain", methods=["GET", "POST"])
def subdomain():
    """Subdomain enumeration page."""
    if request.method == "POST":
        target = request.form.get("target", "").strip()
        if not target:
            return render_template("subdomain.html", error="Please enter a target domain.")

        finder = SubdomainFinder(target)
        subdomain_data = finder.collect()
        return render_template("subdomain.html", subdomain=subdomain_data)

    return render_template("subdomain.html")


@app.route("/scan", methods=["GET", "POST"])
def scan():
    """Dedicated scanning page."""
    if request.method == "POST":
        target = request.form.get("target", "").strip()
        scan_type = request.form.get("scan_type", "full")

        if not target:
            return render_template("scan.html", error="Please enter a target.")

        scanner = NetworkScanner(target, scan_type)
        scan_data = scanner.collect()
        return render_template("scan.html", scan=scan_data)

    return render_template("scan.html")


@app.route("/report", methods=["GET", "POST"])
def report():
    """Dedicated report generation page."""
    if request.method == "POST":
        target = request.form.get("target", "").strip()
        report_type = request.form.get("report_type", "html")

        system_info = SystemInfo().collect()
        recon_data = None
        scan_data = None
        fingerprint_data = None
        subdomain_data = None

        if target:
            recon_data = TargetRecon(target).collect()
            scan_data = NetworkScanner(target, "full").collect()
            fingerprint_data = WebsiteFingerprinter(target).collect()
            subdomain_data = SubdomainFinder(target).collect()

        generator = ReportGenerator(
            system_info=system_info,
            recon_data=recon_data,
            scan_data=scan_data,
            fingerprint_data=fingerprint_data,
            subdomain_data=subdomain_data
        )

        if report_type == "txt":
            filepath, filename = generator.generate_txt()
        else:
            filepath, filename = generator.generate_html()

        return send_from_directory(generator.report_dir, filename, as_attachment=True)

    return render_template("report.html")


@app.route("/results")
def results():
    """Unified results display (optional direct access)."""
    return render_template("results.html")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)