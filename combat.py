import random
from inventory import use_item
from status import add_status, has_status, get_status, remove_status, tick_statuses
from enemies import get_enemy_ability_messages
from constants import (
    SPEED_DODGE_PER_POINT, SPEED_DODGE_CAP, SKILL_ACCURACY_CAP,
    SPEED_EXTRA_TURN_DIFF, SPEED_EXTRA_TURN_BASE_CHANCE,
    SPEED_EXTRA_TURN_CHANCE_PER_POINT, SPEED_EXTRA_TURN_CAP,
)


def _calc_speed_dodge(defender_speed, attacker_speed):
    diff = defender_speed - attacker_speed
    bonus = diff * SPEED_DODGE_PER_POINT
    return max(-SPEED_DODGE_CAP, min(SPEED_DODGE_CAP, bonus))


def _get_effective_dodge(base_dodge, defender_speed, attacker_speed):
    speed_dodge = _calc_speed_dodge(defender_speed, attacker_speed)
    return max(0, min(50, base_dodge + speed_dodge))


def _roll_hit(accuracy, effective_dodge):
    acc = min(accuracy, 100)
    hit = random.randint(1, 100) <= acc
    if not hit:
        return False, 0.0
    dodge = random.randint(1, 100) <= effective_dodge
    if dodge:
        return False, 0.0
    overflow = max(0, accuracy - 100)
    bonus_crit = min(0.50, overflow / 100)
    return True, bonus_crit


def _get_enemy_speed(enemy):
    return enemy.get("speed", 10)


def _get_enemy_accuracy(enemy):
    return enemy.get("accuracy", 100)


def _consume_shields(player, raw, messages):
    shields = []
    for s in player.statuses:
        if s["id"] in ("shield", "mana_shield") and s.get("value", 0) > 0:
            shields.append(s)
    if not shields:
        return raw
    shields.sort(key=lambda s: s.get("turns", 0))
    for s in shields:
        if raw <= 0:
            break
        sid = s["id"]
        val = s.get("value", 0)
        if sid == "mana_shield":
            absorbed = min(val, raw, player.mp)
            player.mp -= absorbed
        else:
            absorbed = min(val, raw)
        s["value"] -= absorbed
        raw -= absorbed
        if sid == "mana_shield":
            messages.append(f"Mana Shield absorbs {absorbed} damage as MP!")
        else:
            messages.append(f"Shield absorbs {absorbed} damage!")
        if s["value"] <= 0:
            remove_status(player.statuses, sid)
    return raw


def _get_enemy_crit(enemy):
    return enemy.get("crit", 0.0)


def _get_enemy_intent(enemy):
    enemy_statuses = enemy.get("statuses", [])
    if has_status(enemy_statuses, "stunned"):
        return {"type": "stunned"}

    hp_ratio = enemy["hp"] / enemy.get("max_hp", enemy["hp"]) if enemy.get("max_hp", enemy["hp"]) > 0 else 1
    abilities = enemy.get("abilities", {})

    for abil_key, abil in abilities.items():
        chance = abil.get("chance", 0.3)
        threshold = abil.get("threshold", 0.0)
        if hp_ratio > threshold and threshold > 0:
            continue
        if random.random() < chance:
            return {
                "type": "ability",
                "key": abil_key,
                "ability": abil,
            }

    return {"type": "basic"}


