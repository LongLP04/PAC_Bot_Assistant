import json
import time
from pathlib import Path
from datetime import datetime


LOG_DIR = Path("logs")
USAGE_LOG_FILE = LOG_DIR / "usage.jsonl"


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def write_usage_log(data: dict):
    """
    Ghi mỗi lượt sử dụng thành 1 dòng JSON.
    File này dùng để xuất báo cáo và dựng dashboard sau này.
    """
    ensure_log_dir()

    record = {
        "time": now_iso(),
        **data
    }

    with open(USAGE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def start_timer():
    return time.perf_counter()


def end_timer(start_time):
    return round(time.perf_counter() - start_time, 3)