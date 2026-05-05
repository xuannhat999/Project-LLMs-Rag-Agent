import streamlit as st
import time

from backend.model import (
    get_api_model,
    get_model,
    get_ollama_models,
    load_config_file,
    save_config,
)
from backend.chain_rag import get_embedder
from frontend.components.chatbox import render_chatbox
from frontend.components.sidebar import render_sidebar


@st.cache_resource
def init():
    return (get_embedder(), get_model(), get_api_model())


def load_config(
    config_data, models
):  # LOAD MODEL CONFIG (MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP)
    if config_data:
        model_name = config_data.get("model")
        if model_name in models:
            st.session_state.selected_model = config_data.get("model")
        else:
            st.session_state.selected_model = models[0]
        if "chunk_size" not in st.session_state:
            st.session_state.chunk_size = config_data.get("chunk_size")
        if "chunk_overlap" not in st.session_state:
            st.session_state.chunk_overlap = config_data.get("chunk_overlap")
    else:
        chunk_size = 1000
        chunk_overlap = 200
        model = models[0]
        st.session_state.chunk_size = chunk_size
        st.session_state.chunk_overlap = chunk_overlap
        st.session_state.selected_model = model
        save_config(
            model_name=model, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )


models = get_ollama_models()

if len(models) == 0:  # ERROR HANDLING: OLLAMA SERVICE
    st.warning(
        "⚠️ Ollama Service chưa được khởi động hoặc chưa được cài đặt\nVui lòng cài đặt và khởi động Ollama"
    )
    placeholder = st.empty()
    with placeholder.container():
        while len(models) == 0:
            time.sleep(2)
            models = get_ollama_models()
    st.success("✅ Ollama đã kết nối!")
    time.sleep(1)
    st.rerun()
else:
    st.session_state.models = models
    config_data = load_config_file()
    load_config(config_data, models)

embedder, model, api_model = init()

st.set_page_config(page_title="SmartDoc AI - OSSD 2026", layout="wide")

st.title("SnartDoc AI")
render_sidebar(embedder=embedder)
st.session_state.scroll = True
render_chatbox(model=model, api_model=api_model)
