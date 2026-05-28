from pathlib import Path
from datetime import datetime

from app.config import TRAIN_FOLDER
from app.document_reader import is_supported_file, SUPPORTED_EXTENSIONS


UPLOAD_FOLDER = Path(TRAIN_FOLDER) / "uploads"


def ensure_upload_folder():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def is_txt_file(file_name):
    """
    Giữ tên hàm cũ để không phải sửa nhiều ở handlers.py.
    Nhưng hiện tại hàm này kiểm tra toàn bộ định dạng được hỗ trợ.
    """
    return is_supported_file(file_name)


def is_supported_document(file_name):
    return is_supported_file(file_name)


def save_uploaded_txt_file(file_name, file_bytes):
    """
    Giữ tên hàm cũ để tương thích code cũ.
    Hiện tại dùng để lưu mọi file được hỗ trợ.
    """
    ensure_upload_folder()

    safe_name = Path(file_name).name
    saved_path = UPLOAD_FOLDER / safe_name

    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    return saved_path


def list_uploaded_documents():
    ensure_upload_folder()

    documents = []

    for file_path in sorted(UPLOAD_FOLDER.iterdir()):
        if not file_path.is_file():
            continue

        if not is_supported_file(file_path.name):
            continue

        stat = file_path.stat()

        documents.append({
            "name": file_path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "extension": file_path.suffix.lower(),
        })

    return documents


def get_supported_upload_extensions_text():
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))