from app.handlers import register_handlers
from app.commands import setup_bot_commands
from app.bot_instance import bot

register_handlers()
setup_bot_commands()

print("=== PAC Support Assistant đang hoạt động và trực tuyến! ===")
bot.infinity_polling()