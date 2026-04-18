import streamlit as st
import os
import time
import logging

from backend.chain_rag import process_documents
import json
import streamlit.components.v1 as components
from backend.model import load_config_file, save_config
from backend.chat import HISTORY_DIR, get_chat_history
from backend.file_loader import delete_all_files, files_size_validation


def render_sidebar(embedder):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    noti_place_holder = st.empty()  # NOTIFICATION WIDGET

    btn_new_chat = st.sidebar.button(
        "Cuộc trò chuyện mới", use_container_width=True, icon=":material/add:"
    )
    if btn_new_chat:  # Bỏ session hiện tại, tạo file chat json mới khi nhập prompt
        st.session_state.current_files_id = None
        del st.session_state.messages
        del st.session_state.current_session_file
        delete_all_files()
    change_button_color("Cuộc trò chuyện mới", "black", "#007BFF")

    history_files = get_chat_history()
    with st.sidebar.expander(
        "Lịch sử trò chuyện", expanded=False, icon=":material/chat:"
    ):
        history_container = st.container(height=300, border=False)
        with history_container:
            for f in history_files:
                display_name = f.get("title")
                # Nút bấm sẽ nằm gọn trong vùng cuộn
                if st.button(
                    f"{display_name}",
                    key=f"btn_{f.get('filename')}",
                    use_container_width=True,
                ):
                    file_path = os.path.join(HISTORY_DIR, f.get("filename"))
                    with open(file_path, "r", encoding="utf-8") as file:
                        st.session_state.messages = json.load(file)
                        st.session_state.current_session_file = f.get("filename")
                    st.rerun()

    if st.sidebar.button(
        "Xóa lịch sử chat", use_container_width=True, icon=":material/delete:"
    ):
        confirm_dialog("Bạn có chắc chắn muốn xóa lịch sử chat", "delete_chat_his")
    change_button_color("Xóa lịch sử chat", "white", "#af2828")

    st.sidebar.divider()

    if st.sidebar.button(
        "Xóa tất cả tài liệu", use_container_width=True, icon=":material/delete:"
    ):
        if "vector_db" in st.session_state:
            confirm_dialog("Bạn có chắc chắn muốn xóa tất cả tài liệu", "delete_docs")
        else:
            noti_place_holder.error("Không có tài liệu để xóa")
            time.sleep(3)
            noti_place_holder.empty()

    change_button_color("Xóa tất cả tài liệu", "white", "#af2828")

    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    st.session_state.uploaded_files = st.sidebar.file_uploader(
        "Upload Files",
        type=["pdf", "doc", "docx", "odt"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
    )

    config_data = load_config_file()

    with st.sidebar.expander(
        "Tùy chỉnh nâng cao", expanded=False, icon=":material/settings:"
    ):
        st.slider(
            "Chunk Size (Kích thước đoạn)",
            min_value=100,
            max_value=4000,
            step=100,
            key="chunk_size",
        )

        st.slider(
            "Chunk Overlap (Độ gối đầu)",
            min_value=0,
            max_value=1000,
            step=100,
            key="chunk_overlap",
        )
        if "models" in st.session_state:
            models = st.session_state.models
            index = 0
            for i, model in enumerate(models):
                if model == st.session_state.selected_model:
                    index = i
            selected_model = st.selectbox(
                "Model:",
                options=models,
                key="model_selector_box",  # Key để tránh trùng lặp component
                help="Chọn model LLM bạn muốn sử dụng cho hệ thống RAG",
                index=index,
            )
            if (
                "selected_model" not in st.session_state
                or st.session_state.selected_model != selected_model
            ):
                st.session_state.selected_model = selected_model

        apply_config = st.button("Áp dụng", use_container_width=True)
    change_button_color("Áp dụng", "black", "#007BFF")

    current_files_id = (
        str([(f.name, f.size) for f in st.session_state.uploaded_files])
        if st.session_state.uploaded_files
        else ""
    )
    last_files_id = st.session_state.get("last_files_id", "")

    if current_files_id != last_files_id or apply_config:
        if apply_config:
            if st.session_state.selected_model != config_data.get("model"):
                st.cache_resource.clear()
            save_config(
                model_name=st.session_state.get("selected_model"),
                chunk_size=st.session_state.get("chunk_size"),
                chunk_overlap=st.session_state.get("chunk_overlap"),
            )
            noti_place_holder.success("Cấu hình đã được lưu thành công!", icon="✅")
            time.sleep(3)
            noti_place_holder.empty()
            st.session_state.uploader_key += 1

        if "uploaded_files" in st.session_state:
            oversized_files = []
            for f in st.session_state.uploaded_files:
                if f not in files_size_validation(st.session_state.uploaded_files):
                    oversized_files.append(f)
            if len(oversized_files) > 0:
                logger.info("Failed file size validation")
                st.session_state.uploader_key += 1
                filenames = [f.name for f in oversized_files]
                noti_place_holder.error(f"""
                **Các tài liệu vượt quá dung lượng (50MB/file):**  
                - {
                    '''
                - '''.join(filenames)
                }  
                **Vui lòng tải tài liệu lên lại**
                """)
                time.sleep(4)
                noti_place_holder.empty()
                st.rerun()

            elif len(st.session_state.uploaded_files) > 0:
                start_time = time.time()
                st.session_state.vector_db = process_documents(
                    st.session_state.uploaded_files, embedder
                )
                st.session_state.last_files_id = current_files_id
                procces_doc_time = time.time() - start_time
                noti_place_holder.success(
                    f"Đã tải {len(st.session_state.uploaded_files)} tài liệu"
                )
                time.sleep(2)
                noti_place_holder.empty()
                logger.info(f"DOC Proccessed time: {procces_doc_time}")
                logger.info(f"Proccess {len(st.session_state.uploaded_files)} files")
        else:
            del st.session_state.vector_db
            st.session_state.last_files_id = ""

    if "delete_docs" in st.session_state:
        delete_all_files()

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


@st.dialog("Cảnh báo")
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
            if action_key in st.session_state:
                del st.session_state[action_key]
            st.rerun()


def change_button_color(widget_label, font_color, background_color="transparent"):
    htmlstr = f"""
    <script>
        var elements = window.parent.document.querySelectorAll('button');
        for (var i = 0; i < elements.length; ++i) {{ 
            if (elements[i].innerText.includes('{widget_label}')) {{ 
                elements[i].style.color = '{font_color}';
                elements[i].style.background = '{background_color}';

                elements[i].onmouseout = function() {{ 
                    this.style.color = '{font_color}';
                    // Reset to a default border or keep current
                }};
            }}
        }}
    </script>
    """
    components.html(htmlstr, height=0, width=0)
