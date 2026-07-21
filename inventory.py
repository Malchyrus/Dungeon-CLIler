import random
from status import add_status, remove_status, has_status


def add_item(player, item):
    if item.get("type") != "key":
        non_key_count = sum(1 for i in player.inventory if i.get("type") != "key")
        if non_key_count >= player.max_inventory:
            return False, "Inventory full!"
    player.inventory.append(dict(item))
    return True, f"Picked up {item['name']}."


def remove_item(player, item):
    for i, inv_item in enumerate(player.inventory):
        if inv_item.get("name") == item.get("name"):
            player.inventory.pop(i)
            return True
    return False


def _effect_heal(player, item):
    healed = player.heal(item.get("value", 15))
    return f"Used {item['name']}. Restored {healed} HP."


def _effect_full_heal(player, item):
    healed = player.heal(player.max_hp)
    mp_r = player.restore_mp(player.max_mp)
    return f"Used {item['name']}. Fully restored! (+{healed} HP, +{mp_r} MP)"


def _effect_full_heal_small(player, item):
    val = item.get("value", 12)
    healed = player.heal(val)
    mp_r = player.restore_mp(val)
    return f"Used {item['name']}. Restored {healed} HP and {mp_r} MP!"


def _effect_restore_mp(player, item):
    restored = player.restore_mp(item.get("value", 15))
    return f"Used {item['name']}. Restored {restored} MP."


def _effect_revive(player, item):
    if player.revive_used:
        return "The Holy Grail has already been used."
    player.revive_used = True
    player.heal(player.max_hp)
    return f"Used {item['name']}. You feel renewed vitality!"


def _effect_buff_atk(player, item):
    add_status(player.statuses, "atk_up", 9999, item.get("value", 3))
    return f"Used {item['name']}. ATK boosted!"


def _effect_buff_def(player, item):
    add_status(player.statuses, "def_up", 9999, item.get("value", 3))
    return f"Used {item['name']}. DEF boosted!"


def _effect_buff_speed(player, item):
    add_status(player.statuses, "speed_up", 3, item.get("value", 3))
    return f"Used {item['name']}. Speed surged for 3 turns!"


def _effect_buff_accuracy(player, item):
    add_status(player.statuses, "accuracy_up", 3, item.get("value", 20))
    return f"Used {item['name']}. Accuracy sharpened for 3 turns!"


def _effect_cleanse(player, item):
    negative = ["poison", "burn", "stunned", "blinded", "def_down", "speed_down",
                "atk_down", "accuracy_down", "dodge_down"]
    removed = []
    for sid in negative:
        if has_status(player.statuses, sid):
            remove_status(player.statuses, sid)
            removed.append(sid)
    if removed:
        return f"Used {item['name']}. Purged {len(removed)} negative effects!"
    return f"Used {item['name']}. No negative effects to cleanse."


def _effect_ele_resist_fire(player, item):
    add_status(player.statuses, "ele_resist_fire", 3, item.get("value", 50))
    return f"Used {item['name']}. Fire resistance active for 3 turns!"


def _effect_ele_resist_ice(player, item):
    add_status(player.statuses, "ele_resist_ice", 3, item.get("value", 50))
    return f"Used {item['name']}. Ice resistance active for 3 turns!"


def _effect_ele_resist_lightning(player, item):
    add_status(player.statuses, "ele_resist_lightning", 3, item.get("value", 50))
    return f"Used {item['name']}. Lightning resistance active for 3 turns!"


def _effect_random_mushroom(player, item):
    roll = random.random()
    if roll < 0.25:
        healed = player.heal(20)
        return f"The mushroom glows red! Restored {healed} HP!"
    elif roll < 0.50:
        restored = player.restore_mp(15)
        return f"The mushroom glows blue! Restored {restored} MP!"
    elif roll < 0.70:
        healed = player.heal(10)
        restored = player.restore_mp(10)
        return f"The mushroom glows purple! Restored {healed} HP and {restored} MP!"
    elif roll < 0.85:
        add_status(player.statuses, "atk_up", 3, 4)
        return "The mushroom glows yellow! ATK surged for 3 turns!"
    else:
        damage = random.randint(5, 15)
        player.hp = max(1, player.hp - damage)
        return f"The mushroom was poison! You take {damage} damage!"


