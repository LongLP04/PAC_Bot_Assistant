from telebot import types
from app.bot_instance import bot


def setup_bot_commands():
    commands = [
        types.BotCommand("start", "Khởi động PAC Assistant"),
        types.BotCommand("help", "Xem các nhóm hỗ trợ IT"),
        types.BotCommand("status", "Kiểm tra trạng thái bot"),
        types.BotCommand("clear", "Xóa lịch sử trao đổi tạm thời"),
        types.BotCommand("version", "Xem phiên bản bot"),
        types.BotCommand("debug", "Kiểm tra cấu hình và tài liệu bot"),
        types.BotCommand("reload", "Nạp lại dữ liệu bot"),
        types.BotCommand("myid", "Xem Telegram user ID của tôi"),
        ]

    bot.set_my_commands(commands)