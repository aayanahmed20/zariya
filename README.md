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

The actively developed version of Zariya now lives in [`webapp/`](webapp/) — a
Flask backend plus browser frontend, with a genuinely offline knowledge engine,
optional Claude API / web search / real GitHub OAuth sign-in (all server-side,
so no one using the app ever has to enter a key), and an optional local
llama.cpp-based model in the same spirit as the original design below.

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

Zariya requires a local language model to run.

