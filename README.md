# Argus 2.0

> **A Comprehensive Web-Based Network Intelligence, Attack Surface Management, and AI-Powered Security Auditing Platform.**

Argus 2.0 is a modern, unified cybersecurity platform designed for security analysts, penetration testers, and enterprise threat defenders. Built on Python (Flask) and a robust REST API backend, Argus 2.0 provides project-centric attack surface mapping, automated risk engine scoring, contextual finding correlation, AI-driven remediation guides, and multi-tenant user isolation.

---

## Key Features & Capability Modules

### 1. **User Authentication & Multi-Tenant Isolation**
* **Secure Registration & Login**: Full-screen authentication UI with password strength evaluation, scrypt/PBKDF2 password hashing, and cryptographically signed session tokens.
* **Strict Object-Level Authorization (BOLA/IDOR Protection)**: Every REST API endpoint (`/api/v1/*`) enforces `@require_auth` and scopes projects, targets, assets, scans, and findings strictly to the authenticated user.

### 2. **Project-Centric Workspace Hub**
* **Project Inventory**: Group targets, assets, and scans by project scope. Supports project status filtering (`ACTIVE`, `ARCHIVED`), keyword search, target management, and project deletion protection.
* **Interactive Dashboard**: Dedicated project dashboards providing real-time vulnerability statistics, high-risk asset summaries, discovery sources, and timeline events.

### 3. **Asset Inventory & Dynamic Risk Engine**
* **Contextual Risk Scoring**: Dynamically calculates asset risk scores (0–100) and maps them into severity tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`).
* **Contributing Risk Factors**: Categorizes risk weights by internet exposure, open sensitive ports (e.g. 3389, 445, 22, 3306), administrative endpoints, and technology vulnerabilities.
* **Asset Timeline History & Change Detector**: Tracks asset changes across sequential scans (port changes, web footprint updates, and status transitions).

### 4. **Finding Correlation & Contextual Prioritization Engine**
* **Automated Correlation**: Correlates security observations across affected assets, targets, and scans while preserving original finding severity.
* **Contextual Urgency Priority**: Derives priority levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFORMATIONAL`) and urgency scores (0-100) with detailed contributing factor explanations.
* **Lifecycle Tracking**: Identifies finding lifecycles (`NEW`, `EXISTING`, `RECURRING`, `RESOLVED`) across repeated scan passes.

### 5. **AI Remediation Advisor Engine (`AIRemediationAdvisor`)**
* **Live LLM Integration**: Connects to LiteRouter, OpenRouter (`gemma-3-27b-it:free` or custom models), Google Gemini, or OpenAI API to generate tailored, 2-bullet actionable security fix guides for novel/uncertain vulnerabilities.
* **Local Heuristic AI Fallback**: Zero-dependency built-in AI synthesizer that guarantees actionable remediation output even when offline or without an API key.

### 6. **Web Security Engine & OSINT Intelligence**
* **Web Security Engine**: Audits security headers (`CSP`, `HSTS`, `X-Frame-Options`), SSL/TLS certificates, CORS policies, HTTP methods, sensitive directory discovery (`.git`, `.env`, `/admin`), and Nikto vulnerability scans.
* **Web Intelligence Engine**: Extracts emails, email pattern formulas, role categories, social media footprints, downloadable document metadata (PDFs, DOCX), and historical Wayback Machine URL archives.

### 7. **Graph Topology Visualizer**
* **Interactive Relationship Graph**: Maps multi-node topology links (`SUBDOMAIN_OF`, `RESOLVES_TO`, `HAS_PORT`, `RUNS_SERVICE`, `USES_TECH`, `HAS_ENDPOINT`) for individual assets or full project scopes.

### 8. **Professional Report Generator**
* Compiles all gathered reconnaissance, port scans, web fingerprints, OSINT data, and prioritized findings.
* Export formats:
  * **Plain Text (.txt)**: Structured ASCII report for log archives.
  * **HTML (.html)**: Modern, dark-mode report with color-coded severity badges and tabbed findings.

---

## Tech Stack

