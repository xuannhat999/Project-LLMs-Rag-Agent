import os

from langchain_community.document_loaders import Docx2txtLoader, PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path):
    # Lấy đuôi file (ví dụ: .pdf, .docx)
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        loader = PDFPlumberLoader(file_path)
    elif ext == ".docx" or ext == ".doc":
        loader = Docx2txtLoader(file_path)
    else:
        # Nếu là file không hỗ trợ, có thể trả về list rỗng hoặc báo lỗi
        raise ValueError(f"Định dạng file {ext} không được hỗ trợ.")
    
    doc = loader.load()
    return doc


def split_text(doc):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(doc)
