# Zariya

Offline-first AI platform for Urdu and other low-resource languages.

Built around four things: **privacy-first AI**, **offline/local systems**,
**accessibility**, and being a **culturally aware communication tool** for
Urdu speakers.

## How it's actually built

This is a real Flask backend + a browser frontend, not a single static file.
That matters for a few reasons:

- **API keys never touch the browser.** Claude, Google Search, and GitHub
  OAuth credentials live in a server-side `.env` file. Whoever deploys this
  configures them once; the person *using* the app is never asked to enter
  a key.
- **Real GitHub sign-in.** This uses the actual OAuth authorization-code
  flow — the client secret is exchanged server-side, exactly as GitHub's
  own docs require. It is not a public-profile lookup pretending to be a
  login.
- **A genuine offline core.** `kb_engine.py` has zero dependencies and zero
  network calls: arithmetic, unit conversion, a ~340-word bilingual
  Urdu/English dictionary, and a ~395-entry curated knowledge base matched
  with a fuzzy scorer. This is what makes the "offline-first" claim true —
  it's the fallback whenever no AI key is configured or a request fails,
  not a marketing line.
- **Answers get remembered.** When Claude (or a local model) gives a real
  answer, it's cached server-side and reused for similarly-worded questions
  later — a growing local memory, not model retraining.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in whichever keys you want, or leave blank
python app.py
```

Then open `http://localhost:5000`. With an empty `.env`, everything still
works — you get the offline knowledge engine, notepad, and flashcards, with
zero setup and zero external connections.

### Optional: Claude API
Get a key from the [Anthropic Console](https://console.anthropic.com/) and
set `ANTHROPIC_API_KEY` in `.env`.

### Optional: Web search
Create a search engine at
[programmablesearchengine.google.com](https://programmablesearchengine.google.com/)
(set it to search the whole web) and an API key at
[console.cloud.google.com](https://console.cloud.google.com/apis/credentials)
(enable the Custom Search API). Set `GOOGLE_API_KEY` and `GOOGLE_CX`.

### Optional: Real GitHub sign-in
Create an OAuth App at
[github.com/settings/developers](https://github.com/settings/developers):
- Homepage URL: `http://localhost:5000`
- Authorization callback URL: `http://localhost:5000/auth/github/callback`

Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env`.

### Optional: a real local model
`local_model.py` supports running an actual GGUF model server-side via
`llama-cpp-python`, in the same spirit as this project's original
llama.cpp-based design. Install `llama-cpp-python`, drop a small
instruction-tuned GGUF file into `server/models/`, and set
`LOCAL_MODEL_PATH` in `.env` to its filename.

## An honest limit, stated plainly

The offline knowledge engine is a curated lookup table with a fuzzy matcher,
not a language model. It will always have gaps outside its ~395 entries. For
genuinely open-ended understanding, connect the Claude API or a local model —
there's no way around that trade-off, and this README won't pretend otherwise.

## Project layout

```
app.py              Flask app: routes, OAuth, Claude/Search proxying
kb_engine.py         Offline knowledge engine (no dependencies, no network)
local_model.py       Optional real local-model inference (llama.cpp)
templates/index.html Frontend markup
static/app.js        Frontend logic (talks only to this server's own API)
static/style.css      Styling
server/kb_data.json   Dictionary + knowledge base data
server/store.json     Per-user notes/sessions/decks (created at runtime)
server/learned.json   Cached AI answers (created at runtime)
```