def _execute_enemy_intent(player, enemy, intent, player_blocked):
    messages = []
    enemy_statuses = enemy.get("statuses", [])
    damage_dealt = 0

    if intent["type"] == "stunned":
        messages.append(f"The {enemy['name']} is stunned and cannot act!")
        return messages, 0

    if intent["type"] == "ability":
        abil = intent["ability"]
        abil_type = abil.get("type", "damage")

        if abil_type in ("heal", "buff"):
            ability_msgs, extra_dmg, pierce_data = get_enemy_ability_messages(
                enemy, player_statuses=player.statuses, force_key=intent["key"]
            )
            messages.extend(ability_msgs)
            return messages, 0

        accuracy = abil.get("accuracy", SKILL_ACCURACY_CAP)
        effective_dodge = _get_effective_dodge(
            player.dodge_chance, player.speed, _get_enemy_speed(enemy)
        )
        hits, _ = _roll_hit(accuracy, effective_dodge)

        if not hits:
            messages.append(f"The {enemy['name']} uses {abil.get('name', 'a skill')} but misses!")
            return messages, 0

        ability_msgs, extra_dmg, pierce_data = get_enemy_ability_messages(
            enemy, player_statuses=player.statuses, force_key=intent["key"]
        )
        messages.extend(ability_msgs)

        if abil_type in ("debuff", "stun", "dot", "reflect"):
            return messages, 0

        raw = enemy["atk"] + random.randint(-1, 2) + extra_dmg

        if has_status(player.statuses, "divine_shield"):
            messages.append("Divine Shield absorbs all damage!")
            remove_status(player.statuses, "divine_shield")
            return messages, 0

        if player_blocked:
            raw = raw // 2

        if pierce_data:
            pierce_raw = pierce_data["armor_pierce"]
            pierce_ratio = pierce_data["pierce_ratio"]
            pierced_def = int(player.defense * (1 - pierce_ratio))
            reduced = max(1, pierce_raw - pierced_def)
            player.hp = max(0, player.hp - reduced)
            messages.append(f"Armor-piercing strike! {reduced} damage!")
            return messages, reduced

        raw = _consume_shields(player, raw, messages)

        if raw > 0:
            from constants import ARMOR_DR_K, ARMOR_DR_CAP
            dr = min(ARMOR_DR_CAP, player.defense / (player.defense + ARMOR_DR_K * enemy.get("level", 1))) if player.defense > 0 else 0.0
            reduced = max(1, int(raw * (1 - dr)))
            player.hp = max(0, player.hp - reduced)
            messages.append(f"The {enemy['name']} hits you for {reduced} damage!")
            damage_dealt = reduced
            if player.thorns > 0:
                enemy["hp"] = max(0, enemy["hp"] - player.thorns)
                messages.append(f"Thorns deals {player.thorns} damage back!")
        else:
            messages.append(f"The {enemy['name']}'s attack is fully absorbed!")

        return messages, damage_dealt

    if has_status(player.statuses, "divine_shield"):
        messages.append("Divine Shield absorbs all damage!")
        remove_status(player.statuses, "divine_shield")
        return messages, 0

    accuracy = _get_enemy_accuracy(enemy)
    effective_dodge = _get_effective_dodge(
        player.dodge_chance, player.speed, _get_enemy_speed(enemy)
    )
    hits, _ = _roll_hit(accuracy, effective_dodge)

    if not hits:
        messages.append(f"The {enemy['name']} attacks but misses!")
        return messages, 0

    raw = enemy["atk"] + random.randint(-1, 2)

    if player_blocked:
        raw = raw // 2

    raw = _consume_shields(player, raw, messages)

    if raw > 0:
        from constants import ARMOR_DR_K, ARMOR_DR_CAP
        dr = min(ARMOR_DR_CAP, player.defense / (player.defense + ARMOR_DR_K * enemy.get("level", 1))) if player.defense > 0 else 0.0
        reduced = max(1, int(raw * (1 - dr)))
        player.hp = max(0, player.hp - reduced)
        messages.append(f"The {enemy['name']} hits you for {reduced} damage!")
        damage_dealt = reduced
        if player.thorns > 0:
            enemy["hp"] = max(0, enemy["hp"] - player.thorns)
            messages.append(f"Thorns deals {player.thorns} damage back!")
    else:
        messages.append(f"The {enemy['name']}'s attack is fully absorbed!")

    return messages, damage_dealt


ABILITY_HANDLERS = {}


def _ability_fireball(player, enemy):
    dmg = 10 + player.atk // 2
    enemy["hp"] = max(0, enemy["hp"] - dmg)
    return [f"You hurl a fireball! {dmg} magic damage!"], "fireball", False


