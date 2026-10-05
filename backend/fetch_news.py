import feedparser
from urllib.parse import quote
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

QUERIES = {
    "politic": [
        "guvern motiune de cenzura",
        "vot de investitura guvern",
        "coalitie de guvernare criza",
        "alegeri anticipate Romania",
        "premier demisie",
    ],
    "fiscal": [
        "deficit bugetar Romania",
        "rectificare bugetara",
        "crestere taxe guvern",
        "datorie publica imprumut Ministerul Finantelor",
        "randamente obligatiuni Romania",
    ],
    "banca_centrala": [
        "BNR dobanda de politica monetara",
        "rezerve valutare BNR",
        "curs euro leu BNR",
    ],
    "rating": [
        "rating Romania S&P",
        "rating Romania Fitch",
        "rating Romania Moody's",
        "Romania junk",
    ],
    "ue": [
        "fonduri europene PNRR Romania",
        "procedura de deficit excesiv Romania",
        "Comisia Europeana Romania buget",
    ],
    "extern": [
        "BCE dobanda",
        "Fed dobanda",
    ],
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEWS_FILE=DATA_DIR/"news.csv"

def fetch_query(query,category):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ro&gl=RO&ceid=RO:ro"
    feed= feedparser.parse(url)
    rows=[]
    for entry in feed.entries:
        rows.append({
            "published": entry.get("published", ""),
            "source": entry.get("source", {}).get("title", "?"),
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "query": query,
            "category":category,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows

def main():
    all_rows=[]
    for category, queries in QUERIES.items():
        for q in queries:
            rows = fetch_query(q, category)
            print(f"[{category}] {q}: {len(rows)} articole")
            all_rows.extend(rows)

    new=pd.DataFrame(all_rows)

    if NEWS_FILE.exists():
        old=pd.read_csv(NEWS_FILE)
        before=len(old)
        combined=pd.concat([old,new])
    else:
        before=0
        combined=new

    combined=combined.drop_duplicates(subset='link')
    combined.to_csv(NEWS_FILE,index=False)

    print(f"\nArticole noi: {len(combined)-before}")
    print(f"Total articole salvate: {len(combined)}")

if __name__=="__main__":
    main()