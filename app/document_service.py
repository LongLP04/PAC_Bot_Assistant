import json
from pathlib import Path
from datetime import datetime, timedelta

from app.config import TRAIN_FOLDER
from app.document_reader import is_supported_file, SUPPORTED_EXTENSIONS


UPLOAD_FOLDER = Path(TRAIN_FOLDER) / "uploads"
UPLOAD_LOG_FILE = Path("logs") / "document_uploads.jsonl"


def ensure_upload_folder():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def ensure_upload_log_folder():
    UPLOAD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def is_txt_file(file_name):
    """
    Giữ tên hàm cũ để không phải sửa nhiều ở handlers.py.
    Hiện tại hàm này kiểm tra toàn bộ định dạng được hỗ trợ.
    """
    return is_supported_file(file_name)


def is_supported_document(file_name):
    return is_supported_file(file_name)


def save_document_upload_log(data: dict):
    """
    Ghi log mỗi lần upload tài liệu.
    """
    ensure_upload_log_folder()

    with open(UPLOAD_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def save_uploaded_txt_file(file_name, file_bytes, uploaded_by=None):
    """
    Giữ tên hàm cũ để tương thích code cũ.
    Hiện tại dùng để lưu mọi file được hỗ trợ.
    """
    ensure_upload_folder()

    safe_name = Path(file_name).name
    saved_path = UPLOAD_FOLDER / safe_name

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    uploaded_by = uploaded_by or {}

    upload_log = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "file_name": saved_path.name,
        "file_path": str(saved_path).replace("\\", "/"),
        "extension": saved_path.suffix.lower(),
        "size": saved_path.stat().st_size,
        "uploaded_by_user_id": uploaded_by.get("user_id"),
        "uploaded_by_username": uploaded_by.get("username"),
        "uploaded_by_first_name": uploaded_by.get("first_name"),
    }

    save_document_upload_log(upload_log)

    return saved_path


def load_document_upload_logs():
    """
    Đọc log upload tài liệu.
    """
    if not UPLOAD_LOG_FILE.exists():
        return []

    logs = []

    with open(UPLOAD_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
                logs.append(item)
            except Exception:
                continue

    return logs


def get_latest_upload_by_file_name(file_name: str):
    """
    Lấy lần upload mới nhất của một file.
    """
    logs = load_document_upload_logs()

    matched_logs = [
        item for item in logs
        if item.get("file_name") == file_name
    ]

    if not matched_logs:
        return None

    return matched_logs[-1]


def list_uploaded_documents():
    ensure_upload_folder()

    documents = []

    now = datetime.now()

    for file_path in sorted(
        UPLOAD_FOLDER.iterdir(),
        key=lambda path: path.stat().st_mtime if path.is_file() else 0,
        reverse=True,
    ):
        if not file_path.is_file():
            continue

        if not is_supported_file(file_path.name):
            continue

        stat = file_path.stat()
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        latest_log = get_latest_upload_by_file_name(file_path.name)

        uploaded_by = ""

        if latest_log:
            name = latest_log.get("uploaded_by_first_name") or ""
            username = latest_log.get("uploaded_by_username") or ""
            user_id = latest_log.get("uploaded_by_user_id") or ""

            if username:
                uploaded_by = f"{name} (@{username})".strip()
            elif name:
                uploaded_by = name
            elif user_id:
                uploaded_by = str(user_id)

        is_new = modified_time >= now - timedelta(hours=24)

        documents.append({
            "name": file_path.name,
            "size": stat.st_size,
            "modified": modified_time.strftime("%Y-%m-%d %H:%M:%S"),
            "extension": file_path.suffix.lower(),
            "uploaded_by": uploaded_by,
            "uploaded_by_user_id": latest_log.get("uploaded_by_user_id") if latest_log else "",
            "uploaded_at": latest_log.get("time") if latest_log else "",
            "is_new": is_new,
            "status": "Mới" if is_new else "Đã nạp",
        })

    return documents


def get_supported_upload_extensions_text():
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))