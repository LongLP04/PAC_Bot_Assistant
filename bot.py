from app.handlers import register_handlers
from app.bot_instance import bot

register_handlers()

print("=== PAC Support Assistant đang hoạt động và trực tuyến! ===")
bot.infinity_polling()