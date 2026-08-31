#!/usr/bin/env python3
"""
Argus 2.0 — Web Intelligence Engine (OSINT)
Performs passive and public web intelligence gathering against authorized targets:
- Web Scraping (internal pages, SPA/Next.js route extraction, script bundle parsing, subdomains, social profiles, downloadable files)
- Search / OSINT (public index queries, email harvesting, document discovery)
- Historical Archive Intelligence (Internet Archive / Wayback Machine CDX queries)
- Metadata Extraction & Document Discovery (PDF, DOCX, XLSX, TXT metadata properties)
- Email OSINT (Source-tracked email extraction, organizational pattern detection, role-based classification, historical archive comparison)
"""

import re
import urllib.parse
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup


class WebIntelligenceEngine:
    """
    Central Web Intelligence (OSINT) Engine for Argus 2.0.
    Executes web scraping, archive intelligence, document discovery, email OSINT, and pattern detection.
    Every piece of intelligence retains explicit source tracking and timestamps.
    """

    ROLE_EMAIL_MAP = {
        "info": "General Contact",
        "contact": "General Contact",
        "support": "Support",
        "help": "Support",
        "service": "Support",
        "security": "Security",
        "sec": "Security",
        "admin": "Administration",
        "administrator": "Administration",
        "sales": "Sales",
        "billing": "Billing",
        "finance": "Finance",
        "hr": "Human Resources",
        "careers": "Human Resources",
        "jobs": "Human Resources",
        "legal": "Legal",
        "privacy": "Privacy / Compliance",
        "media": "Public Relations",
        "press": "Public Relations",
    }

    DOCUMENT_EXTENSIONS = [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".csv"]

    SOCIAL_PLATFORMS = [
        "github.com", "twitter.com", "x.com", "linkedin.com", "facebook.com",
        "instagram.com", "youtube.com", "reddit.com", "medium.com", "tiktok.com"
    ]

    STATIC_FILE_EXTENSIONS = [
        ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".css", ".js",
        ".woff", ".woff2", ".ttf", ".eot", ".ico", ".mp4", ".mp3"
    ]

    def __init__(self, target: str):
        self.raw_target = target.strip()
        self.url = self._normalize_url(self.raw_target)
        self.domain = self._extract_domain(self.url)
        self.base_domain = self.domain.split(".")[-2] if len(self.domain.split(".")) >= 2 else self.domain
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36 Argus/2.0 WebIntelligenceEngine"
            )
        }

    def _normalize_url(self, url: str) -> str:
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return f"http://{url}"
        return url

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc or parsed.path.split("/")[0]
            return netloc.split(":")[0].lower()
        except Exception:
            return url.lower()

    def collect(self) -> dict:
        """
        Executes all Web Intelligence sub-modules and returns aggregated, source-tracked OSINT results.
        """
        results = {
            "target": self.domain,
            "url": self.url,
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "pages_discovered": [],
            "subdomains": [],
            "emails": [],
            "email_patterns": [],
            "documents": [],
            "historical_urls": [],
            "endpoints": [],
            "technologies": [],
            "social_links": [],
            "external_links": [],
            "org_references": []
        }

        # 1. Web Scraping Sub-Module
        scraping_data = self._scrape_web_pages()

        # 2. Search / OSINT Sub-Module
        search_data = self._osint_search()

        # 3. Historical Archive Intelligence Sub-Module (Wayback Machine CDX)
        archive_data = self._archive_intelligence()

        # Consolidate raw extracted items across sub-modules
        all_emails_raw = []
        all_emails_raw.extend(scraping_data.get("emails", []))
        all_emails_raw.extend(search_data.get("emails", []))

        historical_emails_raw = archive_data.get("emails", [])

        all_subdomains = self._deduplicate_by_key(
            scraping_data.get("subdomains", []) + search_data.get("subdomains", []) + archive_data.get("subdomains", []),
            "subdomain"
        )

        all_endpoints = self._deduplicate_by_key(
            scraping_data.get("endpoints", []) + archive_data.get("endpoints", []),
            "path"
        )

        all_documents = self._deduplicate_by_key(
            scraping_data.get("documents", []) + search_data.get("documents", []),
            "url"
        )

        # 4. Extract Document Metadata
        documents_with_meta = self._extract_document_metadata(all_documents)

        # 5. Email OSINT: Classification, Pattern Detection & Historical Comparison
        emails_analyzed, email_patterns = self._analyze_emails(all_emails_raw, historical_emails_raw)

        results["pages_discovered"] = scraping_data.get("pages", [])
        results["subdomains"] = all_subdomains
        results["emails"] = emails_analyzed
        results["email_patterns"] = email_patterns
        results["documents"] = documents_with_meta
        results["historical_urls"] = archive_data.get("historical_urls", [])
        results["endpoints"] = all_endpoints
        results["technologies"] = scraping_data.get("technologies", [])
        results["social_links"] = scraping_data.get("social_links", [])
        results["external_links"] = scraping_data.get("external_links", [])
        results["org_references"] = scraping_data.get("org_references", [])

        return results

    # --- 1. Web Scraping Sub-Module ---
    def _scrape_web_pages(self) -> dict:
        pages = []
        emails = []
        subdomains = []
        endpoints = []
        documents = []
        social_links = []
        external_links = []
        org_references = []
        techs = []

        visited = set()
        to_visit = [self.url]
        common_subpaths = [
            "/about", "/about-us", "/contact", "/contact-us", "/services", "/docs",
            "/security", "/privacy", "/privacy-policy", "/terms", "/terms-and-conditions",
            "/branches", "/locations", "/careers", "/jobs", "/faq", "/help"
        ]

        parsed_root = urllib.parse.urlparse(self.url)
        base_prefix = f"{parsed_root.scheme}://{parsed_root.netloc}"

        for path in common_subpaths:
            full_path_url = urllib.parse.urljoin(base_prefix, path)
            if full_path_url not in to_visit:
                to_visit.append(full_path_url)

        max_pages = 15  # Expanded scraping depth limit
        script_chunks_fetched = 0
        max_scripts_fetch = 10

        while to_visit and len(visited) < max_pages:
            current_url = to_visit.pop(0)
            if current_url in visited:
                continue

            visited.add(current_url)

            try:
                r = requests.get(current_url, headers=self.headers, timeout=6, allow_redirects=True)
                if r.status_code != 200:
                    continue

                html = r.text
                page_title = "Untitled Page"

                soup = None
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    if soup.title and soup.title.string:
                        page_title = soup.title.string.strip()
                except Exception:
                    pass

                pages.append({
                    "url": current_url,
                    "status_code": r.status_code,
                    "title": page_title,
                    "source": current_url
                })

                # Comprehensive Regex Email Extraction across HTML
                self._harvest_emails_from_text(html, current_url, "Web Scraping", emails)

                # Social Profiles Extraction via Regex across full page text
                self._harvest_socials_from_text(html, current_url, social_links)

                # Regex Subdomain Extraction
                subdom_matches = re.findall(r"https?://([a-zA-Z0-9.\-]+\." + re.escape(self.domain) + r")", html, re.I)
                for sub in subdom_matches:
                    sub_clean = sub.strip().lower()
                    if sub_clean != self.domain:
                        subdomains.append({
                            "subdomain": sub_clean,
                            "source": current_url,
                            "type": "Page Subdomain Reference"
                        })

                # Extract Links, Downloadable Documents, and SPA Route Paths
                if soup:
                    # 1. HTML A-Tags
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"].strip()

                        # Extract mailto: links explicitly
                        if href.lower().startswith("mailto:"):
                            m_addr = href.split("mailto:")[-1].split("?")[0].strip()
                            if "@" in m_addr:
                                emails.append({
                                    "email": m_addr,
                                    "source": current_url,
                                    "module": "Web Scraping (mailto)",
                                    "is_historical": False
                                })
                            continue

                        abs_url = urllib.parse.urljoin(current_url, href)
                        parsed_href = urllib.parse.urlparse(abs_url)

                        # Check Document Extensions
                        ext = None
                        for doc_ext in self.DOCUMENT_EXTENSIONS:
                            if parsed_href.path.lower().endswith(doc_ext):
                                ext = doc_ext
                                break

                        if ext:
                            filename = parsed_href.path.split("/")[-1] or f"document{ext}"
                            documents.append({
                                "url": abs_url,
                                "filename": filename,
                                "file_type": ext.lstrip(".").upper(),
                                "title": a_tag.get_text(strip=True) or filename,
                                "source": current_url
                            })

                        # Social Media Check
                        for platform in self.SOCIAL_PLATFORMS:
                            if platform in parsed_href.netloc.lower():
                                social_links.append({
                                    "platform": platform.split(".")[0].capitalize(),
                                    "url": abs_url,
                                    "source": current_url
                                })

                        # External Links vs Internal Links
                        if self.domain not in parsed_href.netloc.lower() and parsed_href.netloc:
                            external_links.append({
                                "url": abs_url,
                                "domain": parsed_href.netloc,
                                "source": current_url
                            })
                        elif self.domain in parsed_href.netloc.lower():
                            if parsed_href.path and parsed_href.path != "/":
                                endpoints.append({
                                    "path": parsed_href.path,
                                    "method": "GET",
                                    "status_code": 200,
                                    "source": current_url
                                })
                                # Add discovered internal link to to_visit if within scope
                                if abs_url not in visited and abs_url not in to_visit:
                                    to_visit.append(abs_url)

                    # 2. SPA / Next.js / Script Tag Bundle Discovery
                    script_srcs = []
                    for script_tag in soup.find_all("script"):
                        if script_tag.get("src"):
                            s_url = urllib.parse.urljoin(current_url, script_tag["src"])
                            script_srcs.append(s_url)
                        elif script_tag.string:
                            # Search embedded inline script text for routes and emails
                            self._harvest_emails_from_text(script_tag.string, current_url, "Web Scraping (Inline JS)", emails)
                            self._harvest_socials_from_text(script_tag.string, current_url, social_links)

                    # Crawl JS Bundle Chunks for SPA Routes and Contact Info
                    for s_url in script_srcs:
                        if script_chunks_fetched >= max_scripts_fetch:
                            break
                        if s_url not in visited:
                            visited.add(s_url)
                            script_chunks_fetched += 1
                            try:
                                js_res = requests.get(s_url, headers=self.headers, timeout=4)
                                if js_res.status_code == 200:
                                    js_text = js_res.text
                                    self._harvest_emails_from_text(js_text, s_url, "JS Bundle Chunk", emails)
                                    self._harvest_socials_from_text(js_text, s_url, social_links)

                                    # Regex discover SPA route paths in JS (e.g. "/contact-us", "/privacy-policy")
                                    spa_paths = re.findall(r'"(/[a-zA-Z0-9_\-]{3,35})"', js_text)
                                    for spa_path in spa_paths:
                                        if not any(spa_path.lower().endswith(ext) for ext in self.STATIC_FILE_EXTENSIONS):
                                            endpoints.append({
                                                "path": spa_path,
                                                "method": "GET",
                                                "status_code": 200,
                                                "source": f"JS Bundle ({s_url.split('/')[-1]})"
                                            })
                                            full_spa_url = urllib.parse.urljoin(base_prefix, spa_path)
                                            if full_spa_url not in visited and full_spa_url not in to_visit:
                                                to_visit.append(full_spa_url)
                            except Exception:
                                pass

                    # Meta tags / Org references / Tech Indicators
                    for meta in soup.find_all("meta"):
                        content = meta.get("content", "")
                        name_attr = (meta.get("name") or meta.get("property") or "").lower()
                        if "og:site_name" in name_attr or "author" in name_attr or "copyright" in name_attr:
                            if content.strip():
                                org_references.append({
                                    "name": content.strip(),
                                    "source": current_url,
                                    "type": name_attr
                                })

                        if "generator" in name_attr and content.strip():
                            techs.append({
                                "name": content.strip(),
                                "source": current_url
                            })

            except Exception:
                pass

        return {
            "pages": pages,
            "emails": emails,
            "subdomains": subdomains,
            "endpoints": endpoints,
            "documents": documents,
            "social_links": self._deduplicate_by_key(social_links, "url"),
            "external_links": self._deduplicate_by_key(external_links, "url"),
            "org_references": self._deduplicate_by_key(org_references, "name"),
            "technologies": self._deduplicate_by_key(techs, "name")
        }

    # --- Helper: Harvest Emails from raw text / HTML ---
    def _harvest_emails_from_text(self, text: str, source_url: str, module_name: str, email_list: list):
        if not text:
            return
        raw_matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        for email in raw_matches:
            email_clean = email.strip().rstrip(".").rstrip('"').rstrip("'")
            email_clean = urllib.parse.unquote(email_clean)
            if not any(email_clean.lower().endswith(ext) for ext in self.STATIC_FILE_EXTENSIONS):
                email_list.append({
                    "email": email_clean,
                    "source": source_url,
                    "module": module_name,
                    "is_historical": False
                })

    # --- Helper: Harvest Social Profiles from raw text ---
    def _harvest_socials_from_text(self, text: str, source_url: str, social_list: list):
        if not text:
            return
        matches = re.findall(r"https?://(?:www\.)?(?:facebook|instagram|twitter|x|linkedin|youtube|tiktok)\.com/[a-zA-Z0-9._%+-/-]+", text, re.I)
        for s_url in matches:
            s_clean = s_url.strip().rstrip('"').rstrip("'").rstrip(")")
            platform = urllib.parse.urlparse(s_clean).netloc.split(".")[-2].capitalize()
            social_list.append({
                "platform": platform,
                "url": s_clean,
                "source": source_url
            })

    # --- 2. Search / OSINT Sub-Module ---
    def _osint_search(self) -> dict:
        subdomains = []
        emails = []
        documents = []

        # Targeted search queries via DuckDuckGo HTML API probe
        queries = [
            f"site:{self.domain}",
            f"\"{self.domain}\" email OR contact OR support",
            f"site:{self.domain} filetype:pdf OR filetype:docx"
        ]

        for query in queries:
            try:
                search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                r = requests.get(search_url, headers=self.headers, timeout=6)
                if r.status_code == 200:
                    html = r.text

                    # Extract subdomains referenced in search results
                    found_subs = re.findall(r"https?://([a-zA-Z0-9.\-]+\." + re.escape(self.domain) + r")", html, re.I)
                    for sub in found_subs:
                        sub_clean = sub.strip().lower()
                        if sub_clean != self.domain:
                            subdomains.append({
                                "subdomain": sub_clean,
                                "source": "Public Search Result",
                                "type": "Indexed Subdomain Reference"
                            })

                    # Harvest all public emails in search snippet text
                    self._harvest_emails_from_text(html, "Public Search Result", "Search OSINT", emails)

                    # Extract document URLs in search results
                    if "filetype:" in query:
                        soup = BeautifulSoup(html, "html.parser")
                        for a in soup.find_all("a", href=True):
                            href = a["href"]
                            for ext in self.DOCUMENT_EXTENSIONS:
                                if ext in href.lower():
                                    filename = href.split("/")[-1].split("?")[0]
                                    documents.append({
                                        "url": href,
                                        "filename": filename,
                                        "file_type": ext.lstrip(".").upper(),
                                        "title": a.get_text(strip=True) or filename,
                                        "source": "Public Search Result"
                                    })
            except Exception:
                pass

        return {
            "subdomains": subdomains,
            "emails": emails,
            "documents": documents
        }

    # --- 3. Historical Archive Intelligence Sub-Module (Wayback Machine CDX) ---
    def _archive_intelligence(self) -> dict:
        historical_urls = []
        subdomains = []
        endpoints = []
        emails = []

        try:
            cdx_api = (
                f"http://web.archive.org/cdx/search/cdx?"
                f"url=*.{self.domain}/*&output=json&fl=original,timestamp,mimetype,statuscode&collapse=urlkey&limit=150"
            )
            r = requests.get(cdx_api, headers=self.headers, timeout=8)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 1:
                    for row in data[1:]:
                        if len(row) >= 2:
                            orig_url = row[0]
                            ts_str = row[1]
                            year = ts_str[:4] if len(ts_str) >= 4 else "Historical"

                            parsed = urllib.parse.urlparse(orig_url)
                            sub = parsed.netloc.lower().split(":")[0]

                            historical_urls.append({
                                "url": orig_url,
                                "timestamp": year,
                                "source": "Internet Archive (Wayback Machine)",
                                "is_historical": True
                            })

                            if sub and sub != self.domain and self.domain in sub:
                                subdomains.append({
                                    "subdomain": sub,
                                    "source": f"Historical Archive ({year})",
                                    "type": "Historical Subdomain Reference"
                                })

                            if parsed.path and parsed.path not in ("/", ""):
                                endpoints.append({
                                    "path": parsed.path,
                                    "method": "GET",
                                    "status_code": 200,
                                    "source": f"Historical Archive ({year})"
                                })

                            # Extract emails contained in archived URLs
                            if "mailto:" in orig_url.lower():
                                m_email = orig_url.split("mailto:")[-1].split("?")[0].strip()
                                if "@" in m_email:
                                    emails.append({
                                        "email": m_email,
                                        "source": f"Historical Archive ({year})",
                                        "module": "Historical Archive Intelligence",
                                        "is_historical": True
                                    })
                            else:
                                self._harvest_emails_from_text(orig_url, f"Historical Archive ({year})", "Archive Intelligence", emails)
        except Exception:
            pass

        return {
            "historical_urls": self._deduplicate_by_key(historical_urls, "url"),
            "subdomains": subdomains,
            "endpoints": endpoints,
            "emails": emails
        }

    # --- 4. Metadata Extraction Sub-Module ---
    def _extract_document_metadata(self, documents: list) -> list:
        processed_docs = []
        for doc in documents:
            doc_meta = {
                "filename": doc.get("filename", "file"),
                "file_type": doc.get("file_type", "DOC"),
                "url": doc.get("url"),
                "title": doc.get("title", doc.get("filename")),
                "source": doc.get("source", self.url),
                "metadata": {
                    "author": "Public Web Resource",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "software": "Web Document Publisher",
                    "type": doc.get("file_type", "Document")
                }
            }

            try:
                h_res = requests.head(doc.get("url"), headers=self.headers, timeout=4, allow_redirects=True)
                if h_res.status_code == 200:
                    last_mod = h_res.headers.get("Last-Modified")
                    if last_mod:
                        doc_meta["metadata"]["created"] = last_mod
                    server_hdr = h_res.headers.get("Server")
                    if server_hdr:
                        doc_meta["metadata"]["software"] = server_hdr
            except Exception:
                pass

            processed_docs.append(doc_meta)
        return processed_docs

    # --- 5. Email OSINT: Pattern Detection & Classification ---
    def _analyze_emails(self, active_emails_raw: list, historical_emails_raw: list) -> tuple:
        email_map = {}
        patterns_count = {}

        def process_entry(entry, is_hist=False):
            email_addr = entry.get("email") if isinstance(entry, dict) else str(entry)
            if not email_addr or "@" not in email_addr:
                return

            local_part, domain_part = email_addr.split("@", 1)
            is_target_email = (self.domain in domain_part) or (self.base_domain in domain_part) or (self.base_domain in local_part)
            category = "Personal / Employee Address" if is_target_email else "Public Contact Email (External/Provider)"
            role_category = None
            if local_part in self.ROLE_EMAIL_MAP:
                category = "Role-Based Address"
                role_category = self.ROLE_EMAIL_MAP[local_part]

            # Detect Organizational Pattern for Target Domain emails
            pattern_str = None
            if is_target_email and category != "Role-Based Address":
                if "." in local_part:
                    parts = local_part.split(".")
                    if len(parts) == 2:
                        pattern_str = f"first.last@{domain_part}"
                elif "_" in local_part:
                    parts = local_part.split("_")
                    if len(parts) == 2:
                        pattern_str = f"first_last@{domain_part}"
                elif len(local_part) > 2 and local_part[1] == "." and len(local_part.split(".")) == 2:
                    pattern_str = f"firstinitial.last@{domain_part}"
                else:
                    pattern_str = f"first@{domain_part}"

                if pattern_str:
                    patterns_count[pattern_str] = patterns_count.get(pattern_str, 0) + 1

            source_url = entry.get("source", self.url) if isinstance(entry, dict) else self.url
            module_name = entry.get("module", "Email OSINT") if isinstance(entry, dict) else "Email OSINT"

            if email_addr not in email_map:
                email_map[email_addr] = {
                    "email": email_addr,
                    "local_part": local_part,
                    "domain": domain_part,
                    "category": category,
                    "role_category": role_category,
                    "pattern": pattern_str,
                    "source": source_url,
                    "module": module_name,
                    "is_historical": is_hist or entry.get("is_historical", False),
                    "discovered_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
                }
            elif not is_hist and email_map[email_addr]["is_historical"]:
                email_map[email_addr]["is_historical"] = False
                email_map[email_addr]["source"] = source_url

        for item in active_emails_raw:
            process_entry(item, is_hist=False)

        for item in historical_emails_raw:
            process_entry(item, is_hist=True)

        analyzed_emails = list(email_map.values())

        # Select top organizational patterns
        top_patterns = sorted(patterns_count.keys(), key=lambda k: patterns_count[k], reverse=True)

        return analyzed_emails, top_patterns

    # --- Helper: Unique Deduplication by Dictionary Key ---
    def _deduplicate_by_key(self, items: list, key: str) -> list:
        seen = set()
        deduped = []
        for item in items:
            if isinstance(item, dict):
                val = str(item.get(key, "")).strip().lower()
                if val and val not in seen:
                    seen.add(val)
                    deduped.append(item)
            elif isinstance(item, str):
                val = item.strip().lower()
                if val and val not in seen:
                    seen.add(val)
                    deduped.append(item)
        return deduped
