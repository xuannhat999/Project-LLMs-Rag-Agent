import streamlit as st
from streamlit.runtime.state import session_state
from backend.chain_rag import process_query  # Giữ nguyên hàm gốc của bạn
import os, json
from datetime import datetime
from backend.chat import HISTORY_DIR, get_chat_history
import re



def highlight_text(text, query):
    # Lấy các từ quan trọng từ query (bỏ qua các từ quá ngắn)
    keywords = [w for w in query.split() if len(w) > 3]
    for word in keywords:
        # Sử dụng Regex để thay thế không phân biệt hoa thường
        try:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub(f"**{word}**", text) 
        except:
            continue
    return text
def save_chat_history(messages):
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)

    # Tạo tên file cố định cho mỗi session để tránh lưu quá nhiều file nhỏ
    if "current_session_file" not in st.session_state:
        st.session_state.current_session_file = (
            f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        filepath = os.path.join(HISTORY_DIR, st.session_state.current_session_file)
    else:
        filepath = os.path.join(HISTORY_DIR, st.session_state.current_session_file)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)


def load_current_session(filename):
    file_path = os.path.join(HISTORY_DIR, filename)
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data
    except Exception:
        return None


def display_sources(details, user_query=""):
    if details:
        st.markdown("---")
        st.caption("📚 Nguồn trích dẫn (Click để xem chi tiết):")
        
        # Hiển thị các nguồn dưới dạng các nút nhỏ (popover)
        cols = st.columns(len(details) if len(details) < 3 else 3)
        for idx, item in enumerate(details):
            with cols[idx % 3]:
                # Đây là phần "Cho phép người dùng click để xem context gốc"
                with st.popover(f"📄 Trang {item['page']}"):
                    st.markdown(f"**Tài liệu:** {item['source']}")
                    st.markdown("**Nội dung gốc:**")
                    
                    # Thực hiện highlight các đoạn liên quan đến câu hỏi
                    highlighted_content = highlight_text(item['content'], user_query)
                    st.info(highlighted_content)


