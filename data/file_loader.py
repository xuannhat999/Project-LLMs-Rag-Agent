from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_document(file_path):
    loader = PDFPlumberLoader(file_path)
    doc = loader.load()
    return doc


def split_text(doc):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(doc)
