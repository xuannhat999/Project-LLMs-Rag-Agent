import streamlit as st
from data.chain_rag import process_query  # Giữ nguyên hàm gốc của bạn
import os, json
from datetime import datetime

HISTORY_DIR = os.path.expanduser("data/chat_history/")

# --- HÀM QUẢN LÝ LỊCH SỬ (Giữ nguyên logic file 1) ---
def save_chat_history(messages):
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)
    
    # Tạo tên file cố định cho mỗi session để tránh lưu quá nhiều file nhỏ
    if "current_session_file" not in st.session_state:
        st.session_state.current_session_file = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    filepath = os.path.join(HISTORY_DIR, st.session_state.current_session_file)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def load_latest_chat_history():
    if not os.path.exists(HISTORY_DIR):
        return []
    files = [os.path.join(HISTORY_DIR, f) for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    if not files:
        return []
    latest_file = max(files, key=os.path.getctime)
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

# --- GIAO DIỆN CHATBOX ---
@st.fragment
def render_chatbox(model):
    # --- 1. CSS TỐI ƯU (Theo phong cách file 2) ---
    st.markdown("""
    <style>
    /* Ẩn avatar mặc định của Streamlit */
    [data-testid="stChatMessageAvatarUser"], 
    [data-testid="stChatMessageAvatarAssistant"] {
        display: none !important;
    }

    /* Định dạng chung cho tin nhắn */
    [data-testid="stChatMessage"] {
        padding: 10px 0px !important;
    }

    /* STYLE CHO USER (Màu xanh nhạt, lệch phải) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stMarkdownContainer"] {
        background-color: #E1F5FE !important;
        border: 1px solid #01579B !important;
        color: #01579B !important;
        border-radius: 15px !important;
        padding: 10px 20px !important;
        margin-left: auto !important;
        width: fit-content !important;
        max-width: 80% !important;
    }
    
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {
        color: #01579B !important;
        font-weight: 500;
    }

    /* STYLE CHO ASSISTANT (Nền xám nhạt, có khung bao quát) */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #F5F5F5 !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 20px !important;
    }
    
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) p {
        color: #333333 !important;
    }

    /* Tiêu đề cột RAG và CoRAG */
    .column-header {
        font-weight: bold;
        text-transform: uppercase;
        border-bottom: 2px solid #333;
        margin-bottom: 15px;
        padding-bottom: 5px;
        color: #333 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Chỉnh Chat Input sát đáy */
    [data-testid="stChatInput"] {
        padding-bottom: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    vector_db = st.session_state.get("vector_db")

    # Khởi tạo tin nhắn nếu chưa có
    if "messages" not in st.session_state:
        st.session_state.messages = load_latest_chat_history()

    # Tạo container hiển thị nội dung chat
    chat_placeholder = st.container()

    # Ô nhập liệu
    user_input = st.chat_input("Nhập câu hỏi để so sánh RAG và CoRAG...", max_chars=500)

    with chat_placeholder:
        # 2. HIỂN THỊ LỊCH SỬ CHAT
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "user":
                    st.markdown(msg["content"])
                else:
                    # Nếu là tin nhắn của Assistant và có dữ liệu so sánh
                    if "rag_content" in msg and "corag_content" in msg:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("<div class='column-header'>🤖 MÔ HÌNH RAG</div>", unsafe_allow_html=True)
                            st.markdown(msg["rag_content"])
                        with c2:
                            st.markdown("<div class='column-header'>🛡️ MÔ HÌNH CoRAG</div>", unsafe_allow_html=True)
                            st.markdown(msg["corag_content"])
                    else:
                        # Trường hợp tin nhắn cũ hoặc tin nhắn thông báo
                        st.markdown(msg.get("content", ""))

    # 3. XỬ LÝ KHI NGƯỜI DÙNG NHẬP CÂU HỎI MỚI
    if user_input:
        with chat_placeholder:
            # Hiển thị câu hỏi User ngay lập tức
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Phản hồi của Assistant
            with st.chat_message("assistant"):
                # Tạo tiêu đề cột trước khi có kết quả
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("<div class='column-header'>🤖 MÔ HÌNH RAG</div>", unsafe_allow_html=True)
                    rag_area = st.empty() # Vùng trống để cập nhật sau
                with col2:
                    st.markdown("<div class='column-header'>🛡️ MÔ HÌNH CoRAG</div>", unsafe_allow_html=True)
                    corag_area = st.empty() # Vùng trống để cập nhật sau

                with st.spinner("Đang truy vấn dữ liệu và so sánh..."):
                    try:
                        # GỌI HÀM LOGIC CỦA FILE 1 (Workflow gốc)
                        # Đảm bảo hàm process_query trả về dict có key 'rag' và 'corag'
                        results = process_query(vector_db, model, user_input)
                        
                        # Hiển thị kết quả vào đúng cột
                        rag_area.markdown(results.get('rag', 'Không có phản hồi từ RAG.'))
                        
                        corag_text = results.get('corag')
                        if not corag_text:
                            corag_text = "Không đủ dữ liệu tin cậy để đánh giá."
                        corag_area.markdown(corag_text)

                        # 4. LƯU VÀO LỊCH SỬ
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "So sánh RAG & CoRAG", # Text ẩn cho logic
                            "rag_content": results.get('rag'),
                            "corag_content": corag_text
                        })
                        save_chat_history(st.session_state.messages)
                        
                    except Exception as e:
                        st.error(f"Đã xảy ra lỗi khi xử lý: {str(e)}")