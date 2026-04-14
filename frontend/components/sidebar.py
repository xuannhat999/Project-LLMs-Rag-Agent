import streamlit as st
import os
import time
import logging
from data.chain_rag import process_documents
import glob
import json

HISTORY_DIR = os.path.expanduser("data/chat_history/")


def render_sidebar(embedder):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    #     st.markdown(
    #         """
    # <style>
    # div.stButton > button {
    #     background-color: #af2828;
    #     color:#ffffff;
    # }
    # div.stButton > button:hover {
    #     background-color: #e74444;
    # }
    # </style>""",
    #     unsafe_allow_html=True,
    # )
    if st.sidebar.button("Xóa lịch sử chat", use_container_width=True):
        confirm_dialog("Bạn có chắc chắn muốn xóa lịch sử chat", "delete_chat_his")

    if st.sidebar.button(
        "Cuộc trò chuyện mới", use_container_width=True
    ):  # Bỏ session hiện tại, tạo file chat json mới khi nhập prompt
        st.session_state.current_files_id = None
        del st.session_state.messages
        st.session_state.vector_db = None
        st.session_state.last_files_id = ""
        del st.session_state.current_session_file
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0
        st.session_state.uploader_key += 1
        st.session_state["delete_docs"] = None
        st.rerun()

    history_files = get_chat_history()
    with st.sidebar.expander("💬 Lịch sử trò chuyện", expanded=True):
        for f in history_files:
            display_name = f.get("title")
            if st.button(
                f"📄 {display_name}",
                key=f"btn_{f.get('filename')}",
                use_container_width=True,
            ):
                with open(
                    os.path.join(HISTORY_DIR, f.get("filename")), "r", encoding="utf-8"
                ) as file:
                    st.session_state.messages = json.load(file)
                    st.session_state.current_session_file = f.get("filename")
                st.rerun()

    st.sidebar.divider()

    if st.sidebar.button("Xóa tất cả tài liệu", use_container_width=True):
        confirm_dialog("Bạn có chắc chắn muốn xóa tất cả tài liệu", "delete_docs")

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    uploaded_files = st.sidebar.file_uploader(
        "Upload Files",
        type=["pdf", "doc", "docx"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
    )

    st.sidebar.divider()

    with st.sidebar.expander("🛠️ Tùy chỉnh nâng cao", expanded=False):
        st.slider(
            "Chunk Size (Kích thước đoạn)",
            min_value=100,
            max_value=4000,
            value=1000,
            step=100,
            key="chunk_size",
        )

        st.slider(
            "Chunk Overlap (Độ gối đầu)",
            min_value=0,
            max_value=1000,
            value=200,
            step=100,
            key="chunk_overlap",
        )
        apply_config = st.button("Áp dụng", use_container_width=True)

    current_files_id = (
        str([(f.name, f.size) for f in uploaded_files]) if uploaded_files else ""
    )
    last_files_id = st.session_state.get("last_files_id", "")

    if current_files_id != last_files_id or apply_config:
        if uploaded_files:
            start_time = time.time()
            with st.sidebar.status("🔄"):
                st.session_state.vector_db = process_documents(uploaded_files, embedder)
                st.session_state.last_files_id = current_files_id
            procces_doc_time = time.time() - start_time
            logger.info(f"DOC Proccessing time: {procces_doc_time}")
            st.rerun()
        else:
            st.session_state.vector_db = None
            st.session_state.last_files_id = ""

    if st.session_state.get("delete_docs"):
        st.session_state.vector_db = None
        st.session_state.last_files_id = ""
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0
        st.session_state.uploader_key += 1
        st.session_state["delete_docs"] = None
        st.rerun()

    if st.session_state.get("delete_chat_his"):
        del st.session_state.messages
        if "current_session_file" in st.session_state:
            file_path = os.path.join(HISTORY_DIR, st.session_state.current_session_file)
            if os.path.exists(file_path):
                os.remove(file_path)
            del st.session_state.current_session_file
        st.session_state["delete_chat_his"] = None
        st.rerun()

    # st.sidebar.divider()
    # st.sidebar.write("🔍 **Debug Info:**")
    # st.sidebar.write(
    #     f"- ID hiện tại: `{current_files_id[:100]}...`"
    #     if current_files_id
    #     else "- ID hiện tại: Trống"
    # )
    # st.sidebar.write(
    #     f"- ID cũ: `{last_files_id[:30]}...`" if last_files_id else "- ID cũ: Trống"
    # )


@st.dialog("Cảnh báo")  ## Confirm delete dialog
def confirm_dialog(message, action_key):
    st.write(message)
    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Đồng ý", key="btn_confirm", type="primary", use_container_width=True
        ):
            st.session_state[action_key] = True
            st.rerun()

    with col2:
        if st.button("Hủy", key="btn_cancel", use_container_width=True):
            st.session_state[action_key] = False
            st.rerun()


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
