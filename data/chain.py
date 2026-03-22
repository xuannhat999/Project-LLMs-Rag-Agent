import os
import time

import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from data.file_loader import load_document, split_text
from data.model import get_prompt_template
import tempfile


def get_retriever(vector):
    retriever = vector.as_retriever(
        search_type=" similarity ",
        search_kwargs={"k": 3},
    )
    return retriever


@st.cache_resource
def get_embedder():
    model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": True}

    return HuggingFaceEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )


def process_documents_pdf(uploaded_files, embedder):
    if not uploaded_files:
        return None

    all_splitted_docs = []

    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        try:
            docs = load_document(tmp_path)
            for doc in docs:
                doc.metadata["source"] = uploaded_file.name
                print(f"--- NỘI DUNG TRÍCH XUẤT TỪ {uploaded_file.name} ---")
                print(doc.page_content)  # Xem 500 ký tự đầu tiên
                print("-----------------------------------------------")

            chunk = split_text(docs)
            all_splitted_docs.extend(chunk)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    if all_splitted_docs:
        print(
            f"🚀 Đang tạo Vector DB cho tổng cộng {len(all_splitted_docs)} đoạn văn bản..."
        )
        return FAISS.from_documents(all_splitted_docs, embedder)
    return None


def process_query(vector_db, model, user_input):
    start_time = time.time()
    if vector_db is not None:
        retriever = vector_db.as_retriever(search_kwargs={"k": 3})
        related_docs = retriever.invoke(user_input)

        context = "\n\n".join([doc.page_content for doc in related_docs])

        prompt_text = get_prompt_template(user_input).format(
            context=context, user_input=user_input
        )
        # DEBUG=======================================
        print(f"\n📝 [LOG - PROMPT SENT TO OLLAMA]")
        print("-" * 30)
        print(prompt_text[:200] + "...")
        print("-" * 30)
        print("🤖 Model đang sinh câu trả lời...")
        # ======================================================
        inference_start = time.time()
        response = model.invoke(prompt_text)
        inference_time = time.time() - inference_start
    else:
        response = model.invoke(user_input)
        inference_time = time.time() - start_time

    total_time = time.time() - start_time
    print(f"\n⏱️  [LOG - PERFORMANCE]")
    print(f"  - Thời gian Retrieval: {total_time - inference_time:.2f}s")
    print(f"  - Thời gian Model xử lý: {inference_time:.2f}s")
    print(f"  - Tổng thời gian: {total_time:.2f}s")
    print(
        f"  - Tốc độ ước tính: {len(str(response)) / 4 / inference_time:.2f} tokens/s"
    )
    print("=" * 50 + "\n")
    return response.content if hasattr(response, "content") else str(response)


#
# if __name__ == "__main__":
#     file = ["~/Project-LLMs-Rag-Agent/documentation/OSAssignment.pdf"]
#     model = get_model()
#     query = "Đồ án này yêu cầu làm gì ?"
#     embedder = get_embedder()
#     vector = process_documents_pdf(file, embedder)
#     final_anser = process_query(vector, model, query)
#     print(final_anser)
