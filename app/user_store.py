import json
from pathlib import Path


USERS_FILE = Path("users.json")


DEFAULT_USERS = {}


def ensure_users_file():
    """
    Đảm bảo file users.json tồn tại.
    Nếu chưa có thì tạo file rỗng.
    """
    if not USERS_FILE.exists():
        save_users(DEFAULT_USERS)


def load_users():
    """
    Đọc danh sách user từ users.json.
    Hỗ trợ cấu trúc hiện tại:
    {
      "7538013839": {
        "name": "Long",
        "role": "admin"
      }
    }

    Nếu thiếu status/note thì tự bổ sung mặc định.
    """
    ensure_users_file()

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
    except json.JSONDecodeError:
        users = {}
    except Exception:
        users = {}

    if not isinstance(users, dict):
        users = {}

    normalized_users = {}

    for user_id, info in users.items():
        if not isinstance(info, dict):
            continue

        user_id_str = str(user_id).strip()

        if not user_id_str:
            continue

        normalized_users[user_id_str] = {
            "name": info.get("name", ""),
            "role": info.get("role", "user"),
            "status": info.get("status", "active"),
            "note": info.get("note", ""),
        }

    return normalized_users


def save_users(users: dict):
    """
    Ghi danh sách user vào users.json.
    """
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_user(user_id):
    """
    Lấy thông tin 1 user theo Telegram user_id.
    """
    users = load_users()
    return users.get(str(user_id))


def user_exists(user_id) -> bool:
    users = load_users()
    return str(user_id) in users


def is_user_active(user_id) -> bool:
    """
    User được xem là active nếu:
    - Có trong users.json
    - status không phải inactive
    """
    user = get_user(user_id)

    if not user:
        return False

    return user.get("status", "active") == "active"


def is_user_admin(user_id) -> bool:
    """
    User là admin nếu:
    - Có trong users.json
    - status = active
    - role = admin
    """
    user = get_user(user_id)

    if not user:
        return False

    return (
        user.get("status", "active") == "active"
        and user.get("role", "user") == "admin"
    )


def add_or_update_user(user_id, name="", role="user", status="active", note=""):
    """
    Thêm mới hoặc cập nhật user.
    """
    users = load_users()

    user_id_str = str(user_id).strip()

    if not user_id_str:
        raise ValueError("user_id không được để trống")

    if role not in ["admin", "user"]:
        role = "user"

    if status not in ["active", "inactive"]:
        status = "active"

    users[user_id_str] = {
        "name": str(name).strip(),
        "role": role,
        "status": status,
        "note": str(note).strip(),
    }

    save_users(users)

    return users[user_id_str]


def delete_user(user_id):
    """
    Xóa user khỏi users.json.
    """
    users = load_users()
    user_id_str = str(user_id).strip()

    if user_id_str in users:
        deleted_user = users.pop(user_id_str)
        save_users(users)
        return deleted_user

    return None


def get_all_users_as_list():
    """
    Trả danh sách user dạng list để dashboard dễ hiển thị bằng dataframe.
    """
    users = load_users()

    result = []

    for user_id, info in users.items():
        result.append({
            "user_id": user_id,
            "name": info.get("name", ""),
            "role": info.get("role", "user"),
            "status": info.get("status", "active"),
            "note": info.get("note", ""),
        })

    return result