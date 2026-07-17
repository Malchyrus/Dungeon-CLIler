import random
from data_loader import load_json
from constants import (
    CHEST_TIER_TABLE, BONUS_CHEST_TIER_PROBS, RELIC_TIER_TABLE,
    BONUS_RELIC_TIER_PROBS, LOOT_BAG_TIER_TABLE, BONUS_LOOT_BAG_TIER_PROBS,
)

CLASS_WEAPON_AFFINITY = {
    "warrior": "axe",
    "rogue": "dagger",
    "mage": "staff",
    "paladin": "holy",
}

AFFINITY_BONUS = 1.5
MISSING_BONUS = 1.3
LOWEST_TIER_BONUS = 1.25


def get_all_items():
    data = load_json("items.json")
    all_items = {}
    for category in data.values():
        all_items.update(category)
    return all_items


def get_item(item_id):
    all_items = get_all_items()
    return all_items.get(item_id)


def _calc_item_weight(item, player, equipped_set):
    weight = 1.0
    if player:
        cls = getattr(player, "class_key", None)
        if item.get("type") == "weapon":
            affinity = CLASS_WEAPON_AFFINITY.get(cls)
            if affinity and item.get("weapon_type") == affinity:
                weight *= AFFINITY_BONUS
        elif item.get("type") == "armor":
            bonus_key = f"class_{cls}_hp_bonus" if cls else None
            if bonus_key and item.get(bonus_key):
                weight *= AFFINITY_BONUS
            elif item.get("class_bonus") == cls:
                weight *= AFFINITY_BONUS
        elif item.get("type") == "accessory":
            if item.get("class_bonus") == cls:
                weight *= AFFINITY_BONUS
        item_name = item.get("name")
        if equipped_set is not None and item_name not in equipped_set:
            weight *= MISSING_BONUS
    return weight


def _weighted_choice(candidates, player=None):
    if not candidates:
        return None
    equipped_set = None
    if player:
        equipped_set = set()
        if hasattr(player, "weapon") and player.weapon:
            equipped_set.add(player.weapon.get("name"))
        if hasattr(player, "armor") and player.armor:
            equipped_set.add(player.armor.get("name"))
        if hasattr(player, "accessory") and player.accessory:
            equipped_set.add(player.accessory.get("name"))
    weights = [_calc_item_weight(c, player, equipped_set) for c in candidates]
    total = sum(weights)
    if total <= 0:
        return random.choice(candidates)
    roll = random.random() * total
    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w
        if roll < cumulative:
            return candidates[i]
    return candidates[-1]


def random_weapon(min_tier=1, max_tier=5, player=None):
    data = load_json("items.json")
    candidates = []
    for k, v in data["weapons"].items():
        if min_tier <= v.get("tier", 1) <= max_tier:
            candidates.append(v)
    return _weighted_choice(candidates, player)


def random_armor(min_tier=1, max_tier=5, player=None):
    data = load_json("items.json")
    candidates = []
    for k, v in data["armor"].items():
        if min_tier <= v.get("tier", 1) <= max_tier:
            candidates.append(v)
    return _weighted_choice(candidates, player)


def random_consumable(tier=1):
    data = load_json("items.json")
    candidates = [v for v in data["consumables"].values() if v.get("tier", 1) <= tier]
    return random.choice(candidates) if candidates else None


def random_accessory(floor, player=None):
    data = load_json("items.json")
    candidates = list(data.get("artifacts", {}).values())
    if not candidates:
        return None
    max_tier = min(floor + 1, 6)
    tiered = [a for a in candidates if a.get("tier", 1) <= max_tier and a.get("type") == "accessory"]
    pool = tiered if tiered else [a for a in candidates if a.get("type") == "accessory"]
    if not pool:
        return None
    return dict(_weighted_choice(pool, player))


def random_relic(floor):
    data = load_json("items.json")
    candidates = list(data.get("relics", {}).values())
    if not candidates:
        return None
    tier_probs = RELIC_TIER_TABLE.get(floor, RELIC_TIER_TABLE.get(5, [0.03, 0.10, 0.25, 0.30, 0.22, 0.10]))
    tier = _roll_from_probs(tier_probs)
    tier_relics = [r for r in candidates if r.get("tier", 1) == tier]
    if not tier_relics:
        tier_relics = candidates
    return dict(random.choice(tier_relics))


