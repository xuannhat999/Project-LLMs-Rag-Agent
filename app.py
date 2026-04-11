import streamlit as st
import time
from data.model import get_model
from data.chain_rag import get_retriever, get_embedder
from frontend.components.chatbox import render_chatbox
from frontend.components.sidebar import render_sidebar


@st.cache_resource
def init():
    return (
        get_embedder(),
        get_model(),
    )


embedder, model = init()

st.set_page_config(
    page_title="Test Streamlit UI - OSSD 2026", page_icon="🧪", layout="centered"
)

st.title("Project LLMs-RAG-Agent")

render_sidebar(embedder=embedder)
render_chatbox(model=model)
