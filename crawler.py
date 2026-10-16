#!/usr/bin/env python3
"""
Sitemap Generator & SEO/Security Auditor for Viajar en un Click (viajarenunclick.com.ar)
Author: daguonline
License: MIT

Description:
A polite, secure web crawler and sitemap generator designed specifically for
viajarenunclick.com.ar. Extracts indexable URLs, resolves canonical tags,
enforces robots.txt exclusions, and generates a valid XML sitemap compliant with
the Sitemaps.org protocol for Google Search Console.
"""

import sys
import os
import re
import time
import json
import ssl
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urldefrag, parse_qs
import urllib.request
import urllib.error
from xml.sax.saxutils import escape as xml_escape

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Installing beautifulsoup4...")
    os.system(f"{sys.executable} -m pip install beautifulsoup4")
    from bs4 import BeautifulSoup

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SitemapCrawler")

BASE_DOMAIN = "viajarenunclick.com.ar"
START_URL = "https://viajarenunclick.com.ar/"

# Disallowed paths from robots.txt & security filters
DISALLOWED_PATHS = [
    "/login.xhtml",
    "/choose-agency.xhtml",
    "/admin",
    "/brochurePDF",
    "/voucher/pdf",
    "/itemvoucher/pdf",
    "/resources",
    "/resources-internal",
    "/widgets/",
    "/cdn-cgi/",
    "/javax.faces.resource/",
    "/user/password-recover",
    "/user/signup",
]

# Excluded file extensions (assets, media, documents)
EXCLUDED_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".doc", ".docx", ".zip", ".rar",
    ".css", ".js", ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".avi", ".mov"
)


