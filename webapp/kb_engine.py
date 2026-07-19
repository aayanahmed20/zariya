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

# Optional supplementary knowledge base file, kept separate from kb_data.json
# (the large generated dataset) so new dictionary words / KB entries can be
# added in small, easy-to-review batches without touching that file at all.
# This is purely additive and never a hard dependency: if the file is missing,
# empty, or malformed, the app must still start up fine on kb_data.json alone.
EXTRA_DATA_PATH = Path(__file__).parent / "server" / "kb_data_extra.json"
if EXTRA_DATA_PATH.exists():
    try:
        _extra = json.loads(EXTRA_DATA_PATH.read_text(encoding="utf-8"))
        DICT = {**DICT, **_extra.get("dict", {})}
        KB = KB + _extra.get("kb", [])
    except Exception as _e:
        print(f"kb_engine: ignoring invalid kb_data_extra.json ({_e})")

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
    entries.insert(0, {"q": q, "a": answer, "ts": time.time(), "score": 0})
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
        score += entry.get("score", 0) * 0.5
        if score > best_score:
            best, best_score = entry, score
    return best["a"] if best_score > 0 else None


def rate_learned_answer(question: str, rating: str) -> bool:
    """Apply user feedback to a cached learned answer. An "up" rating nudges
    that answer to be preferred over other loosely-matching cached answers in
    future lookups; a "down" rating removes it entirely, so a bad cached
    answer never gets served again. Returns True if a matching cached entry
    was found and updated, False otherwise (e.g. the reply came straight from
    the offline knowledge base rather than a real model, so there's nothing
    cached to rate)."""
    q = (question or "").strip().lower()
    if not q or rating not in ("up", "down"):
        return False
    entries = _load_learned()
    match = next((e for e in entries if e["q"].lower() == q), None)
    if not match:
        return False
    if rating == "down":
        entries = [e for e in entries if e is not match]
    else:
        match["score"] = match.get("score", 0) + 1
    _save_learned(entries)
    return True

def _significant_words(text: str):
    return {w for w in re.findall(r"[\w']+", text.lower()) if len(w) > 2 and w not in KB_STOPWORDS}

