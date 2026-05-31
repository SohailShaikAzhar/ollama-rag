# Ollama Chatbot (Flask)

A minimal Flask app that forwards chat messages to an Ollama server.

Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. (Optional) Configure Ollama endpoint and model via environment variables:

- `OLLAMA_URL` (default: `http://127.0.0.1:11434/api/generate`)
- `OLLAMA_MODEL` (default: `llama2`)

3. Run the app:

```bash
python main.py
```

4. Open http://127.0.0.1:5000 in your browser.

Notes

- The app uses a permissive approach to parse Ollama responses (tries several common fields). Adjust `main.py` if your Ollama server returns a different JSON shape.
- For production use, disable `debug=True` and run behind a production server.
