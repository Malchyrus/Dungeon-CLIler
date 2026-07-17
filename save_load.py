import json
import os
import tempfile

SAVE_DIR = os.path.join(os.path.dirname(__file__), "saves")
SCHEMA_VERSION = 1


def _filepath(filename="save.json"):
    return os.path.join(SAVE_DIR, filename)


def ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def save_game(player, rooms, ascension=0, lore_entries=None, filename="save.json"):
    ensure_save_dir()
    path = _filepath(filename)
    data = {
        "schema_version": SCHEMA_VERSION,
        "player": player.to_dict(),
        "rooms": {f"{k[0]},{k[1]}": v.to_dict() for k, v in rooms.items()},
        "ascension": ascension,
        "lore_entries": lore_entries or [],
    }
    fd, tmp_path = tempfile.mkstemp(dir=SAVE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return path


def load_game(filename="save.json"):
    path = _filepath(filename)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    from player import Player
    from room import Room

    player = Player.from_dict(data["player"])

    rooms = {}
    for key_str, room_data in data["rooms"].items():
        x, y = map(int, key_str.split(","))
        rooms[(x, y)] = Room.from_dict(room_data)

    ascension = data.get("ascension", 0)
    lore_entries = data.get("lore_entries", [])

    return player, rooms, ascension, lore_entries


def delete_save(filename="save.json"):
    path = _filepath(filename)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def has_save(filename="save.json"):
    return os.path.exists(_filepath(filename))
