import argparse
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import feedparser
import pandas as pd

QUERIES = {
    "politic": [
        "alegeri prezidențiale",
        "alegeri parlamentare",
        "moțiune de cenzură",
        "vot de învestitură",
        "demisia premierului",
        "alegeri anticipate",
        "criză politică",
    ],
    "fiscal": [
        "deficit bugetar",
        "rectificare bugetară",
        "creșterea taxelor",
        "datoria publică",
        "randamentele obligațiunilor",
    ],
    "banca_centrala": [
        "BNR dobânda de politică monetară",
        "rezervele valutare BNR",
        "curs euro leu BNR",
    ],
    "rating": [
        "rating România S&P",
        "rating România Fitch",
        "rating România Moody's",
    ],
    "ue": [
        "fonduri europene",
        "PNRR",
        "procedura de deficit excesiv",
    ],
    "extern": [
        "BCE dobânda",
        "Fed dobânda",
    ],
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = DATA_DIR / "news_history"
PROGRESS_FILE = DATA_DIR / "news_history_progress.txt"
PAUSE = 5
LIMIT = 40


def fetch(query, start, end):
    q = f"{query} after:{start.isoformat()} before:{end.isoformat()}"
    url = f"https://news.google.com/rss/search?q={quote(q)}&hl=ro&gl=RO&ceid=RO:ro"

    for attempt in range(3):
        feed = feedparser.parse(url)
        time.sleep(PAUSE)
        status = feed.get("status", 200)
        if status == 200:
            return [{
                "published": e.get("published", ""),
                "source": e.get("source", {}).get("title", "?"),
                "title": e.get("title", ""),
                "link": e.get("link", ""),
            } for e in feed.entries]
        wait = 60 * (attempt + 1)
        print(f"   Status {status} - astept {wait} secunde...")
        time.sleep(wait)

    print("   Renunt la aceasta fereastra dupa 3 incercari")
    return []


def fetch_window(query, start, end):
    rows = fetch(query, start, end)
    days = (end - start).days

    dates = pd.to_datetime([r["published"] for r in rows], utc=True,
                           format="%a, %d %b %Y %H:%M:%S GMT", errors="coerce")
    inside = [r for r, d in zip(rows, dates) if pd.notna(d) and start <= d.date() <= end]

    if rows and len(inside) < len(rows) * 0.8:
        print(f"   ATENTIE: doar {len(inside)}/{len(rows)} articole in fereastra {start} -> {end} - pastrez doar pe acestea")
        return inside

    if len(rows) >= LIMIT and days > 1:
        mid = start + timedelta(days=days // 2)
        print(f"   {start} -> {end}: limita atinsa, impart in doua")
        return fetch_window(query, start, mid) + fetch_window(query, mid, end)

    if len(rows) >= LIMIT:
        print(f"   ATENTIE: {start} are peste {LIMIT} articole intr-o singura zi")
    return inside

def month_range(start_ym, end_ym):
    year, month = map(int, start_ym.split("-"))
    end_year, end_month = map(int, end_ym.split("-"))
    while (year, month) <= (end_year, end_month):
        first = date(year, month, 1)
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
        yield first, date(year, month, 1)


def load_progress():
    if PROGRESS_FILE.exists():
        return set(PROGRESS_FILE.read_text(encoding="utf-8").splitlines())
    return set()


def mark_done(key):
    with open(PROGRESS_FILE, "a", encoding="utf-8") as f:
        f.write(key + "\n")


def main():
    parser = argparse.ArgumentParser(description="Colectare istorica de stiri din Google News")
    parser.add_argument("--start", default="2015-01", help="luna de inceput, format AAAA-LL")
    parser.add_argument("--end", default=date.today().strftime("%Y-%m"), help="luna de final, format AAAA-LL")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)
    done = load_progress()

    for start, end in month_range(args.start, args.end):
        for category, queries in QUERIES.items():
            for query in queries:
                key = f"{category}|{query}|{start:%Y-%m}"
                if key in done:
                    continue

                rows = fetch_window(query, start, end)
                for r in rows:
                    r["category"] = category
                    r["query"] = query

                if rows:
                    out_file = OUT_DIR / f"{start.year}.csv"
                    pd.DataFrame(rows).to_csv(out_file, mode="a", header=not out_file.exists(),
                                              index=False, encoding="utf-8")
                mark_done(key)
                print(f"[{start:%Y-%m}] {category} | {query}: {len(rows)} articole")


if __name__ == "__main__":
    main()