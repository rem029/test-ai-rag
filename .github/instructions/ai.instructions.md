# GitHub Copilot Guide for Python AI Service

```yaml
applyTo: '**'
```

---

## 📉 Project Context

This Python service lives under `apps/ai/` in the monorepo and handles all **AI logic** for the system. It is designed to be a private, locally accessible service called only by the secure Node.js API (`apps/api`).

It is responsible for the following:

- Receiving unified requests from the Node.js layer
- Using Moondream for vision tasks if the message includes an image
- Embedding input using sentence-transformers
- Searching the vector DB (PostgreSQL with pgvector)
- Triggering fallback web search when needed
- Assembling prompts and querying Ollama (e.g., Gemma 3 1B)
- Returning streaming text response
- Returning optional TTS audio if requested

---

## ⚖️ Stack

- FastAPI (Python Web Framework)
- sentence-transformers (text embeddings)
- Piper or Coqui TTS (local text-to-speech)
- PostgreSQL + pgvector (vector search)
- Ollama (Gemma, Moondream)
- Optional: BeautifulSoup / DuckDuckGo / SearXNG for web search fallback

---

## ✅ Coding Guidelines for Copilot & Contributors

### General Rules

- Use Pydantic for request/response types
- Add type hints and docstrings
- Keep endpoints unified and use a single `/message` route for main requests
- Logic should be functionally split into clear service modules (embed, speak, vision, search, prompt)
- Use StreamingResponse when generating replies

### File Naming Convention

- `main.py` - FastAPI app + `/message` route
- `embed.py` - Embedding + pgvector logic
- `tts.py` - Text-to-speech
- `vision.py` - Moondream wrapper
- `prompt.py` - RAG flow, prompt building
- `ollama.py` - Request/stream wrapper for Ollama

### Testing

- Functions must be independently testable
- No global state or I/O coupling
- Use unit tests for vector matching, search fallback, and TTS audio generation

### Code Style

- PEP8 with `black`
- Strict typing + mypy-friendly
- Avoid unnecessary globals or stateful classes

---

## 🤖 Copilot Prompt Patterns

### Unified RAG Call

```python
# Handle a single user message that may include image, text, and audio flag
```

### Vision (if image present)

```python
# Use Moondream via Ollama to generate caption or OCR from image
```

### Embedding and Vector Search

```python
# Generate embedding and search pgvector-enabled Postgres DB
```

### Web Fallback + RAG

```python
# If similarity score is low, fetch web content and re-embed into vector DB
```

### Stream LLM Response

```python
# Stream response from Ollama as it generates text
```

### Text-to-Speech

```python
# Generate TTS audio (base64 WAV) if audioResponse is True
```

---

## 📂 Folder Layout

```bash
apps/ai/
├── main.py
├── embed.py
├── tts.py
├── vision.py
├── prompt.py
├── ollama.py
├── requirements.txt
└── README.md
```

---

## 🚀 Goal

Enable GitHub Copilot (and human contributors) to generate maintainable, testable AI logic for a local AI engine that powers RAG, vision, and audio inside a cleanly decoupled backend architecture.