* **Backend Core**: Python 3.8+ (Flask, SQLAlchemy ORM, Pydantic)
* **Database Layer**: PostgreSQL (Supabase pooler support) with fallback to SQLite (`argus.db`)
* **Frontend**: Vanilla HTML5, Vanilla CSS3 (Dark-mode responsive design system), Vanilla JavaScript ES6
* **Security & Auth**: `itsdangerous` URLSafeTimedSerializer, `werkzeug.security` (scrypt/PBKDF2)
* **Reconnaissance Utilities**: Nmap CLI, Python Sockets, `requests`, `beautifulsoup4`, `dnspython`, `python-whois`, `psutil`
* **AI Providers**: OpenRouter / LiteRouter, Google Gemini REST API, OpenAI Chat Completions API

---

## Repository Structure

```text
Argus/
├── backend/
│   ├── api/
│   │   └── api_v1.py           # REST API routes with @require_auth enforcement
│   ├── db/
│   │   └── database.py         # SQLAlchemy engine, PostgreSQL/SQLite connection setup
│   ├── models/
│   │   ├── models.py           # ORM schemas (User, Project, Asset, Finding, Scan, Relationship, etc.)
│   │   └── schemas.py          # Pydantic validation schemas
│   ├── services/
│   │   ├── ai_advisor.py       # AI Remediation Advisor (LiteRouter / OpenRouter / Fallback)
│   │   ├── asset_correlator.py # Asset relationship topology graph generator
│   │   ├── asset_processor.py  # Scan result ingestion and asset deduplication
│   │   ├── auth_service.py     # User registration, password hashing & token verification
│   │   ├── change_detector.py  # Asset change comparison & timeline history
│   │   ├── finding_correlator.py # Contextual finding correlation & prioritization engine
│   │   ├── project_service.py  # Project workspace CRUD & activity logging
│   │   └── risk_engine.py      # Asset risk scoring (0-100) & severity calculator
│   ├── app.py                  # Main Flask application entry point
│   ├── scanner.py              # Safe Nmap port scanner
│   ├── recon.py                # OSINT Target Reconnaissance & SystemInfo
│   ├── fingerprint.py          # Web technology footprinting & CMS detector
│   ├── subdomain.py            # Subdomain enumeration (crt.sh + wordlists)
│   ├── web_security.py         # Headers, SSL/TLS, CORS & Nikto integration
│   ├── web_intelligence.py     # Scraping, email/social OSINT & Wayback archives
│   ├── report.py               # Professional HTML/TXT report generator
│   └── tests/                  # Pytest automated test suite (52 unit tests)
├── frontend/
│   ├── static/
│   │   ├── css/style.css       # Complete dark-theme design system
│   │   └── js/
│   │       ├── app.js          # Main dashboard logic & asset graph controls
│   │       └── auth.js         # Authentication UI handlers & password strength evaluator
│   └── templates/              # HTML Jinja2 templates (dashboard, projects, assets, findings, login, etc.)
├── .env.example                # Documented environment configuration template
└── vercel.json                 # Vercel cloud deployment manifest
```

---

## Installation & Setup

### Prerequisites

1. **Python 3.8+** installed.
2. **Nmap** installed and added to your system PATH:
   * **Windows**: Download from [nmap.org](https://nmap.org/download.html) and check "Register Nmap path".
   * **Linux**: `sudo apt-get install nmap`
   * **macOS**: `brew install nmap`

### Step-by-Step Local Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dnssneak/Argus.git
   cd Argus
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env`:*
   ```env
   # PostgreSQL / Supabase or SQLite
   DATABASE_URL=sqlite:///backend/argus.db

   # Cryptographic Keys (Required for session security)
   SECRET_KEY=YOUR_GENERATED_SECRET_KEY
   SECURITY_SALT=YOUR_GENERATED_SECURITY_SALT

   # Optional AI Remediation Advisor
   OPENROUTER_API_KEY=your_openrouter_key_here
   FLASK_DEBUG=False
   PORT=5001
   ```

---

## Running the Application

1. **Start the server**:
   ```bash
   python backend/app.py
   ```

2. **Access the Portal**:
   Open `http://localhost:5001` in your browser.

3. **Run Automated Test Suite**:
   ```bash
   python -m pytest backend/tests
   ```
---

## Security & Compliance Disclaimer

*Argus 2.0 is designed strictly for authorized security auditing, threat hunting, and educational research. Scanning targets without explicit prior written authorization from the system owner is illegal. The developers assume no liability for unauthorized usage or damages.*
