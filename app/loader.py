import os
from app.config import TRAIN_FOLDER, SKILL_FOLDER


def load_txt_files(folder_path, empty_message):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return empty_message

    combined_content = ""

    for file_name in sorted(os.listdir(folder_path)):
        if file_name.endswith(".txt"):
            file_path = os.path.join(folder_path, file_name)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    combined_content += f"\n\n[{file_name}]\n"
                    combined_content += f.read()
            except Exception as e:
                print(f"❌ Không thể đọc file {file_name}: {e}")

    return combined_content if combined_content.strip() else empty_message


def load_all_knowledge():
    return load_txt_files(
        TRAIN_FOLDER,
        "Thư mục tài liệu hiện tại đang trống."
    )


def load_system_prompt():
    return load_txt_files(
        SKILL_FOLDER,
        "Bạn là một kỹ sư IT Support nội bộ chuyên nghiệp."
    )



def count_txt_files(folder_path):
    if not os.path.exists(folder_path):
        return 0

    count = 0

    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith(".txt"):
                count += 1

    return count