def _ability_ice_shield(player, enemy):
    add_status(player.statuses, "divine_shield", 1)
    return ["An ice shield forms around you. Damage blocked this turn!"], "ice_shield", True


def _ability_heal(player, enemy):
    healed = player.heal(15)
    return [f"You channel healing magic. Restored {healed} HP!"], "heal", False


def _ability_lightning_bolt(player, enemy):
    dmg = 10 + player.atk // 2
    enemy["hp"] = max(0, enemy["hp"] - dmg)
    msgs = [f"A bolt of lightning strikes! {dmg} magic damage!"]
    if random.random() < 0.3:
        enemy.setdefault("statuses", [])
        add_status(enemy["statuses"], "stunned", 1)
        msgs.append("The enemy is stunned by the lightning!")
    return msgs, "lightning_bolt", False


def _ability_mana_shield(player, enemy):
    add_status(player.statuses, "mana_shield", 9999, 3)
    return ["Mana Shield active! Next 3 attacks drain MP instead of HP!"], "mana_shield", False


def _ability_holy_smite(player, enemy):
    base_dmg = 8
    if enemy.get("key", "") in ("skeleton", "wraith", "vampire", "lich", "death_knight", "ghoul"):
        base_dmg = 14
    total_dmg = base_dmg + player.atk // 2
    enemy["hp"] = max(0, enemy["hp"] - total_dmg)
    msgs = []
    if base_dmg == 14:
        msgs.append("Holy Smite burns the undead!")
    msgs.append(f"Divine light smites the enemy! {total_dmg} damage!")
    return msgs, "holy_smite", False


def _ability_bless(player, enemy):
    add_status(player.statuses, "regen", 3, 5)
    return ["You are blessed. Regenerating 5 HP per turn for 3 turns!"], "bless", False


def _ability_lay_on_hands(player, enemy):
    heal_amount = int(player.max_hp * 0.4)
    healed = player.heal(heal_amount)
    return [f"You channel divine healing. Restored {healed} HP!"], "lay_on_hands", False


def _ability_retribution(player, enemy):
    missing_hp = player.max_hp - player.hp
    dmg = int(missing_hp * 0.3) + player.atk // 2
    enemy["hp"] = max(0, enemy["hp"] - dmg)
    return [f"Retribution! {dmg} damage!"], "retribution", False


def _ability_divine_shield(player, enemy):
    add_status(player.statuses, "divine_shield", 1)
    return ["Divine Shield! Immune to all damage this turn!"], "divine_shield", True


def _ability_war_cry(player, enemy):
    enemy.setdefault("statuses", [])
    add_status(enemy["statuses"], "stunned", 1)
    return ["You roar! The enemy is stunned for 1 turn!"], "war_cry", False


def _ability_shield_bash(player, enemy):
    enemy["atk"] = max(1, enemy["atk"] - 3)
    return ["Shield Bash! Enemy ATK reduced by 3!"], "shield_bash", False


def _ability_cleave(player, enemy):
    damage = int(player.calc_damage() * 1.5)
    enemy_def = enemy.get("def", 0)
    ignore_def = max(0, enemy_def - 2)
    reduced = max(1, damage - ignore_def)
    enemy["hp"] = max(0, enemy["hp"] - reduced)
    return [f"Cleave! {reduced} damage, slicing through armor!"], "cleave", False


def _ability_execute(player, enemy):
    hp_ratio = enemy["hp"] / enemy.get("max_hp", enemy["hp"]) if enemy.get("max_hp", 1) > 0 else 1
    damage = player.calc_damage()
    msgs = []
    if hp_ratio < 0.3:
        damage *= 2
        msgs.append("Execute! Enemy below 30% HP! Double damage!")
    reduced = max(1, damage - enemy.get("def", 0))
    enemy["hp"] = max(0, enemy["hp"] - reduced)
    msgs.append(f"You strike for {reduced} damage!")
    return msgs, "execute", False


