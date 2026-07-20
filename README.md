# Zariya

Zariya is an offline-first AI assistant for Urdu and other low-resource languages. Once a model is downloaded, it runs entirely on your own device, so it works without an internet connection and doesn't depend on any cloud API to hold a conversation.

## Why this exists

A lot of AI tools quietly assume two things: that you have a solid internet connection, and that your language already has good support baked into the model. Neither of those is true everywhere, and they're especially not true for a lot of Urdu speakers. I started Zariya to see how far a genuinely local, privacy-first AI system could go, and to make sure Urdu wasn't treated as an afterthought.

## Two versions in this repo

The project has gone through two iterations, and both still work:

- **`webapp/`** - the version I'm actively developing. A Flask backend with a browser front end. It talks to a local model through Ollama, streams responses back token by token, and falls back to a small offline knowledge engine (no dependencies, no network calls) if a model isn't available yet. Claude API access, web search, and GitHub sign-in are all optional and configured server-side, so nobody using the app ever has to hold an API key.
- **the original Streamlit app** (`app/`, `core/`, `models/`) - a single-process version that loads a GGUF model directly with `llama.cpp`. Simpler to reason about, no server involved.

If you're only going to run one, use the web app - see [`webapp/README.md`](webapp/README.md) for its full setup.

## Features

- Works fully offline once a model is downloaded
- Bilingual Urdu/English support
- Local inference - no data leaves your machine unless you turn on an optional cloud feature yourself
- Streaming, token-by-token responses in the web app
- A small offline knowledge engine as a safety net when no model is loaded yet

## Tech stack

- Python
- Flask (web app)
- Streamlit + llama-cpp-python (original app)
- Ollama for local model inference (web app)
- Vanilla JS/CSS front end

## Getting started

Web app:

```bash
cd webapp
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Then open `http://localhost:5000`.

Streamlit app:

```bash
pip install -r requirements.txt
python run.py
```

`run.py` sets up the `models/` and `data/` folders, checks whether a model is already downloaded, and launches the UI. If there's no model yet, you can download one from inside the app under Settings > Model (Phi-3 Mini, Mistral 7B Instruct, and Llama 3 8B Instruct are built in as presets), or place any GGUF file at `models/model.gguf` yourself.

## Project structure

- `webapp/` - Flask app, local model + offline fallback, browser front end
- `app/`, `core/`, `models/` - original Streamlit app and inference engine
- `run.py` - entry point for the Streamlit app
- `requirements.txt` - dependencies for the Streamlit app

## Status

Actively working on this. The offline knowledge engine is still fairly small, and the local model is only as good as whatever you point it at - a 1.5B model on a laptop CPU won't compete with a hosted large model, and I'd rather say that upfront than pretend otherwise.
