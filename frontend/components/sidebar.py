import streamlit as st
import os
from data.chain_rag import process_documents


def render_sidebar(embedder):
    st.sidebar.title("📁 Quản lý tài liệu")

    st.markdown(
        """
<style>
div.stButton > button {
    background-color: #af2828;
    color:#ffffff;
}
div.stButton > button:hover {
    background-color: #e74444;
}
</style>""",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("Xóa tất cả tài liệu", use_container_width=True):
        # Xóa các biến liên quan trong session_state
        st.session_state.vector_db = None
        st.session_state.last_files_id = ""
        # Tạo key mới cho uploader để reset widget
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0
        st.session_state.uploader_key += 1
        st.rerun()
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    # Upload file
    uploaded_files = st.sidebar.file_uploader(
        "Upload Files",
        type=["pdf", "doc", "docx"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
    )

    current_files_id = (
        str([(f.name, f.size) for f in uploaded_files]) if uploaded_files else ""
    )
    last_files_id = st.session_state.get("last_files_id", "")

    st.sidebar.divider()
    # st.sidebar.write("🔍 **Debug Info:**")
    # st.sidebar.write(
    #     f"- ID hiện tại: `{current_files_id[:100]}...`"
    #     if current_files_id
    #     else "- ID hiện tại: Trống"
    # )
    # st.sidebar.write(
    #     f"- ID cũ: `{last_files_id[:30]}...`" if last_files_id else "- ID cũ: Trống"
    # )

    # ------------------------
    if current_files_id != last_files_id:
        if uploaded_files:
            with st.sidebar.status("🔄"):
                st.session_state.vector_db = process_documents(
                    uploaded_files, embedder
                )
                st.session_state.last_files_id = current_files_id
        else:
            st.session_state.vector_db = None
            st.session_state.last_files_id = ""
