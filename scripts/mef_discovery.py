"""MEF / Treasury source discovery utilities."""

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from config import MEF_ALLOWED_DOMAIN, MEF_EXCLUDED_FILE_KEYWORDS, MEF_FILE_EXTENSIONS, MEF_LINK_KEYWORDS, MEF_MAX_CRAWL_PAGES, MEF_MAX_DEPTH, MEF_START_URLS, PROCESSED_DIR, RAW_DIR, SOURCE_MANIFEST_FILE
from io_utils import absolute_url, make_folder, request_bytes, safe_filename, same_domain, stable_hash, url_extension, write_csv


def has_keyword(text):
    text = str(text).lower()
    return any(keyword.lower() in text for keyword in MEF_LINK_KEYWORDS)


def load_manifest_mef_urls():
    if not SOURCE_MANIFEST_FILE.exists():
        return []
    manifest = pd.read_csv(SOURCE_MANIFEST_FILE, dtype=str, keep_default_na=False)
    if "institution" not in manifest.columns or "url" not in manifest.columns:
        return []
    mask = manifest["institution"].str.contains("MEF", case=False, na=False)
    urls = manifest.loc[mask, "url"].drop_duplicates().tolist()
    return [url for url in urls if same_domain(url, MEF_ALLOWED_DOMAIN)]


def get_start_urls():
    urls = []
    for url in load_manifest_mef_urls() + MEF_START_URLS:
        if url not in urls:
            urls.append(url)
    return urls


def keep_link(url, label):
    if not same_domain(url, MEF_ALLOWED_DOMAIN):
        return False
    ext = url_extension(url)
    text = f"{url} {label}"
    if any(keyword.lower() in text.lower() for keyword in MEF_EXCLUDED_FILE_KEYWORDS):
        return False
    if ext in MEF_FILE_EXTENSIONS:
        return has_keyword(text)
    if ext in ["", ".html", ".htm"]:
        return has_keyword(text)
    return False


def extract_html_links(html):
    links = []
    for href in re.findall(r"href=[\"']([^\"']+)[\"']", html, flags=re.I):
        links.append((href, href))
    return links


def links_from_page(page_url):
    html = request_bytes(page_url).decode("utf-8", errors="replace")
    rows = []
    for href, label in extract_html_links(html):
        url = absolute_url(page_url, href)
        if keep_link(url, label):
            rows.append({"source_page": page_url, "url": url, "label": label, "extension": url_extension(url)})
    return rows


def discover_mef_links():
    queue = [(url, 0) for url in get_start_urls()]
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
    parsed = urlparse(url)
    ext = Path(parsed.path).suffix.lower() or ".bin"
    name = safe_filename(Path(parsed.path).name, "mef_file")
    if not name.lower().endswith(ext):
        name = f"{name}{ext}"
    return RAW_DIR / "mef" / f"{stable_hash(url)}_{name}"


def download_mef_links(file_links):
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
