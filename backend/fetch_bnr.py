from datetime import date
from pathlib import Path
import requests
import xml.etree.ElementTree as ET
import pandas as pd

CURRENCIES= ["EUR","USD"]
START_YEAR= 2015

URL="https://curs.bnr.ro/files/xml/years/nbrfxrates{year}.xml"
DATA_DIR=Path(__file__).resolve().parent.parent / "data"

def fetch_year(year):
    resp=requests.get(URL.format(year=year), timeout=30,headers={"User-Agent":"Mozilla/5.0"})
    resp.raise_for_status();
    root=ET.fromstring(resp.content)

    rows=[]
    for cube in root.iterfind(".//{*}Cube"):
        day=cube.get("date")
        for rate in cube.iterfind(".//{*}Rate"):
            currency=rate.get("currency")
            if currency in CURRENCIES:
                multiplier=int(rate.get("multiplier",1))
                rows.append({"date":day,"currency":currency,"rate":float(rate.text)/multiplier})

    return rows

def main():
    DATA_DIR.mkdir(exist_ok=True)
    all_rows=[]

    for year in range(START_YEAR,date.today().year+1):
        try:
            rows=fetch_year(year)
            all_rows.extend(rows)
            print(f"{year}:{len(rows)} inregistrari")
        except Exception as e:
            print(f"{year}:eroare -{e}")
            raise

    if not all_rows:
        print("Nu s-a descarcat nimic")
        return

    df=pd.DataFrame(all_rows)
    df["date"]=pd.to_datetime(df["date"])
    wide=df.pivot_table(index="date",columns="currency",values="rate").sort_index()

    out=DATA_DIR/"bnr_rates.csv"
    wide
    print(f"\nSalvat {len(wide)} zile in {out}")
    print(wide.tail())

if __name__ =='__main__':
    main()