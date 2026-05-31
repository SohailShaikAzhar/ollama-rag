import os
from flask import Flask, render_template, request, jsonify
import requests
import json
import uuid
from pathlib import Path
from io import BytesIO
import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import docx
except ImportError:
    docx = None

OLLAMA_URL   = os.environ.get("OLLAMA_URL",   "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "tinyllama")

app = Flask(__name__)

# Simple file-based memory (persistent across restarts)
MEMORY_DIR = Path(os.environ.get("CHAT_MEMORY_DIR", "./memories"))
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_MAX = int(os.environ.get("CHAT_MEMORY_MAX", 50))  # max messages to keep

# Simple global knowledge base for custom data
KB_DIR = Path(os.environ.get("CHAT_KB_DIR", "./kb"))
KB_DIR.mkdir(parents=True, exist_ok=True)
KB_FILE = KB_DIR / "kb_data.json"
KB_MAX = int(os.environ.get("CHAT_KB_MAX", 50))

# Load embedding model for RAG
EMBED_MODEL_NAME = os.environ.get('EMBED_MODEL', 'all-MiniLM-L6-v2')
try:
    embed_model = SentenceTransformer(EMBED_MODEL_NAME)
except Exception:
    embed_model = None


def _memfile_for_session(session_id: str) -> Path:
    safe = ''.join([c for c in session_id if c.isalnum() or c in ('_', '-')])[:64]
    return MEMORY_DIR / f"chat_memory_{safe}.json"


def load_memory(session_id: str):
    try:
        p = _memfile_for_session(session_id)
        if p.exists():
            return json.loads(p.read_text(encoding='utf-8')) or []
    except Exception:
        return []
    return []


def save_memory(mem, session_id: str):
    try:
        # ensure embeddings exist for each item
        if embed_model is not None:
            texts_to_embed = [m['text'] for m in mem if 'embedding' not in m]
            if texts_to_embed:
                embs = embed_model.encode(texts_to_embed, convert_to_numpy=True)
                idx = 0
                for m in mem:
                    if 'embedding' not in m:
                        m['embedding'] = embs[idx].tolist()
                        idx += 1

        p = _memfile_for_session(session_id)
        p.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def clear_memory(session_id: str):
    try:
        p = _memfile_for_session(session_id)
        if p.exists():
            p.unlink()
    except Exception:
        pass


def load_kb():
    try:
        if KB_FILE.exists():
            return json.loads(KB_FILE.read_text(encoding='utf-8')) or []
    except Exception:
        return []
    return []


def save_kb(docs):
    try:
        KB_FILE.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def add_kb_doc(text: str, title: str = None):
    docs = load_kb()
    doc = {
        'title': title or f'Doc {len(docs) + 1}',
        'text': text,
    }
    if embed_model is not None:
        emb = embed_model.encode([text], convert_to_numpy=True)[0]
        doc['embedding'] = emb.tolist()
    docs.append(doc)
    if len(docs) > KB_MAX:
        docs = docs[-KB_MAX:]
    save_kb(docs)
    return doc


def clear_kb():
    try:
        if KB_FILE.exists():
            KB_FILE.unlink()
    except Exception:
        pass


def extract_text_from_file(filename: str, content: bytes):
    name = filename.lower()
    if name.endswith('.pdf'):
        if pdfplumber is None:
            raise RuntimeError('pdfplumber is not installed')
        text = []
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ''
                text.append(page_text)
        return '\n\n'.join(text).strip()
    if name.endswith('.docx'):
        if docx is None:
            raise RuntimeError('python-docx is not installed')
        document = docx.Document(BytesIO(content))
        return '\n'.join(paragraph.text for paragraph in document.paragraphs).strip()
    if name.endswith('.csv'):
        if pd is None:
            raise RuntimeError('pandas is not installed')
        df = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        rows = []
        for _, row in df.iterrows():
            rows.append(', '.join(f"{col}: {val}" for col, val in row.items()))
        return '\n'.join(rows).strip()
    if name.endswith('.xls') or name.endswith('.xlsx'):
        if pd is None:
            raise RuntimeError('pandas is not installed')
        df = pd.read_excel(BytesIO(content), dtype=str, keep_default_na=False)
        rows = []
        for _, row in df.iterrows():
            rows.append(', '.join(f"{col}: {val}" for col, val in row.items()))
        return '\n'.join(rows).strip()
    if name.endswith('.txt'):
        return content.decode('utf-8', errors='replace').strip()
    # fallback: attempt plain text
    try:
        return content.decode('utf-8', errors='replace').strip()
    except Exception:
        return ''


def retrieve_knowledge(query: str, k: int = 5):
    if embed_model is None:
        return []
    docs = load_kb()
    if not docs:
        return []
    entries = []
    embs = []
    for item in docs:
        if 'embedding' in item:
            entries.append(item)
            embs.append(np.array(item['embedding'], dtype=np.float32))
    if not embs:
        return []
    embs = np.vstack(embs)
    q_emb = embed_model.encode([query], convert_to_numpy=True)[0]
    embs_norm = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    q_norm = q_emb / np.linalg.norm(q_emb)
    sims = (embs_norm @ q_norm)
    topk_idx = np.argsort(-sims)[:k]
    return [entries[i] for i in topk_idx]


def retrieve_relevant(session_id: str, query: str, k: int = 5):
    if embed_model is None:
        return []
    mem = load_memory(session_id)
    if not mem:
        return []
    # build matrix of embeddings
    entries = []
    embs = []
    for item in mem:
        if 'embedding' in item:
            entries.append({'role': item.get('role', 'user'), 'text': item.get('text', '')})
            embs.append(np.array(item['embedding'], dtype=np.float32))
    if not embs:
        return []
    embs = np.vstack(embs)
    q_emb = embed_model.encode([query], convert_to_numpy=True)[0]
    # cosine similarity
    embs_norm = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    q_norm = q_emb / np.linalg.norm(q_emb)
    sims = (embs_norm @ q_norm)
    topk_idx = np.argsort(-sims)[:k]
    results = [entries[i] for i in topk_idx]
    return results


def _ensure_session_id():
    sid = request.cookies.get('session_id')
    if sid:
        return sid, False
    sid = uuid.uuid4().hex
    return sid, True


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data   = request.get_json() or {}
    prompt = data.get("message", "").strip()
    use_memory = bool(data.get("useMemory", False))
    use_knowledge = bool(data.get("useKnowledge", False))
    session_id, created = _ensure_session_id()
    if not prompt:
        return jsonify({"error": "no message provided"}), 400

    # Build prompt with optional memory and optional custom knowledge base.
    context_pieces = []
    if use_memory:
        rels = []
        try:
            rels = retrieve_relevant(session_id, prompt, k=5) if embed_model is not None else []
        except Exception:
            rels = []

        if rels:
            ctx_items = []
            for r in rels:
                text = r.get('text','')
                role = r.get('role','user')
                if role == 'bot':
                    continue
                s = ' '.join(text.splitlines())
                if len(s) > 800:
                    s = s[:800] + '...'
                ctx_items.append(f"- {s}")
            if ctx_items:
                context_pieces.append(
                    "Instruction: Use the Relevant context to answer the user's question directly. "
                    "Do not repeat previous assistant replies, and do not output any conversational labels like 'User:' or 'Assistant:'."
                )
                context_pieces.append("Relevant context:")
                context_pieces.extend(ctx_items)

    if use_knowledge:
        kb_rels = []
        try:
            kb_rels = retrieve_knowledge(prompt, k=5) if embed_model is not None else []
        except Exception:
            kb_rels = []

        if kb_rels:
            kb_items = []
            for item in kb_rels:
                s = ' '.join(item.get('text', '').splitlines())
                if len(s) > 800:
                    s = s[:800] + '...'
                title = item.get('title', 'Knowledge')
                kb_items.append(f"- [{title}] {s}")
            context_pieces.append("Knowledge base facts:")
            context_pieces.extend(kb_items)

    if context_pieces:
        full_prompt = "\n".join(context_pieces) + f"\n\nQuestion: {prompt}\nAnswer:"
    else:
        full_prompt = f"Question: {prompt}\nAnswer:"

    payload = {
        "model":  OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        j    = resp.json()
        text = j.get("response", "").strip()
        if not text:
            text = resp.text
    except requests.exceptions.Timeout:
        return jsonify({"error": "ollama timed out", "details": "Model took too long to respond"}), 502
    except Exception as e:
        return jsonify({"error": "ollama request failed", "details": str(e)}), 502

    # Persist to server memory (simple append)
    if use_memory:
        try:
            mem = load_memory(session_id)
            mem.append({ 'role': 'user', 'text': prompt })
            mem.append({ 'role': 'bot',  'text': text })
            if len(mem) > MEMORY_MAX:
                mem = mem[-MEMORY_MAX:]
            save_memory(mem, session_id)
        except Exception:
            pass

    resp = jsonify({"reply": text})
    if created:
        # set session cookie for continuous chat
        response = app.make_response(resp)
        response.set_cookie('session_id', session_id, httponly=True)
        return response
    return resp


@app.route('/memory', methods=['GET'])
def get_memory():
    session_id, created = _ensure_session_id()
    mem = load_memory(session_id)
    resp = jsonify({'memory': mem})
    if created:
        response = app.make_response(resp)
        response.set_cookie('session_id', session_id, httponly=True)
        return response
    return resp


@app.route('/memory/clear', methods=['POST'])
def post_clear_memory():
    session_id, created = _ensure_session_id()
    clear_memory(session_id)
    resp = jsonify({'ok': True})
    if created:
        response = app.make_response(resp)
        response.set_cookie('session_id', session_id, httponly=True)
        return response
    return resp


@app.route('/kb/add', methods=['POST'])
def post_add_kb():
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    title = data.get('title')
    if not text:
        return jsonify({'error': 'no kb text provided'}), 400
    doc = add_kb_doc(text, title=title)
    return jsonify({'ok': True, 'doc': {'title': doc['title'], 'text': doc['text']}})


@app.route('/kb/list', methods=['GET'])
def get_kb():
    docs = load_kb()
    return jsonify({'kb': [{'title': d.get('title'), 'text': d.get('text')} for d in docs]})


@app.route('/kb/upload', methods=['POST'])
def post_upload_kb():
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    upload = request.files['file']
    if upload.filename == '':
        return jsonify({'error': 'no file selected'}), 400
    try:
        content = upload.read()
        text = extract_text_from_file(upload.filename, content)
        if not text:
            return jsonify({'error': 'no text extracted from file'}), 400
        title = request.form.get('title') or upload.filename
        doc = add_kb_doc(text, title=title)
        return jsonify({'ok': True, 'doc': {'title': doc['title'], 'text': doc['text'][:500]}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/kb/clear', methods=['POST'])
def post_clear_kb():
    clear_kb()
    return jsonify({'ok': True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)