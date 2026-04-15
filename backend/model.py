from numpy import exceptions
import streamlit as st
from langchain_ollama import OllamaLLM
import requests
import os
import json

CONFIG_FILE = "config.json"


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
    if "selected_model" in st.session_state:
        model = OllamaLLM(
            model=st.session_state.selected_model,
            num_thread=10,
            num_ctx=2048,
            temperature=0.1,
        )
        return model
    return None


def get_ollama_models():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=1)
        if response.status_code == 200:
            models_info = response.json().get("models", [])
            return [m["name"] for m in models_info]
        return []
    except:
        return []


def load_config_file():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(model_name, chunk_size, chunk_overlap):
    with open(CONFIG_FILE, "w") as f:
        json.dump(
            {
                "model": model_name,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
            f,
        )
