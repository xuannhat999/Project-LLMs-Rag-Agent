import os
import time
import threading
import tempfile
import logging
import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenVINOEmbeddings
from backend.file_loader import load_document, split_text
# Gộp chung các import từ backend.model
from backend.model import get_prompt_template, get_external_model
from backend.chain_corag import evaluate
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever



def get_retriever(vector, all_docs):
    logging.info("🔍 Khởi tạo Hybrid Search (FAISS + BM25)...")
    
    # 1. Tìm kiếm theo Ý nghĩa (Vector Search)
    faiss_retriever = vector.as_retriever(search_kwargs={"k": 3})
    
    # 2. Tìm kiếm theo Từ khóa (Keyword Search)
    bm25_retriever = BM25Retriever.from_documents(all_docs)
    bm25_retriever.k = 3
    
    # 3. Gộp cả 2 (Hybrid Search)
    ensemble = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever],
        weights=[0.5, 0.5]
    )
    logging.info("✅ Đã cấu hình xong Ensemble Retriever.")
    return ensemble
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
        st.session_state.all_docs = all_splitted_docs 
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


# def process_query(vector_db, model, user_input):
#     # Nếu có context từ doc:
#     # return {
#     #   "rag": Response của RAG,
#     #   "corag": Response của CoRAG
#     #   "rag_sources": document nguồn liên quan từ rag
#     #   "corag_sources": document nguồn liên quan từ corag
#     # }
#     #
#     # Nếu chỉ có query của user:
#     # return {
#     #   "rag": Response của RAG,
#     #   "corag": None,
#     #   "rag_sources": document nguồn liên quan từ rag
#     #   "corag_sources": []
#     # }
#     logging.basicConfig(level=logging.INFO)
#     logger = logging.getLogger(__name__)
#     logger.info(f"Proccessing query: {user_input}")

#     results = {
#         "rag": None,
#         "corag": None,
#         "rag_sources": [],
#         "corag_sources": [],
#         "rag_details": [],
#         "corag_details": [],
#     }
#     start_time = time.time()
#     if vector_db is not None:
#         retriever = get_retriever(vector_db)
#         related_docs = retriever.invoke(user_input)
#         retrieved_time = time.time() - start_time
#         logger.info(f"Retrieved time: {retrieved_time}")
#         logger.info(f"Responding with model: {st.session_state.selected_model}")
#         # Lấy nguồn cho RAG
#         results["rag_sources"] = extract_sources(related_docs)

#         results["rag_details"] = [
#             {
#                 "content": doc.page_content,
#                 "source": doc.metadata.get("source", "Unknown"),
#                 "page": doc.metadata.get("page", "?"),
#             }
#             for doc in related_docs
#         ]

#         def process_rag():
#             logger.info("Started procces RAG !")
#             context = "\n\n".join([doc.page_content for doc in related_docs])
#             prompt_text = get_prompt_template(user_input).format(
#                 context=context, user_input=user_input
#             )
#             logger.info("RAG begin thinking...")
#             results["rag"] = model.invoke(prompt_text)

#             response_time_rag = time.time() - start_time
#             logger.info(f"Response time (RAG): {response_time_rag}")
#             logger.info(f"Response (RAG): {results['rag']}")

#         def proccess_corag():
#             logger.info("Started procces CoRAG !")
#             score, validated_docs = evaluate(user_input, related_docs)
#             evaluate_time = time.time() - start_time
#             logger.info(f"Evaluate time (CoRAG): {evaluate_time}")
#             if score == "success":
#                 results["corag_sources"] = extract_sources(validated_docs)
#                 results["corag_details"] = [
#                     {
#                         "content": d.page_content,
#                         "source": d.metadata.get("source", "Unknown"),
#                         "page": d.metadata.get("page", "?"),
#                     }
#                     for d in validated_docs
#                 ]
#                 context = "\n\n".join(
#                     [d.page_content for d in validated_docs]
#                 )  # .page_content vì giờ là object
#                 prompt = get_prompt_template(user_input).format(
#                     context=context, user_input=user_input
#                 )
#                 logger.info("CoRAG begin thinking...")
#                 results["corag"] = model.invoke(prompt)

#                 response_time_corag = time.time() - start_time
#                 logger.info(f"Response time (CoRAG): {response_time_corag}")
#                 logger.info(f"Response (CoRAG): {results['corag']}")

