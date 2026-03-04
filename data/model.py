import streamlit as st
from langchain_community.llms import Ollama
from langchain_community.embeddings import (
    HuggingFaceEmbeddings,
)  # Bản cập nhật mới của LangChain


@st.cache_resource
def get_embedder():
    # Khởi tạo Embedder chạy trên CPU cho Pipeline
    model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model_kwargs = {"device": "cpu"}
    encode_kwargs = {"normalize_embeddings": True}

    return HuggingFaceEmbeddings(
        model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
    )


@st.cache_resource
def get_llm():
    # Khởi tạo LLM từ Ollama (Local)
    return Ollama(model="qwen2.5:7b", temperature=0.7, top_p=0.9, repeat_penalty=1.1)
