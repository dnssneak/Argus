#!/usr/bin/env python3
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, send_from_directory, redirect, url_for

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import init_db
from api.api_v1 import api_bp
from recon import SystemInfo, TargetRecon
from scanner import NetworkScanner
from report import ReportGenerator
from fingerprint import WebsiteFingerprinter
from subdomain import SubdomainFinder

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# Initialize DB tables on startup
init_db()

# Register REST API blueprint
app.register_blueprint(api_bp)


@app.route("/")
def index():
    """Landing page (Argus v1.0 Home)."""
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    """System info & Security Overview dashboard."""
    sys_info = SystemInfo()
    system_data = sys_info.collect()
    return render_template("dashboard.html", system=system_data)


@app.route("/projects-page")
def projects_page():
    """Projects list view."""
    return render_template("projects.html")


@app.route("/projects/<int:project_id>")
def project_detail_page(project_id):
    """Dedicated Project Dashboard view."""
    return render_template("project_detail.html", project_id=project_id)


@app.route("/assets-page")
def assets_page():
    """Asset inventory view."""
    return render_template("assets.html")


# Standalone scanning routes now redirect to Projects workspace
@app.route("/recon", methods=["GET", "POST"])
@app.route("/fingerprint", methods=["GET", "POST"])
@app.route("/subdomain", methods=["GET", "POST"])
@app.route("/scan", methods=["GET", "POST"])
@app.route("/report", methods=["GET", "POST"])
@app.route("/results")
def legacy_standalone_scanners_redirect():
    """Redirect legacy standalone scanner pages to Projects hub."""
    return redirect("/projects-page")



if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)