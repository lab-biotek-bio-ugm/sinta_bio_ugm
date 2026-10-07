"""Roster loading and SINTA / Google Scholar scraping (needs network)."""
import json
import logging
from datetime import datetime

import pandas as pd

from . import PROCESSED, RAW, SCRAPE_SETS


def extract_birth_date(nidn):
    """NIDN digits 3-8 are ddmmyy; returns 'dd/mm/19yy' or None."""
    if pd.isnull(nidn) or len(nidn) < 8:
        return None
    # ponytail: assumes 19xx births, wrong for lecturers born 2000+
    return nidn[2:4] + "/" + nidn[4:6] + "/19" + nidn[6:8]


def calculate_age(birth_date):
    if pd.isnull(birth_date):
        return None
    return datetime.now().year - int(birth_date.split("/")[-1])


def load_roster(raw_dir):
    """Read <raw_dir>/*_data_NIDN.txt, drop names listed in *_bio_retired.txt, add birth_date/age."""
    folder = RAW / raw_dir
    df_nidn = pd.read_csv(next(folder.glob("*_data_NIDN.txt")), dtype={"id": str, "NIDN": str})
    df_retired = pd.read_csv(next(folder.glob("*_bio_retired.txt")))
    df = df_nidn[~df_nidn.name.isin(df_retired.Retired)].copy()
    df["birth_date"] = df["NIDN"].apply(extract_birth_date)
    df["age"] = df["birth_date"].apply(calculate_age)
    return df.rename(columns={"name": "name_inputted"})


def fetch_scholar(sinta_id, google_id, author_name, cache_dir):
    """Google Scholar profile for one author, cached as <cache_dir>/<sinta_id>.json."""
    from scholarly import MaxTriesExceededException, scholarly

    outfile = cache_dir / f"{sinta_id}.json"
    if outfile.exists():
        return json.loads(outfile.read_text())
    if pd.isnull(google_id):
        logging.warning(f"Unable to get google scholar id for {sinta_id}")
        return {}
    try:
        author = scholarly.search_author_id(google_id)
    except MaxTriesExceededException as e:
        logging.warning(e)
        author = next(scholarly.search_author(author_name))
    # sanity check: only keep profiles whose name matches the roster
    if author["name"].lower() != author_name.lower():
        return {}
    author = scholarly.fill(author, sections=[])
    outfile.write_text(json.dumps(author, indent=2))
    return author


def scrape(dataset):
    """Roster -> SINTA -> Google Scholar, written to data/processed/<out>. Returns the merged frame."""
    import sinta

    cfg = SCRAPE_SETS[dataset]
    df = load_roster(cfg["raw"])
    df_sinta = pd.DataFrame.from_dict(sinta.author(df.id.dropna().to_list()))
    df_clean = df.merge(df_sinta, on="id").set_index("id")
    df_clean = df_clean.rename(columns={"name": "name_sinta", "affiliation": "affiliation_sinta"})

    cache_dir = PROCESSED / cfg["cache"] / "google_scholar"
    cache_dir.mkdir(parents=True, exist_ok=True)
    google = {
        sid: fetch_scholar(sid, row.google_scholar_id, row.name_inputted, cache_dir)
        for sid, row in df_clean.iterrows()
    }
    df_final = df_clean.merge(pd.DataFrame.from_dict(google).T, left_index=True, right_index=True)
    df_final.T.to_json(PROCESSED / cfg["out"], indent=2)
    return df_final


def suspicious_domains(df_final, affiliation):
    """Authors whose Scholar email domain is missing or doesn't contain the affiliation code."""
    cols = ["name_inputted", "name", "email_domain", "scholar_id", "affiliation", "interests", "homepage"]
    dom = df_final.email_domain
    bad = dom.isnull() | ~dom.fillna("").str.contains(affiliation.lower(), regex=False)
    return df_final.loc[bad, cols]
