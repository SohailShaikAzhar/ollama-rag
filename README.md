# Ollama Chatbot (Flask)

A feature-rich Flask web application that forwards chat messages to an Ollama server with persistent memory management, knowledge base support, and RAG (Retrieval-Augmented Generation) capabilities.

## Overview

This project provides a modern web interface for interacting with Ollama language models. It includes:
- **Chat Memory**: Persistent session-based conversation storage with embeddings
- **Knowledge Base**: Support for uploading and querying custom documents (PDF, Excel, Word)
- **RAG Integration**: Embedding-based retrieval for context-aware responses
- **Modern UI**: Dark theme with intuitive controls and real-time chat interface

## Project Structure

```
ollama-chatbot/
├── main.py                    # Flask backend & API routes
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── .gitignore                 # Git ignore configuration
├── kb/
│   └── kb_data.json          # Knowledge base storage
├── memories/
│   └── chat_memory_*.json    # Session-based chat memory
├── static/
│   ├── css/
│   │   └── style.css         # Responsive dark theme styling
│   └── js/
│       └── chat.js           # Frontend chat logic & UI interactions
├── templates/
│   └── index.html            # Main HTML template
└── lib/                       # Ollama binaries (excluded from git)
```

## Features

### Core Functionality
- **Real-time Chat**: Send messages to Ollama and receive responses
- **Session Memory**: Automatic conversation history storage per session
- **Knowledge Base**: Upload and query custom documents
- **Embedding Support**: Semantic search using SentenceTransformer

### File Format Support
- **Documents**: PDF, Excel (.xlsx, .xls), Word (.docx)
- **Text**: Plain text pasting directly into knowledge base
- **Memory**: JSON-based persistent storage

## Installation & Setup

### 1. Create Virtual Environment
```bash
python -m venv .venv
.\.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables (Optional)
Create a `.env` file or set environment variables:
```bash
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_MODEL=tinyllama
CHAT_MEMORY_DIR=./memories
CHAT_MEMORY_MAX=50
CHAT_KB_DIR=./kb
CHAT_KB_MAX=50
EMBED_MODEL=all-MiniLM-L6-v2
```

### 4. Run the Application
```bash
python main.py
```

Open your browser and navigate to: **http://127.0.0.1:5000**

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | >=2.0 | Web framework |
| Requests | >=2.25 | HTTP client for Ollama |
| SentenceTransformers | >=2.2.2 | Embedding generation |
| NumPy | >=1.24 | Numerical computations |
| Pandas | >=2.0 | Data processing |
| pdfplumber | >=0.9.0 | PDF text extraction |
| python-docx | >=0.8.11 | Word document parsing |
| openpyxl | >=3.1 | Excel file handling |
| xlrd | >=2.0 | Legacy Excel support |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://127.0.0.1:11434/api/generate` | Ollama API endpoint |
| `OLLAMA_MODEL` | `tinyllama` | Default model to use |
| `CHAT_MEMORY_DIR` | `./memories` | Directory for session memory files |
| `CHAT_MEMORY_MAX` | `50` | Maximum messages per session |
| `CHAT_KB_DIR` | `./kb` | Directory for knowledge base storage |
| `CHAT_KB_MAX` | `50` | Maximum KB items |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model for embeddings |

## Usage

### Chat Interface
1. Type your message in the input field
2. Press Enter or click Send
3. Wait for the model to respond

### Memory Management
- **Use server memory**: Enable to persist conversation across sessions
- **Load server memory**: Restore previous conversation
- **Clear server memory**: Delete saved conversation history

### Knowledge Base
1. **Add text**: Paste content into the text area and click "Add to knowledge base"
2. **Upload file**: Select a PDF, Excel, or Word document and click "Upload file to knowledge base"
3. **Use KB**: Enable the checkbox to include KB context in responses
4. **Clear KB**: Delete all knowledge base entries

## API Endpoints

### POST `/chat`
Send a chat message to the model.

**Request:**
```json
{
  "message": "Your message here",
  "use_memory": true,
  "use_knowledge": false
}
```

**Response:**
```json
{
  "response": "Model response here",
  "session_id": "session-uuid"
}
```

## Production Notes

- **Security**: Set `debug=False` in production
- **Server**: Use a production WSGI server (Gunicorn, uWSGI)
- **SSL**: Deploy behind HTTPS reverse proxy
- **Memory**: Monitor chat_memory_*.json files for cleanup
- **Rate Limiting**: Consider adding request throttling

## Troubleshooting

### Ollama Connection Issues
- Verify Ollama is running: `curl http://127.0.0.1:11434/api/generate`
- Check `OLLAMA_URL` environment variable
- Ensure model is installed: `ollama pull tinyllama`

### Embedding Model Issues
- First run downloads the embedding model (~50MB)
- Check internet connection
- Verify HuggingFace model availability

### File Upload Issues
- Check file format is supported (PDF, Excel, Word)
- Verify file is not corrupted
- Check disk space for temporary processing

## Development

To modify the application:
- Backend: Edit `main.py`
- Frontend: Update `templates/index.html` and `static/`
- Styling: Modify `static/css/style.css`
- Logic: Update `static/js/chat.js`

## License

Creative Commons Zero v1.0 Universal
