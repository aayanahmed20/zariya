<div align="center">

# Zariya

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=500&size=22&duration=3000&pause=1000&color=58A6FF&center=true&vCenter=true&width=700&lines=Offline-First+AI+Platform;Urdu+%26+Low-Resource+Language+AI;Privacy-Preserving+AI+Systems;Building+Culturally+Aware+Intelligent+Tools" />

<br>

<a href="https://github.com/aayanahmed20/zariya">
  <img src="https://img.shields.io/badge/Project-Zariya-0d1117?style=for-the-badge&logo=github&logoColor=58A6FF"/>
</a>

<a href="https://github.com/aayanahmed20">
  <img src="https://img.shields.io/badge/Developer-Aayan%20Ahmed-0d1117?style=for-the-badge&logo=github&logoColor=white"/>
</a>

</div>

---

## Web App (recommended)

The actively developed version of Zariya now lives in [`webapp/`](webapp/): a
Flask backend plus browser frontend, with a genuinely offline knowledge engine,
optional Claude API / web search / real GitHub OAuth sign-in (all server-side,
so no one using the app ever has to enter a key), and an optional local model (via Ollama) in the same spirit as the original design below.

```bash
cd webapp
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Then open `http://localhost:5000`. See [`webapp/README.md`](webapp/README.md)
for the full setup (Claude API, web search, GitHub OAuth, local model).

---

## Overview

Zariya is an **offline-first AI assistant platform** designed to make intelligent language models accessible in **low-resource languages such as Urdu**.

It runs fully on local devices without requiring internet connectivity, focusing on **privacy, accessibility, and inclusivity**.

The project explores how AI systems can function independently of cloud infrastructure while supporting underserved linguistic communities.

---

## Purpose

Zariya is built to explore:

- Offline AI system design  
- Urdu and low-resource language support  
- Privacy-preserving AI architectures  
- Edge-based (local) LLM inference  
- Educational AI applications  

---

## Key Features

- Fully offline AI chat system  
- Urdu + English bilingual support  
- Local inference using quantized LLMs (GGUF)  
- No cloud or API dependency  
- Privacy-first architecture  
- Lightweight system for low-resource devices  
- Local memory storage for conversations  

---

## System Architecture

User → Streamlit UI → Inference Engine (llama.cpp) → Local LLM → Response

---

## Model Setup

Zariya requires a local language model to run. It runs the same fallback-free, no-internet-required design either way:

1. **Easiest -- download a model from inside the app.** Launch Zariya (see below), open **Settings > Model**, and pick one of the built-in presets (Phi-3 Mini, ~2.2 GB; Mistral 7B Instruct, ~4.4 GB; Llama 3 8B Instruct, ~4.9 GB), or paste any direct `.gguf` URL. The app streams it straight into `models/model.gguf`.
2. **Manual.** Download any GGUF-format model yourself (for example from [Hugging Face](https://huggingface.co/models?search=gguf)), and place it at `models/model.gguf`.

Either way, once a model file is in place, Zariya loads it locally via `llama.cpp` and never calls out to the network to answer a chat message.

---

## Running Zariya (Streamlit app)

```bash
pip install -r requirements.txt
python run.py
```

`run.py` creates the `models/` and `data/` folders if they don't exist, checks whether `streamlit` and `llama-cpp-python` are installed and whether a model is already in place, then launches the Streamlit UI. If no model has been downloaded yet, the app still starts -- it just won't be able to generate real replies until you add one from **Settings > Model**, as described above.

---

## Which version should I use?

- Want the simplest possible standalone LLM chat, with everything (UI, inference, storage) in one Python process and no server concepts to think about? Use the **Streamlit app** (`run.py`) above.
- Want a browser-based UI with notes/flashcards/spaced-repetition study tools, and don't mind running a small Flask server? Use **[`webapp/`](webapp/)**. It talks to a local model through [Ollama](https://ollama.com) instead of `llama.cpp` directly (no C++ build tools required), answers with streaming, token-by-token responses, and only ever reaches out to the network if you explicitly configure an optional Claude API key or web search -- with neither configured, it is just as standalone as the Streamlit app.
