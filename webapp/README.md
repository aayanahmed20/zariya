# Zariya

Offline-first AI platform for Urdu and other low-resource languages.

Built around four things: privacy-first AI, offline/local systems, accessibility, and being a culturally aware communication tool for Urdu speakers.

## How it's actually built

This is a real Flask backend + a browser frontend, not a single static file. That matters for a few reasons:

- **No API key required, ever.** By default Zariya runs entirely on a local language model that downloads itself the first time you start the server. There's nothing to sign up for and nothing to paste into a settings screen.
- **API keys never touch the browser, if you choose to add any.** Claude, Google Search, and GitHub OAuth credentials (all optional) live in a server-side `.env` file. Whoever deploys this configures them once; the person using the app is never asked to enter a key.
- **Real GitHub sign-in.** This uses the actual OAuth authorization-code flow — the client secret is exchanged server-side, exactly as GitHub's own docs require. It is not a public-profile lookup pretending to be a login.
- **A genuine offline core.** `kb_engine.py` has zero dependencies and zero network calls: arithmetic, unit conversion, a ~340-word bilingual Urdu/English dictionary, and a ~395-entry curated knowledge base matched with a fuzzy scorer. This is the guaranteed fallback while the local model is downloading/loading, or if it fails to load for any reason — the app never goes blank.
- **Answers get remembered.** When the local model (or Claude, if configured) gives a real answer, it's cached server-side and reused for similarly-worded questions later — a growing local memory, not model retraining.

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # nothing needs to be filled in to get a real model running
python app.py
```

Then open http://localhost:5000. On first run, the server starts a background download of a small instruction-tuned local model (Qwen2.5-1.5B-Instruct, GGUF, ~1GB, a public file — no account or key needed) into `server/models/`. Chat works immediately using the offline knowledge engine while that download and load happen, then automatically switches over to the real local model once it's ready (check `/api/config` or the status shown in the UI). This is a one-time download; subsequent restarts load straight from disk.

Everything above works with zero external network calls after that initial model download, and zero API keys, forever.

### Using your own local model instead

Drop a different GGUF file into `server/models/` and set `LOCAL_MODEL_PATH` in `.env` to its filename — Zariya will load that instead of downloading the default one.

### Disabling the local model entirely

Set `DISABLE_LOCAL_MODEL_DOWNLOAD=1` in `.env` if you want a purely offline, lookup-table-only deployment with no model download at all.

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

The bundled default local model is small (1.5B parameters) so it can download quickly and run on ordinary laptop CPUs — it will be noticeably less capable than a large hosted model, and slower per reply. The offline knowledge engine below it is a curated lookup table with a fuzzy matcher, not a language model, and will always have gaps outside its ~395 entries. For higher-quality or faster answers, connect the Claude API or point `LOCAL_MODEL_PATH` at a larger GGUF model — there's no way around that trade-off, and this README won't pretend otherwise.

## Project layout

- `app.py` — Flask app: routes, OAuth, Claude/Search proxying, model fallback chain
- `kb_engine.py` — Offline knowledge engine (no dependencies, no network)
- `local_model.py` — Local-model inference: auto-downloads and runs a GGUF model via llama.cpp
- `templates/index.html` — Frontend markup
- `static/app.js` — Frontend logic (talks only to this server's own API)
- `static/style.css` — Styling
- `server/kb_data.json` — Dictionary + knowledge base data
- `server/models/` — Local GGUF model file(s) (downloaded automatically, or provided by you)
- `server/store.json` — Per-user notes/sessions/decks (created at runtime)
- `server/learned.json` — Cached AI answers (created at runtime)
