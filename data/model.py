import streamlit as st
from langchain_ollama import OllamaLLM


def get_prompt_template(user_input):
    vn_chars = "àáảãạăâèéêìíòóôơùúưỳýđịĩủũụừứặắằếềốồớờộỗỡ"
    # Kiểm tra nếu có bất kỳ ký tự tiếng Việt đặc trưng nào
    is_vn = any(c in user_input.lower() for c in vn_chars)

    if is_vn:
        return """Sử dụng ngữ cảnh sau đây để trả lời câu hỏi.
Nếu bạn không biết, chỉ cần nói là bạn không biết.
Trả lời ngắn gọn (3-4 câu) BẮT BUỘC bằng tiếng Việt.
Ngữ cảnh: {context}
Câu hỏi: {user_input}
Trả lời: """

    return """Use the following context to answer the question.
If you don't know the answer, just say you don't know.
Keep answer concise (3-4 sentences).
Context: {context}
Question: {user_input}
Answer: """


@st.cache_resource
def get_model():
    return OllamaLLM(
        model="gemma4:e2b",
        num_thread=8,
        num_ctx=2048,
        temperature=0.1,
        repeat_penalty=1.1,
    )