# --- GIAO DIỆN CHATBOX ---
@st.fragment
def render_chatbox(model):
    st.markdown(
        """
    <style>
    /* Ẩn avatar mặc định của Streamlit */
    [data-testid="stChatMessageAvatarUser"], 
    [data-testid="stChatMessageAvatarAssistant"] {
        display: none !important;
    }

    /* Định dạng chung cho tin nhắn */
    [data-testid="stChatMessage"] {
        padding: 10px 0px !important;
        # background-color: transparent !important;
    }

    /* STYLE CHO USER*/
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stMarkdownContainer"] {
        # background-color: #333333 !important;
        border-radius: 15px !important;
        padding: 10px 20px !important;
        margin-left: auto !important;
        width: fit-content !important;
        max-width: 80% !important;
        border: 1px solid #CCCCCC !important
    }
    
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {
        font-weight: 500;
    }

    /* STYLE CHO ASSISTANT*/
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        # background-color: #F5F5F5 !important;
        border: 1px solid #CCCCCC !important;
        border-radius: 10px !important;
        padding: 15px !important;
        margin-bottom: 20px !important;
    }
    
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) p {
        # color: #333333 !important;
    }

    /* Tiêu đề cột RAG và CoRAG */
    .column-header {
        font-weight: bold;
        text-transform: uppercase;
        border-bottom: 2px solid #333;
        margin-bottom: 15px;
        padding-bottom: 5px;
        # color: #333 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Chỉnh Chat Input sát đáy */
    [data-testid="stChatInput"] {
        padding-bottom: 20px !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    vector_db = st.session_state.get("vector_db")

    # Khởi tạo tin nhắn nếu chưa có
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Tạo container hiển thị nội dung chat
    chat_placeholder = st.container()

    # Ô nhập liệu
    user_input = st.chat_input("Nhập câu hỏi để so sánh RAG và CoRAG...", max_chars=500)

    with chat_placeholder:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg["role"] == "user":
                    st.markdown(msg["content"])

                else:
                    # Nếu là tin nhắn của Assistant và có dữ liệu so sánh
                    if "rag_content" in msg and "corag_content" in msg:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(
                                "<div class='column-header'>🤖 MÔ HÌNH RAG</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(msg["rag_content"])
                             # Hiển thị nguồn có kèm nội dung để click
                            display_sources(msg.get("rag_details", []), msg.get("user_query", ""))
                        with c2:
                            st.markdown(
                                "<div class='column-header'>🛡️ MÔ HÌNH CoRAG</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(msg["corag_content"])
                            # HIỂN THỊ NGUỒN CORAG
                            display_sources(msg.get("corag_details", []), msg.get("user_query", ""))
                    else:
                        # Trường hợp tin nhắn cũ hoặc tin nhắn thông báo
                        col1, col2 = st.columns(2)
                        col1.info(f"**📍 Vector RAG:**\n\n{msg['rag_content']}")
                        col2.success(
                            f"**✨ CoRAG (Verified):**\n\n{msg['corag_content']}"
                        )

    # 3. XỬ LÝ KHI NGƯỜI DÙNG NHẬP CÂU HỎI MỚI
    if user_input:
        with chat_placeholder:
            is_new_session = len(st.session_state.messages) == 0

            # Hiển thị câu hỏi User
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Phản hồi của Assistant
            with st.chat_message("assistant"):
                # Tạo tiêu đề cột trước khi có kết quả
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        "<div class='column-header'>🤖 MÔ HÌNH RAG</div>",
                        unsafe_allow_html=True,
                    )
                    rag_area = st.empty()  # Vùng trống để cập nhật sau
                with col2:
                    st.markdown(
                        "<div class='column-header'>🛡️ MÔ HÌNH CoRAG</div>",
                        unsafe_allow_html=True,
                    )
                    corag_area = st.empty()  # Vùng trống để cập nhật sau

                with st.spinner("Đang truy vấn dữ liệu và so sánh..."):
                    try:
                        # GỌI HÀM LOGIC CỦA FILE 1 (Workflow gốc)
                        # Đảm bảo hàm process_query trả về dict có key 'rag' và 'corag'
                        results = process_query(vector_db, model, user_input)

                        # Hiển thị kết quả vào đúng cột
                        rag_area.markdown(
                            results.get("rag", "Không có phản hồi từ RAG.")
                        )

                        corag_text = results.get("corag")
                        if not corag_text:
                            corag_text = "Không đủ dữ liệu tin cậy để đánh giá."
                        corag_area.markdown(corag_text)
                        # --- SỬA ĐOẠN NÀY ĐỂ HIỆN NGUỒN CHI TIẾT NGAY LẬP TỨC ---
                        with col1:
                            display_sources(results.get("rag_details", []), user_input)
                        with col2:
                            display_sources(results.get("corag_details", []), user_input)
                        # -----------------------------------------------------
                        # 4. LƯU VÀO LỊCH SỬ
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": "So sánh RAG & CoRAG",  # Text ẩn cho logic
                                "user_query": user_input,        # QUAN TRỌNG: Lưu lại câu hỏi để highlight từ khóa
                                "rag_content": results.get("rag"),
                                "corag_content": corag_text,
                                "rag_sources": results.get("rag_sources"),
                                "corag_sources": results.get("corag_sources"),
                                "rag_details": results.get("rag_details"),     # Danh sách object chứa content, page...
                                "corag_details": results.get("corag_details")   # Danh sách object chứa content, page...
                            }
                        )
                        save_chat_history(st.session_state.messages)
                        if is_new_session:
                            st.rerun()
                    except Exception as e:
                        st.error(f"Đã xảy ra lỗi khi xử lý: {str(e)}")
            # # Trả lời của Assistant
            # with st.chat_message("assistant"):
            #     with st.spinner("Đang truy vấn song song..."):
            #         results = process_query(vector_db, model, user_input)
            #
            #         # HIỂN THỊ CHIA CỘT NGAY LẬP TỨC
            #         col1, col2 = st.columns(2)
            #         with col1:
            #             st.info(f"**📍 Vector RAG:**\n\n{results['rag']}")
            #         with col2:
            #             corag_text = (
            #                 results["corag"]
            #                 if results["corag"]
            #                 else "Không đủ dữ liệu tin cậy để đánh giá."
            #             )
            #             st.success(f"**✨ CoRAG (Verified):**\n\n{corag_text}")
            #
            #         # LƯU VÀO HISTORY (Sử dụng cấu trúc mới)
            #         st.session_state.messages.append(
            #             {
            #                 "role": "assistant",
            #                 "rag_content": results["rag"],
            #                 "corag_content": results["corag"],
            #             }
            #         )
            #         save_chat_history(st.session_state.messages)
