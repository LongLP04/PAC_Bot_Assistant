import re
import unicodedata
from typing import List, Dict


DEFAULT_MAX_CHARS = 3000
DEFAULT_MAX_CHUNKS = 5


STOPWORDS = {
    "la", "là", "cua", "của", "va", "và", "cho", "toi", "tôi", "anh", "chi", "chị",
    "em", "co", "có", "khong", "không", "duoc", "được", "trong", "ngoai", "ngoài",
    "the", "thế", "nao", "nào", "gi", "gì", "hay", "hoac", "hoặc", "mot", "một",
    "cac", "các", "nhung", "những", "neu", "nếu", "thi", "thì", "ve", "về",
    "dua", "dựa", "tren", "trên", "tai", "tại", "file", "tai_lieu", "tài", "liệu",
}


def remove_vietnamese_accents(text: str) -> str:
    """
    Chuyển tiếng Việt có dấu thành không dấu để tìm kiếm dễ hơn.
    """
    text = str(text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text


def normalize_text(text: str) -> str:
    """
    Chuẩn hóa text để tìm kiếm.
    """
    text = remove_vietnamese_accents(text).lower()
    text = re.sub(r"[^a-z0-9_\-\. ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_keywords(question: str) -> List[str]:
    """
    Tách từ khóa từ câu hỏi người dùng.
    Giữ lại cả mã thiết bị như PAC-SW-001.
    """
    normalized = normalize_text(question)
    words = normalized.split()

    keywords = []

    for word in words:
        word = word.strip()

        if not word:
            continue

        if len(word) <= 1:
            continue

        if word in STOPWORDS:
            continue

        keywords.append(word)

    # Loại trùng nhưng giữ thứ tự
    unique_keywords = []
    seen = set()

    for keyword in keywords:
        if keyword not in seen:
            unique_keywords.append(keyword)
            seen.add(keyword)

    return unique_keywords


def split_knowledge_documents(knowledge: str) -> List[Dict[str, str]]:
    """
    Tách toàn bộ knowledge thành từng tài liệu dựa trên marker:
    [TÀI LIỆU: ten_file]
    """
    if not knowledge or not knowledge.strip():
        return []

    pattern = r"\n\n\[TÀI LIỆU:\s*(.*?)\]\n"
    matches = list(re.finditer(pattern, knowledge))

    documents = []

    if not matches:
        documents.append({
            "source": "knowledge",
            "content": knowledge.strip(),
        })
        return documents

    for index, match in enumerate(matches):
        source = match.group(1).strip()
        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(knowledge)

        content = knowledge[start:end].strip()

        if content:
            documents.append({
                "source": source,
                "content": content,
            })

    return documents


def split_document_into_chunks(
    source: str,
    content: str,
    max_chunk_chars: int = 1200,
) -> List[Dict[str, str]]:
    """
    Chia tài liệu thành các đoạn nhỏ để chấm điểm.
    Ưu tiên chia theo đoạn văn.
    """
    paragraphs = [
        para.strip()
        for para in re.split(r"\n\s*\n", content)
        if para.strip()
    ]

    chunks = []
    current_parts = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)

        if paragraph_length > max_chunk_chars:
            if current_parts:
                chunks.append({
                    "source": source,
                    "content": "\n\n".join(current_parts).strip(),
                })
                current_parts = []
                current_length = 0

            for start in range(0, paragraph_length, max_chunk_chars):
                chunk_text = paragraph[start:start + max_chunk_chars].strip()
                if chunk_text:
                    chunks.append({
                        "source": source,
                        "content": chunk_text,
                    })

            continue

        if current_length + paragraph_length > max_chunk_chars and current_parts:
            chunks.append({
                "source": source,
                "content": "\n\n".join(current_parts).strip(),
            })
            current_parts = [paragraph]
            current_length = paragraph_length
        else:
            current_parts.append(paragraph)
            current_length += paragraph_length

    if current_parts:
        chunks.append({
            "source": source,
            "content": "\n\n".join(current_parts).strip(),
        })

    return chunks


def build_chunks_from_knowledge(knowledge: str) -> List[Dict[str, str]]:
    """
    Tạo danh sách chunk từ toàn bộ knowledge.
    """
    documents = split_knowledge_documents(knowledge)
    chunks = []

    for document in documents:
        source = document["source"]
        content = document["content"]

        document_chunks = split_document_into_chunks(
            source=source,
            content=content,
            max_chunk_chars=1200,
        )

        chunks.extend(document_chunks)

    return chunks


def score_chunk(question: str, keywords: List[str], chunk: Dict[str, str]) -> int:
    """
    Chấm điểm mức liên quan giữa câu hỏi và một chunk tài liệu.
    """
    source = chunk.get("source", "")
    content = chunk.get("content", "")

    normalized_question = normalize_text(question)
    normalized_source = normalize_text(source)
    normalized_content = normalize_text(content)
    searchable_text = f"{normalized_source} {normalized_content}"

    score = 0

    # Ưu tiên nếu nguyên câu hỏi xuất hiện trong tài liệu
    if normalized_question and normalized_question in searchable_text:
        score += 50

    for keyword in keywords:
        if not keyword:
            continue

        # Từ khóa xuất hiện trong tên file/tên tài liệu
        if keyword in normalized_source:
            score += 8

        # Từ khóa xuất hiện trong nội dung
        occurrences = searchable_text.count(keyword)

        if occurrences > 0:
            score += min(occurrences, 10) * 3

        # Mã thiết bị hoặc mã định danh thường có dấu -
        if "-" in keyword and keyword in searchable_text:
            score += 25

    return score


def select_relevant_knowledge(
    question: str,
    knowledge: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> str:
    """
    Lọc ra phần tài liệu liên quan nhất với câu hỏi.
    Đây là phần sẽ được gửi vào Groq thay vì gửi toàn bộ knowledge.
    """
    if not knowledge or not knowledge.strip():
        return "Không có tài liệu nội bộ nào đang được nạp."

    keywords = extract_keywords(question)
    chunks = build_chunks_from_knowledge(knowledge)

    if not chunks:
        return knowledge[:max_chars]

    scored_chunks = []

    for chunk in chunks:
        score = score_chunk(question, keywords, chunk)

        if score > 0:
            scored_chunks.append({
                "score": score,
                "source": chunk["source"],
                "content": chunk["content"],
            })

    # Nếu không tìm thấy gì liên quan, vẫn gửi một phần rất ngắn để tránh trống context
    if not scored_chunks:
        return (
            "Không tìm thấy đoạn tài liệu nội bộ nào thật sự liên quan đến câu hỏi.\n"
            "Nếu cần, hãy yêu cầu người dùng cung cấp thêm thông tin hoặc kiểm tra lại tài liệu đã nạp."
        )

    scored_chunks = sorted(
        scored_chunks,
        key=lambda item: item["score"],
        reverse=True,
    )

    selected_parts = []
    total_chars = 0

    for item in scored_chunks[:max_chunks]:
        source = item["source"]
        content = item["content"]
        score = item["score"]

        part = (
            f"\n\n[NGUỒN: {source} | ĐIỂM LIÊN QUAN: {score}]\n"
            f"{content}"
        )

        if total_chars + len(part) > max_chars:
            remaining = max_chars - total_chars

            if remaining > 300:
                selected_parts.append(part[:remaining])
                total_chars += remaining

            break

        selected_parts.append(part)
        total_chars += len(part)

    return "\n".join(selected_parts).strip()


def get_retrieval_debug_info(question: str, knowledge: str) -> str:
    """
    Dùng để kiểm tra nhanh bộ lọc tài liệu.
    """
    keywords = extract_keywords(question)
    chunks = build_chunks_from_knowledge(knowledge)

    scored = []

    for chunk in chunks:
        score = score_chunk(question, keywords, chunk)

        if score > 0:
            scored.append({
                "score": score,
                "source": chunk["source"],
            })

    scored = sorted(scored, key=lambda item: item["score"], reverse=True)

    lines = [
        f"Từ khóa: {', '.join(keywords) if keywords else '(không có)'}",
        f"Tổng số chunk: {len(chunks)}",
        "Top nguồn liên quan:",
    ]

    for item in scored[:10]:
        lines.append(f"- {item['source']} | điểm: {item['score']}")

    return "\n".join(lines)