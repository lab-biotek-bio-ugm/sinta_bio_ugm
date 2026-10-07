"""SINTA + Google Scholar scraping and analysis for Indonesian life-science lecturers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"

UNIVERSITIES = ["UGM", "UI", "ITB", "IPB", "UB"]

# Scrapable sets. raw: folder in data/raw, out: JSON under data/processed,
# cache: folder whose google_scholar/ holds the per-author Scholar cache.
SCRAPE_SETS = {u: {"raw": u, "out": f"{u}/life_science.json", "cache": u} for u in UNIVERSITIES}
SCRAPE_SETS["UGM_BIO"] = {"raw": "UGM_BIO", "out": "UGM_BIO/life_science.json", "cache": "UGM"}

# Analysis sets: which scraped JSONs to combine and how many KMeans clusters.
ANALYSIS_SETS = {
    "ALL": {"members": UNIVERSITIES, "k": 6},
    "UGM_BIO": {"members": ["UGM_BIO"], "k": 12},
}
