"""
Zariya offline knowledge engine.

This is the guaranteed-to-work core: pure Python, no network calls, no API keys.
It handles arithmetic, unit conversions, a bilingual Urdu/English dictionary, and
a curated general-knowledge base matched with a lightweight fuzzy scorer.

It is intentionally honest about what it is: a rule-based lookup system, not a
language model. The Claude API / local model integrations in app.py sit in front
of this and are tried first when configured; this is the fallback that never
needs a key, a server, or an internet connection.
"""
import json
import math
import os
import re
import time
from pathlib import Path

DATA_PATH = Path(__file__).parent / "server" / "kb_data.json"
LEARNED_PATH = Path(__file__).parent / "server" / "learned.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    _data = json.load(f)

DICT = _data["dict"]
KB = _data["kb"]

# Build a reverse-safe stopword-filtered index once at import time for speed.
KB_STOPWORDS = {
    "who", "what", "the", "is", "are", "was", "were", "a", "an", "of", "in", "on",
    "to", "do", "does", "did", "how", "can", "you", "your", "tell", "me", "about",
    "please", "and", "for", "it", "this", "that", "with", "i", "my", "could", "would",
}
KB_FILLERS = [
    "please tell me", "can you tell me", "could you tell me", "i want to know", "do you know",
    "what is the", "what's the", "what is", "what are the", "what are", "who is the", "who is",
    "who was", "tell me about", "explain", "define", "how do i", "how to", "how can i",
    "can you explain", "what does", "mean",
]

URDU_RE = re.compile(r"[\u0600-\u06FF]")


def is_urdu(text: str) -> bool:
    return bool(URDU_RE.search(text or ""))


