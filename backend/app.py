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

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/static'))

import secrets

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    secret_key = secrets.token_hex(32)
app.config['SECRET_KEY'] = secret_key
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Initialize DB tables on startup
init_db()

# Register REST API blueprint
app.register_blueprint(api_bp)


@app.route("/")
def index():
    """Landing page (Argus v1.0 Home)."""
    return render_template("index.html")


@app.route("/login")
def login():
    """Argus Full-Screen Login Page."""
    return render_template("login.html")


@app.route("/signup")
def signup():
    """Argus Full-Screen Sign Up Page."""
    return render_template("signup.html")



def is_authenticated():
    """Helper to check if request has valid argus_token cookie or header."""
    token = request.cookies.get("argus_token")
    if not token and request.headers.get("Authorization", "").startswith("Bearer "):
        token = request.headers.get("Authorization", "").split(" ", 1)[1].strip()
    if not token:
        return False
    from db.database import SessionLocal
    from services.auth_service import AuthService
    db = SessionLocal()
    try:
        user = AuthService.verify_token(db, token)
        return user is not None
    finally:
        db.close()


@app.route("/dashboard")
def dashboard():
    """System info & Security Overview dashboard (Protected)."""
    if not is_authenticated():
        return redirect(url_for("login"))
    sys_info = SystemInfo()
    system_data = sys_info.collect()
    return render_template("dashboard.html", system=system_data)


@app.route("/projects-page")
def projects_page():
    """Projects list view (Protected)."""
    if not is_authenticated():
        return redirect(url_for("login"))
    return render_template("projects.html")


@app.route("/projects/<int:project_id>")
def project_detail_page(project_id):
    """Dedicated Project Dashboard view (Protected)."""
    if not is_authenticated():
        return redirect(url_for("login"))
    return render_template("project_detail.html", project_id=project_id)


@app.route("/assets-page")
def assets_page():
    """Asset inventory view (Protected)."""
    if not is_authenticated():
        return redirect(url_for("login"))
    return render_template("assets.html")


@app.route("/findings-page")
def findings_page():
    """Global Prioritized Findings view (Protected)."""
    if not is_authenticated():
        return redirect(url_for("login"))
    return render_template("findings.html")


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
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)