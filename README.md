#  Argus

> **A Comprehensive Web-Based Network Intelligence, Reconnaissance, and Security Auditing Suite.**

Argus is a modern, unified network intelligence tool designed for security analysts, network administrators, and penetration testers. It provides a lightweight, highly intuitive web-based interface built on Flask to collect information about local environments, perform active and passive reconnaissance on remote targets, discover subdomains, identify web application stacks, and generate clean, structured security assessment reports.

---

##  Key Features & Modules

Argus is built using a modular architecture where each component is isolated and dedicated to a specific aspect of target intelligence:

### 1.  Local System Information Dashboard
* Gathers hardware and host environment information about the hosting machine.
* Tracks operating system name/version, local and public IP addresses, hostname, current logged-in user, and lists active network interfaces (using `psutil`).

### 2.  Target Reconnaissance & OSINT (`TargetRecon`)
* **WHOIS lookup**: Retrieves registrar details, registration, updating, and expiration dates.
* **DNS Resolution**: Queries `A`, `MX`, `NS`, and `TXT` records.
* **Reverse DNS**: Resolves IP addresses back to domain names.
* **IP Geolocation**: Leverages the IP-API to determine country, region, city, ISP, ASN, timezone, and geographic coordinates of the target.
* **HTTP Headers Analysis**: Evaluates HTTP response codes, server headers, content attributes, and checks for critical security headers (`X-Frame-Options`, `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `X-XSS-Protection`).

### 3.  Safe Network Port Scanning (`NetworkScanner`)
* Executing automted, safe `Nmap` scans with no shell injection risk.
* **Ping Scan (`ping`)**: Verifies host reachability without invasive port probes (`nmap -sn`).
* **Full TCP Scan (`full`)**: Checks 20 commonly targeted ports and performs service/version detection (`nmap -sV --open`).

### 4.  Web Fingerprinting (`WebsiteFingerprinter`)
* **Web Server Detection**: Identifies hosting daemons (Nginx, Apache, IIS, etc.).
* **Backend Language/Framework Detection**: Analyzes cookies and server signatures to identify languages like PHP, Java, ASP.NET, Django, or Next.js.
* **CMS Enumeration**: Detects platforms like WordPress (with version detection), Joomla, Drupal, Ghost, and Shopify.
* **Frontend Library Identification**: Sniffs scripts for Bootstrap, jQuery, React, Angular, and Vue.js.
* **CDN Footprinting**: Detects proxy caches including Cloudflare, Amazon CloudFront, Akamai, and Fastly.
* **Protocol Negotiation**: Resolves SSL ALPN protocols to determine support for HTTP/1.1, HTTP/2, or HTTP/3.

### 5.  Subdomain Enumeration (`SubdomainFinder`)
* Combines **passive certificate logs** parsing via `crt.sh` (Certificate Transparency) with a **fallback dictionary enumeration** of standard subdomains.
* Resolves discovered subdomains to their IP addresses and validates their status (Active/Inactive).

### 6.  Professional Report Generation (`ReportGenerator`)
* Compiles all gathered reconnaissance data, network scans, website fingerprints, and subdomain lists.
* Generates downloadable reports in two formats:
  * **Plain Text (.txt)**: Structured ASCII report, perfect for console logs.
  * **HTML (.html)**: Beautiful, modern dark-themed web report with color-coded open ports, tabular subdomains, and formatted JSON attributes.

---

##  Tech Stack

Argus utilizes a modern, clean, and lightweight tech stack:

* **Backend / Core Engine**: Python 3.8+
* **Web Framework**: Flask (Python)
* **Frontend View Template Engine**: Jinja2 (HTML5)
* **Design & Styling**: Vanilla CSS3 (Custom-built dark-mode layout with responsive grid styling)
* **Interactions**: Vanilla JavaScript
* **Underlying Scanner Utility**: Nmap CLI
* **Key Dependencies**:
  * `requests`: For API querying and HTTP banner grabbing.
  * `beautifulsoup4`: For parsing web headers and scripts.
  * `dnspython`: For custom DNS resolutions.
  * `python-whois`: For WHOIS registry inquiries.
  * `psutil`: For collecting OS interface information.

---

##  Repository Structure

```text
Argus/
├── backend/               # Backend logic & modules
│   ├── app.py             # Flask web server and routing definitions
│   ├── recon.py           # Module 1 (SystemInfo) & Module 2 (TargetRecon)
│   ├── scanner.py         # Module 3 (NetworkScanner - Nmap integration)
│   ├── fingerprint.py     # Module 4 (WebsiteFingerprinter - Tech stack detection)
│   ├── subdomain.py       # Module 5 (SubdomainFinder - crt.sh + wordlist)
│   ├── report.py          # Module 6 (ReportGenerator - HTML & TXT formatting)
│   └── requirements.txt   # Python package list
├── frontend/              # Frontend assets and views
│   ├── static/            # Static assets
│   │   ├── script.js      # Interactive dashboard controls and charts
│   │   └── style.css      # Dark-mode security themed styling
│   └── templates/         # Jinja2 HTML templates
│       ├── base.html      # Standard layout container
│       ├── index.html     # Landing / main portal page
│       ├── dashboard.html # System status page
│       ├── recon.html     # Targets OSINT page
│       ├── scan.html      # Port scanner configuration & results
│       ├── fingerprint.html # Web tech stack results
│       ├── subdomain.html # Subdomain listing page
│       ├── report.html    # Export menu and generator page
│       └── results.html   # Consolidated quick results view
└── reports/               # Output directory for generated reports (Auto-created)
```

---

##  Installation & Setup

### Prerequisites

1. **Python 3.8+** must be installed.
2. **Nmap** must be installed and added to your system's Environment Variables (PATH).
   * **Windows**: Download the installer from the [Nmap Official Site](https://nmap.org/download.html). Ensure you check "Register Nmap path" during setup.
   * **Linux/Debian**: Run `sudo apt-get install nmap`.
   * **macOS**: Run `brew install nmap`.

### Step-by-Step Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dnssneak/Argus.git
   cd Argus
   ```

2. **Create a Python Virtual Environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate the Virtual Environment**:
   * **Windows (Command Prompt)**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   * **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   * **Linux / macOS**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install Python dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

---

##  Running the Application

1. **Start the local Flask dev server**:
   ```bash
   python backend/app.py
   ```
   *By default, the server will launch in debug mode on port `5000`.*

2. **Access the application**:
   Open your preferred web browser and navigate to:
   ```text
   http://localhost:5000
   ```

3. **Generating Reports**:
   Once you've run target queries or network scans, navigate to the **Report Generator** page to build, export, and download comprehensive HTML or TXT reports instantly.

---

##  Disclaimer

*This application is built strictly for authorized security auditing, educational purposes, and administrative network analysis. Scanning systems and networks without explicit prior written authorization from the owner is illegal and unethical. The authors assume no liability for misuse, damages, or potential security/legal issues resulting from this software.*

---

## Happy Reconnaissance!

Thank you for choosing **Argus** as your network auditing companion. May your network visibility be high, your open ports expected, and your configurations secure. 

If you encounter any bugs, have feature requests, or wish to contribute, please feel free to open a Pull Request or file an issue in the repository.

*Keep scanning safely!* 
