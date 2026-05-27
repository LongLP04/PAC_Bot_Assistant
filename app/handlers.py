from app.bot_instance import bot
from app.loader import load_all_knowledge, load_system_prompt, count_txt_files
from app.memory import get_user_history, add_to_history, clear_history
from app.prompts import build_system_prompt, build_user_context
from app.groq_service import ask_groq
from app.config import BOT_NAME, BOT_VERSION, BOT_ENV, GROQ_MODEL, TRAIN_FOLDER, SKILL_FOLDER



def register_handlers():

    # Xử lý lệnh /start
    @bot.message_handler(commands=["start"])
    def send_welcome(message):
        user_id = message.from_user.id
        clear_history(user_id)

        bot.reply_to(
            message,
            "Xin chào! Em là PAC Assistant - Trợ lý ảo IT Support nội bộ. "
            "Anh/chị cần em hỗ trợ vấn đề gì thì nhập nội dung bên dưới nhé."
        )

    # Xử lý lệnh /help
    @bot.message_handler(commands=["help"])
    def send_help(message):
        help_text = (
            "Em có thể hỗ trợ các nhóm việc sau:\n"
            "- Sự cố máy in, in ấn, kết nối máy in\n"
            "- Cài đặt và lỗi Microsoft Office, Outlook, Teams\n"
            "- Lỗi mạng nội bộ, WiFi, LAN, VPN\n"
            "- Lỗi máy tính, Windows, phần mềm cơ bản\n"
            "- Hướng dẫn sử dụng hệ thống, tài khoản, dữ liệu nội bộ\n"
            "...\n\n"
            "Anh/chị chỉ cần mô tả lỗi, ví dụ: “máy in không in được”, “Outlook không gửi mail được”."
        )

        bot.reply_to(message, help_text)

    # Xử lý lệnh /status
    @bot.message_handler(commands=["status"])
    def send_status(message):
        bot.reply_to(
            message,
            "🟢 PAC Assistant đang trực tuyến và sẵn sàng hỗ trợ anh/chị."
        )

    # Xử lý lệnh /clear
    @bot.message_handler(commands=["clear"])
    def clear_user_memory(message):
        user_id = message.from_user.id
        clear_history(user_id)

        bot.reply_to(
            message,
            "Em đã xóa lịch sử trao đổi tạm thời. Anh/chị có thể nhập lại nội dung cần hỗ trợ."
        )

    # Xử lý lệnh /version
    @bot.message_handler(commands=["version"])
    def send_version(message):
        version_text = (
            f"{BOT_NAME}\n"
            f"Phiên bản: {BOT_VERSION}\n"
            f"Môi trường: {BOT_ENV}\n"
            f"Model: {GROQ_MODEL}"
        )

        bot.reply_to(message, version_text)

    # Xử lý lệnh /debug
    @bot.message_handler(commands=["debug"])
    def send_debug(message):
        training_count = count_txt_files(TRAIN_FOLDER)
        skills_count = count_txt_files(SKILL_FOLDER)

        debug_text = (
            "Thông tin kiểm tra bot:\n"
            f"- Tài liệu training: {training_count} file .txt\n"
            f"- Luật/kỹ năng bot: {skills_count} file .txt\n"
            f"- Model: {GROQ_MODEL}\n"
            f"- Phiên bản: {BOT_VERSION}"
        )

        bot.reply_to(message, debug_text)


    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        user_id = message.from_user.id
        user_question = message.text

        if not user_question:
            bot.reply_to(message, "Em chưa nhận được nội dung cần hỗ trợ.")
            return

        try:
            knowledge = load_all_knowledge()
            base_instructions = load_system_prompt()

            system_prompt = build_system_prompt(base_instructions)
            user_context = build_user_context(knowledge, user_question)
            history = get_user_history(user_id)

            messages_to_send = [
                {"role": "system", "content": system_prompt}
            ] + history + [
                {"role": "user", "content": user_context}
            ]

            bot_response = ask_groq(messages_to_send)

            bot.reply_to(message, bot_response)

            add_to_history(user_id, user_question, bot_response)

        except Exception as e:
            bot.reply_to(
                message,
                "Hệ thống đang bận hoặc gặp lỗi kết nối, anh/chị vui lòng thử lại sau nhé."
            )
            print(f"❌ Lỗi vận hành: {e}")