def _ability_backstab(player, enemy):
    damage = player.calc_damage() * 2
    reduced = max(1, damage - enemy.get("def", 0))
    enemy["hp"] = max(0, enemy["hp"] - reduced)
    return [f"Backstab! {reduced} damage!"], "backstab", False


def _ability_poison_blade(player, enemy):
    enemy.setdefault("statuses", [])
    add_status(enemy["statuses"], "poison", 3, 3)
    return ["You coat your blade in poison!"], "poison_blade", False


def _ability_smoke_bomb(player, enemy):
    add_status(player.statuses, "dodge_up", 3, 25)
    return ["Smoke fills the air! Dodge increased!"], "smoke_bomb", False


def _ability_steal(player, enemy):
    damage = player.calc_damage()
    reduced = max(1, damage - enemy.get("def", 0))
    enemy["hp"] = max(0, enemy["hp"] - reduced)
    msgs = [f"You strike for {reduced} damage!"]
    if random.random() < 0.5:
        stolen_gold = random.randint(5, 15 + player.floor * 3)
        player.gold += stolen_gold
        msgs.append(f"You steal {stolen_gold} gold!")
    if random.random() < 0.25:
        from items import random_loot
        loot = random_loot(player.floor, player=player)
        if loot:
            from inventory import add_item
            add_item(player, loot[0])
            msgs.append(f"You steal: {loot[0]['name']}!")
    return msgs, "steal", False


def _ability_assassinate(player, enemy):
    damage = player.calc_damage() * 3
    reduced = max(1, damage - enemy.get("def", 0))
    enemy["hp"] = max(0, enemy["hp"] - reduced)
    return [f"Assassinate! {reduced} devastating damage!"], "assassinate", False


ABILITY_HANDLERS = {
    "fireball": _ability_fireball,
    "ice_shield": _ability_ice_shield,
    "heal": _ability_heal,
    "lightning_bolt": _ability_lightning_bolt,
    "mana_shield": _ability_mana_shield,
    "holy_smite": _ability_holy_smite,
    "bless": _ability_bless,
    "lay_on_hands": _ability_lay_on_hands,
    "retribution": _ability_retribution,
    "divine_shield": _ability_divine_shield,
    "war_cry": _ability_war_cry,
    "shield_bash": _ability_shield_bash,
    "cleave": _ability_cleave,
    "execute": _ability_execute,
    "backstab": _ability_backstab,
    "poison_blade": _ability_poison_blade,
    "smoke_bomb": _ability_smoke_bomb,
    "steal": _ability_steal,
    "assassinate": _ability_assassinate,
}


