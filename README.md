**Requiments** 
- Ollama
- Python

**1. Clone Repo:**
   ```bash
   git clone git@github.com:xuannhat999/Project-LLMs-Rag-Agent.git
   cd Project-LLMs-Rag-Agent
   ```
**2. Create & Activate venv**
   ```bash
   # Window
   python -m venv venv
   venv\Scripts\activate
   ```
   ```bash
   # Linux/MacOS
   python3 -m venv venv
   source venv/bin/activate
  ```
**3. Install Python packages**  
   ! Lưu ý: nếu máy có GPU rời thì edit file requirements.txt, bỏ dòng --extra-index-url https://download.pytorch.org/whl/cpu và +cpu ở package 'torch' trước khi cài dependencies
   ```bash
   pip install -r requirents.txt
   ```
**4. Pull model Ollama**
   ```bash
   ollama pull qwen2.5:7b
  ```
**5. Run app**
  ```bash
  streamlit run app.py
  ```
