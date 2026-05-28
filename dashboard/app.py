import json
from pathlib import Path

import pandas as pd
import streamlit as st


USAGE_LOG_FILE = Path("logs/usage.jsonl")


st.set_page_config(
    page_title="PAC Bot Usage Dashboard",
    layout="wide"
)


@st.cache_data(ttl=5)
def load_data():
    records = []

    if not USAGE_LOG_FILE.exists():
        return pd.DataFrame()

    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df["date"] = df["time"].dt.date

    return df


st.title("PAC Bot Usage Dashboard")
st.caption("Theo dõi vận hành, lỗi API, token và chi phí ước tính của PAC Assistant")

df = load_data()

if df.empty:
    st.warning("Chưa có dữ liệu trong logs/usage.jsonl.")
    st.stop()


# =========================
# BỘ LỌC NGÀY
# =========================

st.sidebar.header("Bộ lọc")
if st.sidebar.button("Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()
min_date = df["date"].min()
max_date = df["date"].max()

date_range = st.sidebar.date_input(
    "Khoảng ngày",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]


status_options = ["Tất cả"] + sorted(df["status"].dropna().unique().tolist())
selected_status = st.sidebar.selectbox("Trạng thái", status_options)

if selected_status != "Tất cả":
    df = df[df["status"] == selected_status]


# =========================
# CHỈ SỐ TỔNG QUAN
# =========================

total_requests = len(df)
success_requests = len(df[df["status"] == "success"]) if "status" in df.columns else 0
error_requests = len(df[df["status"] == "error"]) if "status" in df.columns else 0

total_tokens = int(df["total_tokens"].fillna(0).sum()) if "total_tokens" in df.columns else 0
total_cost = float(df["estimated_cost_usd"].fillna(0).sum()) if "estimated_cost_usd" in df.columns else 0
avg_latency = float(df["latency_seconds"].fillna(0).mean()) if "latency_seconds" in df.columns else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Tổng lượt hỏi", total_requests)
col2.metric("Thành công", success_requests)
col3.metric("Lỗi", error_requests)
col4.metric("Tổng token", f"{total_tokens:,}")
col5.metric("Chi phí ước tính", f"${total_cost:.6f}")
col6.metric("Phản hồi TB", f"{avg_latency:.2f}s")

st.divider()


# =========================
# THỐNG KÊ THEO NGÀY
# =========================

st.subheader("Thống kê theo ngày")

daily = df.groupby("date").agg(
    total_requests=("question", "count"),
    total_tokens=("total_tokens", "sum"),
    total_cost_usd=("estimated_cost_usd", "sum"),
    avg_latency_seconds=("latency_seconds", "mean"),
).reset_index()

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.write("Số lượt hỏi theo ngày")
    st.line_chart(daily.set_index("date")[["total_requests"]])

with col_chart2:
    st.write("Tổng token theo ngày")
    st.bar_chart(daily.set_index("date")[["total_tokens"]])

st.dataframe(daily, use_container_width=True)

st.divider()


# =========================
# THỐNG KÊ LỖI
# =========================

st.subheader("Thống kê lỗi")

error_df = df[df["status"] == "error"] if "status" in df.columns else pd.DataFrame()

if error_df.empty:
    st.success("Không có lỗi trong khoảng thời gian đã chọn.")
else:
    error_summary = error_df.groupby("error_code", dropna=False).agg(
        total_errors=("error_code", "count")
    ).reset_index()

    st.dataframe(error_summary, use_container_width=True)

st.divider()


# =========================
# TOP USER
# =========================

st.subheader("Top người dùng")

user_summary = df.groupby(["user_id", "username", "first_name"], dropna=False).agg(
    total_requests=("question", "count"),
    total_tokens=("total_tokens", "sum"),
    total_cost_usd=("estimated_cost_usd", "sum"),
    avg_latency_seconds=("latency_seconds", "mean"),
).reset_index().sort_values("total_requests", ascending=False)

st.dataframe(user_summary, use_container_width=True)

st.divider()


# =========================
# CHI TIẾT LOG
# =========================

st.subheader("Chi tiết log vận hành")

columns_to_show = [
    "time",
    "user_id",
    "username",
    "first_name",
    "question",
    "response_preview",
    "model",
    "status",
    "error_code",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "latency_seconds",
]

available_columns = [col for col in columns_to_show if col in df.columns]

st.dataframe(
    df[available_columns].sort_values("time", ascending=False),
    use_container_width=True
)