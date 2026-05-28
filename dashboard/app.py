import json
import os
import sys
from io import BytesIO
from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st


# Đảm bảo dashboard import được module trong thư mục app/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


from app.user_store import (
    get_all_users_as_list,
    add_or_update_user,
    delete_user,
)
USAGE_LOG_FILE = Path("logs/usage.jsonl")


# =========================
# CẤU HÌNH NGƯỠNG CẢNH BÁO
# Có thể chỉnh bằng .env sau này
# =========================

ERROR_THRESHOLD = int(os.getenv("DASHBOARD_ERROR_THRESHOLD", "5"))
DAILY_TOKEN_THRESHOLD = int(os.getenv("DASHBOARD_DAILY_TOKEN_THRESHOLD", "20000"))
DAILY_COST_THRESHOLD = float(os.getenv("DASHBOARD_DAILY_COST_THRESHOLD", "1.0"))
LATENCY_THRESHOLD = float(os.getenv("DASHBOARD_LATENCY_THRESHOLD", "10"))


st.set_page_config(
    page_title="PAC Bot Usage Dashboard",
    layout="wide"
)


# =========================
# HÀM ĐỌC DỮ LIỆU
# =========================

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

    # Đảm bảo các cột quan trọng luôn tồn tại
    default_columns = {
        "time": None,
        "user_id": None,
        "username": None,
        "first_name": None,
        "question": None,
        "response_preview": None,
        "model": None,
        "status": None,
        "error_code": None,
        "error_message": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0,
        "latency_seconds": 0,
    }

    for col, default_value in default_columns.items():
        if col not in df.columns:
            df[col] = default_value

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["date"] = df["time"].dt.date

    numeric_cols = [
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "latency_seconds",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["user_display"] = (
        df["first_name"].fillna("").astype(str)
        + " | "
        + df["username"].fillna("").astype(str)
        + " | ID: "
        + df["user_id"].fillna("").astype(str)
    )

    return df


def make_excel_file(df, daily_summary, error_summary, user_summary):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Raw Logs", index=False)
        daily_summary.to_excel(writer, sheet_name="Daily Summary", index=False)
        error_summary.to_excel(writer, sheet_name="Error Summary", index=False)
        user_summary.to_excel(writer, sheet_name="User Summary", index=False)

        workbook = writer.book

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]

            # Freeze header
            worksheet.freeze_panes = "A2"

            # Auto filter
            worksheet.auto_filter.ref = worksheet.dimensions

            # Chỉnh độ rộng cột
            for column_cells in worksheet.columns:
                max_length = 0
                column_letter = column_cells[0].column_letter

                for cell in column_cells:
                    try:
                        cell_value = str(cell.value) if cell.value is not None else ""
                        max_length = max(max_length, len(cell_value))
                    except Exception:
                        pass

                adjusted_width = min(max(max_length + 2, 12), 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

            # Định dạng header
            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
                cell.alignment = cell.alignment.copy(horizontal="center")

    output.seek(0)
    return output


def format_usd(value):
    return f"${value:,.6f}"


# =========================
# GIAO DIỆN CHÍNH
# =========================

st.title("PAC Bot Usage Dashboard")
st.caption("Bảng điều hành theo dõi vận hành, lỗi API, token, chi phí và hiệu suất phản hồi của PAC Assistant.")

raw_df = load_data()

if raw_df.empty:
    st.warning("Chưa có dữ liệu trong logs/usage.jsonl.")
    st.stop()


# =========================
# SIDEBAR - BỘ LỌC
# =========================

st.sidebar.header("Bộ lọc dữ liệu")

if st.sidebar.button("Làm mới dữ liệu"):
    st.cache_data.clear()
    st.rerun()

min_date = raw_df["date"].min()
max_date = raw_df["date"].max()

date_range = st.sidebar.date_input(
    "Khoảng ngày",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

df = raw_df.copy()

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

# Lọc user
user_options = sorted(df["user_display"].dropna().unique().tolist())
selected_users = st.sidebar.multiselect(
    "Lọc theo user",
    options=user_options,
    default=[]
)

if selected_users:
    df = df[df["user_display"].isin(selected_users)]

# Lọc model
model_options = sorted(df["model"].dropna().unique().tolist())
selected_models = st.sidebar.multiselect(
    "Lọc theo model",
    options=model_options,
    default=[]
)

if selected_models:
    df = df[df["model"].isin(selected_models)]

# Lọc status
status_options = sorted(df["status"].dropna().unique().tolist())
selected_statuses = st.sidebar.multiselect(
    "Lọc theo trạng thái",
    options=status_options,
    default=[]
)

if selected_statuses:
    df = df[df["status"].isin(selected_statuses)]

# Lọc mã lỗi
error_code_options = sorted(df["error_code"].dropna().unique().tolist())
selected_error_codes = st.sidebar.multiselect(
    "Lọc theo mã lỗi",
    options=error_code_options,
    default=[]
)

if selected_error_codes:
    df = df[df["error_code"].isin(selected_error_codes)]


if df.empty:
    st.warning("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
    st.stop()


# =========================
# TỔNG HỢP DỮ LIỆU
# =========================

total_requests = len(df)
success_requests = len(df[df["status"] == "success"])
error_requests = len(df[df["status"] == "error"])

total_tokens = int(df["total_tokens"].sum())
input_tokens = int(df["input_tokens"].sum())
output_tokens = int(df["output_tokens"].sum())

total_cost = float(df["estimated_cost_usd"].sum())
avg_latency = float(df["latency_seconds"].mean())

daily_summary = df.groupby("date").agg(
    total_requests=("question", "count"),
    success_requests=("status", lambda x: (x == "success").sum()),
    error_requests=("status", lambda x: (x == "error").sum()),
    input_tokens=("input_tokens", "sum"),
    output_tokens=("output_tokens", "sum"),
    total_tokens=("total_tokens", "sum"),
    total_cost_usd=("estimated_cost_usd", "sum"),
    avg_latency_seconds=("latency_seconds", "mean"),
).reset_index()

error_df = df[df["status"] == "error"]

if not error_df.empty:
    error_summary = error_df.groupby("error_code", dropna=False).agg(
        total_errors=("error_code", "count")
    ).reset_index()
else:
    error_summary = pd.DataFrame(columns=["error_code", "total_errors"])

user_summary = df.groupby(
    ["user_id", "username", "first_name", "user_display"],
    dropna=False
).agg(
    total_requests=("question", "count"),
    success_requests=("status", lambda x: (x == "success").sum()),
    error_requests=("status", lambda x: (x == "error").sum()),
    total_tokens=("total_tokens", "sum"),
    total_cost_usd=("estimated_cost_usd", "sum"),
    avg_latency_seconds=("latency_seconds", "mean"),
).reset_index().sort_values("total_requests", ascending=False)


# =========================
# TABS
# =========================

tab_overview, tab_alerts, tab_logs, tab_download, tab_users = st.tabs(
    [
        "Tổng quan",
        "Lỗi & cảnh báo",
        "Chi tiết log",
        "Tải báo cáo",
        "Quản lý user",
    ]
)


# =========================
# TAB 1 - TỔNG QUAN
# =========================

with tab_overview:
    st.subheader("Chỉ số tổng quan")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Tổng lượt hỏi", total_requests)
    col2.metric("Thành công", success_requests)
    col3.metric("Lỗi", error_requests)
    col4.metric("Tổng token", f"{total_tokens:,}")
    col5.metric("Chi phí ước tính", format_usd(total_cost))
    col6.metric("Phản hồi TB", f"{avg_latency:.2f}s")

    st.divider()

    col_token1, col_token2, col_token3 = st.columns(3)
    col_token1.metric("Input token", f"{input_tokens:,}")
    col_token2.metric("Output token", f"{output_tokens:,}")
    col_token3.metric("Số user", df["user_id"].nunique())

    st.divider()

    st.subheader("Biểu đồ vận hành theo ngày")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("Lượt hỏi theo ngày")
        st.line_chart(daily_summary.set_index("date")[["total_requests"]])

    with chart_col2:
        st.write("Tổng token theo ngày")
        st.bar_chart(daily_summary.set_index("date")[["total_tokens"]])

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.write("Chi phí API ước tính theo ngày")
        st.line_chart(daily_summary.set_index("date")[["total_cost_usd"]])

    with chart_col4:
        st.write("Thời gian phản hồi trung bình theo ngày")
        st.line_chart(daily_summary.set_index("date")[["avg_latency_seconds"]])

    st.divider()

    st.subheader("Bảng tổng hợp theo ngày")
    st.dataframe(daily_summary, use_container_width=True)

    st.subheader("Top người dùng")
    st.dataframe(user_summary, use_container_width=True)


# =========================
# TAB 2 - LỖI & CẢNH BÁO
# =========================

with tab_alerts:
    st.subheader("Cảnh báo vận hành")

    today = date.today()
    today_df = raw_df[raw_df["date"] == today]

    if today_df.empty:
        latest_date = raw_df["date"].max()
        today_df = raw_df[raw_df["date"] == latest_date]
        st.info(f"Chưa có dữ liệu ngày hôm nay. Đang hiển thị cảnh báo theo ngày gần nhất: {latest_date}")

    today_total_errors = len(today_df[today_df["status"] == "error"])
    today_total_tokens = int(today_df["total_tokens"].sum())
    today_total_cost = float(today_df["estimated_cost_usd"].sum())
    today_avg_latency = float(today_df["latency_seconds"].mean()) if not today_df.empty else 0

    alert_count = 0

    if today_total_errors >= ERROR_THRESHOLD:
        st.error(
            f"Cảnh báo: số lỗi trong ngày đã đạt {today_total_errors}, "
            f"vượt/ngang ngưỡng {ERROR_THRESHOLD}."
        )
        alert_count += 1

    if today_total_tokens >= DAILY_TOKEN_THRESHOLD:
        st.warning(
            f"Cảnh báo: tổng token trong ngày là {today_total_tokens:,}, "
            f"vượt/ngang ngưỡng {DAILY_TOKEN_THRESHOLD:,}."
        )
        alert_count += 1

    if today_total_cost >= DAILY_COST_THRESHOLD:
        st.warning(
            f"Cảnh báo: chi phí ước tính trong ngày là {format_usd(today_total_cost)}, "
            f"vượt/ngang ngưỡng {format_usd(DAILY_COST_THRESHOLD)}."
        )
        alert_count += 1

    if today_avg_latency >= LATENCY_THRESHOLD:
        st.warning(
            f"Cảnh báo: thời gian phản hồi trung bình là {today_avg_latency:.2f}s, "
            f"vượt/ngang ngưỡng {LATENCY_THRESHOLD:.2f}s."
        )
        alert_count += 1

    today_429 = len(today_df[today_df["error_code"] == "429"])
    today_413 = len(today_df[today_df["error_code"] == "413"])
    today_timeout = len(today_df[today_df["error_code"] == "timeout"])

    if today_429 > 0:
        st.error(f"Cảnh báo: có {today_429} lỗi 429. Bot có nguy cơ vượt giới hạn API.")
        alert_count += 1

    if today_413 > 0:
        st.error(f"Cảnh báo: có {today_413} lỗi 413. Prompt hoặc request có thể đang quá lớn.")
        alert_count += 1

    if today_timeout > 0:
        st.warning(f"Cảnh báo: có {today_timeout} lỗi timeout. Cần kiểm tra kết nối hoặc API.")
        alert_count += 1

    if alert_count == 0:
        st.success("Không phát hiện cảnh báo nghiêm trọng trong dữ liệu đang theo dõi.")

    st.divider()

    st.subheader("Tóm tắt lỗi")

    col_err1, col_err2, col_err3, col_err4 = st.columns(4)

    col_err1.metric("Tổng lỗi", error_requests)
    col_err2.metric("Lỗi 429", len(df[df["error_code"] == "429"]))
    col_err3.metric("Lỗi 413", len(df[df["error_code"] == "413"]))
    col_err4.metric("Timeout", len(df[df["error_code"] == "timeout"]))

    st.divider()

    if error_summary.empty:
        st.success("Không có lỗi trong phạm vi dữ liệu đã lọc.")
    else:
        st.write("Số lượng lỗi theo mã lỗi")
        st.dataframe(error_summary, use_container_width=True)

    st.divider()

    st.subheader("Biểu đồ lỗi theo ngày")

    if error_df.empty:
        st.info("Không có dữ liệu lỗi để vẽ biểu đồ.")
    else:
        error_daily = error_df.groupby("date").agg(
            total_errors=("status", "count")
        ).reset_index()

        st.bar_chart(error_daily.set_index("date")[["total_errors"]])

        error_by_code_daily = error_df.groupby(["date", "error_code"], dropna=False).size().reset_index(name="count")
        st.dataframe(error_by_code_daily, use_container_width=True)


# =========================
# TAB 3 - CHI TIẾT LOG
# =========================

with tab_logs:
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
        "error_message",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "latency_seconds",
    ]

    available_columns = [col for col in columns_to_show if col in df.columns]

    st.dataframe(
        df[available_columns].sort_values("time", ascending=False),
        use_container_width=True,
    )


# =========================
# TAB 4 - TẢI BÁO CÁO
# =========================

with tab_download:
    st.subheader("Tải báo cáo theo dữ liệu đang lọc")

    csv_text = "sep=,\r\n" + df.to_csv(index=False, lineterminator="\r\n")
    csv_data = ("\ufeff" + csv_text).encode("utf-8")

    st.download_button(
        label="Tải CSV",
        data=csv_data,
        file_name="pac_bot_usage_report.csv",
        mime="text/csv",
    )

    excel_file = make_excel_file(
        df=df,
        daily_summary=daily_summary,
        error_summary=error_summary,
        user_summary=user_summary,
    )

    st.download_button(
        label="Tải Excel",
        data=excel_file,
        file_name="pac_bot_usage_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.info(
        "File Excel gồm các sheet: Raw Logs, Daily Summary, Error Summary, User Summary."
    )

# =========================
# TAB 5 - QUẢN LÝ USER
# =========================

with tab_users:
    st.subheader("Quản lý user sử dụng PAC Assistant")

    st.info(
        "Danh sách user được lưu trực tiếp trong file users.json ở thư mục gốc. "
        "User có status=active mới được sử dụng bot. Role=admin được dùng các lệnh quản trị."
    )

    users_list = get_all_users_as_list()
    users_df = pd.DataFrame(users_list)

    selected_user = None

    if users_df.empty:
        st.warning("Chưa có user nào trong users.json.")
    else:
        st.write("Danh sách user hiện tại")

        # Cho phép click chọn 1 dòng user trong bảng
        selected_event = st.dataframe(
            users_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        selected_rows = selected_event.selection.rows

        if selected_rows:
            selected_index = selected_rows[0]
            selected_user = users_df.iloc[selected_index].to_dict()

            st.success(
                f"Đang chọn user: {selected_user.get('user_id')} | "
                f"{selected_user.get('name')} | {selected_user.get('role')}"
            )

    st.divider()

    # =========================
    # FORM THÊM / CẬP NHẬT USER
    # =========================

    st.subheader("Thêm hoặc cập nhật user")

    is_selected_admin = (
        selected_user is not None
        and selected_user.get("role") == "admin"
    )

    if is_selected_admin:
        st.warning(
            "User đang chọn là admin. Thông tin được hiển thị để xem, "
            "nhưng không cho chỉnh sửa trực tiếp trên dashboard."
        )

    default_user_id = selected_user.get("user_id", "") if selected_user else ""
    default_name = selected_user.get("name", "") if selected_user else ""
    default_role = selected_user.get("role", "user") if selected_user else "user"
    default_status = selected_user.get("status", "active") if selected_user else "active"
    default_note = selected_user.get("note", "") if selected_user else ""

    role_options = ["user", "admin"]
    status_options = ["active", "inactive"]

    role_index = role_options.index(default_role) if default_role in role_options else 0
    status_index = status_options.index(default_status) if default_status in status_options else 0

    with st.form("user_form"):
        col_user_1, col_user_2 = st.columns(2)

        with col_user_1:
            input_user_id = st.text_input(
                "Telegram user ID",
                value=str(default_user_id),
                placeholder="Ví dụ: 7538013839",
                disabled=is_selected_admin,
            )

            input_name = st.text_input(
                "Tên hiển thị",
                value=str(default_name),
                placeholder="Ví dụ: Long",
                disabled=is_selected_admin,
            )

        with col_user_2:
            input_role = st.selectbox(
                "Role",
                options=role_options,
                index=role_index,
                disabled=is_selected_admin,
            )

            input_status = st.selectbox(
                "Trạng thái",
                options=status_options,
                index=status_index,
                disabled=is_selected_admin,
            )

        input_note = st.text_area(
            "Ghi chú",
            value=str(default_note),
            placeholder="Ví dụ: Phòng IT, Phòng Kỹ thuật, Admin chính...",
            disabled=is_selected_admin,
        )

        submitted = st.form_submit_button(
            "Lưu user",
            disabled=is_selected_admin,
        )

        if submitted:
            if not input_user_id.strip():
                st.error("Telegram user ID không được để trống.")
            elif not input_user_id.strip().isdigit():
                st.error("Telegram user ID chỉ nên gồm chữ số.")
            else:
                add_or_update_user(
                    user_id=input_user_id.strip(),
                    name=input_name.strip(),
                    role=input_role,
                    status=input_status,
                    note=input_note.strip(),
                )

                st.success(f"Đã lưu user ID: {input_user_id.strip()}")
                st.cache_data.clear()
                st.rerun()

    st.caption(
        "Muốn thêm user mới: không chọn dòng admin, nhập Telegram user ID mới và bấm Lưu user."
    )

    st.divider()

    # =========================
    # XÓA USER - KHÔNG HIỂN THỊ ADMIN
    # =========================

    st.subheader("Xóa user")

    users_list_delete = get_all_users_as_list()

    # Không cho hiển thị admin trong danh sách xóa
    deletable_users = [
        user for user in users_list_delete
        if user.get("role") != "admin"
    ]

    if not deletable_users:
        st.info("Không có user thường để xóa. Admin không được hiển thị trong danh sách xóa.")
    else:
        delete_options = [
            f"{user['user_id']} | {user.get('name', '')} | {user.get('role', '')} | {user.get('status', '')}"
            for user in deletable_users
        ]

        selected_delete = st.selectbox(
            "Chọn user cần xóa",
            options=delete_options
        )

        confirm_delete = st.checkbox("Tôi xác nhận muốn xóa user này khỏi users.json")

        if st.button("Xóa user"):
            if not confirm_delete:
                st.warning("Anh cần tick xác nhận trước khi xóa.")
            else:
                selected_user_id = selected_delete.split("|")[0].strip()
                deleted = delete_user(selected_user_id)

                if deleted:
                    st.success(f"Đã xóa user ID: {selected_user_id}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Không tìm thấy user để xóa.")

    st.divider()

    