#!/usr/bin/env python3
"""
Reverso Context example fetcher (unofficial endpoint).

Hits the internal bst-query-service used by context.reverso.net. Undocumented and
Cloudflare-fronted, so it is best-effort: callers should fall back to an LLM when
this returns None.
"""

import re
import requests

URL = "https://context.reverso.net/bst-query-service"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:77.0) "
                   "Gecko/20100101 Firefox/77.0"),
    "Origin": "https://context.reverso.net",
    "Accept-Language": "en-US,en;q=0.5",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json",
}

_ISO = {
    "chinese": "zh", "french": "fr", "english": "en", "spanish": "es",
    "german": "de", "italian": "it", "portuguese": "pt", "russian": "ru",
    "japanese": "ja", "korean": "ko", "arabic": "ar", "dutch": "nl",
}


def _iso(lang):
    lang = (lang or "").lower()
    return _ISO.get(lang, lang[:2])


def _strip_em(s):
    return re.sub(r"</?em>", "", s or "")


def _clean(s):
    s = _strip_em(s)
    s = re.sub(r"\s+([\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])", r"\1", s)
    s = re.sub(r"([\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])\s+", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm(s):
    s = _strip_em(s).lower()
    s = re.sub(r"[^0-9a-z\u00c0-\u024f\u4e00-\u9fff]+", " ", s)
    return " ".join(s.split())


def _measure(s):
    s = _strip_em(s or "")
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]", s))
    latin = len(re.findall(r"[A-Za-z\u00c0-\u024f']+", s))
    return cjk, latin


def _outside(raw):
    return " ".join(re.split(r"</?em>", raw or "")[0::2])


def _is_usable(example, raw):
    if not example or "..." in example or "\u2026" in example:
        return False
    cjk, latin = _measure(example)
    n = cjk if cjk >= 5 else latin
    if n < 5 or n > 32:
        return False
    oc, ol = _measure(_outside(raw))
    o = oc if cjk >= 5 else ol
    return o >= 3


def fetch(src, tgt, text):
    r = requests.post(URL, headers=HEADERS, json={
        "source_lang": src, "target_lang": tgt, "mode": 0,
        "npage": 1, "source_text": text, "target_text": ""}, timeout=25)
    r.raise_for_status()
    return r.json()


def best_example(learn_lang, input_lang, text):
    """Return {'example', 'translation', 'senses'} in the learning language, or None."""
    learn = _iso(learn_lang)
    given = _iso(input_lang or learn_lang)
    if given == learn:
        src, tgt, side = learn, "en", "s"
    else:
        src, tgt, side = given, learn, "t"

    try:
        data = fetch(src, tgt, text)
    except Exception:
        return None

    senses = [e.get("term", "") for e in data.get("dictionary_entry_list", []) if e.get("term")]
    nt = _norm(text)
    best = None
    for e in data.get("list", []):
        s_raw, t_raw = e.get("s_text", ""), e.get("t_text", "")
        chosen = s_raw if side == "s" else t_raw
        other = t_raw if side == "s" else s_raw
        example = _clean(chosen)
        if not _is_usable(example, chosen):
            continue
        exact = nt in _norm(s_raw) or nt in _norm(t_raw)
        cjk, latin = _measure(example)
        n = cjk if cjk >= 5 else latin
        oc, ol = _measure(_outside(chosen))
        o = oc if cjk >= 5 else ol
        score = (4 if exact else 0) + (1 if "<em>" in chosen else 0) + min(o, 10) * 0.3 - abs(n - 14) * 0.1
        if best is None or score > best[0]:
            best = (score, {"example": example, "translation": _clean(other),
                            "senses": senses, "src": src, "tgt": tgt})
    return best[1] if best else None


if __name__ == "__main__":
    import sys, json
    print(json.dumps(best_example(sys.argv[1], sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=2))
