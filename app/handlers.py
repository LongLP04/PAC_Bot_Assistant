from app.bot_instance import bot
from app.loader import count_txt_files
from app.cache import get_knowledge_cache, get_system_prompt_cache, reload_cache
from app.memory import get_user_history, add_to_history, clear_history
from app.prompts import build_system_prompt, build_user_context
from app.groq_service import ask_groq
from app.config import BOT_NAME, BOT_VERSION, BOT_ENV, GROQ_MODEL, TRAIN_FOLDER, SKILL_FOLDER
from app.logger import logger
from app.security import (
    is_allowed_user,
    is_admin,
    deny_access,
    deny_admin,
    get_user_id,
)
from app.document_service import (
    is_txt_file,
    save_uploaded_txt_file,
    list_uploaded_documents,
)


def register_handlers():

    # Xử lý lệnh /start
    @bot.message_handler(commands=["start"])
    def send_welcome(message):
        if not is_allowed_user(message):
            deny_access(bot, message)
            return

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
        if not is_allowed_user(message):
            deny_access(bot, message)
            return

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
        if not is_allowed_user(message):
            deny_access(bot, message)
            return
        bot.reply_to(
            message,
            "🟢 PAC Assistant đang trực tuyến và sẵn sàng hỗ trợ anh/chị."
        )

    # Xử lý lệnh /clear
    @bot.message_handler(commands=["clear"])
    def clear_user_memory(message):
        if not is_allowed_user(message):
            deny_access(bot, message)
            return

        user_id = message.from_user.id
        clear_history(user_id)

        bot.reply_to(
            message,
            "Em đã xóa lịch sử trao đổi tạm thời. Anh/chị có thể nhập lại nội dung cần hỗ trợ."
        )

    # Xử lý lệnh /version
    @bot.message_handler(commands=["version"])
    def send_version(message):
        if not is_allowed_user(message):
            deny_access(bot, message)
            return

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
        if not is_admin(message):
            deny_admin(bot, message)
            return

        training_count = count_txt_files(TRAIN_FOLDER)
        skills_count = count_txt_files(SKILL_FOLDER)

        knowledge = get_knowledge_cache()
        system_prompt = get_system_prompt_cache()

        debug_text = (
            "Thông tin kiểm tra bot:\n"
            f"- Tài liệu training: {training_count} file .txt\n"
            f"- Luật/kỹ năng bot: {skills_count} file .txt\n"
            f"- Cache training: {len(knowledge)} ký tự\n"
            f"- Cache skills: {len(system_prompt)} ký tự\n"
            f"- Model: {GROQ_MODEL}\n"
            f"- Phiên bản: {BOT_VERSION}"
        )

        bot.reply_to(message, debug_text)

    #Xư lý lệnh /reload 
    @bot.message_handler(commands=["reload"])
    def reload_bot_data(message):
        if not is_admin(message):
            deny_admin(bot, message)
            return

        result = reload_cache()

        reload_text = (
            "Em đã nạp lại tài liệu và luật bot.\n"
            f"- Dung lượng tài liệu training: {result['knowledge_length']} ký tự\n"
            f"- Dung lượng luật/kỹ năng bot: {result['system_prompt_length']} ký tự"
        )

        bot.reply_to(message, reload_text)

    # Xử lý lệnh /myid
    @bot.message_handler(commands=["myid"])
    def send_my_id(message):
        user_id = get_user_id(message)

        bot.reply_to(
            message,
            f"Telegram user ID của anh/chị là: {user_id}"
        )

    # Xử lý lệnh /docs
    @bot.message_handler(commands=["docs"])
    def send_docs(message):
        if not is_admin(message):
            deny_admin(bot, message)
            return

        docs = list_uploaded_documents()

        if not docs:
            bot.reply_to(
                message,
                "Hiện chưa có tài liệu upload nào trong training_materials/uploads/."
            )
            return

        lines = ["Danh sách tài liệu đã upload:"]

        for index, doc in enumerate(docs, start=1):
            lines.append(
                f"{index}. {doc['name']} | {doc['size']} bytes | cập nhật: {doc['modified']}"
            )

        bot.reply_to(message, "\n".join(lines))

    
    @bot.message_handler(content_types=["document"])
    def handle_document_upload(message):
        if not is_admin(message):
            deny_admin(bot, message)
            return

        document = message.document
        file_name = document.file_name

        if not is_txt_file(file_name):
            bot.reply_to(
                message,
                "Hiện tại em chỉ nhận file .txt để nạp tài liệu. "
                "Anh vui lòng chuyển văn bản sang .txt rồi gửi lại."
            )
            return

        try:
            file_info = bot.get_file(document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            saved_path = save_uploaded_txt_file(file_name, downloaded_file)

            result = reload_cache()

            bot.reply_to(
                message,
                "Em đã nhận và nạp tài liệu mới.\n"
                f"- File: {saved_path.name}\n"
                f"- Đã lưu tại: training_materials/uploads/\n"
                f"- Dung lượng cache training: {result['knowledge_length']} ký tự"
            )

        except Exception as e:
            bot.reply_to(
                message,
                "Em chưa lưu được tài liệu upload. Anh kiểm tra lại file hoặc thử gửi lại."
            )
            print(f"❌ Lỗi upload tài liệu: {e}")


    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        if not is_allowed_user(message):
            deny_access(bot, message)
            return

        user_id = message.from_user.id
        user_question = message.text

        if not user_question:
            bot.reply_to(message, "Em chưa nhận được nội dung cần hỗ trợ.")
            return

        try:
            knowledge = get_knowledge_cache()
            base_instructions = get_system_prompt_cache()

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
            logger.exception(f"Lỗi khi xử lý câu hỏi của người dùng: {e}")
            print(f"❌ Lỗi vận hành: {e}")