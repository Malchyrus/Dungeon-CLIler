import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_cache = {}


def load_json(filename):
    if filename not in _cache:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]


def clear_cache():
    _cache.clear()
