STATUS_DEFS = {
    "stunned": {"name": "Stunned", "category": "debuff"},
    "poison": {"name": "Poisoned", "category": "debuff", "is_dot": True},
    "burn": {"name": "Burning", "category": "debuff", "is_dot": True},
    "blinded": {"name": "Blinded", "category": "debuff"},
    "atk_down": {"name": "Weakened", "category": "debuff", "stat": "ATK", "invert": True},
    "dodge_down": {"name": "Slowed", "category": "debuff", "stat": "Dodge", "invert": True},
    "def_down": {"name": "Exposed", "category": "debuff", "stat": "DEF", "invert": True},
    "atk_up": {"name": "Empowered", "category": "buff", "stat": "ATK"},
    "def_up": {"name": "Iron Skin", "category": "buff", "stat": "DEF"},
    "dodge_up": {"name": "Evasion", "category": "buff", "stat": "Dodge"},
    "speed_up": {"name": "Haste", "category": "buff", "stat": "SPD"},
    "speed_down": {"name": "Hampered", "category": "debuff", "stat": "SPD", "invert": True},
    "double_damage": {"name": "Double Strike", "category": "buff"},
    "reflect": {"name": "Reflect", "category": "buff"},
    "regen": {"name": "Regen", "category": "buff", "is_hot": True},
    "shield": {"name": "Shielded", "category": "buff"},
    "mana_shield": {"name": "Mana Shield", "category": "buff"},
    "divine_shield": {"name": "Divine Shield", "category": "buff"},
    "accuracy_up": {"name": "Focused", "category": "buff", "stat": "ACC"},
    "accuracy_down": {"name": "Disoriented", "category": "debuff", "stat": "ACC", "invert": True},
    "ele_resist_fire": {"name": "Fire Resist", "category": "buff"},
    "ele_resist_ice": {"name": "Ice Resist", "category": "buff"},
    "ele_resist_lightning": {"name": "Lightning Resist", "category": "buff"},
}


def add_status(statuses, status_id, turns, value=0):
    existing = get_status(statuses, status_id)
    if existing:
        existing["turns"] += turns
        if value > 0:
            existing["value"] = max(existing.get("value", 0), value)
        return existing
    entry = {"id": status_id, "turns": turns, "value": value, "_fresh": True}
    statuses.append(entry)
    return entry


def remove_status(statuses, status_id):
    for i, s in enumerate(statuses):
        if s["id"] == status_id:
            statuses.pop(i)
            return True
    return False


def has_status(statuses, status_id):
    return any(s["id"] == status_id for s in statuses)


def get_status(statuses, status_id):
    for s in statuses:
        if s["id"] == status_id:
            return s
    return None


def tick_statuses(statuses):
    messages = []
    to_remove = []

    for s in statuses:
        if s.get("_fresh"):
            s["_fresh"] = False
            continue

        s["turns"] -= 1
        if s["turns"] <= 0:
            to_remove.append(s["id"])

    for sid in to_remove:
        remove_status(statuses, sid)
        defn = STATUS_DEFS.get(sid, {})
        name = defn.get("name", sid)
        messages.append(f"{name} faded.")

    return messages


def tick_dots(statuses):
    messages = []
    for s in statuses:
        sid = s["id"]
        val = s.get("value", 0)
        if sid == "poison" and val > 0:
            messages.append(f"poison:{val}")
        elif sid == "burn" and val > 0:
            messages.append(f"burn:{val}")
        elif sid == "regen" and val > 0:
            messages.append(f"regen:{val}")
    return messages


def apply_dot_damage(entity_hp_func, entity_set_hp_func, statuses):
    messages = []
    for s in list(statuses):
        sid = s["id"]
        val = s.get("value", 0)
        if sid == "poison" and val > 0:
            entity_set_hp_func(max(0, entity_hp_func() - val))
            messages.append(f"Poison deals {val} damage!")
        elif sid == "burn" and val > 0:
            entity_set_hp_func(max(0, entity_hp_func() - val))
            messages.append(f"Fire burns you for {val} damage!")
        elif sid == "regen" and val > 0:
            messages.append(f"regen:{val}")
    return messages


def format_statuses(statuses):
    if not statuses:
        return ""
    parts = []
    for s in statuses:
        sid = s["id"]
        turns = s["turns"]
        val = s.get("value", 0)
        defn = STATUS_DEFS.get(sid, {})
        name = defn.get("name", sid)
        stat = defn.get("stat")
        invert = defn.get("invert", False)
        if val > 0 and sid in ("poison", "burn"):
            parts.append(f"{name}({turns}t,{val}d)")
        elif val > 0 and sid in ("shield", "mana_shield"):
            parts.append(f"{name}({val}HP,{turns}t)")
        elif val > 0 and sid in ("regen",):
            parts.append(f"{name}({val}/t,{turns}t)")
        elif stat and val > 0:
            sign = "-" if invert else "+"
            parts.append(f"{stat}{sign}{val}({turns}t)")
        elif sid in ("ele_resist_fire", "ele_resist_ice", "ele_resist_lightning"):
            parts.append(f"{name}({val}%,{turns}t)")
        else:
            parts.append(f"{name}({turns}t)")
    return " ".join(parts)


def clear_all(statuses):
    statuses.clear()


def calc_dr(armor, enemy_level):
    from constants import ARMOR_DR_K, ARMOR_DR_CAP
    if armor <= 0 or enemy_level <= 0:
        return 0.0
    dr = armor / (armor + ARMOR_DR_K * enemy_level)
    return min(ARMOR_DR_CAP, dr)