#         t1 = threading.Thread(target=process_rag)
#         t2 = threading.Thread(target=proccess_corag)
#         t1.start()
#         t2.start()
#         t1.join()
#         t2.join()
#     else:
#         results["rag"] = model.invoke(user_input)
#         res_time = time.time() - start_time
#         logger.info(f"Response time with no doc: {res_time}")
#         logger.info(f"Response with no doc: {results['rag']}")
#     return results
def process_query(vector_db, model, user_input):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info(f"\n{'='*50}\n[BẮT ĐẦU] Xử lý ĐA LUỒNG câu hỏi: {user_input}\n{'='*50}")
    
    # Khởi tạo mô hình ngoài (Gemini)
    external_model = get_external_model() 

    results = {
        "rag": None,
        "corag": None,
        "rag_sources": [],
        "corag_sources": [],
        "rag_details": [],
        "corag_details": [],
    }
    
    start_time = time.time()
    
    if vector_db is not None:
        # 1. TRUY XUẤT BAN ĐẦU (Hybrid Search) - Làm tuần tự vì là bước đệm chung
        logger.info("Step 1: Đang thực hiện Hybrid Search (FAISS + BM25)...")
        retrieval_start = time.time()
        
        retriever = get_retriever(vector_db, st.session_state.all_docs) 
        related_docs = retriever.invoke(user_input)
        
        retrieval_duration = time.time() - retrieval_start
        logger.info(f"✅ Hoàn thành Retrieval ban đầu. Tìm thấy {len(related_docs)} đoạn. Thời gian: {retrieval_duration:.2f}s")
        
        # Lưu thông tin chi tiết ban đầu cho RAG (để hiển thị nguồn sớm)
        results["rag_sources"] = extract_sources(related_docs)
        results["rag_details"] = [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", "?"),
            }
            for doc in related_docs
        ]

        # --- ĐỊNH NGHĨA LUỒNG 1: XỬ LÝ RAG (OLLAMA LOCAL) ---
        def run_rag_thread():
            nonlocal results
            logger.info("🧵 [THREAD RAG] Bắt đầu suy luận RAG truyền thống...")
            rag_thread_start = time.time()
            try:
                context_rag = "\n\n".join([doc.page_content for doc in related_docs])
                prompt_rag = get_prompt_template(user_input).format(
                    context=context_rag, user_input=user_input
                )
                results["rag"] = model.invoke(prompt_rag)
                logger.info(f"✅ [THREAD RAG] Hoàn thành. Thời gian: {time.time() - rag_thread_start:.2f}s")
            except Exception as e:
                logger.error(f"❌ [THREAD RAG] Lỗi: {e}")
                results["rag"] = f"Lỗi RAG: {str(e)}"

        # --- ĐỊNH NGHĨA LUỒNG 2: XỬ LÝ CoRAG (VÒNG LẶP KIỂM CHỨNG) ---
        def run_corag_thread():
            nonlocal results
            logger.info("🧵 [THREAD CoRAG] Bắt đầu vòng lặp kiểm chứng...")
            corag_thread_start = time.time()
            try:
                current_query = user_input
                attempts = 0
                max_attempts = 2 
                success_finding = False
                final_docs = []

                while attempts < max_attempts:
                    attempts += 1
                    logger.info(f"🔄 [CoRAG] Thử lần {attempts}. Query: '{current_query}'")

                    # Truy vấn lại nếu không phải lần đầu hoặc nếu cần cập nhật
                    iter_docs = retriever.invoke(current_query) if attempts > 1 else related_docs

                    # Đánh giá (Evaluate)
                    score, validated_docs = evaluate(user_input, iter_docs)
                    
                    if score == "success":
                        logger.info(f"✨ [CoRAG] Thành công ở lần {attempts}!")
                        success_finding = True
                        final_docs = validated_docs
                        break 
                    
                    if attempts < max_attempts:
                        logger.warning(f"⚠️ [CoRAG] Lần {attempts} không đạt điểm. Đang Rewrite bằng Gemini...")
                        rewrite_prompt = f"""Bạn là chuyên gia tối ưu hóa tìm kiếm. 
                        Câu hỏi gốc: '{user_input}' không tìm thấy kết quả.
                        Hãy viết lại một câu truy vấn ngắn gọn, tập trung vào từ khóa chính.
                        Chỉ trả về câu truy vấn mới."""
                        
                        rewrite_res = external_model.invoke(rewrite_prompt)
                        # Lấy text content
                        content = getattr(rewrite_res, 'content', str(rewrite_res))
                        if isinstance(content, list) and len(content) > 0:
                            if isinstance(content[0], dict) and 'text' in content[0]:
                                content = content[0]['text']
                        
                        current_query = str(content).strip()
                        logger.info(f"📝 [CoRAG] Query mới: '{current_query}'")

                # Tổng hợp kết quả CoRAG
                if success_finding:
                    results["corag_sources"] = extract_sources(final_docs)
                    results["corag_details"] = [
                        {"content": d.page_content, "source": d.metadata.get("source", "Unknown"), "page": d.metadata.get("page", "?")}
                        for d in final_docs
                    ]
                    context_corag = "\n\n".join([d.page_content for d in final_docs])
                    prompt_corag = get_prompt_template(user_input).format(context=context_corag, user_input=user_input)
                    
                    response = external_model.invoke(prompt_corag)
                    
                    final_text = getattr(response, 'content', str(response))
                    if isinstance(final_text, list) and len(final_text) > 0:
                        if isinstance(final_text[0], dict) and 'text' in final_text[0]:
                            final_text = final_text[0]['text']

                    results["corag"] = str(final_text).strip()
                else:
                    logger.error("❌ [CoRAG] Không tìm thấy thông tin tin cậy.")
                    results["corag"] = "🛡️ CoRAG: Không tìm thấy thông tin phù hợp trong tài liệu."
                
                logger.info(f"✅ [THREAD CoRAG] Hoàn thành. Tổng thời gian luồng: {time.time() - corag_thread_start:.2f}s")
            except Exception as e:
                logger.error(f"❌ [THREAD CoRAG] Lỗi: {e}")
                results["corag"] = f"Lỗi CoRAG: {str(e)}"

        # --- KHỞI TẠO VÀ CHẠY SONG SONG ---
        t1 = threading.Thread(target=run_rag_thread)
        t2 = threading.Thread(target=run_corag_thread)

        with st.spinner("🚀 Hệ thống đang xử lý song song RAG & CoRAG..."):
            t1.start()
            t2.start()

            # Đợi cả 2 luồng kết thúc
            t1.join()
            t2.join()

    else:
        logger.info("ℹ️ Không có VectorDB. Trả lời bằng kiến thức chung...")
        results["rag"] = model.invoke(user_input)
        
    total_time = time.time() - start_time
    logger.info(f"\n{'='*50}\n[HOÀN TẤT] Tổng thời gian xử lý toàn bộ: {total_time:.2f}s\n{'='*50}")
    
    return results