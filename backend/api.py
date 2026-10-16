import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
FEATURES_FILE = DATA_DIR / "features.csv"
MODEL_FILE = MODEL_DIR / "model.pkl"
META_FILE = MODEL_DIR / "model_meta.json"

_cache = {"mtime": None}


def level_of(score, thresholds):
    if score < thresholds["scazut"]:
        return "scazut"
    if score < thresholds["mediu"]:
        return "mediu"
    return "ridicat"


def get_state():
    mtime = max(FEATURES_FILE.stat().st_mtime, MODEL_FILE.stat().st_mtime)
    if _cache["mtime"] != mtime:
        model = joblib.load(MODEL_FILE)
        meta = json.loads(META_FILE.read_text(encoding="utf-8"))
        features = meta["features"]

        f = pd.read_csv(FEATURES_FILE, index_col="date", parse_dates=True)
        f = f.dropna(subset=features)
        rates = pd.read_csv(DATA_DIR / "bnr_rates.csv", index_col="date", parse_dates=True)
        f = f.join(rates[["EUR"]])
        f["score"] = model.predict_proba(f[features])[:, 1]
        f["level"] = f["score"].apply(lambda s: level_of(s, meta["level_thresholds"]))

        _cache.update({"mtime": mtime, "meta": meta, "table": f})
    return _cache


def data_is_stale():
    now = datetime.now()
    last_day = get_state()["table"].index[-1].date()
    after_publication = (now.hour, now.minute) >= (13, 30)
    return now.weekday() < 5 and after_publication and last_day < now.date()


scheduler = BackgroundScheduler(timezone="Europe/Bucharest")
scheduler.add_job(run_pipeline, "cron", day_of_week="mon-fri", hour=13, minute=30,
                  id="daily_update", max_instances=1, coalesce=True)


@asynccontextmanager
async def lifespan(app):
    scheduler.start()
    if data_is_stale():
        scheduler.add_job(run_pipeline, id="catch_up_update", max_instances=1)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="FXcast API",
              description="Riscul unei miscari mari a cursului EUR/RON in ziua urmatoare",
              lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["GET"], allow_headers=["*"])


@app.get("/risk/latest")
def risk_latest():
    state = get_state()
    table, meta = state["table"], state["meta"]
    day = table.index[-1]
    row = table.iloc[-1]
    level = row["level"]
    return {
        "date": day.date().isoformat(),
        "eur_ron": round(float(row["EUR"]), 4),
        "risk_level": level,
        "historical_big_move_rate": meta["big_move_rate_by_level"][level],
        "big_move_threshold_pct": meta["big_move_threshold_pct"],
        "drivers": {
            "eur_change_today_pct": round(float(row["EUR_ret_1"]), 3),
            "eur_volatility_5d": round(float(row["EUR_vol_5"]), 3),
            "eur_max_move_5d_pct": round(float(row["EUR_maxabs_5"]), 3),
        },
    }


@app.get("/history")
def history(days: int = Query(90, ge=5, le=1000)):
    part = get_state()["table"].iloc[-days:]
    return [
        {
            "date": d.date().isoformat(),
            "eur_ron": round(float(r["EUR"]), 4),
            "risk_level": r["level"],
            "big_move_next_day": None if pd.isna(r["target_big"]) else bool(r["target_big"]),
        }
        for d, r in part.iterrows()
    ]


@app.get("/model")
def model_info():
    return get_state()["meta"]


@app.get("/status")
def status():
    job = scheduler.get_job("daily_update")
    state = get_state()
    return {
        "data_until": state["table"].index[-1].date().isoformat(),
        "model_trained_on": state["meta"]["trained_on"],
        "next_update": job.next_run_time.isoformat() if job else None,
        "update_running": scheduler.get_job("catch_up_update") is not None,
    }