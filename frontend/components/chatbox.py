import streamlit as st
from data.chain import process_query
import os, json
from datetime import datetime

HISTORY_DIR = os.path.expanduser("data/chat_history/")


def save_chat_history(messages):
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)

    filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(HISTORY_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)


def load_latest_chat_history():
    if not os.path.exists(HISTORY_DIR):
        return []

    files = [
        os.path.join(HISTORY_DIR, f)
        for f in os.listdir(HISTORY_DIR)
        if f.endswith(".json")
    ]
    if not files:
        return []

    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


@st.fragment
def render_chatbox(model):
    vector_db = st.session_state.get("vector_db")

    # mode_label = "📚 RAG Mode" if vector_db else "🌐 General Mode"
    # st.caption(f"Đang chạy ở chế độ: {mode_label}")

    if "messages" not in st.session_state:
        st.session_state.messages = load_latest_chat_history()
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Nhập câu hỏi..."):
        vector_db = st.session_state.get("vector_db")
        if vector_db is not None:
            num_vectors = vector_db.index.ntotal
            print(f"📊 Đang lưu trữ: {num_vectors} đoạn văn bản.")
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Đang xử lý..."):
                answer = process_query(vector_db, model, prompt)
                st.markdown(answer)
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )
                save_chat_history(st.session_state.messages)
