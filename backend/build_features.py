from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEWS_DIR = DATA_DIR / "news_history"
OUT_FILE = DATA_DIR / "features.csv"

CATEGORIES= ["politic","fiscal","banca_centrala","ue","extern"]
BASELINE_DAYS=20
BIG_MOVE=0.25
DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

def load_rates():
    rates=pd.read_csv(DATA_DIR/ "bnr_rates.csv", parse_dates=["date"])
    rates=rates.sort_values("date").set_index("date")
    rates.index=rates.index.astype("datetime64[ns]")
    return rates

def load_news():
    files = sorted(NEWS_DIR.glob("*.csv"))
    print("Fisiere gasite:", len(files))
    news = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    raw = news["published"].copy()
    news["published"] = pd.to_datetime(news["published"], utc=True,
                                       format=DATE_FORMAT, errors="coerce")
    bad = news["published"].isna().mean()
    if bad > 0.01:
        raise ValueError(f"{bad:.0%} din date nu pot fi citite. "
                         f"Exemplu din fisier: {raw.iloc[0]!r} | Formatul asteptat: {DATE_FORMAT!r}")
    news = news.dropna(subset=["published"])

    aliases = pd.read_csv(DATA_DIR / "source_aliases.csv")
    news["source"] = news["source"].replace(dict(zip(aliases["alias"], aliases["source"])))

    sources = pd.read_csv(DATA_DIR / "sources.csv")
    allowed = set(sources.loc[sources["tier"] > 0, "source"])
    print("   Surse permise:", len(allowed))
    news = news[news["source"].isin(allowed)]

    news["category"] = news["category"].replace({"rating": "fiscal"})
    news = news.drop_duplicates(subset=["link", "category"])
    return news

def assign_bnr_day(news, bnr_days):
    local = news["published"].dt.tz_convert("Europe/Bucharest")
    shifted = (local + pd.Timedelta(hours=11)).dt.tz_localize(None).dt.normalize()
    news = news.assign(shifted=shifted.astype("datetime64[ns]")).sort_values("shifted")

    days = pd.DataFrame({"bnr_day": bnr_days})
    news = pd.merge_asof(news, days, left_on="shifted", right_on="bnr_day",
                         direction="forward")
    return news.dropna(subset=["bnr_day"])

def daily_counts(news, bnr_days):
    counts = news.pivot_table(index="bnr_day", columns="category", values="link",
                              aggfunc="count", fill_value=0)
    counts = counts.reindex(index=bnr_days, columns=CATEGORIES, fill_value=0)

    total = news.drop_duplicates("link").groupby("bnr_day").size()
    counts["total"] = total.reindex(bnr_days, fill_value=0)
    return counts

def news_features(counts):
    f = pd.DataFrame(index=counts.index)

    for col in CATEGORIES + ["total"]:
        baseline = counts[col].rolling(BASELINE_DAYS, min_periods=BASELINE_DAYS).median().shift(1)
        f[f"{col}_ratio"] = (counts[col] + 1) / (baseline + 1)
        f[f"{col}_ratio_3d"] = (counts[col].rolling(3).sum() + 1) / (3 * baseline + 1)

    for col in CATEGORIES:
        f[f"{col}_share"] = (counts[col] / counts["total"].replace(0, np.nan)).fillna(0)

    return f

def price_features(rates):
    f = pd.DataFrame(index=rates.index)

    for cur in ["EUR", "USD"]:
        ret = rates[cur].pct_change() * 100
        f[f"{cur}_ret_1"] = ret
        f[f"{cur}_absret_1"] = ret.abs()
        f[f"{cur}_vol_5"] = ret.rolling(5).std()
        f[f"{cur}_vol_20"] = ret.rolling(20).std()
        f[f"{cur}_maxabs_5"] = ret.abs().rolling(5).max()

    f["EUR_vol_ratio"] = (f["EUR_vol_5"] + 0.01) / (f["EUR_vol_20"] + 0.01)
    f["weekday"] = rates.index.dayofweek
    return f

def build_target(rates):
    next_ret = rates["EUR"].pct_change().shift(-1) * 100

    t = pd.DataFrame(index=rates.index)
    t["next_ret"] = next_ret
    t["target_big"] = (next_ret.abs() > BIG_MOVE).astype(float)
    t["target_up"] = (next_ret > 0).astype(float)
    t.loc[next_ret.isna(), ["target_big", "target_up"]] = np.nan
    return t

def main():
    rates = load_rates()
    bnr_days = rates.index

    news = load_news()
    news = assign_bnr_day(news, bnr_days)
    counts = daily_counts(news, bnr_days)

    features = (counts.add_prefix("n_")
                .join(news_features(counts))
                .join(price_features(rates))
                .join(build_target(rates)))

    needed = [f"{c}_ratio" for c in CATEGORIES] + ["EUR_vol_20"]
    features = features.dropna(subset=needed)
    features.index.name = "date"
    features.to_csv(OUT_FILE, encoding="utf-8")

    print(f"Articole folosite: {news['link'].nunique()}")
    print(f"Zile in tabel: {len(features)} "
          f"({features.index.min().date()} -> {features.index.max().date()})")
    print(f"Coloane: {features.shape[1]}")

    big = features["target_big"]
    print(f"\nZile cu miscare mare (>{BIG_MOVE}%): {int(big.sum())} ({big.mean() * 100:.1f}%)")
    print("Pe ani:")
    print(big.groupby(features.index.year).sum().astype(int).to_string())


if __name__ == "__main__":
    main()