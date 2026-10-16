import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "data" / "pipeline.log"

STEPS = [
    (["backend/fetch_bnr.py"], True),
    (["backend/fetch_news_history.py", "--recent", "3"], False),
    (["backend/build_features.py"], True),
    (["backend/train_model.py"], True),
]


def log(message):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_pipeline():
    log("Pornesc actualizarea")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    for command, critical in STEPS:
        started = time.time()
        result = subprocess.run([sys.executable, *command], cwd=ROOT, env=env,
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        name = " ".join(command)
        if result.returncode != 0:
            log(f"EROARE la {name}:\n{result.stderr[-2000:]}")
            if critical:
                log("Actualizare oprita")
                return False
            log("Pas necritic - continui")
            continue
        lines = result.stdout.strip().splitlines()
        summary = lines[-1] if lines else ""
        log(f"OK {name} ({time.time() - started:.0f}s) {summary}")

    log("Actualizare terminata")
    return True


if __name__ == "__main__":
    sys.exit(0 if run_pipeline() else 1)