def _edit_distance(a: str, b: str) -> int:
    """Standard Levenshtein distance, used to tolerate small typos in queries.
    Kept dependency-free since the offline engine can't rely on external packages."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]

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

_KB_INDEX_WORDS = sorted(_KB_INDEX.keys())
# Bucket index words by length so a typo'd query word only gets compared against
# words of a similar length, instead of the whole vocabulary, on every lookup.
_KB_WORDS_BY_LEN: dict[int, list[str]] = {}
for _w in _KB_INDEX_WORDS:
    _KB_WORDS_BY_LEN.setdefault(len(_w), []).append(_w)

def _fuzzy_correct(word: str):
    """Find the closest known index word for a possibly-misspelled query word.
    Only tries words within 1 character of length, and only accepts a match within
    a small edit-distance budget that scales with word length, so short words don't
    get falsely corrected into unrelated short words."""
    if word in _KB_INDEX:
        return word
    if len(word) < 4:
        return None
    max_dist = 1 if len(word) <= 5 else 2
    best, best_dist = None, max_dist + 1
    for length in (len(word) - 1, len(word), len(word) + 1):
        for candidate in _KB_WORDS_BY_LEN.get(length, []):
            d = _edit_distance(word, candidate)
            if d < best_dist:
                best, best_dist = candidate, d
    return best if best_dist <= max_dist else None

def knowledge_base_lookup(text: str):
    lower = text.lower()
    normalized = _normalize_query(text)
    query_words = {w for w in normalized.split() if len(w) > 2 and w not in KB_STOPWORDS}

    candidate_idxs: set[int] = set()
    matched_words = set(query_words)
    for w in query_words:
        hits = _KB_INDEX.get(w)
        if hits:
            candidate_idxs |= hits
        else:
            corrected = _fuzzy_correct(w)
            if corrected:
                candidate_idxs |= _KB_INDEX[corrected]
                matched_words.add(corrected)

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
                    overlap = len([w for w in phrase_words if w in matched_words])
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

    # The generic evaluator below used to fire whenever the message contained
    # *any* digits plus *any* operator-like character, anywhere in the text.
    # That misfired on plenty of non-math messages that merely happen to
    # contain a run of digits and a hyphen/plus/etc -- phone numbers ("call me
    # at 555-1234"), dates, addresses, and scores ("we won 3-2") were all
    # silently "solved" as arithmetic and given a nonsense numeric answer.
    # Guard it: only treat the message as an inline calculation if every word
    # in it (aside from digits/operators) is one of a small set of normal
    # math-phrasing words, so a real expression like "what's 12*4" still
    # works but a sentence built around unrelated words is left alone for the
    # knowledge base / fallback reply to handle instead.
    _MATH_PHRASE_WORDS = {
        "what", "whats", "is", "the", "calculate", "compute", "solve", "equals",
        "equal", "to", "of", "answer", "result", "please", "and", "plus", "minus",
        "times", "divided", "by", "sum", "value", "it",
    }
    other_words = [w for w in re.findall(r"[a-zA-Z]{2,}", text.lower()) if w not in _MATH_PHRASE_WORDS]

    cleaned = text.replace("^", "**")
    cleaned = re.sub(r"[^0-9+\-*/().\s]", "", cleaned)
    if (
        not other_words
        and cleaned.strip()
        and re.search(r"[0-9]", cleaned)
        and re.search(r"[+\-*/]", cleaned)
    ):
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
        return f"{v}\u00b0C is **{(v*9/5)+32:.1f}\u00b0F**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(f|fahrenheit)\b.*\b(c|celsius)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v}\u00b0F is **{(v-32)*5/9:.1f}\u00b0C**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*cm\b.*\b(inch|inches|in)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} cm is about **{v/2.54:.2f} inches**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(inch|inches|in)\b.*\bcm\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} inches is about **{v*2.54:.2f} cm**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(l|litres?|liters?)\b.*\bgallons?\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} litres is about **{v*0.264172:.2f} gallons** (US)."
    m = re.search(r"(-?\d+(\.\d+)?)\s*gallons?\b.*\b(l|litres?|liters?)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} gallons (US) is about **{v*3.78541:.2f} litres**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*km\s*/?\s*h(r|our)?\b.*\bmph\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} km/h is about **{v*0.621371:.2f} mph**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*mph\b.*\bkm\s*/?\s*h(r|our)?\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} mph is about **{v*1.60934:.2f} km/h**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(sq\s*km|square\s*kilomet(re|er)s?)\b.*\b(sq\s*miles?|square\s*miles?)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} square kilometres is about **{v*0.386102:.2f} square miles**."
    m = re.search(r"(-?\d+(\.\d+)?)\s*(sq\s*miles?|square\s*miles?)\b.*\b(sq\s*km|square\s*kilomet(re|er)s?)\b", lower)
    if m:
        v = float(m.group(1))
        return f"{v} square miles is about **{v*2.58999:.2f} square kilometres**."
    return None


def try_number_ops(text: str):
    """Small standalone number utilities: factorial, primality, gcd/lcm, and
    base conversion. Kept separate from try_math so try_math's generic
    expression evaluator doesn't have to guess at these special forms."""
    lower = text.lower().strip()

    m = re.search(r"factorial\s*of\s*(\d+)|(\d+)\s*!", lower)
    if m:
        n = int(m.group(1) or m.group(2))
        if 0 <= n <= 170:
            return f"{n}! (factorial) is **{math.factorial(n)}**."
        return "That number is too large to compute a factorial for here."

    m = re.search(r"is\s+(\d+)\s+(a\s+)?prime", lower)
    if m:
        n = int(m.group(1))
        if n < 2:
            is_prime = False
        else:
            is_prime = all(n % d != 0 for d in range(2, int(n**0.5) + 1))
        return f"**{n}** is {'a prime number' if is_prime else 'not a prime number'}."

    m = re.search(r"gcd\s*(of)?\s*(\d+)\D+(\d+)|greatest common (divisor|factor)\s*(of)?\s*(\d+)\D+(\d+)", lower)
    if m:
        nums = [g for g in m.groups() if g and g.isdigit()]
        if len(nums) >= 2:
            a, b = int(nums[0]), int(nums[1])
            return f"The GCD of {a} and {b} is **{math.gcd(a, b)}**."

    m = re.search(r"lcm\s*(of)?\s*(\d+)\D+(\d+)|least common multiple\s*(of)?\s*(\d+)\D+(\d+)", lower)
    if m:
        nums = [g for g in m.groups() if g and g.isdigit()]
        if len(nums) >= 2:
            a, b = int(nums[0]), int(nums[1])
            return f"The LCM of {a} and {b} is **{math.lcm(a, b)}**."

    m = re.search(r"(\d+)\s*to\s*binary|binary\s*(of|for)\s*(\d+)", lower)
    if m:
        n = int(m.group(1) or m.group(3))
        return f"{n} in binary is **{bin(n)[2:]}**."
    m = re.search(r"(\d+)\s*to\s*hex(adecimal)?|hex(adecimal)?\s*(of|for)\s*(\d+)", lower)
    if m:
        n = int(m.group(1) or m.group(5))
        return f"{n} in hexadecimal is **{hex(n)[2:].upper()}**."
    m = re.search(r"0b([01]+)\b|\bbinary\s+([01]+)\b|\b([01]+)\s+(?:in\s+)?binary\b", lower)
    if m and re.search(r"\bdecimal\b", lower):
        bits = next(g for g in m.groups() if g)
        return f"Binary {bits} is **{int(bits, 2)}** in decimal."

    m = re.search(r"(?P<op>average|mean|median|min(?:imum)?|max(?:imum)?)\s*of\s*(?P<nums>[\d,.\s]+)", lower)
    if m:
        op = m.group("op")
        nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", m.group("nums"))]
        if nums:
            display = ", ".join(f"{n:g}" for n in nums)
            if op in ("average", "mean"):
                return f"The average of [{display}] is **{sum(nums)/len(nums):.4g}**."
            if op == "median":
                s = sorted(nums)
                mid = len(s) // 2
                med = s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
                return f"The median of [{display}] is **{med:.4g}**."
            if op.startswith("min"):
                return f"The minimum of [{display}] is **{min(nums):g}**."
            if op.startswith("max"):
                return f"The maximum of [{display}] is **{max(nums):g}**."
    return None

