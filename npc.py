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
