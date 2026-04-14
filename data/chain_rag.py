import os
import time
import threading
import tempfile
import logging

import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from data.file_loader import load_document, split_text
from data.model import get_prompt_template
from data.chain_corag import evaluate


def get_retriever(vector):
    retriever = vector.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5},
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


def process_documents(uploaded_files, embedder):
    if not uploaded_files:
        return None

    all_splitted_docs = []

    for uploaded_file in uploaded_files:
        # Lấy đuôi file thực tế ( .pdf hoặc .docx )
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        try:
            docs = load_document(tmp_path)
            for doc in docs:
                doc.metadata["source"] = uploaded_file.name
            chunk = split_text(docs)
            all_splitted_docs.extend(chunk)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    if all_splitted_docs:
        print(f"🚀 Đang tạo Vector DB cho {len(all_splitted_docs)} đoạn văn bản...")
        return FAISS.from_documents(all_splitted_docs, embedder)
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
    # Nếu có context từ doc:
    # return {
    #   "rag": Response của RAG,
    #   "corag": Response của CoRAG
    # }
    #
    # Nếu chỉ có query của user:
    # return {
    #   "rag": Response của RAG,
    #   "corag": None
    # }
    #
    start_time = time.time()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Proccessing query: {user_input}")

    results = {"rag": None, "corag": None}
    if vector_db is not None:
        retriever = get_retriever(vector_db)
        related_docs = retriever.invoke(user_input)
        retrieved_time = time.time() - start_time
        logger.info(f"Retrieved time: {retrieved_time}")

        def process_rag():
            logger.info("Started procces RAG !")
            context = "\n\n".join([doc.page_content for doc in related_docs])
            prompt_text = get_prompt_template(user_input).format(
                context=context, user_input=user_input
            )
            results["rag"] = model.invoke(prompt_text)

            response_time_rag = time.time() - start_time
            logger.info(f"Response time (RAG): {response_time_rag}")
            logger.info(f"Response (RAG): {results['rag']}")

        def proccess_corag():
            logger.info("Started procces CoRAG")
            score, validated_docs = evaluate(user_input, related_docs)
            evaluate_time = time.time() - start_time
            logger.info(f"Evaluate time (CoRAG): {evaluate_time}")
            if score == "success":
                context = "\n\n".join([d for d in validated_docs])
                prompt = get_prompt_template(user_input).format(
                    context=context, user_input=user_input
                )
                logger.info(f"CoRAG Prompt: \n{prompt}")
                results["corag"] = model.invoke(prompt)

                response_time_corag = time.time() - start_time
                logger.info(f"Response time (CoRAG): {response_time_corag}")
                logger.info(f"Response (CoRAG): {results['corag']}")

        t1 = threading.Thread(target=process_rag)
        t2 = threading.Thread(target=proccess_corag)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    else:
        results["rag"] = model.invoke(user_input)

        res_time = time.time() - start_time
        logger.info(f"Respront time with no doc: {res_time}")
        logger.info(f"Response with no doc: {results['rag']}")
    return results


#
# if __name__ == "__main__":
#     file = ["~/Project-LLMs-Rag-Agent/documentation/OSAssignment.pdf"]
#     model = get_model()
#     query = "Đồ án này yêu cầu làm gì ?"
#     embedder = get_embedder()
#     vector = process_documents_pdf(file, embedder)
#     final_anser = process_query(vector, model, query)
#     print(final_anser)