def random_loot_bag(floor, is_bonus=False):
    data = load_json("items.json")
    candidates = list(data.get("loot_bags", {}).values())
    if not candidates:
        return None
    if is_bonus:
        probs = BONUS_LOOT_BAG_TIER_PROBS
    else:
        probs = LOOT_BAG_TIER_TABLE.get(floor, LOOT_BAG_TIER_TABLE.get(5))
    tier = _roll_from_probs(probs)
    tier_bags = [b for b in candidates if b.get("tier", 1) == tier]
    if not tier_bags:
        tier_bags = candidates
    return dict(random.choice(tier_bags))


def roll_chest_tier(floor, is_bonus=False):
    if is_bonus:
        probs = BONUS_CHEST_TIER_PROBS
    else:
        probs = CHEST_TIER_TABLE.get(floor, CHEST_TIER_TABLE.get(5))
    return _roll_from_probs(probs)


def roll_relic_tier(floor, is_bonus=False):
    if is_bonus:
        probs = BONUS_RELIC_TIER_PROBS
    else:
        probs = RELIC_TIER_TABLE.get(floor, RELIC_TIER_TABLE.get(5))
    return _roll_from_probs(probs)


def random_relic_for_tier(tier):
    data = load_json("items.json")
    candidates = list(data.get("relics", {}).values())
    tier_relics = [r for r in candidates if r.get("tier", 1) == tier]
    if not tier_relics:
        tier_relics = candidates
    return dict(random.choice(tier_relics)) if tier_relics else None


def random_equipment_for_tier(tier, player=None):
    roll = random.random()
    if roll < 0.5:
        return random_weapon(1, tier, player)
    else:
        return random_armor(1, tier, player)


def random_equipment_chest(floor, chest_tier, player=None):
    loot = []
    gold = random.randint(floor * 3, floor * 8)
    loot.append({"name": "Gold", "type": "gold", "value": gold})

    item = random_equipment_for_tier(chest_tier, player)
    if item:
        loot.append(dict(item))

    if chest_tier >= 5 and random.random() < 0.3:
        item = random_equipment_for_tier(chest_tier, player)
        if item:
            loot.append(dict(item))

    return loot


def random_relic_chest(floor, chest_tier):
    loot = []
    gold = random.randint(floor * 3, floor * 8)
    loot.append({"name": "Gold", "type": "gold", "value": gold})

    relic_tier = min(chest_tier, 6)
    relic = random_relic_for_tier(relic_tier)
    if relic:
        loot.append(relic)

    if chest_tier >= 6 and random.random() < 0.2:
        extra = random_relic_for_tier(5)
        if extra:
            loot.append(extra)

    return loot


def random_loot(floor, is_mimic=False, player=None):
    loot = []
    gold = random.randint(floor * 3, floor * 8)
    loot.append({"name": "Gold", "type": "gold", "value": gold})

    max_tier = min(floor + 1, 6)
    if is_mimic:
        max_tier = min(floor + 2, 6)

    roll = random.random()
    if roll < 0.3:
        item = random_consumable(max_tier)
        if item:
            loot.append(dict(item))
    elif roll < 0.5:
        item = random_weapon(1, max_tier, player)
        if item:
            loot.append(dict(item))
    elif roll < 0.65:
        item = random_armor(1, max_tier, player)
        if item:
            loot.append(dict(item))

    if is_mimic:
        extra = random_consumable(max_tier)
        if extra:
            loot.append(dict(extra))

    return loot


def artifact_pool():
    data = load_json("items.json")
    return list(data.get("artifacts", {}).values())


def random_artifact():
    pool = artifact_pool()
    return dict(random.choice(pool)) if pool else None


def _roll_from_probs(probs):
    roll = random.random()
    cumulative = 0.0
    for i, p in enumerate(probs):
        cumulative += p
        if roll < cumulative:
            return i + 1
    return len(probs)
