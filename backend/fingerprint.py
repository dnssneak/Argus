#!/usr/bin/env python3
"""
Module 4: Dynamic Web Scraping & Technology Profiling
Performs active web scraping and technology signature parsing on a target website.
"""

import socket
import ssl
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


class WebsiteFingerprinter:
    """
    Scrapes live web metadata, headings, assets, forms, links, and contact info,
    and dynamically detects technology stack signatures (web server, backend,
    CMS, JS/CSS frameworks, CDNs, and HTTP protocols).
    """

    def __init__(self, target):
        self.raw_target = target.strip()
        self.url = self._normalize_url(self.raw_target)
        self.domain = self._extract_domain(self.url)

    def _normalize_url(self, url):
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return "http://" + url
        return url

    def _extract_domain(self, url):
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc or parsed.path.split("/")[0]
            return netloc.split(":")[0]
        except Exception:
            return url

    def collect(self):
        """Scrapes the site and runs technology signature detection."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            r = requests.get(self.url, headers=headers, timeout=10, allow_redirects=True)
            html = r.text
            status_code = f"{r.status_code} {r.reason}"
            response_headers = r.headers
            cookies = r.cookies
            final_url = r.url
            self.domain = self._extract_domain(final_url)
        except requests.exceptions.Timeout:
            return {
                "target": self.raw_target,
                "error": "Connection timed out. Target host may be down or unreachable."
            }
        except requests.exceptions.ConnectionError:
            return {
                "target": self.raw_target,
                "error": "Connection failed. Host refused connection or DNS resolution failed."
            }
        except Exception as e:
            return {
                "target": self.raw_target,
                "error": f"Failed to scrape target website: {str(e)}"
            }

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            soup = None

        # 1. Scrape Web Metadata
        metadata = self._scrape_metadata(soup)
        
        # 2. Scrape Structural Content (Headings & Forms)
        headings = self._scrape_headings(soup)
        forms_summary = self._scrape_forms(soup)

        # 3. Scrape Assets (Scripts & Stylesheets)
        assets = self._scrape_assets(soup, final_url)

        # 4. Scrape Links, Emails & Social Profiles
        contacts_and_links = self._scrape_contacts_and_links(soup, html, final_url)

        # 5. Dynamic Technology Stack Detection
        tech_stack = self._detect_tech_stack(soup, html, response_headers, cookies, assets)

        return {
            "target": self.domain,
            "final_url": final_url,
            "status_code": status_code,
            "page_size_kb": round(len(html.encode("utf-8")) / 1024, 2),
            "metadata": metadata,
            "headings": headings,
            "forms_summary": forms_summary,
            "assets": assets,
            "contacts_and_links": contacts_and_links,
            "tech_stack": tech_stack,
        }

    def _scrape_metadata(self, soup):
        if not soup:
            return {}

        title = soup.title.string.strip() if (soup.title and soup.title.string) else "Not Found"
        
        meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
        description = meta_desc.get("content", "").strip() if meta_desc else "Not Found"

        meta_keys = soup.find("meta", attrs={"name": re.compile(r"^keywords$", re.I)})
        keywords = meta_keys.get("content", "").strip() if meta_keys else "Not Found"

        canonical = soup.find("link", attrs={"rel": re.compile(r"^canonical$", re.I)})
        canonical_url = canonical.get("href", "").strip() if canonical else "Not Found"

        # OpenGraph
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")

        html_tag = soup.find("html")
        lang = html_tag.get("lang", "Not Specified") if html_tag else "Not Specified"

        return {
            "title": title,
            "description": description,
            "keywords": keywords,
            "canonical": canonical_url,
            "lang": lang,
            "og_title": og_title.get("content", "").strip() if og_title else None,
            "og_description": og_desc.get("content", "").strip() if og_desc else None,
            "og_image": og_image.get("content", "").strip() if og_image else None,
        }

    def _scrape_headings(self, soup):
        if not soup:
            return {"h1": [], "h2": []}

        h1s = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)][:5]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)][:8]
        return {"h1": h1s, "h2": h2s}

    def _scrape_forms(self, soup):
        if not soup:
            return {"total": 0, "has_login": False, "has_search": False, "form_details": []}

        forms = soup.find_all("form")
        form_details = []
        has_login = False
        has_search = False

        for f in forms:
            action = f.get("action", "")
            method = f.get("method", "GET").upper()
            inputs = f.find_all("input")
            input_types = [i.get("type", "text").lower() for i in inputs]

            if "password" in input_types or "login" in action.lower() or "signin" in action.lower():
                has_login = True
            if "search" in input_types or "q" in [i.get("name", "").lower() for i in inputs]:
                has_search = True

            form_details.append({
                "action": action or "(same page)",
                "method": method,
                "input_count": len(inputs)
            })

        return {
            "total": len(forms),
            "has_login": has_login,
            "has_search": has_search,
            "form_details": form_details[:5]
        }

    def _scrape_assets(self, soup, base_url):
        if not soup:
            return {"scripts": [], "stylesheets": []}

        scripts = []
        for script in soup.find_all("script", src=True):
            src = script["src"].strip()
            full_src = urljoin(base_url, src)
            scripts.append(full_src)

        stylesheets = []
        for link in soup.find_all("link", rel=lambda r: r and "stylesheet" in r.lower(), href=True):
            href = link["href"].strip()
            full_href = urljoin(base_url, href)
            stylesheets.append(full_href)

        return {
            "scripts": scripts[:20],
            "stylesheets": stylesheets[:20]
        }

    def _scrape_contacts_and_links(self, soup, html, base_url):
        # 1. Emails regex extraction
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        raw_emails = set(re.findall(email_pattern, html))
        # Exclude common image extensions or fake emails
        valid_emails = [
            e for e in raw_emails
            if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'))
        ][:10]

        # 2. Links categorization & social detection
        internal_links = set()
        external_links = set()
        social_links = set()
        social_domains = ["twitter.com", "x.com", "github.com", "linkedin.com", "facebook.com", "instagram.com", "youtube.com"]

        if soup:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith("#") or href.startswith("javascript:"):
                    continue
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                netloc = parsed.netloc.lower()

                if any(sd in netloc for sd in social_domains):
                    social_links.add(full_url)
                elif self.domain in netloc:
                    internal_links.add(full_url)
                elif netloc:
                    external_links.add(full_url)

        return {
            "emails": valid_emails,
            "social_links": list(social_links)[:10],
            "internal_links_count": len(internal_links),
            "external_links_count": len(external_links)
        }

    def _detect_tech_stack(self, soup, html, headers, cookies, assets):
        web_server = self._detect_web_server(headers)
        backend = self._detect_backend(headers, cookies, html)
        cms = self._detect_cms(soup, html, headers)
        frontend = self._detect_frontend(soup, html, assets.get("scripts", []))
        css_frameworks = self._detect_css_frameworks(soup, html, assets.get("stylesheets", []))
        cdn_security = self._detect_cdn_security(headers, html)
        http_version = self._detect_http_version(self.domain)

        return {
            "web_server": web_server,
            "backend": backend,
            "cms": cms,
            "frontend_frameworks": frontend,
            "css_frameworks": css_frameworks,
            "cdn_security": cdn_security,
            "http_version": http_version
        }

    def _detect_web_server(self, headers):
        server = headers.get("Server", "").strip()
        if server:
            return server
        return "Unknown"

    def _detect_backend(self, headers, cookies, html):
        detected = []

        # 1. X-Powered-By header
        powered_by = headers.get("X-Powered-By", "")
        if powered_by:
            detected.append(powered_by)

        # 2. Cookies signatures
        cookie_names = [c.name.lower() for c in cookies]
        for name in cookie_names:
            if "phpsessid" in name and "PHP" not in detected:
                detected.append("PHP")
            elif "jsessionid" in name and "Java" not in detected:
                detected.append("Java")
            elif ("aspsessionid" in name or "asp.net_sessionid" in name) and "ASP.NET" not in detected:
                detected.append("ASP.NET")
            elif "django" in name and "Python (Django)" not in detected:
                detected.append("Python (Django)")
            elif "laravel_session" in name and "PHP (Laravel)" not in detected:
                detected.append("PHP (Laravel)")
            elif "next-auth" in name and "Node.js (Next.js)" not in detected:
                detected.append("Node.js (Next.js)")

        # 3. Headers
        if ("X-AspNet-Version" in headers or "X-AspNetMvc-Version" in headers) and "ASP.NET" not in detected:
            detected.append("ASP.NET")
        if "X-Generator" in headers and headers["X-Generator"] not in detected:
            detected.append(headers["X-Generator"])

        # 4. HTML signatures
        if ("wp-content" in html or "wp-includes" in html) and "PHP" not in detected:
            detected.append("PHP")

        return ", ".join(detected) if detected else "Unknown"

    def _detect_cms(self, soup, html, headers):
        html_lower = html.lower()

        # Meta generator tag check
        if soup:
            meta_gen = soup.find("meta", attrs={"name": re.compile(r"^generator$", re.I)})
            if meta_gen and meta_gen.get("content"):
                content = meta_gen.get("content").strip()
                v_match = re.search(r"wordpress\s*([\d\.]+)", content, re.I)
                if v_match:
                    return f"WordPress {v_match.group(1)}"
                if "wordpress" in content.lower():
                    return "WordPress"
                if "joomla" in content.lower():
                    return "Joomla"
                if "drupal" in content.lower():
                    return "Drupal"
                if "ghost" in content.lower():
                    return "Ghost"
                if "shopify" in content.lower():
                    return "Shopify"
                if "wix" in content.lower():
                    return "Wix"
                if "squarespace" in content.lower():
                    return "Squarespace"
                return content

        # Path / URL signatures
        if "wp-content" in html_lower or "wp-includes" in html_lower:
            return "WordPress"
        if "joomla" in html_lower or "media/system/js" in html_lower:
            return "Joomla"
        if "sites/default" in html_lower or "drupal.js" in html_lower:
            return "Drupal"
        if "cdn.shopify.com" in html_lower or "shopify.theme" in html_lower or "x-shopify-stage" in headers:
            return "Shopify"
        if "static1.squarespace.com" in html_lower:
            return "Squarespace"
        if "wixstatic.com" in html_lower:
            return "Wix"

        return "None Detected"

    def _detect_frontend(self, soup, html, script_assets):
        detected = []
        html_lower = html.lower()
        all_scripts_str = " ".join(script_assets).lower()

        # jQuery
        jq_match = re.search(r"jquery[.-]?(\d+\.\d+\.\d+)", all_scripts_str + " " + html_lower)
        if jq_match:
            detected.append(f"jQuery {jq_match.group(1)}")
        elif "jquery" in html_lower or "jquery" in all_scripts_str:
            detected.append("jQuery")

        # React / Next.js
        if "__next" in html_lower or "_next/static" in html_lower or "next.js" in all_scripts_str:
            detected.append("Next.js (React)")
        elif "data-reactroot" in html_lower or "react.production" in html_lower or "_reactlisten" in html_lower or "react" in all_scripts_str:
            detected.append("React")

        # Vue / Nuxt
        if "__nuxt" in html_lower or "nuxt.js" in all_scripts_str:
            detected.append("Nuxt.js (Vue)")
        elif "vue.js" in html_lower or "vue.min.js" in html_lower or "v-bind" in html_lower or "v-out" in html_lower:
            detected.append("Vue.js")

        # Angular
        if "ng-version" in html_lower or "ng-app" in html_lower or "angular" in all_scripts_str:
            v_match = re.search(r"ng-version=\"([^\"]+)\"", html)
            if v_match:
                detected.append(f"Angular {v_match.group(1)}")
            else:
                detected.append("Angular")

        # Alpine.js
        if "alpine.js" in html_lower or "x-data=" in html_lower:
            detected.append("Alpine.js")

        # Svelte
        if "__svelte" in html_lower or "svelte" in all_scripts_str:
            detected.append("Svelte")

        return ", ".join(detected) if detected else "None Detected"

    def _detect_css_frameworks(self, soup, html, stylesheet_assets):
        detected = []
        html_lower = html.lower()
        all_styles_str = " ".join(stylesheet_assets).lower()

        # Bootstrap
        bs_match = re.search(r"bootstrap[.-]?(\d+\.\d+\.\d+)", all_styles_str + " " + html_lower)
        if bs_match:
            detected.append(f"Bootstrap {bs_match.group(1)}")
        elif "bootstrap" in html_lower or "bootstrap" in all_styles_str:
            detected.append("Bootstrap")

        # Tailwind CSS
        if "tailwind" in html_lower or "tailwind" in all_styles_str:
            detected.append("Tailwind CSS")

        # Bulma
        if "bulma" in html_lower or "bulma" in all_styles_str:
            detected.append("Bulma")

        # Foundation
        if "foundation" in html_lower or "foundation" in all_styles_str:
            detected.append("Foundation")

        # Font Awesome
        if "font-awesome" in html_lower or "fontawesome" in all_styles_str:
            detected.append("Font Awesome")

        return ", ".join(detected) if detected else "None Detected"

    def _detect_cdn_security(self, headers, html):
        detected = []
        server = headers.get("Server", "").lower()
        via = headers.get("Via", "").lower()
        x_cache = headers.get("X-Cache", "").lower()

        if "cf-ray" in headers or server == "cloudflare":
            detected.append("Cloudflare CDN/WAF")

        if "x-amz-cf-id" in headers or "x-amz-cf-pop" in headers or "cloudfront" in via:
            detected.append("Amazon CloudFront")

        if "akamai" in x_cache or "akamaighost" in server:
            detected.append("Akamai CDN")

        if "fastly" in x_cache or "x-served-by" in headers:
            detected.append("Fastly CDN")

        if "imperva" in headers or "incap_ses" in html.lower():
            detected.append("Imperva Incapsula")

        return ", ".join(detected) if detected else "None Detected"

    def _detect_http_version(self, domain):
        try:
            context = ssl.create_default_context()
            context.set_alpn_protocols(["h3", "h2", "http/1.1"])
            ip = socket.gethostbyname(domain)
            with socket.create_connection((ip, 443), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    negotiated = ssock.selected_alpn_protocol()
                    if negotiated == "h2":
                        return "HTTP/2"
                    elif negotiated == "h3":
                        return "HTTP/3"
                    elif negotiated == "http/1.1":
                        return "HTTP/1.1"
        except Exception:
            pass
        return "HTTP/1.1"
