import random
from data_loader import load_json


def get_random_npc(npc_type=None):
    data = load_json("npcs.json")

    if npc_type == "merchant":
        pool = list(data.get("merchants", {}).values())
    elif npc_type == "quest_giver":
        pool = list(data.get("quest_givers", {}).values())
    elif npc_type == "trapped":
        pool = list(data.get("trapped_npcs", {}).values())
    elif npc_type == "lore":
        pool = list(data.get("lore_npcs", {}).values())
    elif npc_type == "key_seller":
        pool = list(data.get("key_sellers", {}).values())
    elif npc_type == "healer":
        pool = list(data.get("healers", {}).values())
    elif npc_type == "item_trader":
        pool = list(data.get("item_traders", {}).values())
    elif npc_type == "key_trader":
        pool = list(data.get("key_traders", {}).values())
    elif npc_type == "map_seeker":
        pool = list(data.get("map_seekers", {}).values())
    else:
        pool = []
        for category in data.values():
            pool.extend(category.values())

    return dict(random.choice(pool)) if pool else None


def get_celdric_npc():
    data = load_json("npcs.json")
    celdric = data.get("key_sellers", {}).get("celdric")
    return dict(celdric) if celdric else None


def get_npc_dialogue(npc, dialogue_key="greeting"):
    return npc.get("dialogue", {}).get(dialogue_key, "...")


def get_shop_inventory(npc):
    items_data = load_json("items.json")
    all_items = {}
    for category in items_data.values():
        all_items.update(category)

    inventory = []
    for item_id in npc.get("inventory", []):
        if item_id in all_items:
            item = dict(all_items[item_id])
            item["id"] = item_id
            buy_mult = npc.get("buy_multiplier", 0.5)
            item["buy_price"] = max(1, int(item.get("value", 10) * buy_mult))
            inventory.append(item)
    return inventory


def get_sell_price(npc, item):
    sell_mult = npc.get("sell_multiplier", 0.3)
    return max(1, int(item.get("value", 10) * sell_mult))


def generate_merchant_inventory(npc, floor):
    items_data = load_json("items.json")
    consumables = items_data.get("consumables", {})
    buy_mult = npc.get("buy_multiplier", 0.5)
    inventory = []

    hp_pool = [(k, v) for k, v in consumables.items()
               if v.get("effect") in ("heal", "full_heal", "full_heal_small")
               and not v.get("scavenge_item")]
    hp_pool.sort(key=lambda x: x[1].get("tier", 1))
    hp_tier = min(max(1, floor), 3)
    hp_candidates = [v for k, v in hp_pool if v.get("tier", 1) <= hp_tier]
    if not hp_candidates:
        hp_candidates = [v for k, v in hp_pool]
    for _ in range(2):
        if hp_candidates:
            item = dict(random.choice(hp_candidates))
            item["buy_price"] = max(1, int(item.get("value", 10) * buy_mult))
            inventory.append(item)

    mp_pool = [(k, v) for k, v in consumables.items()
               if v.get("effect") == "restore_mp"
               and not v.get("scavenge_item")]
    mp_pool.sort(key=lambda x: x[1].get("tier", 1))
    mp_tier = min(max(1, floor), 3)
    mp_candidates = [v for k, v in mp_pool if v.get("tier", 1) <= mp_tier]
    if not mp_candidates:
        mp_candidates = [v for k, v in mp_pool]
    for _ in range(2):
        if mp_candidates:
            item = dict(random.choice(mp_candidates))
            item["buy_price"] = max(1, int(item.get("value", 10) * buy_mult))
            inventory.append(item)

    from items import random_weapon, random_armor, random_relic_for_tier, roll_chest_tier
    max_tier = min(floor + 1, 6)
    for _ in range(4):
        roll = random.random()
        if roll < 0.4:
            tier = roll_chest_tier(floor)
            item = random_weapon(1, tier)
        elif roll < 0.7:
            tier = roll_chest_tier(floor)
            item = random_armor(1, tier)
        else:
            tier = roll_chest_tier(floor)
            item = random_relic_for_tier(tier)
        if item:
            item = dict(item)
            base_val = item.get("value", 20)
            tier = item.get("tier", 1)
            item["buy_price"] = max(1, int(base_val * buy_mult * (1 + 0.15 * (tier - 1))))
            inventory.append(item)

    return inventory


def generate_key_trader_inventory(npc, floor):
    items_data = load_json("items.json")
    consumables = items_data.get("consumables", {})
    inventory = []

    hp_pool = [(k, v) for k, v in consumables.items()
               if v.get("effect") in ("heal", "full_heal", "full_heal_small")
               and not v.get("scavenge_item")]
    hp_tier = min(max(3, floor), 5)
    hp_candidates = [v for k, v in hp_pool if v.get("tier", 1) <= hp_tier]
    if not hp_candidates:
        hp_candidates = [v for k, v in hp_pool]
    for _ in range(2):
        if hp_candidates:
            item = dict(random.choice(hp_candidates))
            item["key_cost"] = 2
            inventory.append(item)

    mp_pool = [(k, v) for k, v in consumables.items()
               if v.get("effect") == "restore_mp"
               and not v.get("scavenge_item")]
    mp_tier = min(max(3, floor), 5)
    mp_candidates = [v for k, v in mp_pool if v.get("tier", 1) <= mp_tier]
    if not mp_candidates:
        mp_candidates = [v for k, v in mp_pool]
    for _ in range(2):
        if mp_candidates:
            item = dict(random.choice(mp_candidates))
            item["key_cost"] = 2
            inventory.append(item)

    from items import random_weapon, random_armor, random_relic_for_tier, roll_chest_tier
    for _ in range(4):
        tier = max(3, roll_chest_tier(floor))
        roll = random.random()
        if roll < 0.4:
            item = random_weapon(tier, min(tier, 6))
        elif roll < 0.7:
            item = random_armor(tier, min(tier, 6))
        else:
            item = random_relic_for_tier(tier)
        if item:
            item = dict(item)
            item_tier = item.get("tier", 3)
            if item_tier <= 3:
                item["key_cost"] = 2
            elif item_tier <= 4:
                item["key_cost"] = 3
            else:
                item["key_cost"] = 4
            inventory.append(item)

    return inventory
