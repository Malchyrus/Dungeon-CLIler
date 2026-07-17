DIRECTION_VECTORS = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
}

WASD_MAP = {
    "w": "north",
    "a": "west",
    "s": "south",
    "d": "east",
}

LEGACY_SHORTCUTS = {
    "n": "north",
    "e": "east",
}

KEY_MAP = {
    "north": "W",
    "south": "S",
    "east": "D",
    "west": "A",
}

ALL_MOVEMENT_KEYS = set(WASD_MAP) | set(LEGACY_SHORTCUTS) | set(DIRECTION_VECTORS)

OPPOSITE = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}
