from app.bot_instance import bot
from app.loader import count_txt_files, get_supported_extensions_text
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
    get_supported_upload_extensions_text,
)
from app.knowledge_retriever import (
    select_relevant_knowledge_with_source_policy,
    get_available_sources,
    extract_requested_source,
)

# Ghi log vận hành / token / chi phí
from app.usage_tracker import write_usage_log, start_timer, end_timer
from app.cost_estimator import estimate_tokens_by_text, estimate_cost_usd


def get_error_code(error_text: str) -> str:
    """
    Phân loại nhanh mã lỗi để đưa vào dashboard.
    """
    text = str(error_text).lower()

    if "429" in text:
        return "429"
    if "413" in text:
        return "413"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "rate limit" in text:
        return "rate_limit"
    if "request too large" in text:
        return "request_too_large"

    return "unknown"


def safe_get_username(message):
    """
    Lấy username Telegram an toàn, tránh lỗi khi user không có username.
    """
    try:
        return message.from_user.username
    except Exception:
        return None


def safe_get_first_name(message):
    """
    Lấy first_name Telegram an toàn.
    """
    try:
        return message.from_user.first_name
    except Exception:
        return None


def is_document_lookup_request(text: str) -> bool:
    """
    Nhận diện câu hỏi có ý định tra cứu tài liệu.

    Nguyên tắc:
    - Chỉ kích hoạt retrieval khi user nói rõ đang hỏi theo file/tài liệu.
    - Không dùng các từ quá rộng như 'báo cáo', 'hồ sơ' riêng lẻ.
    - Tránh trường hợp câu hỏi thường bị match nhầm với tên file.
    """
    if not text:
        return False

    normalized_text = text.lower()

    document_indicators = [
        "theo file",
        "theo tài liệu",
        "theo tai lieu",
        "theo văn bản",
        "theo van ban",
        "trong file",
        "trong tài liệu",
        "trong tai lieu",
        "trong văn bản",
        "trong van ban",
        "tóm tắt file",
        "tom tat file",
        "tóm tắt tài liệu",
        "tom tat tai lieu",
        "tóm tắt văn bản",
        "tom tat van ban",
        "liệt kê tài liệu",
        "liet ke tai lieu",
        "danh sách tài liệu",
        "danh sach tai lieu",
        "các tài liệu đã nạp",
        "cac tai lieu da nap",
        "các file đã nạp",
        "cac file da nap",
    ]

    return any(
        indicator in normalized_text
        for indicator in document_indicators
    )


def write_success_usage_log(
    message,
    user_question,
    bot_response,
    messages_to_send,
    latency_seconds,
):
    """
    Ghi log khi xử lý thành công.
    Hiện tại ask_groq chỉ trả về nội dung trả lời, chưa trả về usage thật từ Groq,
    nên ta ước tính token bằng độ dài nội dung.
    """
    input_text = str(messages_to_send)
    output_text = bot_response or ""

    input_tokens = estimate_tokens_by_text(input_text)
    output_tokens = estimate_tokens_by_text(output_text)
    total_tokens = input_tokens + output_tokens
    estimated_cost = estimate_cost_usd(input_tokens, output_tokens)

    write_usage_log({
        "user_id": message.from_user.id,
        "username": safe_get_username(message),
        "first_name": safe_get_first_name(message),
        "question": user_question,
        "response_preview": output_text[:300],
        "model": GROQ_MODEL,
        "status": "success",
        "error_code": None,
        "error_message": None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost,
        "latency_seconds": latency_seconds,
    })


def write_error_usage_log(
    message,
    user_question,
    error,
    latency_seconds,
    messages_to_send=None,
):
    """
    Ghi log khi xử lý lỗi.
    Nếu đã tạo được messages_to_send thì tính token theo toàn bộ prompt.
    Nếu lỗi xảy ra sớm thì chỉ tính theo câu hỏi người dùng.
    """
    error_text = str(error)
    error_code = get_error_code(error_text)

    if messages_to_send:
        input_tokens = estimate_tokens_by_text(str(messages_to_send))
    else:
        input_tokens = estimate_tokens_by_text(user_question or "")

    write_usage_log({
        "user_id": message.from_user.id if message.from_user else None,
        "username": safe_get_username(message),
        "first_name": safe_get_first_name(message),
        "question": user_question,
        "response_preview": None,
        "model": GROQ_MODEL,
        "status": "error",
        "error_code": error_code,
        "error_message": error_text[:500],
        "input_tokens": input_tokens,
        "output_tokens": 0,
        "total_tokens": input_tokens,
        "estimated_cost_usd": 0,
        "latency_seconds": latency_seconds,
    })


