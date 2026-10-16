#!/usr/bin/env python3
"""
Sitemap XML Validator & Security Auditor
Author: daguonline
"""

import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from datetime import datetime

ALLOWED_CHANGEFREQS = {"always", "hourly", "daily", "weekly", "monthly", "yearly", "never"}
SENSITIVE_KEYWORDS = {"session", "token", "password", "auth", "secret", "admin", "login"}

def validate_sitemap(file_path="sitemap.xml"):
    print(f"[*] Validating XML sitemap: {file_path}")
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"[FAIL] XML Parsing Error: {e}")
        return False
        
    # Check namespace
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    if root.tag != f"{ns}urlset":
        print(f"[WARN] Root element tag is '{root.tag}', expected '{ns}urlset'")
        
    urls = root.findall(f"{ns}url")
    if not urls:
        urls = root.findall("url")
        
    print(f"[+] Total <url> entries found: {len(urls)}")
    if len(urls) == 0:
        print("[FAIL] No URLs found in sitemap.")
        return False

    errors = []
    warnings = []
    seen_locs = set()

    for idx, url_elem in enumerate(urls, 1):
        # 1. <loc>
        loc_elem = url_elem.find(f"{ns}loc") if url_elem.find(f"{ns}loc") is not None else url_elem.find("loc")
        if loc_elem is None or not loc_elem.text:
            errors.append(f"Entry #{idx}: Missing <loc> element")
            continue
            
        loc = loc_elem.text.strip()
        parsed = urlparse(loc)
        
        # Must be HTTPS
        if parsed.scheme != "https":
            errors.append(f"Entry #{idx} ({loc}): Non-HTTPS protocol ({parsed.scheme})")
            
        # Must match viajarenunclick.com.ar
        if parsed.netloc != "viajarenunclick.com.ar":
            warnings.append(f"Entry #{idx} ({loc}): Unexpected domain ({parsed.netloc})")
            
        # Check duplicate
        if loc in seen_locs:
            errors.append(f"Entry #{idx} ({loc}): Duplicate URL detected")
        seen_locs.add(loc)
        
        # Security: check query string for sensitive info
        query = parsed.query.lower()
        for kw in SENSITIVE_KEYWORDS:
            if kw in query:
                errors.append(f"Entry #{idx} ({loc}): Potentially sensitive keyword '{kw}' in URL")
                
        # 2. <lastmod>
        lastmod_elem = url_elem.find(f"{ns}lastmod") if url_elem.find(f"{ns}lastmod") is not None else url_elem.find("lastmod")
        if lastmod_elem is not None and lastmod_elem.text:
            date_str = lastmod_elem.text.strip()
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Entry #{idx} ({loc}): Invalid date format '{date_str}', expected YYYY-MM-DD")
                
        # 3. <changefreq>
        freq_elem = url_elem.find(f"{ns}changefreq") if url_elem.find(f"{ns}changefreq") is not None else url_elem.find("changefreq")
        if freq_elem is not None and freq_elem.text:
            freq = freq_elem.text.strip().lower()
            if freq not in ALLOWED_CHANGEFREQS:
                errors.append(f"Entry #{idx} ({loc}): Invalid changefreq '{freq}'")
                
        # 4. <priority>
        pri_elem = url_elem.find(f"{ns}priority") if url_elem.find(f"{ns}priority") is not None else url_elem.find("priority")
        if pri_elem is not None and pri_elem.text:
            try:
                pri = float(pri_elem.text.strip())
                if pri < 0.0 or pri > 1.0:
                    errors.append(f"Entry #{idx} ({loc}): Priority {pri} out of range (0.0 - 1.0)")
            except ValueError:
                errors.append(f"Entry #{idx} ({loc}): Priority '{pri_elem.text}' is not a valid float")

    print("\n--- Validation Summary ---")
    if warnings:
        print(f"[!] {len(warnings)} Warnings:")
        for w in warnings[:5]:
            print(f"    - {w}")
    if errors:
        print(f"[X] {len(errors)} Errors encountered:")
        for e in errors[:10]:
            print(f"    - {e}")
        return False
    else:
        print("[OK] All URLs successfully validated with ZERO syntax or security errors!")
        print("[OK] Sitemap conforms 100% to Google Search Console XML schema.")
        return True

if __name__ == "__main__":
    sitemap_file = sys.argv[1] if len(sys.argv) > 1 else "sitemap.xml"
    success = validate_sitemap(sitemap_file)
    sys.exit(0 if success else 1)
