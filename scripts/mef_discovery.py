"""MEF / Treasury source discovery utilities.

The functions search only official Treasury pages listed in config.py. They find
CSV, XLS, XLSX and ZIP files with detailed information on government securities,
auctions, maturities, ISINs, rates and redemptions.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from config import MEF_ALLOWED_DOMAIN, MEF_FILE_EXTENSIONS, MEF_LINK_KEYWORDS, MEF_MAX_CRAWL_PAGES, MEF_MAX_DEPTH, MEF_START_URLS, PROCESSED_DIR, RAW_DIR
from io_utils import absolute_url, make_folder, request_bytes, safe_filename, same_domain, stable_hash, url_extension, write_csv


def has_keyword(text):
    """Return True if a text contains a configured debt-related keyword."""
    text = str(text).lower()
    return any(keyword.lower() in text for keyword in MEF_LINK_KEYWORDS)


def keep_link(url, label):
    """Keep internal Treasury links that point to relevant pages or files."""
    if not same_domain(url, MEF_ALLOWED_DOMAIN):
        return False
    ext = url_extension(url)
    text = f"{url} {label}"
    if ext in MEF_FILE_EXTENSIONS:
        return has_keyword(text)
    if ext in ["", ".html", ".htm"]:
        return has_keyword(text)
    return False


def extract_html_links(html):
    """Extract href and visible label pairs using only the Python standard library."""
    pattern = re.compile(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", flags=re.I | re.S)
    rows = []
    for href, label_html in pattern.findall(html):
        label = re.sub(r"<[^>]+>", " ", label_html)
        label = re.sub(r"\s+", " ", label).strip()
        rows.append((href, label))
    return rows


def links_from_page(page_url):
    """Read one Treasury page and extract relevant links."""
    html = request_bytes(page_url).decode("utf-8", errors="replace")
    rows = []
    for href, label in extract_html_links(html):
        url = absolute_url(page_url, href)
        if keep_link(url, label):
            rows.append({"source_page": page_url, "url": url, "label": label, "extension": url_extension(url)})
    return rows


def discover_mef_links():
    """Discover official MEF file links and pages from configured start URLs."""
    queue = [(url, 0) for url in MEF_START_URLS]
    visited = set()
    files = {}
    pages = []
    while queue and len(visited) < MEF_MAX_CRAWL_PAGES:
        page_url, depth = queue.pop(0)
        if page_url in visited or depth > MEF_MAX_DEPTH:
            continue
        visited.add(page_url)
        try:
            links = links_from_page(page_url)
            pages.append({"url": page_url, "depth": depth, "status": "ok", "error": ""})
        except Exception as error:
            pages.append({"url": page_url, "depth": depth, "status": "error", "error": str(error)})
            continue
        for link in links:
            if link["extension"] in MEF_FILE_EXTENSIONS:
                files[link["url"]] = link
            elif link["url"] not in visited:
                queue.append((link["url"], depth + 1))
    return list(files.values()), pages


def local_path_for_url(url):
    """Create a deterministic local path for a Treasury source URL."""
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower() or ".bin"
    name = safe_filename(Path(parsed.path).name, "mef_file")
    if not name.lower().endswith(ext):
        name = f"{name}{ext}"
    return RAW_DIR / "mef" / f"{stable_hash(url)}_{name}"


def download_mef_links(file_links):
    """Download discovered files and return a catalogue DataFrame."""
    make_folder(RAW_DIR / "mef")
    rows = []
    for link in file_links:
        try:
            content = request_bytes(link["url"])
            local_file = local_path_for_url(link["url"])
            local_file.parent.mkdir(parents=True, exist_ok=True)
            local_file.write_bytes(content)
            rows.append({**link, "local_file": str(local_file.as_posix()), "size_bytes": len(content), "status": "ok", "error": ""})
        except Exception as error:
            rows.append({**link, "local_file": "", "size_bytes": 0, "status": "error", "error": str(error)})
    return pd.DataFrame(rows)


def build_mef_discovery_catalog():
    """Save discovery outputs under data/processed/mef."""
    output_dir = PROCESSED_DIR / "mef"
    make_folder(output_dir)
    links, pages = discover_mef_links()
    catalog = download_mef_links(links)
    write_csv(pd.DataFrame(pages), output_dir / "mef_pages.csv")
    write_csv(pd.DataFrame(links), output_dir / "mef_links.csv")
    write_csv(catalog, output_dir / "mef_download_catalog.csv")
    return catalog


def main():
    catalog = build_mef_discovery_catalog()
    print(f"MEF files found: {len(catalog)}")


if __name__ == "__main__":
    main()
