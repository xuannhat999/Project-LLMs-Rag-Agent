import os
import json

HISTORY_DIR = os.path.expanduser("backend/chat_history/")


def get_chat_history():
    if not os.path.exists(HISTORY_DIR):
        return []

    sessions = []
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    # Sắp xếp file mới nhất lên đầu
    files.sort(
        key=lambda x: os.path.getctime(os.path.join(HISTORY_DIR, x)), reverse=True
    )
    for f in files:
        filepath = os.path.join(HISTORY_DIR, f)
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                data = json.load(file)
                # Tìm tin nhắn đầu tiên của user để làm tiêu đề
                first_question = "Phiên thảo luận trống"
                for msg in data:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        # Cắt ngắn nếu câu hỏi quá dài
                        first_question = (
                            (content[:35] + "...") if len(content) > 35 else content
                        )
                        break

                sessions.append({"filename": f, "title": first_question})
        except Exception:
            continue
    return sessions
