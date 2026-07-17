import random
from data_loader import load_json
from status import add_status


ASCENSION_MODS = {
    0: {"enemy_hp_mult": 1.0, "enemy_atk_mult": 1.0},
    1: {"enemy_hp_mult": 1.15, "enemy_atk_mult": 1.15},
    2: {"enemy_hp_mult": 1.3, "enemy_atk_mult": 1.3},
}


def _deep_copy_template(template):
    t = dict(template)
    if "abilities" in t:
        t["abilities"] = dict(t["abilities"])
    if "loot_table" in t:
        t["loot_table"] = list(t["loot_table"])
    return t


def _apply_scaling(template, ascension, floor_scaling=1.0):
    mod = ASCENSION_MODS.get(ascension, ASCENSION_MODS[0])
    template["hp"] = int(template["hp"] * floor_scaling * mod["enemy_hp_mult"])
    template["max_hp"] = template["hp"]
    template["atk"] = int(template["atk"] * floor_scaling * mod["enemy_atk_mult"])
    if floor_scaling != 1.0:
        template["def"] = int(template.get("def", 0) * floor_scaling)
    template.setdefault("speed", 10)
    template.setdefault("accuracy", 100)
    template.setdefault("crit", 0.0)
    template["statuses"] = []
    return template


def _spawn_from_pool(pool, ascension=0, floor_scaling=1.0):
    if not pool:
        return None
    key = random.choice(list(pool.keys()))
    template = _deep_copy_template(pool[key])
    template["key"] = key
    return _apply_scaling(template, ascension, floor_scaling)


def _get_floor_enemies(floor, exclude_boss=False, variant=None):
    data = load_json("enemies.json")
    floor_key = f"floor_{min(floor, 5)}"
    floor_data = data.get(floor_key, {})
    if not floor_data:
        floor_data = data.get("floor_1", {})

    if variant and variant in floor_data:
        enemies = floor_data[variant]
    elif "standard" in floor_data:
        enemies = floor_data["standard"]
    else:
        enemies = floor_data

    if exclude_boss:
        enemies = {k: v for k, v in enemies.items() if not v.get("boss")}
        if not enemies:
            enemies = data.get("floor_1", {})
    return enemies


def _get_floor_bosses(floor):
    data = load_json("enemies.json")
    floor_key = f"floor_{min(floor, 5)}"
    enemies = data.get(floor_key, {})
    return {k: v for k, v in enemies.items() if v.get("boss")}


def _get_gatekeeper(floor):
    data = load_json("enemies.json")
    floor_key = f"floor_{min(floor, 5)}"
    enemies = data.get(floor_key, {})
    gatekeepers = {k: v for k, v in enemies.items() if v.get("gatekeeper")}
    if gatekeepers:
        return gatekeepers
    return {k: v for k, v in enemies.items() if v.get("boss")}


def spawn_gatekeeper(floor, ascension=0):
    pool = _get_gatekeeper(floor)
    if not pool:
        return spawn_boss(floor, ascension)
    return _spawn_from_pool(pool, ascension=ascension)


def _get_bonus_enemies(boss=False):
    data = load_json("enemies.json")
    pool = data.get("floor_2_5", {})
    if boss:
        return {k: v for k, v in pool.items() if v.get("boss")}
    return {k: v for k, v in pool.items() if not v.get("boss")}


def get_enemy(floor, exclude_boss=False):
    pool = _get_floor_enemies(floor, exclude_boss)
    return _spawn_from_pool(pool, ascension=0, floor_scaling=1.0)


def spawn_enemy(floor, ascension=0, variant=None):
    pool = _get_floor_enemies(floor, exclude_boss=True, variant=variant)
    scaling = 1 + (floor - 1) * 0.1
    return _spawn_from_pool(pool, ascension=ascension, floor_scaling=scaling)


def spawn_boss(floor, ascension=0):
    pool = _get_floor_bosses(floor)
    if not pool:
        return spawn_enemy(floor, ascension)
    return _spawn_from_pool(pool, ascension=ascension)


