from sentence_transformers import CrossEncoder
import logging
import streamlit as st


@st.cache_resource
def get_encoder():

    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")


def evaluate(query, retrieved_docs):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    cross_encoder = get_encoder()
    # Tạo các cặp (query, doc)
    pairs = [[query, doc.page_content] for doc in retrieved_docs]

    # Dự đoán điểm số cho tất cả các cặp cùng lúc (rất nhanh)
    scores = cross_encoder.predict(pairs)
    logger.info(f"Score (CoRAG): {scores}")
    validated_context = []
    success = False

    for i, score in enumerate(scores):
        if float(score) > 0.1:
            logger.info(f"Validated context with score: {score}")
            validated_context.append(retrieved_docs[i].page_content)
            success = True

    return ("success" if success else "fallback_required"), validated_context
