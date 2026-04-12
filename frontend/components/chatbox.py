import streamlit as st
from data.chain_rag import process_query
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
    st.markdown("""
    <style>
    /* 1. ẨN AVATAR */
    [data-testid="stChatMessageAvatarUser"], 
    [data-testid="stChatMessageAvatarAssistant"] {
        display: none !important;
    }

    /* 2. CẤU HÌNH CHUNG (Không để border hay background ở đây) */
    [data-testid="stChatMessage"] {
        background-color: transparent !important;
        display: flex !important;
        width: 100% !important;
        padding: 0px !important;
        margin-bottom: 20px !important;
    }

    [data-testid="stChatMessage"] div[data-testid="stMarkdownContainer"] {
        font-family: 'Inter', sans-serif;
        line-height: 1.6;
        max-width: 80%; /* Giới hạn độ rộng để lệch rõ hơn */
    }

    /* 3. XỬ LÝ RIÊNG CHO USER (Có khung, có viền, lệch phải) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        flex-direction: row-reverse !important;
    }
    
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stMarkdownContainer"] {
        background-color: rgba(255, 255, 255, 0.08) !important; /* Nền nhạt */
        border: 1px solid rgba(255, 255, 255, 0.15) !important; /* Viền nhạt */
        color: white !important;
        border-radius: 25px !important;
        padding: 12px 18px !important;
        margin-left: auto !important;
    }

    /* 4. XỬ LÝ RIÊNG CHO ASSISTANT (Xóa sạch viền và nền) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        flex-direction: row !important;
    }

    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) div[data-testid="stMarkdownContainer"] {
        background-color: transparent !important; /* Xóa nền */
        border: none !important; /* XÓA VIỀN TUYỆT ĐỐI */
        color: #ececec !important;
        padding: 10px 0px !important; /* Padding 0 để sát lề trái */
        margin-right: auto !important;
        max-width: 100% !important;
        box-shadow: none !important; /* Xóa bóng đổ nếu có */
    }
    
    /* Chỉnh màu chữ trong p tag cho chắc chắn */
    [data-testid="stMarkdownContainer"] p {
        color: white !important;
        margin-bottom: 0px !important;
    }
                
    /* 5. CHỈNH Ô NHẬP CÂU HỎI (CHAT INPUT) */
    [data-testid="stChatInput"] {
        padding-bottom: 20px !important; /* Tạo khoảng trống phía dưới cùng */
    }

   
    

    </style>
""", unsafe_allow_html=True)
    vector_db = st.session_state.get("vector_db")

    # mode_label = "📚 RAG Mode" if vector_db else "🌐 General Mode"
    # st.caption(f"Đang chạy ở chế độ: {mode_label}")

    if "messages" not in st.session_state:
        st.session_state.messages = load_latest_chat_history()
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(f'<p style="color: white;">{msg["content"]}</p>', unsafe_allow_html=True)
            else:
                if "rag_content" in msg and "corag_content" in msg:
                    col1, col2 = st.columns(2)
                    col1.info(f"**📍 Vector RAG:**\n\n{msg['rag_content']}")
                    col2.success(f"**✨ CoRAG (Verified):**\n\n{msg['corag_content']}")
                else:
                    st.markdown(msg.get("content",""))

    if user_input := st.chat_input("Nhập câu hỏi...",max_chars=500):
        # Hiển thị câu hỏi User
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)


        # Trả lời của Assistant
        with st.chat_message("assistant"):
            with st.spinner("Đang truy vấn song song..."):
                # GỌI HÀM: Truyền đủ 4 tham số
                # Kết quả trả về là: {"vector": "...", "graph": "..."}
                results = process_query(vector_db, model, user_input)
                
                # HIỂN THỊ CHIA CỘT NGAY LẬP TỨC
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**📍 Vector RAG:**\n\n{results['rag']}")
                with col2:
                    corag_text = results['corag'] if results['corag'] else "Không đủ dữ liệu tin cậy để đánh giá."
                    st.success(f"**✨ CoRAG (Verified):**\n\n{corag_text}")
                
                # LƯU VÀO HISTORY (Sử dụng cấu trúc mới)
                st.session_state.messages.append({
                    "role": "assistant",
                    "rag_content": results['rag'],
                    "corag_content": results['corag']
                })
                save_chat_history(st.session_state.messages)
