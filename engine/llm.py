"""Gemini client with automatic multi-key and multi-model fallback on quota errors."""
import json
import re
import time

import requests

from . import config

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Tracks (key_index, model) pairs that hit 429 during the current process run
_EXHAUSTED = set()
_CALL_COUNT = 0


class QuotaExhausted(Exception):
    pass


class ModelOverloaded(Exception):
    pass


def _call(api_key, model, prompt, temperature, json_mode):
    gen = {"temperature": temperature}
    if json_mode:
        gen["responseMimeType"] = "application/json"
    resp = requests.post(
        API.format(model=model),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": gen},
        timeout=90,
    )
    if resp.status_code in (429, 400, 403):
        raise QuotaExhausted(f"{model} ({resp.status_code})")
    if resp.status_code in (503, 502, 404):
        raise ModelOverloaded(f"{model} ({resp.status_code})")
    resp.raise_for_status()
    data = resp.json()
    parts = data["candidates"][0]["content"].get("parts", [])
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def generate(prompt, models, temperature=0.4, json_mode=False):
    """Return (text, model_used). Load-balances and rotates across all configured API keys and models."""
    global _CALL_COUNT
    keys = config.GEMINI_API_KEYS or ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
    if not keys:
        raise RuntimeError("No GEMINI_API_KEY configured in .env")
    start_key = _CALL_COUNT % len(keys)
    _CALL_COUNT += 1
    ordered_keys = [((start_key + i) % len(keys), keys[(start_key + i) % len(keys)]) for i in range(len(keys))]
    last_error = None
    for model in models:
        for key_idx, api_key in ordered_keys:
            if (key_idx, model) in _EXHAUSTED:
                continue
            try:
                text = _call(api_key, model, prompt, temperature, json_mode)
                label = f"{model}" if len(keys) == 1 else f"{model}[k{key_idx + 1}]"
                return text, label
            except QuotaExhausted as e:
                last_error = e
                _EXHAUSTED.add((key_idx, model))
                continue  # try the next key on this model immediately
            except ModelOverloaded as e:
                last_error = e
                break  # this model is overloaded globally right now; jump to the next model immediately
            except (requests.RequestException, KeyError, IndexError) as e:
                last_error = e
                break
    raise RuntimeError(f"All keys and models failed: {last_error}")


def generate_json(prompt, models, temperature=0.3):
    text, model = generate(prompt, models, temperature, json_mode=True)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    # strict=False accepts raw newlines/tabs inside strings, which models sometimes emit
    return json.loads(text, strict=False), model
