import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"

FEATURES = ["EUR_absret_1", "EUR_vol_5", "EUR_vol_20", "EUR_maxabs_5", "EUR_vol_ratio",
            "USD_vol_5", "USD_vol_20", "USD_maxabs_5"]
C = 0.1
TEST_START = 2019
LEVELS = {"scazut": 0.5, "mediu": 0.9}


def make_model():
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000))


def load_data():
    f = pd.read_csv(DATA_DIR / "features.csv", index_col="date", parse_dates=True)
    f = f.dropna(subset=FEATURES)
    labeled = f.dropna(subset=["target_big"])
    return f, labeled


def walk_forward(labeled):
    preds = []
    for year in range(TEST_START, labeled.index.year.max() + 1):
        train = labeled[labeled.index.year < year]
        test = labeled[labeled.index.year == year]
        model = make_model().fit(train[FEATURES], train["target_big"])
        preds.append(pd.Series(model.predict_proba(test[FEATURES])[:, 1], index=test.index))
    p = pd.concat(preds)
    y = labeled.loc[p.index, "target_big"]
    return p, y


def level_of(percentile):
    if percentile < LEVELS["scazut"]:
        return "scazut"
    if percentile < LEVELS["mediu"]:
        return "mediu"
    return "ridicat"


def historical_rates(p, y):
    levels = p.rank(pct=True).apply(level_of)
    return {lvl: round(float(y[levels == lvl].mean()), 4) for lvl in ["scazut", "mediu", "ridicat"]}


def main():
    f, labeled = load_data()

    p, y = walk_forward(labeled)
    auc = roc_auc_score(y, p)
    ap = average_precision_score(y, p)
    rates = historical_rates(p, y)

    model = make_model().fit(labeled[FEATURES], labeled["target_big"])
    history_scores = model.predict_proba(f[FEATURES])[:, 1]
    thresholds = {lvl: float(pd.Series(history_scores).quantile(q)) for lvl, q in LEVELS.items()}

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_DIR / "model.pkl")

    meta = {
        "trained_on": date.today().isoformat(),
        "data_until": labeled.index.max().date().isoformat(),
        "features": FEATURES,
        "C": C,
        "big_move_threshold_pct": 0.25,
        "evaluation": {"method": f"walk-forward pe ani, {TEST_START}+",
                       "auc": round(auc, 3), "average_precision": round(ap, 3),
                       "base_rate": round(float(y.mean()), 4)},
        "level_thresholds": thresholds,
        "big_move_rate_by_level": rates,
    }
    (MODEL_DIR / "model_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                               encoding="utf-8")

    print(f"Evaluare walk-forward: AUC = {auc:.3f}, AP = {ap:.3f}, baza = {y.mean():.3f}")
    print("Rata miscarilor mari pe niveluri de risc:", rates)
    print(f"Model salvat in {MODEL_DIR / 'model.pkl'}")


if __name__ == "__main__":
    main()