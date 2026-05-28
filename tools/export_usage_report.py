import json
from pathlib import Path
import pandas as pd


USAGE_LOG_FILE = Path("logs/usage.jsonl")
REPORT_DIR = Path("reports")


def load_usage_logs():
    records = []

    if not USAGE_LOG_FILE.exists():
        print("Không tìm thấy logs/usage.jsonl")
        return records

    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def export_report():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    records = load_usage_logs()

    if not records:
        print("Chưa có dữ liệu usage log để xuất báo cáo.")
        return

    df = pd.DataFrame(records)

    # Chuẩn hóa cột thời gian
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["date"] = df["time"].dt.date

    output_excel = REPORT_DIR / "usage_report.xlsx"
    output_csv = REPORT_DIR / "usage_report.csv"

    # Tổng hợp theo ngày
    daily_summary = df.groupby("date").agg(
        total_requests=("question", "count"),
        success_requests=("status", lambda x: (x == "success").sum()),
        error_requests=("status", lambda x: (x == "error").sum()),
        total_tokens=("total_tokens", "sum"),
        total_cost_usd=("estimated_cost_usd", "sum"),
        avg_latency_seconds=("latency_seconds", "mean"),
    ).reset_index()

    # Tổng hợp lỗi
    error_summary = df[df["status"] == "error"].groupby("error_code").agg(
        total_errors=("error_code", "count")
    ).reset_index()

    # Top user
    user_summary = df.groupby(["user_id", "username", "first_name"], dropna=False).agg(
        total_requests=("question", "count"),
        total_tokens=("total_tokens", "sum"),
        total_cost_usd=("estimated_cost_usd", "sum"),
    ).reset_index()

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Raw Logs", index=False)
        daily_summary.to_excel(writer, sheet_name="Daily Summary", index=False)
        error_summary.to_excel(writer, sheet_name="Error Summary", index=False)
        user_summary.to_excel(writer, sheet_name="User Summary", index=False)

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"Đã xuất báo cáo Excel: {output_excel}")
    print(f"Đã xuất báo cáo CSV: {output_csv}")


if __name__ == "__main__":
    export_report()