def spawn_bonus_enemy(ascension=0):
    pool = _get_bonus_enemies(boss=False)
    if not pool:
        return spawn_enemy(3, ascension)
    return _spawn_from_pool(pool, ascension=ascension)


def spawn_bonus_boss(ascension=0):
    pool = _get_bonus_enemies(boss=True)
    if not pool:
        return spawn_bonus_enemy(ascension)
    return _spawn_from_pool(pool, ascension=ascension)


def _ability_damage(abil, enemy, messages, player_statuses):
    val = abil.get("value", 3)
    scale = abil.get("dmg_scale", 0)
    if scale > 0:
        val = val + int(enemy.get("atk", 0) * scale)
    return {"hp_damage": val}


def _ability_heal(abil, enemy, messages, player_statuses):
    heal_amount = abil.get("value", 10)
    scale = abil.get("heal_scale", 0)
    if scale > 0:
        heal_amount = heal_amount + int(enemy.get("atk", 0) * scale)
    enemy["hp"] = min(enemy["hp"] + heal_amount, enemy.get("max_hp", enemy["hp"]))
    messages.append(f"The {enemy['name']} heals for {heal_amount} HP!")
    return None


def _ability_drain(abil, enemy, messages, player_statuses):
    drain_amount = abil.get("value", 5)
    scale = abil.get("dmg_scale", 0)
    if scale > 0:
        drain_amount = drain_amount + int(enemy.get("atk", 0) * scale)
    heal_amount = drain_amount // 2
    enemy["hp"] = min(enemy["hp"] + heal_amount, enemy.get("max_hp", enemy["hp"]))
    messages.append(f"The {enemy['name']} drains {heal_amount} HP!")
    return {"hp_damage": drain_amount}


def _ability_stun(abil, enemy, messages, player_statuses):
    dur = abil.get("duration", 1)
    add_status(player_statuses, "stunned", dur)
    messages.append("You are stunned!")
    val = abil.get("value", 0)
    if val > 0:
        scale = abil.get("dmg_scale", 0)
        if scale > 0:
            val = val + int(enemy.get("atk", 0) * scale)
        messages.append(f"You take {val} damage!")
        return {"hp_damage": val}
    return None


def _ability_dot(abil, enemy, messages, player_statuses):
    val = abil.get("value", 2)
    dur = abil.get("duration", 3)
    add_status(player_statuses, "burn", dur, val)
    messages.append("You are burning!")
    return None


def _ability_debuff(abil, enemy, messages, player_statuses):
    eff = abil.get("effect", "atk_down")
    val = abil.get("value", 1)
    dur = abil.get("duration", 2)
    scale = abil.get("debuff_scale", 0)
    if scale > 0:
        val = val + int(enemy.get("atk", 0) * scale)
    add_status(player_statuses, eff, dur, val)
    if eff == "atk_down":
        messages.append("Your attack is reduced!")
    elif eff == "dodge_down":
        messages.append("Your dodge is reduced!")
    elif eff == "speed_down":
        messages.append("You feel slowed!")
    elif eff == "def_down":
        messages.append("Your defense is exposed!")
    elif eff == "accuracy_down":
        messages.append("Your aim falters!")
    return None


def _ability_buff(abil, enemy, messages, player_statuses):
    val = abil.get("value", 2)
    scale = abil.get("debuff_scale", 0)
    if scale > 0:
        val = val + int(enemy.get("atk", 0) * scale)
    stat = abil.get("stat", "atk")
    if stat == "def":
        enemy["def"] = enemy.get("def", 0) + val
        messages.append(f"The {enemy['name']}'s defense increases by {val}!")
    else:
        enemy["atk"] = enemy.get("atk", 0) + val
        messages.append(f"The {enemy['name']}'s attack increases by {val}!")
    return None


def _ability_armor_pierce(abil, enemy, messages, player_statuses):
    ratio = abil.get("value", 0.5)
    raw = enemy.get("atk", 5) + random.randint(0, 3)
    scale = abil.get("dmg_scale", 0)
    if scale > 0:
        raw = raw + int(enemy.get("atk", 0) * scale)
    return {"armor_pierce": raw, "pierce_ratio": ratio}


