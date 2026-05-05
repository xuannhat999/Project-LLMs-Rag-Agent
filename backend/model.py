import streamlit as st
from langchain_ollama import OllamaLLM
import requests
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"


def get_promt_template(user_input):
    vn_chars = "àáảãạăâèéêìíòóôơùúưỳýđịĩủũụừứặắằếềốồớờộỗỡ"
    is_vn = any(c in user_input.lower() for c in vn_chars)

    if is_vn:
        return """Bạn là một trợ lý ảo thông minh. Dưới đây là ngữ cảnh tài liệu.nếu bạn không biết chỉ cần bạn trả lời không biết.BẮT BUỘC bằng TIẾNG VIỆT
Ngữ cảnh:{context}
Câu hỏi: {user_input}
Trả lời (ngắn gọn 3-4 câu, bằng tiếng Việt): """

    return """You are a helpful assistant. Below is document context.If you don't know the answer just response you don't know
Context:{context}
Question: {user_input}
Answer (concise 3-4 sentences): """


def get_promt_with_memory(user_input):
    vn_chars = "àáảãạăâèéêìíòóôơùúưỳýđịĩủũụừứặắằếềốồớờộỗỡ"
    is_vn = any(c in user_input.lower() for c in vn_chars)

    if is_vn:
        return """Bạn là một trợ lý ảo thông minh. Dưới đây là ngữ cảnh tài liệu và lịch sử trò chuyện.nếu bạn không biết chỉ cần bạn trả lời không biết.BẮT BUỘC bằng TIẾNG VIỆT
Lịch sử: {memory}
Ngữ cảnh:{context}
Câu hỏi: {user_input}
Trả lời ngắn gọn 3-4 câu, bằng tiếng Việt"""

    return """You are a helpful assistant. Below is document context and history chat.If you don't know the answer just response you don't know
History: {memory}
Context:{context}
Question: {user_input}
Answer concise 3-4 sentences"""


def get_promt_memory_no_cont(user_input):
    vn_chars = "àáảãạăâèéêìíòóôơùúưỳýđịĩủũụừứặắằếềốồớờộỗỡ"
    is_vn = any(c in user_input.lower() for c in vn_chars)
    if is_vn:
        return """ Dưới đây là lịch sử trò chuyện
Lịch sử: {memory}
Câu hỏi: {user_input}
Trả lời ngắn gọn 3-4 câu, bằng tiếng Việt"""
    return """You are a helpful assistant. Below is history chat.If you don't know the answer just response you don't know
History: {memory}
Question: {user_input}
Answer concise 3-4 sentences"""


@st.cache_resource
def get_model():
    if "selected_model" in st.session_state:
        model = OllamaLLM(
            model=st.session_state.selected_model,
            num_thread=6,
            num_ctx=2048,
            temperature=0.1,
            num_gpu=35,
        )
        return model
    return None


@st.cache_resource
def get_api_model():
    return ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0.1)


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
