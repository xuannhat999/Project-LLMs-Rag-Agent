import streamlit as st
import time

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Test Streamlit UI - OSSD 2026", page_icon="🧪", layout="centered"
)

st.title("🧪 Streamlit Interface Test")
st.caption("Giao diện thử nghiệm trước khi tích hợp Ollama & RAG")

# --- 2. SIDEBAR (THANH BÊN) ---
with st.sidebar:
    st.header("Cấu hình giả lập")
    speed = st.slider("Tốc độ phản hồi (giây)", 0, 5, 1)
    if st.button("Xóa lịch sử chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.info("Đây là nơi bạn sẽ để các nút Upload PDF sau này.")

# --- 3. QUẢN LÝ TRẠNG THÁI (SESSION STATE) ---
# Khởi tạo danh sách tin nhắn nếu chưa có
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Chào bạn! Tôi là bot thử nghiệm. Bạn cần test gì không?",
        }
    ]

# --- 4. HIỂN THỊ LỊCH SỬ CHAT ---
# Vòng lặp này giúp tin nhắn không bị mất khi giao diện load lại
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. XỬ LÝ NHẬP LIỆU (CHAT INPUT) ---
if prompt := st.chat_input("Nhập tin nhắn thử nghiệm tại đây..."):
    # Hiển thị tin nhắn của User
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Giả lập phản hồi của AI (Mock Response)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()  # Tạo vùng trống để hiệu ứng gõ chữ
        full_response = ""

        # Giả lập nội dung trả về
        mock_response = f"Bạn vừa nói là: '{prompt}'. Giao diện đang hoạt động rất tốt!"

        # Hiệu ứng gõ chữ (Streaming effect)
        for chunk in mock_response.split():
            full_response += chunk + " "
            time.sleep(0.1)  # Tốc độ hiện chữ
            message_placeholder.markdown(full_response + "▌")

        message_placeholder.markdown(full_response)

    # Lưu phản hồi vào lịch sử
    st.session_state.messages.append({"role": "assistant", "content": full_response})