def _execute_player_action(player, enemy, action, player_ability):
    messages = []
    player_blocked = False
    ability_used = None

    if action == "attack":
        crit = player.calc_crit()
        damage = player.calc_damage()
        if crit:
            damage = int(damage * player.crit_mult)
            messages.append("CRITICAL HIT!")
        enemy_def = enemy.get("def", 0)
        ap = player.armor_pen
        effective_def = max(0, enemy_def - int(enemy_def * ap / 100)) if ap > 0 else enemy_def
        reduced = max(1, damage - effective_def)

        if enemy.get("first_strike") and not enemy.get("_first_strike_used"):
            reduced *= 2
            enemy["_first_strike_used"] = True
            messages.append("First Strike! Double damage!")

        enemy["hp"] = max(0, enemy["hp"] - reduced)
        messages.append(f"You deal {reduced} damage to the {enemy['name']}!")

        ls = player.lifesteal
        if ls > 0 and reduced > 0:
            heal = max(1, int(reduced * ls / 100))
            player.heal(heal)
            messages.append(f"Lifesteal restores {heal} HP!")

        reflect = get_status(enemy.get("statuses", []), "reflect")
        if reflect and reflect.get("value", 0) > 0:
            reflected = max(1, int(reduced * reflect["value"] / 100))
            player.hp = max(0, player.hp - reflected)
            messages.append(f"Reflect deals {reflected} damage back to you!")

    elif action == "defend":
        armor_val = player.defense
        existing = get_status(player.statuses, "shield")
        if existing:
            remove_status(player.statuses, "shield")
        entry = add_status(player.statuses, "shield", 2, armor_val)
        entry["_fresh"] = False
        player_blocked = True
        messages.append(f"You raise your guard! Shield absorbs up to {armor_val} damage.")

    elif action == "ability":
        if player_ability and player_ability in player.abilities:
            ability = player.abilities[player_ability]

            level_req = ability.get("level_req", 1)
            if player.level < level_req:
                messages.append(f"{ability['name']} requires level {level_req}!")
                return messages, False, ability_used

            cd = player.cooldowns.get(player_ability, 0)
            if cd > 0:
                messages.append(f"{ability['name']} is on cooldown ({cd} turns).")
                return messages, False, ability_used

            mp_cost = ability.get("mp_cost", 0)
            if player.mp < mp_cost:
                messages.append(f"Not enough MP for {ability['name']}!")
                return messages, False, ability_used

            player.mp -= mp_cost
            player.cooldowns[player_ability] = ability.get("cooldown", 1)

            handler = ABILITY_HANDLERS.get(player_ability)
            if handler:
                msgs, ability_used, player_blocked = handler(player, enemy)
                messages.extend(msgs)
                if ability_used and player.lifesteal > 0:
                    dmg_dealt = max(0, int((enemy.get("max_hp", enemy["hp"]) - enemy["hp"]) * 0))
                    for m in msgs:
                        if "damage" in m.lower():
                            import re
                            nums = re.findall(r'(\d+)\s*damage', m)
                            if nums:
                                dmg_dealt = int(nums[0])
                                break
                    if dmg_dealt > 0:
                        heal = max(1, int(dmg_dealt * player.lifesteal / 100))
                        player.heal(heal)
                        messages.append(f"Lifesteal restores {heal} HP!")

    elif action == "use":
        messages.append("You use an item during combat.")

    return messages, player_blocked, ability_used


def _tick_relic_curses(player):
    messages = []
    for relic in player.relics:
        if not relic.get("cursed"):
            continue
        if not relic.get("_curse_revealed"):
            relic["_curse_revealed"] = True
            messages.append(f"The {relic['name']} reveals its curse!")
        curse_effect = relic.get("curse_effect")
        curse_value = relic.get("curse_value", 0)
        if curse_effect and curse_value > 0:
            if curse_effect == "poison":
                player.hp = max(0, player.hp - curse_value)
                messages.append(f"The {relic['name']} poisons you for {curse_value} damage!")
            elif curse_effect == "burn":
                player.hp = max(0, player.hp - curse_value)
                messages.append(f"The {relic['name']} burns you for {curse_value} damage!")
            elif curse_effect == "stun_self":
                if random.random() < 0.15:
                    messages.append(f"The {relic['name']} stuns you momentarily!")
                    add_status(player.statuses, "stunned", 1)
            elif curse_effect == "atk_down":
                add_status(player.statuses, "atk_down", 1, curse_value)
            elif curse_effect == "speed_down":
                add_status(player.statuses, "speed_down", 1, curse_value)
    return messages


def _tick_player_statuses(player):
    messages = []

    if player.regen_per_turn > 0:
        healed = player.heal(player.regen_per_turn)
        if healed > 0:
            messages.append(f"Item regen heals you for {healed} HP!")
    if player.mp_regen_per_turn > 0:
        restored = player.restore_mp(player.mp_regen_per_turn)
        if restored > 0:
            messages.append(f"Item regen restores {restored} MP!")

    for s in list(player.statuses):
        sid = s["id"]
        val = s.get("value", 0)
        if sid == "poison" and val > 0:
            player.hp = max(0, player.hp - val)
            messages.append(f"Poison deals {val} damage!")
        elif sid == "burn" and val > 0:
            player.hp = max(0, player.hp - val)
            messages.append(f"Fire burns you for {val} damage!")
        elif sid == "regen" and val > 0:
            healed = player.heal(val)
            if healed > 0:
                messages.append(f"Regen heals you for {healed} HP!")

    curse_msgs = _tick_relic_curses(player)
    messages.extend(curse_msgs)

    removed = tick_statuses(player.statuses)
    messages.extend(removed)
    return messages