def _ability_multi(abil, enemy, messages, player_statuses):
    val = abil.get("value", 8)
    scale = abil.get("dmg_scale", 0)
    if scale > 0:
        val = val + int(enemy.get("atk", 0) * scale)
    messages.append(f"You take {val} damage!")
    result = {"hp_damage": val}
    sec = abil.get("secondary")
    if sec and sec.get("type") == "dot":
        sec_val = sec.get("value", 2)
        sec_dur = sec.get("duration", 3)
        add_status(player_statuses, "burn", sec_dur, sec_val)
        messages.append(sec.get("message", "The flames continue to burn!"))
    return result


def _ability_reflect(abil, enemy, messages, player_statuses):
    val = abil.get("value", 20)
    dur = abil.get("duration", 3)
    add_status(player_statuses, "reflect", dur, val)
    messages.append(f"The {enemy['name']} raises a reflective shield!")
    return None


ENEMY_ABILITY_HANDLERS = {
    "damage": _ability_damage,
    "heal": _ability_heal,
    "drain": _ability_drain,
    "stun": _ability_stun,
    "dot": _ability_dot,
    "debuff": _ability_debuff,
    "buff": _ability_buff,
    "armor_pierce": _ability_armor_pierce,
    "multi": _ability_multi,
    "reflect": _ability_reflect,
}


def get_enemy_ability_messages(enemy, player_statuses, force_key=None):
    messages = []
    extra_damage = 0
    armor_pierce_data = None

    abilities = enemy.get("abilities", {})
    hp_ratio = enemy["hp"] / enemy.get("max_hp", enemy["hp"]) if enemy.get("max_hp", enemy["hp"]) > 0 else 1

    if force_key and force_key in abilities:
        abil = abilities[force_key]
        abil_type = abil.get("type", "damage")
        messages.append(abil.get("message", f"The {enemy['name']} uses {abil.get('name', 'a skill')}!"))
        handler = ENEMY_ABILITY_HANDLERS.get(abil_type)
        if handler:
            result = handler(abil, enemy, messages, player_statuses)
            if result:
                if "hp_damage" in result:
                    extra_damage += result["hp_damage"]
                if "armor_pierce" in result:
                    armor_pierce_data = result
        return messages, extra_damage, armor_pierce_data

    for abil_key, abil in abilities.items():
        chance = abil.get("chance", 0.3)
        threshold = abil.get("threshold", 0.0)
        if hp_ratio > threshold and threshold > 0:
            continue
        if random.random() < chance:
            abil_type = abil.get("type", "damage")
            messages.append(abil.get("message", f"The {enemy['name']} uses {abil.get('name', 'a skill')}!"))
            handler = ENEMY_ABILITY_HANDLERS.get(abil_type)
            if handler:
                result = handler(abil, enemy, messages, player_statuses)
                if result:
                    if "hp_damage" in result:
                        extra_damage += result["hp_damage"]
                    if "armor_pierce" in result:
                        armor_pierce_data = result
            break

    return messages, extra_damage, armor_pierce_data


def get_loot(enemy, floor=1):
    loot = []
    gold = enemy.get("gold", 0) + random.randint(-2, 5)
    if gold > 0:
        loot.append({"name": "Gold", "type": "gold", "value": gold})

    for drop in enemy.get("loot_table", []):
        if random.random() < drop["chance"]:
            from items import get_item
            item = get_item(drop["item"])
            if item:
                loot.append(dict(item))

    from constants import LOOT_BAG_DROP_CHANCE, KEY_DROP_CHANCE
    if random.random() < LOOT_BAG_DROP_CHANCE:
        from items import random_loot_bag
        bag = random_loot_bag(floor)
        if bag:
            loot.append(bag)

    if random.random() < KEY_DROP_CHANCE:
        from items import get_item
        key = get_item("chest_key")
        if key:
            loot.append(dict(key))

    return loot