def try_translate(text: str):
    lower = text.lower().strip()
    for k, v in DICT.items():
        if lower == k.lower():
            return f"**{k}** \u2192 {v}"
    return None

def _clip(text: str, limit: int) -> str:
    """Like _truncate_at_boundary, but only ever adds an ellipsis when text was
    actually cut -- summarize_messages used to append '\u2026' even to a two-word
    message, which falsely implied something had been trimmed off."""
    text = text.strip()
    if len(text) <= limit:
        return text
    trimmed = _truncate_at_boundary(text, limit)
    if trimmed.endswith(("\u2026", ".", "?", "!")):
        return trimmed
    return trimmed + "\u2026"

def summarize_messages(messages: list[dict]) -> str:
    user_msgs = [m["content"].strip() for m in messages if m["role"] == "user" and m["content"].strip()]
    if not user_msgs:
        return "Nothing to summarize yet."
    if len(user_msgs) == 1:
        return f'This conversation covered one request: "{_clip(user_msgs[0], 80)}"'
    first, last = _clip(user_msgs[0], 60), _clip(user_msgs[-1], 60)
    return f'This conversation covered {len(user_msgs)} requests, starting with "{first}" and most recently "{last}".'

def key_points(messages: list[dict]) -> str:
    """Surfaces the substance of the conversation -- what was asked and the core
    of what was answered -- rather than just echoing the questions back, which
    isn't really a set of "key points" so much as a list of things already
    visible in the chat above."""
    points = []
    seen = set()
    for i in range(len(messages) - 1):
        if messages[i]["role"] != "user" or messages[i + 1]["role"] != "assistant":
            continue
        q = messages[i]["content"].strip()
        a = messages[i + 1]["content"].strip()
        if not q or not a or a.startswith("I don't have that"):
            continue
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        points.append(f"\u2022 {_clip(q, 70)} - {_clip(a, 110)}")
        if len(points) >= 8:
            break
    if not points:
        return "Not enough back-and-forth yet to pull out key points."
    return "\n".join(points)

def translate_words(text: str) -> str:
    words = text.split()
    out = []
    for w in words:
        clean = "".join(ch for ch in w if ch.isalnum() or ("\u0600" <= ch <= "\u06FF"))
        out.append(DICT.get(clean.lower(), DICT.get(clean, w)))
    return " ".join(out)

def _truncate_at_boundary(text: str, limit: int) -> str:
    """Truncate to at most `limit` characters, preferring to cut at the end of a
    sentence, then a word boundary, rather than slicing mid-word -- so generated
    flashcards read as complete thoughts instead of chopped-off fragments."""
    if len(text) <= limit:
        return text
    window = text[:limit]
    for stop in (". ", "? ", "! "):
        idx = window.rfind(stop)
        if idx > limit * 0.4:
            return window[: idx + 1].strip()
    idx = window.rfind(" ")
    if idx > limit * 0.4:
        return window[:idx].strip() + "\u2026"
    return window.strip() + "\u2026"

def flashcards_from_messages(messages: list[dict]) -> list[dict]:
    cards = []
    for i in range(len(messages) - 1):
        if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
            q, a = messages[i]["content"].strip(), messages[i + 1]["content"].strip()
            if len(q) > 2 and len(a) > 2 and not a.startswith("I don't have that"):
                cards.append({
                    "front": _truncate_at_boundary(q, 140),
                    "back": _truncate_at_boundary(a, 280),
                })
    return cards

def knowledge_base_stats() -> dict:
    return {"dictWords": len(DICT), "kbEntries": len(KB), "learnedEntries": len(_load_learned())}