def _effect_open_loot_bag(player, item):
    from constants import LOOT_BAG_TIER_GOLD, LOOT_BAG_TIER_CONTENTS, KEY_FROM_BAG_CHANCE
    from items import random_consumable, random_weapon, random_armor, random_relic

    tier = item.get("tier", 1)
    gold_range = LOOT_BAG_TIER_GOLD.get(tier, (2, 5))
    gold = random.randint(gold_range[0] * max(1, player.floor),
                          gold_range[1] * max(1, player.floor))
    player.gold += int(gold * player.gold_mult)

    contents = LOOT_BAG_TIER_CONTENTS.get(tier, LOOT_BAG_TIER_CONTENTS[1])
    roll = random.random()
    item_name = None
    granted_item = None

    if roll < contents["relic"]:
        relic = random_relic(player.floor)
        if relic:
            add_item(player, relic)
            item_name = relic["name"]
            granted_item = relic
    elif roll < contents["relic"] + contents["accessory"]:
        from items import random_accessory
        acc = random_accessory(player.floor, player)
        if acc:
            add_item(player, acc)
            item_name = acc["name"]
            granted_item = acc
    elif roll < contents["relic"] + contents["accessory"] + contents["armor"]:
        armor = random_armor(1, min(player.floor + 1, 6), player)
        if armor:
            add_item(player, armor)
            item_name = armor["name"]
            granted_item = armor
    elif roll < contents["relic"] + contents["accessory"] + contents["armor"] + contents["weapon"]:
        weapon = random_weapon(1, min(player.floor + 1, 6), player)
        if weapon:
            add_item(player, weapon)
            item_name = weapon["name"]
            granted_item = weapon
    elif roll < 1.0:
        cons = random_consumable(min(player.floor + 1, 5))
        if cons:
            add_item(player, cons)
            item_name = cons["name"]
            granted_item = cons

    lines = [f"You open the {item['name']}!"]
    lines.append(f"  Found {int(gold * player.gold_mult)} gold!")
    if item_name:
        lines.append(f"  Found: {item_name}!")

    if granted_item and player.double_item_chance > 0 and random.random() < player.double_item_chance:
        success2, msg2 = add_item(player, granted_item)
        lines.append(f"  Double loot! Found another: {granted_item['name']}!")

    if random.random() < KEY_FROM_BAG_CHANCE:
        from items import get_item
        key = get_item("chest_key")
        if key:
            added, msg = add_item(player, dict(key))
            if added:
                lines.append("  Found: Chest Key!")

    return "\n".join(lines)


USE_ITEM_EFFECTS = {
    "heal": _effect_heal,
    "full_heal": _effect_full_heal,
    "full_heal_small": _effect_full_heal_small,
    "restore_mp": _effect_restore_mp,
    "revive": _effect_revive,
    "buff_atk": _effect_buff_atk,
    "buff_def": _effect_buff_def,
    "buff_speed": _effect_buff_speed,
    "buff_accuracy": _effect_buff_accuracy,
    "cleanse": _effect_cleanse,
    "ele_resist_fire": _effect_ele_resist_fire,
    "ele_resist_ice": _effect_ele_resist_ice,
    "ele_resist_lightning": _effect_ele_resist_lightning,
    "random_mushroom": _effect_random_mushroom,
    "open_loot_bag": _effect_open_loot_bag,
}


def use_item(player, item):
    effect = item.get("effect")
    handler = USE_ITEM_EFFECTS.get(effect)
    if handler:
        result = handler(player, item)
        remove_item(player, item)
        return result
    return "You can't use that."


def drop_item(player, item):
    if remove_item(player, item):
        return f"Dropped {item['name']}."
    return "Item not found."


def _format_weapon(item):
    parts = [f"ATK+{item.get('atk', 0)}"]
    if item.get("accuracy_bonus"):
        parts.append(f"ACC+{item['accuracy_bonus']}")
    if item.get("crit_bonus"):
        parts.append(f"Crit+{item['crit_bonus']}%")
    if item.get("lifesteal"):
        parts.append(f"LS {item['lifesteal']}%")
    if item.get("armor_pen"):
        parts.append(f"APen {item['armor_pen']}%")
    if item.get("speed_penalty"):
        parts.append(f"SPD-{item['speed_penalty']}")
    return f" - {', '.join(parts)}"


