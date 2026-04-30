import json
import os
import time
import threading
import tempfile
import logging

from numpy._core.multiarray import promote_types
import streamlit as st
from langchain_community.vectorstores import FAISS

# from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import OpenVINOEmbeddings
from backend.file_loader import load_document, split_text
from backend.model import (
    get_promt_template,
    get_promt_with_memory,
    get_promt_memory_no_cont,
)
from backend.chain_corag import evaluate


def get_memory(data, k=5):
    assistant_messages = [msg for msg in data if msg.get("role") == "assistant"]
    memory = assistant_messages[-k:]
    res = []
    for mem in memory:
        res.append(
            {
                "User query": mem.get("user_query"),
                "Response_rag": mem.get("rag_content"),
                "Response_corag": mem.get("corag_content"),
            }
        )
    return res


def get_retriever(vector):
    faiss_retriever = vector.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )
    return faiss_retriever


@st.cache_resource
def get_embedder():
    model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model_kwargs = {
        "device": "GPU",
        "compile": True,
    }
    return OpenVINOEmbeddings(model_name_or_path=model_name, model_kwargs=model_kwargs)


def process_documents(uploaded_files, embedder):  # TRÍCH VECTOR DATABASE
    if not uploaded_files:
        return None

    all_splitted_docs = []
    progress_text = "Đang khởi tạo..."
    progress_bar = st.sidebar.progress(0, text=progress_text)
    for i, file in enumerate(uploaded_files):
        # Lấy đuôi file thực tế ( .pdf hoặc .docx )
        file_extension = os.path.splitext(file.name)[1].lower()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(file.getbuffer())
            tmp_path = tmp.name

        try:
            docs = load_document(tmp_path)
            for doc in docs:
                doc.metadata["source"] = file.name
            percent_complete = int((i / len(uploaded_files)) * 50)
            progress_bar.progress(percent_complete, text=f"Splitting file: {file.name}")
            chunk = split_text(docs)
            all_splitted_docs.extend(chunk)
            time.sleep(0.1)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    if all_splitted_docs:
        progress_bar.progress(50, text="Embeddings Vector...")
        vector = FAISS.from_documents(all_splitted_docs, embedder)
        progress_bar.progress(100, text="✅ Hoàn thành!")
        time.sleep(1)
        progress_bar.empty()
        return vector
    if not uploaded_files:
        return None


def extract_sources(docs):  # TRÍCH NGUỒN TỪ DOC
    sources = []
    for doc in docs:
        source_name = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "?")
        source_str = f"{source_name} (Trang {page})" if page != "?" else source_name
        if source_str not in sources:
            sources.append(source_str)
    return sources


def process_query(vector_db, model, user_input):
    # Nếu có context từ doc:
    # return {
    #   "rag": Response của RAG,
    #   "corag": Response của CoRAG
    #   "rag_sources": document nguồn liên quan từ rag
    #   "corag_sources": document nguồn liên quan từ corag
    # }
    #
    # Nếu chỉ có query của user:
    # return {
    #   "rag": Response của RAG,
    #   "corag": None,
    #   "rag_sources": document nguồn liên quan từ rag
    #   "corag_sources": []
    # }
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Proccessing query: {user_input}")

    results = {
        "rag": None,
        "corag": None,
        "rag_sources": [],
        "corag_sources": [],
        "rag_details": [],
        "corag_details": [],
    }
    memory = st.session_state.get("memory", None)
    start_time = time.time()
    if vector_db is not None:
        retriever = get_retriever(vector_db)
        related_docs = retriever.invoke(user_input)
        retrieved_time = time.time() - start_time
        logger.info(f"Retrieved time: {retrieved_time}")
        logger.info(f"Responding with model: {st.session_state.selected_model}")
        # Lấy nguồn cho RAG
        results["rag_sources"] = extract_sources(related_docs)

        results["rag_details"] = [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "?"),
            }
            for doc in related_docs
        ]

        def process_rag():
            logger.info("Started procces RAG !")
            context = "\n\n".join([doc.page_content for doc in related_docs])
            if memory:
                print(memory)
                prompt = get_promt_with_memory(user_input).format(
                    context=context, user_input=user_input, memory=memory
                )
            else:
                print("No memory")
                prompt = get_promt_template(user_input).format(
                    context=context, user_input=user_input
                )
            logger.info("RAG begin thinking...")
            results["rag"] = model.invoke(prompt)

            response_time_rag = time.time() - start_time
            logger.info(f"Response time (RAG): {response_time_rag}")
            logger.info(f"Response (RAG): {results['rag']}")

        def proccess_corag():
            logger.info("Started procces CoRAG !")
            score, validated_docs = evaluate(user_input, related_docs)
            evaluate_time = time.time() - start_time
            logger.info(f"Evaluate time (CoRAG): {evaluate_time}")
            if score == "success":
                results["corag_sources"] = extract_sources(validated_docs)
                results["corag_details"] = [
                    {
                        "content": d.page_content,
                        "source": d.metadata.get("source", "Unknown"),
                        "page": d.metadata.get("page", "?"),
                    }
                    for d in validated_docs
                ]
                context = "\n\n".join(
                    [d.page_content for d in validated_docs]
                )  # .page_content vì giờ là object
                if memory:
                    prompt = get_promt_with_memory(user_input).format(
                        context=context, user_input=user_input, memory=memory
                    )
                else:
                    prompt = get_promt_template(user_input).format(
                        context=context, user_input=user_input
                    )
                logger.info("CoRAG begin thinking...")
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
        if memory:
            prompt = get_promt_memory_no_cont(user_input=user_input).format(
                user_input=user_input, memory=memory
            )
        else:
            prompt = user_input
        results["rag"] = model.invoke(prompt)
        res_time = time.time() - start_time
        logger.info(f"Response time with no doc: {res_time}")
        logger.info(f"Response with no doc: {results['rag']}")
    return results
