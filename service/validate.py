"""Output validation against schema.json (no heavy dependencies, easy to unit-test)."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.environ.get("SCHEMA_PATH", ""),
    os.path.join(_HERE, "schema.json"),
    os.path.join(_HERE, "..", "data", "schema.json"),
]


def load_schema():
    for path in _CANDIDATES:
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("schema.json not found")


SCHEMA = load_schema()
KEYS = set(SCHEMA["keys"])
INTENTS = set(SCHEMA["intents"])
SLOTS = ("date", "time", "place")


def is_valid(obj):
    """True only if obj is a dict with exactly the schema keys, a known intent, and string-or-null slots."""
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS:
        return False
    if obj["intent"] not in INTENTS:
        return False
    return all(obj[s] is None or isinstance(obj[s], str) for s in SLOTS)


def parse_output(raw):
    """Take the model's raw text, return the parsed dict if it is valid, else None."""
    lines = raw.strip().splitlines()
    text = lines[0].strip() if lines else ""
    try:
        obj = json.loads(text)
    except ValueError:
        return None
    return obj if is_valid(obj) else None