def _format_armor(item):
    parts = [f"DEF+{item.get('def', 0)}"]
    if item.get("speed_penalty"):
        parts.append(f"SPD-{item['speed_penalty']}")
    if item.get("speed_bonus"):
        parts.append(f"SPD+{item['speed_bonus']}")
    if item.get("thorns"):
        parts.append(f"Thorns {item['thorns']}")
    if item.get("regen_per_turn"):
        parts.append(f"Regen {item['regen_per_turn']}/t")
    if item.get("accuracy_bonus"):
        parts.append(f"ACC+{item['accuracy_bonus']}")
    return f" - {', '.join(parts)}"


def _format_consumable(item):
    return f" - {item.get('description', '')}"


def _format_accessory(item):
    bonus = []
    if item.get("atk_bonus"):
        bonus.append(f"ATK+{item['atk_bonus']}")
    if item.get("def_penalty"):
        bonus.append(f"DEF-{item['def_penalty']}")
    if item.get("hp_bonus"):
        bonus.append(f"HP+{item['hp_bonus']}")
    if item.get("mp_bonus"):
        bonus.append(f"MP+{item['mp_bonus']}")
    if item.get("dodge_bonus"):
        bonus.append(f"Dodge+{item['dodge_bonus']}%")
    if item.get("speed_bonus"):
        bonus.append(f"SPD+{item['speed_bonus']}")
    if item.get("accuracy_bonus"):
        bonus.append(f"ACC+{item['accuracy_bonus']}")
    return f" - {', '.join(bonus)}" if bonus else ""


def _format_relic(item):
    from constants import RELIC_TIER_NAMES
    tier_name = RELIC_TIER_NAMES.get(item.get("tier", 1), "?")
    parts = []
    if item.get("hp_bonus"):
        parts.append(f"HP+{item['hp_bonus']}")
    if item.get("mp_bonus"):
        parts.append(f"MP+{item['mp_bonus']}")
    if item.get("atk_bonus"):
        parts.append(f"ATK+{item['atk_bonus']}")
    if item.get("def_bonus"):
        parts.append(f"DEF+{item['def_bonus']}")
    if item.get("crit_bonus"):
        parts.append(f"Crit+{item['crit_bonus']}%")
    if item.get("crit_mult_bonus"):
        parts.append(f"CritDmg+{int(item['crit_mult_bonus']*100)}%")
    if item.get("lifesteal"):
        parts.append(f"LS {item['lifesteal']}%")
    if item.get("thorns"):
        parts.append(f"Thorns {item['thorns']}")
    if item.get("armor_pen"):
        parts.append(f"APen {item['armor_pen']}%")
    if item.get("dodge_bonus"):
        parts.append(f"Dodge+{item['dodge_bonus']}%")
    if item.get("speed_bonus"):
        parts.append(f"SPD+{item['speed_bonus']}")
    if item.get("regen_per_turn"):
        parts.append(f"Regen {item['regen_per_turn']}/t")
    if item.get("mp_regen_per_turn"):
        parts.append(f"MPR {item['mp_regen_per_turn']}/t")
    if item.get("xp_mult") and item["xp_mult"] != 1.0:
        parts.append(f"XP x{item['xp_mult']}")
    if item.get("gold_mult") and item["gold_mult"] != 1.0:
        parts.append(f"Gold x{item['gold_mult']}")
    if item.get("basic_atk_mult") and item["basic_atk_mult"] != 1.0:
        parts.append(f"AtkMult x{item['basic_atk_mult']}")
    if item.get("basic_atk_mp_cost"):
        parts.append(f"AtkCost {item['basic_atk_mp_cost']}MP")
    if item.get("ability_mp_overhead"):
        parts.append(f"AbilCost+{item['ability_mp_overhead']}MP")
    if item.get("ability_dmg_mult") and item["ability_dmg_mult"] != 1.0:
        parts.append(f"AbilDmg x{item['ability_dmg_mult']}")
    if item.get("ability_mp_mult") and item["ability_mp_mult"] != 1.0:
        parts.append(f"AbilMP x{item['ability_mp_mult']}")
    if item.get("damage_taken_mult") and item["damage_taken_mult"] != 1.0:
        parts.append(f"DmgTaken x{item['damage_taken_mult']}")
    if item.get("on_hit_poison"):
        parts.append(f"Poison+{item['on_hit_poison']}/hit")
    if item.get("on_crit_double"):
        parts.append(f"CritDouble {int(item['on_crit_double']*100)}%")
    if item.get("on_crit_heal_pct"):
        parts.append(f"CritHeal {item['on_crit_heal_pct']}%")
    if item.get("reflect_pct"):
        parts.append(f"Reflect {item['reflect_pct']}%")
    if item.get("chaos_double_chance"):
        parts.append(f"ChaosDmg {int(item['chaos_double_chance']*100)}%")
    if item.get("chaos_double_damage"):
        parts.append(f"ChaosVuln {int(item['chaos_double_damage']*100)}%")
    if item.get("double_item_chance"):
        parts.append(f"DoubleItem {int(item['double_item_chance']*100)}%")
    if item.get("first_debuff_double"):
        parts.append("Debuff x2")
    if item.get("heal_on_kill"):
        parts.append(f"KillHeal {item['heal_on_kill']}")
    if item.get("low_hp_damage_mult") and item["low_hp_damage_mult"] != 1.0:
        parts.append(f"RageDmg x{item['low_hp_damage_mult']}")
    if item.get("execute_bonus_pct"):
        parts.append(f"Execute +{item['execute_bonus_pct']}%")
    if item.get("second_wind_heal_pct"):
        parts.append(f"SecondWind {item['second_wind_heal_pct']}%")
    if item.get("def_reduction"):
        parts.append(f"DEF {item['def_reduction']}")
    if item.get("defend_shield_mult") and item["defend_shield_mult"] != 1.0:
        parts.append(f"DefShield x{item['defend_shield_mult']}")
    if item.get("defend_hp_cost"):
        parts.append(f"DefCost {item['defend_hp_cost']}HP")
    stats = f" [{', '.join(parts)}]" if parts else ""
    cursed = " [CURSED]" if item.get("cursed") else ""
    return f" [{tier_name} Relic]{stats}{cursed}"


