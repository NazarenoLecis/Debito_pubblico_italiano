"""Utility condivise per la pipeline dati.

Tutti i valori letti dalle fonti ufficiali vengono conservati come stringhe.
Questo evita conversioni implicite su codici, date, virgole decimali e note.
"""

import csv
import hashlib
import io
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

from config import REQUEST_TIMEOUT_SECONDS


def utc_now_string():
    """Restituisce un timestamp UTC stabile per cataloghi e metadati."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_folder(path):
    """Svuota una cartella e la ricrea. Serve per run riproducibili."""
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def make_folder(path):
    """Crea una cartella se non esiste."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(text, fallback="file"):
    """Trasforma URL, nomi di file e fogli Excel in nomi portabili."""
    text = str(text).replace("\\", "/").split("/")[-1]
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_.")
    return text or fallback


def stable_hash(text, length=10):
    """Crea un identificativo breve e stabile per URL o nomi lunghi."""
    return hashlib.sha1(str(text).encode("utf-8", errors="ignore")).hexdigest()[:length]


def request_bytes(url):
    """Scarica un file da una fonte ufficiale e restituisce i bytes."""
    headers = {"User-Agent": "debt-data-pipeline/1.0"}
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code != 200:
        preview = response.text[:500] if response.text else ""
        raise RuntimeError(f"HTTP {response.status_code} durante il download di {url}\n{preview}")
    return response.content


def save_bytes(content, path):
    """Salva bytes su disco."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def write_json(payload, path):
    """Salva un dizionario in formato JSON leggibile."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_csv(df, path):
    """Salva un DataFrame in CSV UTF-8 senza indice."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


def decode_text(raw):
    """Decodifica bytes provando gli encoding più comuni delle fonti italiane."""
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def infer_delimiter(text):
    """Stima il separatore di un file CSV."""
    sample = "\n".join([line for line in text.splitlines()[:80] if line.strip()])
    if not sample:
        return ";"
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,|\t").delimiter
    except csv.Error:
        counts = {sep: sample.count(sep) for sep in [";", ",", "\t", "|"]}
        return max(counts, key=counts.get)


def find_header_row(text, delimiter):
    """Trova la riga di intestazione più probabile in un CSV con preambolo."""
    scored = []
    for index, line in enumerate(text.splitlines()):
        if line.strip():
            scored.append((index, line.count(delimiter)))
    if not scored:
        return 0
    max_score = max(score for _, score in scored)
    if max_score == 0:
        return 0
    for index, score in scored:
        if score == max_score:
            return index
    return 0


def read_csv_bytes(raw):
    """Legge un CSV da bytes e restituisce DataFrame più metadati tecnici."""
    text, encoding = decode_text(raw)
    delimiter = infer_delimiter(text)
    header_row = find_header_row(text, delimiter)
    last_error = None
    for skiprows in [header_row, 0]:
        try:
            df = pd.read_csv(
                io.StringIO(text),
                sep=delimiter,
                dtype=str,
                engine="python",
                keep_default_na=False,
                na_values=[],
                skiprows=skiprows,
            )
            df.columns = [str(column).strip() for column in df.columns]
            return df.dropna(axis=1, how="all"), {
                "encoding": encoding,
                "delimiter": delimiter,
                "header_row": skiprows,
            }
        except Exception as error:
            last_error = error
    raise RuntimeError(f"Parsing CSV fallito: {last_error}")


def absolute_url(base_url, href):
    """Rende assoluto un link relativo."""
    return urljoin(base_url, href)


def same_domain(url, domain):
    """Verifica se un URL appartiene al dominio richiesto."""
    return urlparse(url).netloc.lower() == domain.lower()


def url_extension(url):
    """Estrae l'estensione dal path di un URL."""
    return Path(urlparse(url).path).suffix.lower()


def extract_zip(zip_path, output_dir):
    """Estrae uno ZIP usando nomi file sanitizzati e restituisce i file estratti."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            target = output_dir / safe_filename(member.filename, "zip_member")
            target.write_bytes(archive.read(member.filename))
            extracted.append(target)
    return extracted
