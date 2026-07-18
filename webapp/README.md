# Zariya

Offline-first AI platform for Urdu and other low-resource languages.

Built around four things: privacy-first AI, offline/local systems, accessibility, and being a culturally aware communication tool for Urdu speakers.

## How it's actually built

This is a real Flask backend + a browser frontend, not a single static file. That matters for a few reasons:

- **No API key required, ever.** By default Zariya talks to a free local model runner called Ollama, which runs open-source models entirely on your own machine. There's nothing to sign up for and nothing to paste into a settings screen.
- **API keys never touch the browser, if you choose to add any.** Claude, Google Search, and GitHub OAuth credentials (all optional) live in a server-side `.env` file. Whoever deploys this configures them once; the person using the app is never asked to enter a key.
- **Real GitHub sign-in.** This uses the actual OAuth authorization-code flow — the client secret is exchanged server-side, exactly as GitHub's own docs require. It is not a public-profile lookup pretending to be a login.
- **A genuine offline core.** `kb_engine.py` has zero dependencies and zero network calls: arithmetic, unit conversion, a ~340-word bilingual Urdu/English dictionary, and a ~395-entry curated knowledge base matched with a fuzzy scorer. This is the guaranteed fallback if Ollama isn't installed/running, or while a model is still downloading — the app never goes blank.
- **Answers get remembered.** When the local model (or Claude, if configured) gives a real answer, it's cached server-side and reused for similarly-worded questions later — a growing local memory, not model retraining.

## Setup

1. Install Ollama once: https://ollama.com/download (a normal app installer for Windows/Mac/Linux — no C++ compiler, no account, nothing to configure). Make sure it's running.
2. ```
   pip install -r requirements.txt
   cp .env.example .env
   python app.py
   ```
3. Open http://localhost:5000. On first chat request, Zariya asks Ollama to pull a small model (`qwen2.5:1.5b` by default, ~1GB, free, one-time) automatically — no command needed from you. The offline knowledge engine answers immediately in the meantime, then the app switches over to the real local model once it's ready.

This previously used `llama-cpp-python` to load model files directly in-process, which required a working C++ build toolchain and failed to install on a number of machines. Talking to Ollama over plain HTTP instead avoids that entirely — Ollama ships its own prebuilt binaries.

### Using a different local model

Set `LOCAL_MODEL_NAME` in `.env` to any model name from https://ollama.com/library (e.g. `llama3.2:1b`, `qwen2.5:3b`).

### Running Ollama elsewhere

Set `OLLAMA_URL` in `.env` if Ollama is running on a different host/port than the default `http://localhost:11434`.

### Disabling the local model entirely

Set `DISABLE_LOCAL_MODEL=1` in `.env` for a purely offline, lookup-table-only deployment that never tries to contact Ollama.

### Optional: Claude API

Get a key from the Anthropic Console and set `ANTHROPIC_API_KEY` in `.env`. When set, Claude is tried first (highest quality), then the local model, then the offline knowledge engine.

### Optional: Web search

Create a search engine at programmablesearchengine.google.com (set it to search the whole web) and an API key at console.cloud.google.com (enable the Custom Search API). Set `GOOGLE_API_KEY` and `GOOGLE_CX`.

### Optional: Real GitHub sign-in

Create an OAuth App at github.com/settings/developers:

- Homepage URL: `http://localhost:5000`
- Authorization callback URL: `http://localhost:5000/auth/github/callback`

Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env`.

## An honest limit, stated plainly

The default local model is small (1.5B parameters) so it downloads quickly and runs on ordinary laptop CPUs — it will be noticeably less capable and slower than a large hosted model. The offline knowledge engine below it is a curated lookup table with a fuzzy matcher, not a language model, and will always have gaps outside its ~395 entries. For higher-quality or faster answers, connect the Claude API or point `LOCAL_MODEL_NAME` at a larger Ollama model — there's no way around that trade-off, and this README won't pretend otherwise.

## Project layout

- `app.py` — Flask app: routes, OAuth, Claude/Search proxying, model fallback chain
- `kb_engine.py` — Offline knowledge engine (no dependencies, no network)
- `local_model.py` — Local-model inference via Ollama's local HTTP API
- `templates/index.html` — Frontend markup
- `static/app.js` — Frontend logic (talks only to this server's own API)
- `static/style.css` — Styling
- `server/kb_data.json` — Dictionary + knowledge base data
- `server/store.json` — Per-user notes/sessions/decks (created at runtime)
- `server/learned.json` — Cached AI answers (created at runtime)
