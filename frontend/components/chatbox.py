import streamlit as st
from backend.chain_rag import process_query  # Giữ nguyên hàm gốc của bạn
import os
import json
from datetime import datetime
from backend.chat import HISTORY_DIR
import re


def highlight_text(text, query):
    if not query:
        return text

    clean_query = re.sub(r"[?.,!]", "", query)
    stop_words = ["cho", "những", "của", "này", "trong", "bao", "nhiêu"]

    # Lấy từ khóa dài > 2 ký tự
    keywords = [
        w for w in clean_query.split() if len(w) > 2 and w.lower() not in stop_words
    ]
    keywords.sort(key=len, reverse=True)

    highlighted = text
    for word in keywords:
        try:
            # Sử dụng HTML span để đổi màu chữ thành xanh dương và in đậm
            pattern = re.compile(rf"\b({re.escape(word)})\b", re.IGNORECASE)
            # \1 là để giữ nguyên chữ hoa/thường của văn bản gốc
            highlighted = pattern.sub(
                r"<span style='color: #00aaff; font-weight: bold;'>\1</span>",
                highlighted,
            )
        except:
            continue
    return highlighted


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

        cols = st.columns(len(details) if len(details) < 3 else 3)
        for idx, item in enumerate(details):
            with cols[idx % 3]:
                with st.popover(f"📄 Trang {item['page']}"):
                    st.markdown(f"**Tài liệu:** `{item['source']}`")
                    st.markdown("---")

                    content = item["content"]
                    highlighted_content = highlight_text(content, user_query)

                    st.markdown("**Nội dung đoạn văn:**")
                    # THAY ĐỔI Ở ĐÂY: Thêm unsafe_allow_html=True
                    st.markdown(
                        f"<div style='border-left: 3px solid #00aaff; padding-left: 10px; font-style: italic;'>{highlighted_content}</div>",
                        unsafe_allow_html=True,
                    )


def auto_scroll():
    # Tạo ID duy nhất cho mỗi lần nhấn Enter dựa trên số lượng tin nhắn
    msg_count = len(st.session_state.get("messages", []))
    anchor_id = f"anchor-{msg_count}"
    
    # Đặt điểm neo với ID động này ở cuối cùng
    st.markdown(f"<div id='{anchor_id}' style='height: 10px; margin-bottom: 50px;'></div>", unsafe_allow_html=True)
    
    st.components.v1.html(
        f"""
        <script>
            function scrollToAnchor() {{
                const anchor = window.parent.document.getElementById('{anchor_id}');
                if (anchor) {{
                    anchor.scrollIntoView({{behavior: 'smooth', block: 'end'}});
                }}
            }}

            //  Chạy ngay lập tức
            scrollToAnchor();

            //  Chạy sau khi các element cơ bản đã render (300ms)
            setTimeout(scrollToAnchor, 300);

            //  Sử dụng MutationObserver để bám theo tin nhắn AI đang stream hoặc nở ra
            const observer = new MutationObserver(() => scrollToAnchor());
            observer.observe(window.parent.document.body, {{
                childList: true,
                subtree: true
            }});

            // Ngắt observer sau 4 giây để tránh tốn tài nguyên
            setTimeout(() => observer.disconnect(), 4000);
        </script>
        """,
        height=0
    )


# --- GIAO DIỆN CHATBOX ---
@st.fragment
def render_chatbox(model):
    st.markdown(
        """
    <style>
    .block-container {
        padding-top: 1.5rem !important;
        width: 80% !important; /* Độ rộng tổng thể của trang */
    }

    .main .block-container {
        padding-bottom: 250px !important;
    }
    /* Ẩn avatar mặc định của Streamlit */
    [data-testid="stChatMessageAvatarUser"], 
    [data-testid="stChatMessageAvatarAssistant"] {
        display: none !important;
    }

    /* Định dạng chung cho tin nhắn */
    [data-testid="stChatMessage"] {
        padding: 10px 0px !important;
        background-color: transparent !important;
    }
    /* làm trình duyệt cuộn mượt mà*/
    
    html{scroll-behavior: smooth;}

    /* STYLE CHO USER*/
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stMarkdownContainer"] {
        background-color: #007BFF !important;
        border-radius: 15px !important;
        padding: 10px 20px !important;
        margin-left: auto !important;
        width: fit-content !important;
        max-width: 80% !important;
        color: #000000 !important; 
        # border: 1px solid #CCCCCC !important
    }
    
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {
        font-weight: 500;
    }

    /* STYLE CHO ASSISTANT*/
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #1c2c3e !important;
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
        border-bottom: 2px solid #CCCCCC;
        margin-bottom: 15px;
        padding-bottom: 5px;
        # color: #333 !important;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Chỉnh Chat Input sát đáy */
    [data-testid="stChatInput"] {
        position: fixed;
        bottom: 20px;
        z-index: 99;
        border: 1px solid #CCCCCC !important;
        border-radius: 10px !important;
        width: 60%;
        height: 10%;
        box-shadow: 0px 0px 25px 4px rgba(0, 0, 0, 0.5) !important;
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
    chat_container = st.container()

    # Ô nhập liệu
    user_input = st.chat_input("Nhập câu hỏi để so sánh RAG và CoRAG...", max_chars=500)

    with chat_container:
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
                            display_sources(
                                msg.get("rag_details", []), msg.get("user_query", "")
                            )
                        with c2:
                            st.markdown(
                                "<div class='column-header'>🛡️ MÔ HÌNH CoRAG</div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(msg["corag_content"])
                            # HIỂN THỊ NGUỒN CORAG
                            display_sources(
                                msg.get("corag_details", []), msg.get("user_query", "")
                            )
                    else:
                        # Trường hợp tin nhắn cũ hoặc tin nhắn thông báo
                        col1, col2 = st.columns(2)
                        col1.info(f"**📍 Vector RAG:**\n\n{msg['rag_content']}")
                        col2.success(
                            f"**✨ CoRAG (Verified):**\n\n{msg['corag_content']}"
                        )
    # 3. XỬ LÝ KHI NGƯỜI DÙNG NHẬP CÂU HỎI MỚI
    if user_input:
        with chat_container:
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
                    corag_area = st.empty()

                      # Vùng trống để cập nhật sau

                with st.spinner("Đang truy vấn dữ liệu và so sánh..."):
                    try:
                        # GỌI HÀM LOGIC CỦA FILE 1 (Workflow gốc)
                        # Đảm bảo hàm process_query trả về dict có key 'rag' và 'corag'
                        # Chỉ gửi các tin nhắn trước đó, không gửi câu vừa append
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
                            display_sources(
                                results.get("corag_details", []), user_input
                            )

                        # -----------------------------------------------------
                        # 4. LƯU VÀO LỊCH SỬ
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": "So sánh RAG & CoRAG",  # Text ẩn cho logic
                                "user_query": user_input,  # QUAN TRỌNG: Lưu lại câu hỏi để highlight từ khóa
                                "rag_content": results.get("rag"),
                                "corag_content": corag_text,
                                "rag_sources": results.get("rag_sources"),
                                "corag_sources": results.get("corag_sources"),
                                "rag_details": results.get(
                                    "rag_details"
                                ),  # Danh sách object chứa content, page...
                                "corag_details": results.get(
                                    "corag_details"
                                ),  # Danh sách object chứa content, page...
                            }
                        )
                        save_chat_history(st.session_state.messages)
                    except Exception as e:
                        st.error(f"Đã xảy ra lỗi khi xử lý: {str(e)}")
    
    auto_scroll()

    

   