def _normalize_query(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[?.!,]", "", s)
    for filler in KB_FILLERS:
        s = re.sub(r"^" + re.escape(filler) + r"\s+", "", s)
    return s.strip()


def _load_learned():
    if LEARNED_PATH.exists():
        try:
            return json.loads(LEARNED_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_learned(entries):
    LEARNED_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def remember_answer(question: str, answer: str, max_entries: int = 500):
    """Cache a real model answer locally so offline mode can reuse it later.
    This is NOT model training -- it's a local question/answer cache."""
    q = (question or "").strip()
    if not q or not answer:
        return
    entries = _load_learned()
    entries = [e for e in entries if e["q"].lower() != q.lower()]
    entries.insert(0, {"q": q, "a": answer, "ts": time.time()})
    entries = entries[:max_entries]
    _save_learned(entries)


def learned_lookup(text: str):
    entries = _load_learned()
    lower = text.lower()
    normalized = _normalize_query(text)
    query_words = {w for w in normalized.split() if len(w) > 2 and w not in KB_STOPWORDS}
    best, best_score = None, 0
    for entry in entries:
        entry_lower = entry["q"].lower()
        score = 0
        if lower == entry_lower:
            score = 999
        elif lower in entry_lower or entry_lower in lower:
            score = 20
        else:
            entry_words = [w for w in entry_lower.split() if len(w) > 2 and w not in KB_STOPWORDS]
            if entry_words:
                overlap = len([w for w in entry_words if w in query_words])
                ratio = overlap / len(entry_words)
                if ratio >= 0.7:
                    score = overlap
        if score > best_score:
            best, best_score = entry, score
    return best["a"] if best_score > 0 else None


def _significant_words(text: str):
    return {w for w in re.findall(r"[\w']+", text.lower()) if len(w) > 2 and w not in KB_STOPWORDS}


# Inverted index: significant word -> set of KB entry indices whose keyword phrases contain it.
# Built once at import time so lookups only ever score a small candidate set instead of
# scanning every entry in the knowledge base on every single message.
_KB_INDEX: dict[str, set[int]] = {}
for _idx, _entry in enumerate(KB):
    _entry_words = set()
    for _phrase in _entry["k"]:
        _entry_words |= _significant_words(_phrase)
    for _w in _entry_words:
        _KB_INDEX.setdefault(_w, set()).add(_idx)


def knowledge_base_lookup(text: str):
    lower = text.lower()
    normalized = _normalize_query(text)
    query_words = {w for w in normalized.split() if len(w) > 2 and w not in KB_STOPWORDS}

    candidate_idxs: set[int] = set()
    for w in query_words:
        candidate_idxs |= _KB_INDEX.get(w, set())

    best, best_score = None, 0
    for idx in candidate_idxs:
        entry = KB[idx]
        score = 0
        for phrase in entry["k"]:
            if phrase in lower:
                score += len(phrase.split()) * 3
            else:
                phrase_words = [w for w in phrase.split() if len(w) > 2 and w not in KB_STOPWORDS]
                if phrase_words:
                    overlap = len([w for w in phrase_words if w in query_words])
                    ratio = overlap / len(phrase_words)
                    if ratio >= 0.6:
                        score += overlap
        if score > best_score:
            best, best_score = entry, score
    return best["a"] if best_score > 0 else None


def try_math(text: str):
    m = re.search(r"sqrt\(?\s*(-?\d+(\.\d+)?)\s*\)?", text, re.I)
    if m:
        n = float(m.group(1))
        if n >= 0:
            return f"The square root of {m.group(1)} is **{math.sqrt(n)}**."

    m = re.search(r"(-?\d+(\.\d+)?)\s*%\s*of\s*(-?\d+(\.\d+)?)", text, re.I)
    if m:
        pct, of = float(m.group(1)), float(m.group(3))
        return f"{m.group(1)}% of {m.group(3)} is **{(pct/100)*of}**."

    cleaned = text.replace("^", "**")
    cleaned = re.sub(r"[^0-9+\-*/().\s]", "", cleaned)
    if cleaned.strip() and re.search(r"[0-9]", cleaned) and re.search(r"[+\-*/]", cleaned):
        try:
            val = eval(cleaned, {"__builtins__": {}}, {})  # noqa: S307 (sanitized input, digits/operators only)
            if isinstance(val, (int, float)):
                return f"That comes to **{val}**."
        except Exception:
            pass
    return None


def try_convert(text: str):
    lower = text.lower()
    m = re.search(r"(-?\d+(\.\d+)?)\s*km\b.*\bmiles?", lower)
    if m:
        v = float(m.group(1))
        return f"{v} km is about **{v*0.621371:.2f} miles**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*miles?\b.*\bkm\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} miles is about **{v*1.60934:.2f} km**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*kg\b.*\b(lbs?|pounds?)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} kg is about **{v*2.20462:.2f} lbs**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(lbs?|pounds?)\b.*\bkg\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} lbs is about **{v/2.20462:.2f} kg**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(c|celsius)\b.*\b(f|fahrenheit)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v}°C is **{(v*9/5)+32:.1f}°F**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(f|fahrenheit)\b.*\b(c|celsius)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v}°F is **{(v-32)*5/9:.1f}°C**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*cm\b.*\b(inch|inches|in)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} cm is about **{v/2.54:.2f} inches**."
    return None


def try_translate(text: str):
    lower = text.lower().strip()
    for k, v in DICT.items():
        if lower == k.lower():
            return f"**{k}** → {v}"
    return None


def summarize_messages(messages: list[dict]) -> str:
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    if not user_msgs:
        return "Nothing to summarize yet."
    first, last = user_msgs[0][:60], user_msgs[-1][:60]
    return f'This conversation covered {len(user_msgs)} request(s), starting with "{first}…" and most recently "{last}…"'


def key_points(messages: list[dict]) -> str:
    user_msgs = [m["content"] for m in messages if m["role"] == "user"][:6]
    return "\n".join(f"• {m[:80]}" for m in user_msgs)


def translate_words(text: str) -> str:
    words = text.split()
    out = []
    for w in words:
        clean = "".join(ch for ch in w if ch.isalnum() or ("\u0600" <= ch <= "\u06FF"))
        out.append(DICT.get(clean.lower(), DICT.get(clean, w)))
    return " ".join(out)


def flashcards_from_messages(messages: list[dict]) -> list[dict]:
    cards = []
    for i in range(len(messages) - 1):
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            q, a = messages[i]["content"].strip(), messages[i + 1]["content"].strip()
            if len(q) > 2 and len(a) > 2 and not a.startswith("I don't have that"):
                cards.append({"front": q[:140], "back": a[:220]})
    return cards


def knowledge_base_stats() -> dict:
    return {"dictWords": len(DICT), "kbEntries": len(KB)}
_GREETING_RE = re.compile(r"^(hi|hello|hey|salam|assalam)", re.I)
_BYE_RE = re.compile(r"^(bye|goodbye|see you|khuda hafiz)", re.I)


def offline_reply(messages: list[dict]) -> str:
    last_msg = messages[-1]
    last = last_msg.get("content", "").strip()
    lower = last.lower()
    urdu = is_urdu(last)

    conv = try_convert(last)
    if conv:
        return conv
    m = try_math(last)
    if m:
        return m

    if _GREETING_RE.search(lower) or "سلام" in last:
        return "وعلیکم السلام! میں کس طرح مدد کر سکتا ہوں؟" if urdu else "Assalam-o-Alaikum! How can I help you today?"
    if _BYE_RE.search(lower) or "خدا حافظ" in last:
        return "خدا حافظ! پھر ملیں گے۔" if urdu else "Goodbye! Talk again soon."
    if "شکریہ" in last or "thank" in lower:
        return "خوش آمدید! کوئی اور سوال؟" if urdu else "You're welcome! Anything else?"

    tr = try_translate(last)
    if tr:
        return tr

    if "time" in lower and "management" not in lower and "pomodoro" not in lower:
        return "It's currently " + time.strftime("%I:%M %p") + " on the server."
    if "date" in lower or ("today" in lower and "is" in lower):
        return "Today is " + time.strftime("%A, %B %d, %Y") + "."

    learned = learned_lookup(last)
    if learned:
        return learned
    kb_hit = knowledge_base_lookup(last)
    if kb_hit:
        return kb_hit

    generic_en = [
        "I don't have that in my offline knowledge base yet — I can handle arithmetic, unit conversions, "
        "common English⇄Urdu words, a range of general-knowledge questions, small code snippets, and study tips. "
        "For truly open-ended answers, add a Claude API key in Settings.",
        "That one's outside my offline knowledge base. Try a math expression, a conversion (like '10 km to miles'), "
        "a common word to translate, or connect an API key in Settings for full answers.",
    ]
    generic_ur = [
        "یہ سوال میرے آف لائن ڈیٹا بیس میں شامل نہیں ہے — میں حساب کتاب، پیمائش کی تبدیلی، عام الفاظ کا ترجمہ، "
        "اور کچھ عمومی معلومات دے سکتا ہوں۔ مکمل جوابات کے لیے سیٹنگز میں API key شامل کریں۔",
        "معذرت، یہ میری معلومات میں شامل نہیں۔ کوئی حساب، پیمائش، یا لفظ آزمائیں، یا سیٹنگز سے Claude API key جوڑیں۔",
    ]
    import random
    return random.choice(generic_ur if urdu else generic_en)