_GREETING_RE = re.compile(r"^(hi|hello|hey|salam|assalam)", re.I)
_BYE_RE = re.compile(r"^(bye|goodbye|see you|khuda hafiz)", re.I)
# Deliberately an exact-phrase allowlist, not a substring or loose regex match:
# earlier versions matched the bare substrings "time" and "date" anywhere in the
# message (so "what is time complexity" and "what is a candidate" were hijacked
# into the clock/calendar response), and a follow-up regex attempt still matched
# "what is time complexity" as a prefix. Checking against a closed set of full
# phrasings, after stripping trailing punctuation, has no such collision risk.
_TIME_QUERY_PHRASES = {
    "what time is it", "what's the time", "whats the time", "what is the time",
    "current time", "tell me the time", "do you know the time",
}
_DATE_QUERY_PHRASES = {
    "what is the date", "what's the date", "whats the date", "current date",
    "what day is it", "what is today", "what's today", "today's date",
    "todays date", "what is today's date", "what date is it",
}

def _is_time_query(lower: str) -> bool:
    return lower.strip().rstrip("?!.") in _TIME_QUERY_PHRASES

def _is_date_query(lower: str) -> bool:
    return lower.strip().rstrip("?!.") in _DATE_QUERY_PHRASES

def try_confident_reply(text: str):
    """Runs only the deterministic, guaranteed-correct handlers -- arithmetic,
    unit conversions, number utilities, translation, greetings/farewells/thanks,
    exact or fuzzy knowledge-base hits, and time/date -- and returns an answer
    only when one of them actually matched. Returns None otherwise, without ever
    generating the generic "I don't have that" filler.

    This lets a caller that has a real language model available (whether a
    server-side one in app.py, or one running entirely client-side in the
    browser) use that instead of the rule-based fallback for genuinely
    open-ended questions, while still always trusting this deterministic path
    for the categories it's actually built to get right every time.
    """
    last = (text or "").strip()
    lower = last.lower()
    urdu = is_urdu(last)

    conv = try_convert(last)
    if conv:
        return conv
    nums = try_number_ops(last)
    if nums:
        return nums
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

    learned = learned_lookup(last)
    if learned:
        return learned
    kb_hit = knowledge_base_lookup(last)
    if kb_hit:
        return kb_hit

    if _is_time_query(lower):
        return "It's currently " + time.strftime("%I:%M %p") + " on the server."
    if _is_date_query(lower):
        return "Today is " + time.strftime("%A, %B %d, %Y") + "."
    return None


def offline_reply(messages: list[dict]) -> str:
    """Guaranteed-to-answer offline entry point: tries every deterministic
    handler via try_confident_reply first, and only ever falls back to a
    generic "I don't know" message -- honest about the offline engine's
    limits and pointing at Settings -- when truly nothing matched."""
    last_msg = messages[-1]
    last = last_msg.get("content", "").strip()
    urdu = is_urdu(last)

    confident = try_confident_reply(last)
    if confident:
        return confident

    generic_en = [
        "I don't have that in my offline knowledge base yet -- I can handle arithmetic, unit conversions, "
        "common English/Urdu words, a range of general-knowledge questions, small code snippets, and study tips. "
        "Open-ended questions like this are handled automatically by a real AI model once one is ready -- either "
        "the standalone in-browser model (no install needed) or a local/Ollama model -- check Settings to see status.",
        "That one's outside my offline knowledge base. Try a math expression, a conversion (like '10 km to miles'), "
        "a common word to translate, or check Settings -- a real AI model (in-browser, or local via Ollama) handles "
        "open-ended questions like this automatically once it's ready.",
    ]
    generic_ur = [
        "یہ سوال میرے آف لائن ڈیٹا بیس میں شامل نہیں ہے -- میں حساب کتاب، پیمائش کی تبدیلی، عام الفاظ کا ترجمہ، "
        "اور کچھ عمومی معلومات دے سکتا ہوں۔ اس طرح کے کھلے سوالات ایک حقیقی AI ماڈل کے تیار ہوتے ہی خودکار طور پر "
        "جواب دیے جاتے ہیں -- سیٹنگز میں اس کی صورتحال دیکھیں۔",
        "معذرت، یہ میری معلومات میں شامل نہیں۔ کوئی حساب، پیمائش، یا لفظ آزمائیں، یا سیٹنگز میں دیکھیں کہ کوئی حقیقی "
        "AI ماڈل تیار ہے یا نہیں -- تیار ہوتے ہی یہ خود بخود ایسے سوالات کے جواب دے سکتا ہے۔",
    ]
    import random
    return random.choice(generic_ur if urdu else generic_en)
