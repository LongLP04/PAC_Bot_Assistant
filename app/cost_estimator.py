import os


# Giá mặc định có thể chỉnh trong .env
# Đơn vị: USD / 1.000.000 token
DEFAULT_INPUT_PRICE_PER_1M = float(os.getenv("GROQ_INPUT_PRICE_PER_1M", "0.05"))
DEFAULT_OUTPUT_PRICE_PER_1M = float(os.getenv("GROQ_OUTPUT_PRICE_PER_1M", "0.08"))


def estimate_tokens_by_text(text: str) -> int:
    """
    Ước tính token đơn giản.
    Với tiếng Việt, 1 token thường dao động khoảng 3-4 ký tự.
    Dùng mức 3.5 để ước lượng an toàn.
    """
    if not text:
        return 0

    return max(1, int(len(text) / 3.5))


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    input_cost = input_tokens * DEFAULT_INPUT_PRICE_PER_1M / 1_000_000
    output_cost = output_tokens * DEFAULT_OUTPUT_PRICE_PER_1M / 1_000_000
    return round(input_cost + output_cost, 8)


def get_usage_from_groq_response(completion):
    """
    Ưu tiên lấy token thực tế từ Groq response nếu có.
    Nếu không có thì trả None để fallback sang ước tính.
    """
    try:
        usage = getattr(completion, "usage", None)
        if usage:
            return {
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            }
    except Exception:
        pass

    return None