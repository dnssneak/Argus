#!/usr/bin/env python3
from flask import Flask, render_template, request, send_from_directory

from recon import SystemInfo, TargetRecon
from scanner import NetworkScanner
from report import ReportGenerator

app = Flask(__name__)


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

        if target:
            recon_data = TargetRecon(target).collect()
            scan_data = NetworkScanner(target, "full").collect()

        generator = ReportGenerator(
            system_info=system_info,
            recon_data=recon_data,
            scan_data=scan_data
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
    app.run(host="0.0.0.0", port=5000, debug=True)