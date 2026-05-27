from pathlib import Path
from datetime import datetime
from app.config import TRAIN_FOLDER

UPLOAD_FOLDER = Path(TRAIN_FOLDER) / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


def sanitize_filename(file_name):
    safe_name = file_name.replace("\\", "_").replace("/", "_")
    safe_name = safe_name.replace(" ", "_")
    return safe_name


def is_txt_file(file_name):
    return file_name.lower().endswith(".txt")


def save_uploaded_txt_file(file_name, file_content):
    safe_name = sanitize_filename(file_name)
    file_path = UPLOAD_FOLDER / safe_name

    with open(file_path, "wb") as f:
        f.write(file_content)

    return file_path


def list_uploaded_documents():
    if not UPLOAD_FOLDER.exists():
        return []

    files = []

    for file_path in sorted(UPLOAD_FOLDER.glob("*.txt")):
        stat = file_path.stat()
        files.append(
            {
                "name": file_path.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return files