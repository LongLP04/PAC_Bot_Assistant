import os
from pathlib import Path

from app.config import TRAIN_FOLDER, SKILL_FOLDER
from app.document_reader import read_document, is_supported_file, SUPPORTED_EXTENSIONS


def load_supported_files(folder_path, empty_message):
    """
    Đọc toàn bộ tài liệu được hỗ trợ trong folder_path.
    Hỗ trợ:
    - .txt
    - .md
    - .docx
    - .xlsx
    - .csv
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return empty_message

    combined_content = ""

    for root, dirs, files in os.walk(folder_path):
        for file_name in sorted(files):
            if not is_supported_file(file_name):
                continue

            file_path = Path(root) / file_name

            try:
                relative_path = os.path.relpath(file_path, folder_path)
                file_content = read_document(file_path)

                if not file_content.strip():
                    continue

                combined_content += f"\n\n[TÀI LIỆU: {relative_path}]\n"
                combined_content += file_content

            except Exception as e:
                print(f"❌ Không thể đọc file {file_name}: {e}")

    return combined_content if combined_content.strip() else empty_message


def load_all_knowledge():
    return load_supported_files(
        TRAIN_FOLDER,
        "Thư mục tài liệu hiện tại đang trống."
    )


def load_system_prompt():
    return load_supported_files(
        SKILL_FOLDER,
        "Bạn là một kỹ sư IT Support nội bộ chuyên nghiệp."
    )


def count_supported_files(folder_path):
    if not os.path.exists(folder_path):
        return 0

    count = 0

    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            if is_supported_file(file_name):
                count += 1

    return count


def count_txt_files(folder_path):
    """
    Giữ tên hàm cũ để tránh lỗi import ở handlers.py.
    Từ nay hàm này đếm toàn bộ file được hỗ trợ.
    """
    return count_supported_files(folder_path)


def get_supported_extensions_text():
    return ", ".join(sorted(SUPPORTED_EXTENSIONS))