def _format_loot_bag(item):
    from constants import LOOT_BAG_TIER_NAMES
    tier_name = LOOT_BAG_TIER_NAMES.get(item.get("tier", 1), "?")
    return f" [{tier_name} Bag]"


def _format_key(item):
    return ""


def _format_default(item):
    return ""


ITEM_FORMATTERS = {
    "weapon": _format_weapon,
    "armor": _format_armor,
    "consumable": _format_consumable,
    "accessory": _format_accessory,
    "relic": _format_relic,
    "loot_bag": _format_loot_bag,
    "key": _format_key,
}


def show_inventory(player):
    non_key_items = [i for i in player.inventory if i.get("type") != "key"]
    key_items = [i for i in player.inventory if i.get("type") == "key"]
    lines = [f"  === Inventory ({len(non_key_items)}/{player.max_inventory}) ==="]

    if player.weapon:
        aff = " [AFFINITY]" if player.is_weapon_affinity() else ""
        lines.append(f"  [Weapon] {player.weapon['name']}{aff} (ATK+{player.weapon.get('atk', 0)})")
    else:
        lines.append("  [Weapon] Empty")

    if player.armor:
        lines.append(f"  [Armor]  {player.armor['name']} (DEF+{player.armor.get('def', 0)})")
    else:
        lines.append("  [Armor]  Empty")

    if player.accessory:
        lines.append(f"  [Acc.]   {player.accessory['name']}{_format_accessory(player.accessory)}")
    else:
        lines.append("  [Acc.]   Empty")

    if player.relics:
        for i, r in enumerate(player.relics):
            tag = " [CURSED]" if r.get("cursed") else ""
            lines.append(f"  [Relic]  {r['name']}{tag}{_format_relic(r)}")
    else:
        lines.append("  [Relic]  None")

    lines.append("")

    if not non_key_items:
        lines.append("  (empty)")
    else:
        grouped = {}
        for item in non_key_items:
            key = item.get("name", "Unknown")
            if key not in grouped:
                grouped[key] = {"item": item, "count": 0}
            grouped[key]["count"] += 1

        for i, (name, info) in enumerate(grouped.items(), 1):
            item = info["item"]
            count = info["count"]
            tag = f" x{count}" if count > 1 else ""
            itype = item.get("type", "")
            formatter = ITEM_FORMATTERS.get(itype, _format_default)
            lines.append(f"  {i}. {name}{tag}{formatter(item)}")

    if key_items:
        lines.append("")
        lines.append(f"  Keys ({len(key_items)}):")
        key_grouped = {}
        for item in key_items:
            name = item.get("name", "Unknown")
            if name not in key_grouped:
                key_grouped[name] = 0
            key_grouped[name] += 1
        for name, count in key_grouped.items():
            tag = f" x{count}" if count > 1 else ""
            lines.append(f"    {name}{tag}")

    return "\n".join(lines)
