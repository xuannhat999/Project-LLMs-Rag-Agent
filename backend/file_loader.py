import os
import fitz  # Thư viện PyMuPDF
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import streamlit as st


def load_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        print(f"--- Đang đọc file PDF: {file_path} ---")
        loader = PyMuPDFLoader(file_path)
        docs = loader.load()

        # Kiểm tra xem có thực sự đọc được chữ không
        total_chars = sum(len(d.page_content) for d in docs)
        print(f"Số ký tự đọc được bằng cách thông thường: {total_chars}")

        # Nếu số ký tự quá ít (ví dụ dưới 100), khả năng cao là ảnh scan
        if total_chars < 100:
            print("=> PDF rỗng hoặc toàn hình ảnh. Đang chuyển sang chế độ OCR...")
            return load_pdf_with_ocr(file_path)

        return docs

    elif ext in [".docx", ".doc"]:
        loader = Docx2txtLoader(file_path)
        return loader.load()
    else:
        raise ValueError(f"Định dạng file {ext} không được hỗ trợ.")


def load_pdf_with_ocr(file_path):
    """Sử dụng RapidOCR thủ công để đảm bảo chắc chắn đọc được ảnh"""
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        print(
            "Lỗi: Bạn cần cài đặt rapidocr-onnxruntime (pip install rapidocr-onnxruntime)"
        )
        return []

    engine = RapidOCR()
    ocr_docs = []

    # Mở file bằng fitz (PyMuPDF)
    pdf_document = fitz.open(file_path)

    for i in range(len(pdf_document)):
        print(f"Đang OCR trang {i + 1}/{len(pdf_document)}...")
        page = pdf_document[i]

        # Chuyển trang thành ảnh (zoom 2 để rõ nét)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")

        # Chạy OCR trực tiếp trên biến ảnh
        result, _ = engine(img_bytes)

        if result:
            # result là một list các dòng, lấy text ở vị trí index 1 mỗi dòng
            page_text = "\n".join([line[1] for line in result])
            ocr_docs.append(
                Document(
                    page_content=page_text, metadata={"source": file_path, "page": i}
                )
            )

    pdf_document.close()
    print(f"--- Hoàn thành OCR. Đọc được {len(ocr_docs)} trang ---")
    return ocr_docs


def split_text(doc):
    if not doc:
        print("Cảnh báo: Tài liệu rỗng, không có gì để split!")
        return []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=st.session_state.chunk_size,
        chunk_overlap=st.session_state.chunk_overlap,
    )
    print(
        f"Splitted with Chunk size: {st.session_state.chunk_size} - Chunk overlap: {st.session_state.chunk_overlap}"
    )
    return text_splitter.split_documents(doc)
