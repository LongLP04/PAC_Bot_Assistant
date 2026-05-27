import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
USERS_FILE = BASE_DIR / "users.json"


def load_users():
    if not USERS_FILE.exists():
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Không thể đọc users.json: {e}")
        return {}


def get_user_id(message):
    return str(message.from_user.id)


def get_user_info(message):
    users = load_users()
    user_id = get_user_id(message)

    return users.get(user_id)


def is_allowed_user(message):
    user_info = get_user_info(message)
    return user_info is not None


def is_admin(message):
    user_info = get_user_info(message)

    if not user_info:
        return False

    return user_info.get("role") == "admin"


def deny_access(bot, message):
    bot.reply_to(
        message,
        "Tài khoản Telegram này chưa được cấp quyền sử dụng PAC Assistant. "
        "Anh/chị vui lòng liên hệ IT để được kích hoạt."
    )


def deny_admin(bot, message):
    bot.reply_to(
        message,
        "Lệnh này chỉ dành cho quản trị viên PAC Assistant."
    )