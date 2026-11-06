"""
Collects job postings from the Arbeitnow job board API (free and public, covering Europe)
and adds the new ones located in Germany to data/postings.parquet. The description text is
kept, so the skill rules can be improved and re-applied to the whole history. Run daily;
postings already stored are skipped, so the file grows into a history of what was
advertised when.

The API asks users not to abuse it: requests are spaced out, 429 responses are respected,
and only a limited number of pages is read per run.

    python collect.py [--pages 10]
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import skills

API = "https://www.arbeitnow.com/api/job-board-api"
STORE = Path("data/postings.parquet")
HEADERS = {"User-Agent": "job-skill-tracker (portfolio project; github.com/sidd-24/job-skill-tracker)"}
PAUSE = 6          # seconds between pages


def fetch(url: str, retries: int = 4) -> dict:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == retries - 1:
                raise
            wait = int(error.headers.get("Retry-After") or 60)
            print(f"rate limited, waiting {wait} s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def to_rows(jobs: list[dict], seen_at: str) -> pd.DataFrame:
    """Raw fields plus the cleaned description. Skills etc. are derived later, see skills.annotate."""
    return pd.DataFrame([{
        "slug": job["slug"],
        "title": job["title"],
        "company": job["company_name"],
        "location": job["location"],
        "remote": bool(job["remote"]),
        "tags": list(job.get("tags") or []),
        "job_types": list(job.get("job_types") or []),
        "created_at": datetime.fromtimestamp(int(job["created_at"]), tz=timezone.utc),
        "first_seen": seen_at,
        "text": skills.plain_text(job.get("description", "")),
        "url": job["url"],
    } for job in jobs])


def merge(stored: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Keep the first time each posting was seen."""
    combined = pd.concat([stored, new[~new["slug"].isin(stored["slug"])]], ignore_index=True)
    return combined.sort_values("created_at", ignore_index=True)


def main(pages: int) -> None:
    seen_at = datetime.now(timezone.utc).date().isoformat()
    url, frames = f"{API}?page=1", []
    for page in range(pages):
        if not url:
            break
        if page:
            time.sleep(PAUSE)
        data = fetch(url)
        frames.append(to_rows(data["data"], seen_at))
        url = data["links"].get("next")
    new = pd.concat(frames, ignore_index=True).drop_duplicates("slug")
    new = new[new["location"].map(skills.in_germany)]
    stored = pd.read_parquet(STORE) if STORE.exists() else new.iloc[0:0]
    result = merge(stored, new)
    STORE.parent.mkdir(exist_ok=True)
    result.to_parquet(STORE, index=False, compression="zstd")
    print(f"read {len(new)} postings in Germany, {len(result) - len(stored)} new, {len(result)} stored")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pages", type=int, default=10)
    main(parser.parse_args().pages)