def _tick_enemy_statuses(enemy):
    messages = []
    enemy_statuses = enemy.get("statuses", [])
    for s in list(enemy_statuses):
        sid = s["id"]
        val = s.get("value", 0)
        if sid == "poison" and val > 0:
            enemy["hp"] = max(0, enemy["hp"] - val)
            messages.append(f"Poison deals {val} damage to the {enemy['name']}!")
        elif sid == "burn" and val > 0:
            enemy["hp"] = max(0, enemy["hp"] - val)
            messages.append(f"Fire burns the {enemy['name']} for {val} damage!")
    removed = tick_statuses(enemy_statuses)
    for msg in removed:
        messages.append(f"The {enemy['name']}: {msg}")
    return messages


def combat_round(player, enemy, action, player_ability=None, is_extra_turn=False, intent=None):
    regen = enemy.get("passive_regen", 0)
    if regen > 0 and enemy["hp"] > 0:
        before = enemy["hp"]
        enemy["hp"] = min(enemy["hp"] + regen, enemy.get("max_hp", enemy["hp"]))
        healed = enemy["hp"] - before
        if healed > 0:
            print(f"  The {enemy['name']} regenerates {healed} HP!")

    if intent is None:
        intent = _get_enemy_intent(enemy)

    messages, player_blocked, ability_used = _execute_player_action(
        player, enemy, action, player_ability
    )

    spd_diff = player.speed - _get_enemy_speed(enemy)
    extra_turn = False
    if not is_extra_turn and spd_diff >= SPEED_EXTRA_TURN_DIFF and enemy["hp"] > 0:
        excess = spd_diff - SPEED_EXTRA_TURN_DIFF
        chance = min(SPEED_EXTRA_TURN_CAP,
                     SPEED_EXTRA_TURN_BASE_CHANCE + excess * SPEED_EXTRA_TURN_CHANCE_PER_POINT)
        if random.random() < chance:
            extra_turn = True

    if extra_turn:
        return messages, ability_used, intent, True

    if enemy["hp"] > 0:
        enemy_statuses_now = enemy.get("statuses", [])
        if has_status(enemy_statuses_now, "stunned"):
            messages.append(f"The {enemy['name']} is stunned and cannot act!")
        else:
            enemy_msgs, _ = _execute_enemy_intent(player, enemy, intent, player_blocked)
            messages.extend(enemy_msgs)

            if spd_diff <= -SPEED_EXTRA_TURN_DIFF and enemy["hp"] > 0:
                excess = abs(spd_diff) - SPEED_EXTRA_TURN_DIFF
                chance = min(SPEED_EXTRA_TURN_CAP,
                             SPEED_EXTRA_TURN_BASE_CHANCE + excess * SPEED_EXTRA_TURN_CHANCE_PER_POINT)
                if random.random() < chance:
                    enemy_statuses_now2 = enemy.get("statuses", [])
                    if not has_status(enemy_statuses_now2, "stunned"):
                        intent2 = _get_enemy_intent(enemy)
                        extra_enemy_msgs, _ = _execute_enemy_intent(player, enemy, intent2, False)
                        if extra_enemy_msgs:
                            messages.append("--- Enemy Extra Action! ---")
                            messages.extend(extra_enemy_msgs)

    player_tick_msgs = _tick_player_statuses(player)
    messages.extend(player_tick_msgs)

    enemy_tick_msgs = _tick_enemy_statuses(enemy)
    messages.extend(enemy_tick_msgs)

    intent = _get_enemy_intent(enemy)

    return messages, ability_used, intent, False


def use_item_in_combat(player, item):
    result = use_item(player, item)
    success = result != "You can't use that."
    return [result], success