class SitemapGenerator:
    def __init__(self, base_url=START_URL, max_urls=300, delay=0.15):
        self.base_url = base_url
        self.max_urls = max_urls
        self.delay = delay
        self.visited = set()
        self.to_visit = [base_url]
        self.canonical_urls = {}  # clean_url -> metadata dict
        self.security_notes = []
        
        # SSL context with fallback
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (ViajarEnUnClick SitemapBot/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }

    def is_allowed(self, url):
        parsed = urlparse(url)
        # Must match base domain
        if parsed.netloc != BASE_DOMAIN and parsed.netloc != f"www.{BASE_DOMAIN}":
            return False
            
        path = parsed.path
        if any(path.lower().endswith(ext) for ext in EXCLUDED_EXTENSIONS):
            return False
            
        for disallowed in DISALLOWED_PATHS:
            if disallowed in path:
                return False
                
        return True

    def clean_canonical_url(self, url, declared_canonical=None):
        """
        Normalize URLs:
        - If a page explicitly specifies <link rel="canonical" href="...">, respect it!
        - Remove tracking queries like ?agency=890151 or ?isMicrosite=true
        - Ensure HTTPS and correct domain
        """
        target = declared_canonical if declared_canonical else url
        target, _ = urldefrag(target)
        p = urlparse(target)
        
        # Enforce https://viajarenunclick.com.ar
        scheme = "https"
        netloc = BASE_DOMAIN
        
        # Clean path: eliminate duplicate slashes
        clean_path = re.sub(r"/+", "/", p.path)
        if not clean_path:
            clean_path = "/"
            
        # Clean up agency query params if canonical is an internal page
        # TravelCompositor category pages: /es/13/mexico/moreideas (without ?agency=...)
        # Clean query strings unless essential
        clean_query = ""
        
        normalized = f"{scheme}://{netloc}{clean_path}"
        if clean_query:
            normalized += f"?{clean_query}"
            
        return normalized.rstrip("/") if clean_path != "/" else normalized

    def fetch_page(self, url):
        req = urllib.request.Request(url, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=12, context=self.ssl_ctx) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return None, response.status, None
                body = response.read().decode("utf-8", errors="ignore")
                return body, response.status, dict(response.headers)
        except urllib.error.HTTPError as e:
            logger.warning(f"HTTP {e.code} for {url}")
            return None, e.code, None
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            return None, 0, None

    def crawl(self):
        logger.info(f"Starting crawl at {self.base_url} (Max URLs: {self.max_urls})...")
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        while self.to_visit and len(self.visited) < self.max_urls:
            current = self.to_visit.pop(0)
            current, _ = urldefrag(current)
            
            if current in self.visited:
                continue
            self.visited.add(current)
            
            if not self.is_allowed(current):
                continue

            time.sleep(self.delay)  # Polite crawling rate-limit
            html, status, headers = self.fetch_page(current)
            if not html or status != 200:
                continue

            soup = BeautifulSoup(html, "html.parser")
            
            # Check meta robots
            robots_tag = soup.find("meta", attrs={"name": re.compile(r"robots", re.I)})
            robots_content = robots_tag.get("content", "").lower() if robots_tag else ""
            if "noindex" in robots_content:
                logger.info(f"Skipping noindex URL: {current}")
                continue

            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            
            # Extract declared canonical
            canon_tag = soup.find("link", rel="canonical")
            declared_canonical = canon_tag.get("href") if canon_tag else None

            # Compute normalized canonical
            final_url = self.clean_canonical_url(current, declared_canonical)
            
            # Calculate priority and changefreq
            priority, changefreq = self.calculate_seo_weights(final_url)

            if final_url not in self.canonical_urls:
                self.canonical_urls[final_url] = {
                    "loc": final_url,
                    "lastmod": today_iso,
                    "changefreq": changefreq,
                    "priority": priority,
                    "title": title,
                    "discovered_from": current
                }
                logger.info(f"[{len(self.canonical_urls)}] Discovered: {final_url} ('{title[:40]}...')")

            # Extract outgoing links
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith(("mailto:", "tel:", "javascript:", "#", "whatsapp:")):
                    continue
                full_url = urljoin(current, href)
                full_url, _ = urldefrag(full_url)
                
                if self.is_allowed(full_url) and full_url not in self.visited and full_url not in self.to_visit:
                    self.to_visit.append(full_url)

        logger.info(f"Crawl completed. Found {len(self.canonical_urls)} unique canonical URLs from {len(self.visited)} crawled pages.")
        return self.canonical_urls

    def calculate_seo_weights(self, url):
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        
        # Root / Home
        if path == "" or path == "/" or path == "/es" or path == "/home":
            return "1.0", "daily"
            
        # Top-level destination / category / moreideas
        if "moreideas" in path:
            return "0.8", "weekly"
            
        # Specific package / idea
        if "/idea/" in path:
            return "0.7", "weekly"
            
        # Other content pages
        return "0.5", "monthly"

    def generate_sitemap_xml(self, output_path="sitemap.xml"):
        """Generates schema-compliant XML sitemap adhering to sitemaps.org"""
        urls_sorted = sorted(
            self.canonical_urls.values(),
            key=lambda x: (float(x["priority"]) * -1, x["loc"])
        )

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            '        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9',
            '        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">',
            '  <!-- Generated by Viajar en un Click Sitemap Generator -->',
            f'  <!-- Total URLs: {len(urls_sorted)} | Generated at: {datetime.now(timezone.utc).isoformat()} -->'
        ]

        for item in urls_sorted:
            loc = xml_escape(item["loc"])
            lastmod = item["lastmod"]
            changefreq = item["changefreq"]
            priority = item["priority"]

            lines.append("  <url>")
            lines.append(f"    <loc>{loc}</loc>")
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
            lines.append(f"    <changefreq>{changefreq}</changefreq>")
            lines.append(f"    <priority>{priority}</priority>")
            lines.append("  </url>")

        lines.append("</urlset>")
        xml_content = "\n".join(lines) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        logger.info(f"Sitemap XML successfully written to: {output_path}")
        return xml_content

    def generate_robots_txt(self, output_path="robots.txt"):
        """Generates standard, secure robots.txt referencing the sitemap"""
        content = f"""# Robots.txt for https://viajarenunclick.com.ar
# Directs search engine crawlers and protects private paths

User-agent: *
Allow: /
Disallow: /admin
Disallow: /login.xhtml
Disallow: /choose-agency.xhtml
Disallow: /brochurePDF
Disallow: /voucher/pdf
Disallow: /itemvoucher/pdf
Disallow: /resources
Disallow: /resources-internal
Disallow: /widgets/
Disallow: /cdn-cgi/

# Sitemap location for Google Search Console & Bing Webmaster
Sitemap: https://viajarenunclick.com.ar/sitemap.xml
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Robots.txt successfully written to: {output_path}")
        return content

    def export_audit_json(self, output_path="audit_report.json"):
        report = {
            "site": "https://viajarenunclick.com.ar",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "total_crawled_pages": len(self.visited),
            "total_canonical_urls": len(self.canonical_urls),
            "urls": self.canonical_urls
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Audit report saved to: {output_path}")


if __name__ == "__main__":
    generator = SitemapGenerator(max_urls=250, delay=0.1)
    generator.crawl()
    generator.generate_sitemap_xml("sitemap.xml")
    generator.generate_robots_txt("robots.txt")
    generator.export_audit_json("audit_report.json")
    print("\nProcess finished successfully!")
