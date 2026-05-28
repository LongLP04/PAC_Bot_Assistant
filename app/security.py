import os

from app.user_store import is_user_active, is_user_admin


def _parse_ids_from_env(value: str):
    """
    Chuyển chuỗi ID trong .env thành set.
    Hỗ trợ dạng:
    ADMIN_USER_IDS=123,456,789
    ALLOWED_USER_IDS=123,456,789
    """
    if not value:
        return set()

    return {
        item.strip()
        for item in value.split(",")
        if item.strip()
    }


# Admin gốc từ .env để tránh bị khóa nhầm nếu users.json lỗi
ROOT_ADMIN_IDS = _parse_ids_from_env(os.getenv("ADMIN_USER_IDS", ""))

# Danh sách user được phép từ .env, giữ để tương thích cũ
ENV_ALLOWED_USER_IDS = _parse_ids_from_env(os.getenv("ALLOWED_USER_IDS", ""))


def get_user_id(message):
    """
    Lấy Telegram user_id từ message.
    """
    try:
        return message.from_user.id
    except Exception:
        return None


def is_root_admin(user_id) -> bool:
    """
    Admin gốc lấy từ .env.
    Quyền này luôn được ưu tiên.
    """
    if user_id is None:
        return False

    return str(user_id) in ROOT_ADMIN_IDS


def is_allowed_user(message) -> bool:
    """
    Kiểm tra user có được dùng bot hay không.

    Ưu tiên:
    1. Admin gốc trong .env
    2. User active trong users.json
    3. User nằm trong ALLOWED_USER_IDS của .env
    """
    user_id = get_user_id(message)

    if user_id is None:
        return False

    user_id_str = str(user_id)

    if is_root_admin(user_id):
        return True

    if is_user_active(user_id_str):
        return True

    if user_id_str in ENV_ALLOWED_USER_IDS:
        return True

    return False


def is_admin(message) -> bool:
    """
    Kiểm tra user có quyền admin hay không.

    Admin gồm:
    1. Admin gốc trong .env
    2. User có role=admin trong users.json và status=active
    """
    user_id = get_user_id(message)

    if user_id is None:
        return False

    user_id_str = str(user_id)

    if is_root_admin(user_id_str):
        return True

    if is_user_admin(user_id_str):
        return True

    return False


def deny_access(bot, message):
    """
    Phản hồi khi user không có quyền dùng bot.
    """
    bot.reply_to(
        message,
        "Anh/chị chưa được cấp quyền sử dụng PAC Assistant. "
        "Vui lòng liên hệ bộ phận quản trị để được hỗ trợ."
    )


def deny_admin(bot, message):
    """
    Phản hồi khi user không có quyền admin.
    """
    bot.reply_to(
        message,
        "Anh/chị chưa có quyền quản trị để thực hiện lệnh này."
    )