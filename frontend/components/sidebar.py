from numpy import size
import streamlit as st
import os
from data.chain import process_documents_pdf


def render_sidebar(embedder):
    st.sidebar.title("📁 Quản lý tài liệu")

    # Upload file (Bỏ nút Index, thay bằng logic tự động)
    uploaded_files = st.sidebar.file_uploader(
        "Upload PDF để bắt đầu RAG",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader",
    )

    current_files_id = (
        str([(f.name, f.size) for f in uploaded_files]) if uploaded_files else ""
    )
    last_files_id = st.session_state.get("last_files_id", "")

    st.sidebar.divider()
    st.sidebar.write("🔍 **Debug Info:**")
    st.sidebar.write(
        f"- ID hiện tại: `{current_files_id[:100]}...`"
        if current_files_id
        else "- ID hiện tại: Trống"
    )
    st.sidebar.write(
        f"- ID cũ: `{last_files_id[:30]}...`" if last_files_id else "- ID cũ: Trống"
    )

    # ------------------------
    if current_files_id != last_files_id:
        if uploaded_files:
            with st.sidebar.status("🔄"):
                st.session_state.vector_db = process_documents_pdf(
                    uploaded_files, embedder
                )
                st.session_state.last_files_id = current_files_id
            st.sidebar.success(f"✅ Đã nạp {len(uploaded_files)} tài liệu")
        else:
            st.session_state.vector_db = None
            st.session_state.last_files_id = ""
            st.sidebar.info("Đã xóa kho dữ liệu.")