def build_docs_list_text():
    """
    Tạo nội dung danh sách tài liệu đã upload.
    """
    docs = list_uploaded_documents()

    if not docs:
        return "Hiện chưa có tài liệu upload nào trong training_materials/uploads/."

    lines = ["Danh sách tài liệu đã upload:"]

    for index, doc in enumerate(docs, start=1):
        lines.append(
            f"{index}. {doc['name']} | {doc['size']} bytes | cập nhật: {doc['modified']}"
        )

    return "\n".join(lines)


def is_list_documents_request(text: str) -> bool:
    """
    Nhận diện câu hỏi tự nhiên yêu cầu liệt kê tài liệu đã nạp.
    """
    if not text:
        return False

    normalized_text = text.lower()

    keyword_groups = [
        ["liệt kê", "tài liệu"],
        ["liet ke", "tai lieu"],
        ["danh sách", "tài liệu"],
        ["danh sach", "tai lieu"],
        ["tài liệu", "đã nạp"],
        ["tai lieu", "da nap"],
        ["tài liệu", "đã upload"],
        ["tai lieu", "da upload"],
        ["file", "đã nạp"],
        ["file", "da nap"],
        ["file", "đã upload"],
        ["file", "da upload"],
        ["các file", "đang có"],
        ["cac file", "dang co"],
        ["các tài liệu", "đang có"],
        ["cac tai lieu", "dang co"],
    ]

    return any(
        all(keyword in normalized_text for keyword in group)
        for group in keyword_groups
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
            "Xin chào👋! Em là PAC Assistant 😊- Trợ lý ảo IT Support nội bộ. "
            "Anh/chị cần em hỗ trợ vấn đề gì thì nhập nội dung bên dưới ạ. "
            "Anh/chị cứ xưng hô anh/chị thoải mái nhé 😊."
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
            "Anh/chị chỉ cần mô tả lỗi, ví dụ: “máy in không in được”, "
            "“Outlook không gửi mail được”."
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
            f"- Tài liệu training: {training_count} file được hỗ trợ\n"
            f"- Luật/kỹ năng bot: {skills_count} file được hỗ trợ\n"
            f"- Định dạng hỗ trợ : {get_supported_extensions_text()}\n"
            f"- Cache training: {len(knowledge)} ký tự\n"
            f"- Cache skills: {len(system_prompt)} ký tự\n"
            f"- Model: {GROQ_MODEL}\n"
            f"- Phiên bản: {BOT_VERSION}"
        )

        bot.reply_to(message, debug_text)

    # Xử lý lệnh /reload
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

        bot.reply_to(message, build_docs_list_text())

    # Xử lý upload tài liệu
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
                "File này chưa được hỗ trợ để nạp tài liệu.\n"
                f"Các định dạng hiện hỗ trợ: {get_supported_upload_extensions_text()}."
            )
            return

        try:
            file_info = bot.get_file(document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            uploaded_by = {
                "user_id": message.from_user.id if message.from_user else None,
                "username": message.from_user.username if message.from_user else None,
                "first_name": message.from_user.first_name if message.from_user else None,
            }

            saved_path = save_uploaded_txt_file(
                file_name,
                downloaded_file,
                uploaded_by=uploaded_by,
            )

            result = reload_cache()

            bot.reply_to(
                message,
                "Em đã nhận và nạp tài liệu mới.\n"
                f"- File: {saved_path.name}\n"
                f"- Đã lưu tại: training_materials/uploads/\n"
                f"- Dung lượng cache training: {result['knowledge_length']} ký tự\n"
                f"- Định dạng hỗ trợ: {get_supported_upload_extensions_text()}"
            )

        except Exception as e:
            bot.reply_to(
                message,
                "Em chưa lưu được tài liệu upload. "
                "Anh/chị vui lòng kiểm tra lại file, định dạng hoặc thử gửi lại giúp em nhé.\n"
                f"Các định dạng hiện hỗ trợ: {get_supported_upload_extensions_text()}."
            )
            logger.exception(f"Lỗi upload tài liệu: {e}")
            print(f"❌ Lỗi upload tài liệu: {e}")

    # Xử lý tin nhắn thường
    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        if not is_allowed_user(message):
            deny_access(bot, message)
            return

        timer = start_timer()
        messages_to_send = None

        user_id = message.from_user.id
        user_question = message.text

        if not user_question:
            bot.reply_to(message, "Em chưa nhận được nội dung cần hỗ trợ.")
            return

        try:
            # Câu hỏi quản trị tài liệu: xử lý bằng code, không gọi Groq
            if is_list_documents_request(user_question):
                if not is_admin(message):
                    deny_admin(bot, message)
                    return

                bot.reply_to(message, build_docs_list_text())
                return

            full_knowledge = get_knowledge_cache()
            history = get_user_history(user_id)

            document_lookup_intent = is_document_lookup_request(user_question)

            current_requested_source = None

            if document_lookup_intent:
                available_sources = get_available_sources(full_knowledge)

                current_requested_source = extract_requested_source(
                    question=user_question,
                    available_sources=available_sources,
                )

            use_document_retrieval = document_lookup_intent

            if use_document_retrieval:
                retrieval_result = select_relevant_knowledge_with_source_policy(
                    question=user_question,
                    knowledge=full_knowledge,
                    max_chars=3000,
                    max_chunks=5,
                )

                relevant_knowledge = retrieval_result["context"]
                retrieval_mode = retrieval_result["mode"]
                retrieval_source = retrieval_result["source"]
                should_recommend_source_name = retrieval_result["should_recommend_source_name"]

            else:
                relevant_knowledge = ""
                retrieval_mode = "normal_chat"
                retrieval_source = None
                should_recommend_source_name = False

            base_instructions = get_system_prompt_cache()
            system_prompt = build_system_prompt(base_instructions)

            if retrieval_mode == "specified_source" and retrieval_source:
                source_instruction = (
                    f"\n\n[LƯU Ý NGUỒN]\n"
                    f"Người dùng đã chỉ định tài liệu: {retrieval_source}.\n"
                    f"Trước tiên hãy kiểm tra thông tin trong tài liệu này.\n"
                    f"Nếu tài liệu không có đủ thông tin để trả lời, hãy nói rõ: "
                    f"'Trong tài liệu chưa có thông tin này', sau đó trả lời bằng kiến thức IT Support chung.\n"
                    f"Tuyệt đối không tự chuyển sang tài liệu khác.\n"
                    f"Không tự ghi dòng nguồn tài liệu trong câu trả lời, hệ thống sẽ tự thêm ở cuối.\n"
                )

            elif retrieval_mode == "auto_retrieval" and retrieval_source:
                source_instruction = (
                    f"\n\n[LƯU Ý NGUỒN]\n"
                    f"Người dùng có ý định tra cứu tài liệu nhưng chưa chỉ định rõ file.\n"
                    f"Hệ thống đã tự chọn tài liệu liên quan nhất: {retrieval_source}.\n"
                    f"Nếu tài liệu này không có đủ thông tin để trả lời, hãy nói rõ: "
                    f"'Tài liệu đang tham chiếu chưa có thông tin này', sau đó trả lời bằng kiến thức IT Support chung.\n"
                    f"Tuyệt đối không tự chuyển sang tài liệu khác.\n"
                    f"Không tự ghi dòng nguồn tài liệu trong câu trả lời, hệ thống sẽ tự thêm ở cuối.\n"
                )

            else:
                source_instruction = (
                    "\n\n[LƯU Ý HỘI THOẠI]\n"
                    "Người dùng đang trao đổi hoặc xử lý sự cố thông thường, không phải đang yêu cầu tra cứu tài liệu. "
                    "Không tự mở đầu bằng 'theo tài liệu'. "
                    "Không tự truy cứu bất kỳ tài liệu nội bộ nào. "
                    "Hãy trả lời theo ngữ cảnh hội thoại và vai trò IT Support nội bộ.\n"
                )

            user_context = build_user_context(
                relevant_knowledge + source_instruction,
                user_question,
            )

            messages_to_send = [
                {"role": "system", "content": system_prompt}
            ] + history + [
                {"role": "user", "content": user_context}
            ]

            bot_response = ask_groq(messages_to_send)

            source_note = ""

            if retrieval_source:
                source_name = str(retrieval_source).replace("\\", "/").split("/")[-1]

                if retrieval_mode == "specified_source":
                    source_note = (
                        f"\n\nNguồn tài liệu được chỉ định: {source_name}"
                    )

                elif retrieval_mode == "auto_retrieval":
                    source_note = (
                        f"\n\nNguồn hệ thống tự tham chiếu: {source_name}"
                    )

            if source_note and source_note not in bot_response:
                bot_response += source_note

            if should_recommend_source_name:
                bot_response += (
                    "\n\nGợi ý: Để em tra cứu chính xác hơn, anh/chị có thể hỏi kèm tên tài liệu.😊"
                )

            bot.reply_to(message, bot_response)

            add_to_history(user_id, user_question, bot_response)

            latency_seconds = end_timer(timer)

            write_success_usage_log(
                message=message,
                user_question=user_question,
                bot_response=bot_response,
                messages_to_send=messages_to_send,
                latency_seconds=latency_seconds,
            )

        except Exception as e:
            latency_seconds = end_timer(timer)

            bot.reply_to(
                message,
                "Hệ thống đang bận hoặc gặp lỗi kết nối, anh/chị vui lòng thử lại sau nhé."
            )

            write_error_usage_log(
                message=message,
                user_question=user_question,
                error=e,
                latency_seconds=latency_seconds,
                messages_to_send=messages_to_send,
            )

            logger.exception(f"Lỗi khi xử lý câu hỏi của người dùng: {e}")
            print(f"❌ Lỗi vận hành: {e}")