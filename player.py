import random
from data_loader import load_json
from status import has_status, get_status, add_status, remove_status, clear_all, calc_dr
from constants import SPEED_BASE, ACCURACY_BASE

_narrative = load_json("narrative.json")

CLASSES = load_json("classes.json")

WISH_OUTCOMES = _narrative["wish_outcomes"]
TRUE_ENDING = _narrative["true_ending"]
MEMORY_FRAGMENTS = _narrative["memory_fragments"]
LORE_ENTRIES = _narrative["lore_entries"]
LORE_ENTRIES["memory"] = MEMORY_FRAGMENTS


class Player:
    def __init__(self, name, class_key):
        stats = CLASSES[class_key]
        self.name = name
        self.class_key = class_key
        self.class_name = stats["name"]
        self.max_hp = stats["hp"]
        self.hp = stats["hp"]
        self.base_atk = stats["atk"]
        self.base_def = stats["def"]
        self.max_mp = stats["mp"]
        self.mp = stats["mp"]
        self.xp = 0
        self.level = 1
        self.gold = 0
        self.weapon_affinity = stats["weapon_affinity"]
        self.damage_mult = stats["damage_mult"]
        self.crit_chance = stats.get("crit_chance", 0.0)
        self._base_crit_mult = stats.get("crit_mult", 1.0)
        self.abilities = stats["abilities"]
        self.cooldowns = {k: 0 for k in self.abilities}

        self.weapon = None
        self.armor = None
        self.accessory = None
        self.relics = []
        self.inventory = []
        self.max_inventory = 20
        self.floor = 1
        self.x = 0
        self.y = 0
        self.explored = set()
        self.kills = {}
        self.revive_used = False
        self._second_wind_used = False
        self._first_debuff_used = False
        self.statuses = []

    def get_available_abilities(self):
        return {
            k: v for k, v in self.abilities.items()
            if self.level >= v.get("level_req", 1)
        }

    def xp_to_next_level(self):
        return self.level * 9 + 3

    def level_up(self):
        self.level += 1
        stats = CLASSES.get(self.class_key, {}).get("level_up_stats", {})
        hp_gain = stats.get("hp", 5)
        mp_gain = stats.get("mp", 3)
        atk_gain = stats.get("atk", 1)
        def_gain = stats.get("def", 1)
        self.max_hp += hp_gain
        self.hp = min(self.hp + hp_gain + 5, self.max_hp)
        self.base_atk += atk_gain
        self.base_def += def_gain
        self.max_mp += mp_gain
        self.mp = min(self.mp + mp_gain + 3, self.max_mp)
        return f"Level up! You are now level {self.level}!"

    def check_level_up(self):
        messages = []
        while self.xp >= self.xp_to_next_level():
            self.xp -= self.xp_to_next_level()
            messages.append(self.level_up())
        return messages

    @property
    def atk(self):
        total = self.base_atk
        if self.weapon:
            total += self.weapon.get("atk", 0)
        if self.accessory:
            total += self.accessory.get("atk_bonus", 0)
            aff = self.accessory.get("class_bonus", "")
            if aff == self.class_key:
                total += self.accessory.get("class_atk_bonus", 0) - self.accessory.get("atk_bonus", 0)
        for r in self.relics:
            total += r.get("atk_bonus", 0)
        up = get_status(self.statuses, "atk_up")
        if up:
            total += up.get("value", 0)
        down = get_status(self.statuses, "atk_down")
        if down:
            total -= down.get("value", 0)
        return max(0, total)

    @property
    def defense(self):
        total = self.base_def
        if self.armor:
            total += self.armor.get("def", 0)
        if self.accessory:
            total -= self.accessory.get("def_penalty", 0)
        for r in self.relics:
            total += r.get("def_bonus", 0)
        up = get_status(self.statuses, "def_up")
        if up:
            total += up.get("value", 0)
        total += self.def_reduction
        return max(0, total)

    @property
    def dodge_chance(self):
        chance = 0
        if self.accessory:
            chance += self.accessory.get("dodge_bonus", 0)
        for r in self.relics:
            chance += r.get("dodge_bonus", 0)
        if self.class_key == "rogue":
            chance += 5
        up = get_status(self.statuses, "dodge_up")
        if up:
            chance += up.get("value", 0)
        down = get_status(self.statuses, "dodge_down")
        if down:
            chance -= down.get("value", 0)
        return max(0, min(chance, 50))

    @property
    def speed(self):
        total = SPEED_BASE
        if self.weapon:
            total -= self.weapon.get("speed_penalty", 0)
        if self.armor:
            total -= self.armor.get("speed_penalty", 0)
        if self.accessory:
            total += self.accessory.get("speed_bonus", 0)
        for r in self.relics:
            total += r.get("speed_bonus", 0)
            total -= r.get("speed_penalty", 0)
        up = get_status(self.statuses, "speed_up")
        if up:
            total += up.get("value", 0)
        down = get_status(self.statuses, "speed_down")
        if down:
            total -= down.get("value", 0)
        return max(0, total)

    @property
    def accuracy(self):
        total = ACCURACY_BASE
        if self.class_key == "rogue":
            total += 10
        if self.weapon:
            total += self.weapon.get("accuracy_bonus", 0)
        if self.accessory:
            total += self.accessory.get("accuracy_bonus", 0)
        for r in self.relics:
            total += r.get("accuracy_bonus", 0)
        if has_status(self.statuses, "blinded"):
            return 0
        up = get_status(self.statuses, "accuracy_up")
        if up:
            total += up.get("value", 0)
        down = get_status(self.statuses, "accuracy_down")
        if down:
            total -= down.get("value", 0)
        return max(0, total)

    @property
    def crit(self):
        total = 0
        if self.weapon:
            total += self.weapon.get("crit_bonus", 0)
        if self.armor:
            total += self.armor.get("crit_bonus", 0)
        if self.accessory:
            total += self.accessory.get("crit_bonus", 0)
        for r in self.relics:
            total += r.get("crit_bonus", 0)
        return total

    @property
    def crit_mult(self):
        base = self._base_crit_mult
        for r in self.relics:
            base += r.get("crit_mult_bonus", 0)
        return base

    @property
    def lifesteal(self):
        total = 0
        if self.weapon:
            total += self.weapon.get("lifesteal", 0)
        for r in self.relics:
            total += r.get("lifesteal", 0)
        return total

    @property
    def thorns(self):
        total = 0
        if self.armor:
            total += self.armor.get("thorns", 0)
        for r in self.relics:
            total += r.get("thorns", 0)
        return total

    @property
    def armor_pen(self):
        total = 0
        if self.weapon:
            total += self.weapon.get("armor_pen", 0)
        for r in self.relics:
            total += r.get("armor_pen", 0)
        return total

    @property
    def regen_per_turn(self):
        total = 0
        if self.armor:
            total += self.armor.get("regen_per_turn", 0)
        for r in self.relics:
            total += r.get("regen_per_turn", 0)
        return total

    @property
    def mp_regen_per_turn(self):
        total = 0
        if self.armor:
            total += self.armor.get("mp_regen_per_turn", 0)
        for r in self.relics:
            total += r.get("mp_regen_per_turn", 0)
        return total

    @property
    def xp_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("xp_mult", 1.0)
        return total

    @property
    def gold_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("gold_mult", 1.0)
        return total

    @property
    def basic_atk_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("basic_atk_mult", 1.0)
        return total

    @property
    def basic_atk_mp_cost(self):
        total = 0
        for r in self.relics:
            total += r.get("basic_atk_mp_cost", 0)
        return total

    @property
    def ability_mp_overhead(self):
        total = 0
        for r in self.relics:
            total += r.get("ability_mp_overhead", 0)
        return total

    @property
    def ability_dmg_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("ability_dmg_mult", 1.0)
        return total

    @property
    def ability_mp_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("ability_mp_mult", 1.0)
        return total

    @property
    def damage_taken_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("damage_taken_mult", 1.0)
        return total

    @property
    def on_hit_poison(self):
        total = 0
        for r in self.relics:
            total += r.get("on_hit_poison", 0)
        return total

    @property
    def on_hit_poison_dur(self):
        total = 0
        for r in self.relics:
            dur = r.get("on_hit_poison_dur", 0)
            if dur > total:
                total = dur
        return total

    @property
    def on_crit_double(self):
        total = 0.0
        for r in self.relics:
            total += r.get("on_crit_double", 0.0)
        return min(total, 1.0)

    @property
    def on_crit_heal_pct(self):
        total = 0
        for r in self.relics:
            total += r.get("on_crit_heal_pct", 0)
        return total

    @property
    def reflect_pct(self):
        total = 0
        for r in self.relics:
            total += r.get("reflect_pct", 0)
        return min(total, 50)

    @property
    def chaos_double_chance(self):
        total = 0.0
        for r in self.relics:
            total += r.get("chaos_double_chance", 0.0)
        return min(total, 1.0)

    @property
    def chaos_double_damage(self):
        total = 0.0
        for r in self.relics:
            total += r.get("chaos_double_damage", 0.0)
        return min(total, 1.0)

    @property
    def double_item_chance(self):
        total = 0.0
        for r in self.relics:
            total += r.get("double_item_chance", 0.0)
        return min(total, 0.50)

    @property
    def first_debuff_double(self):
        for r in self.relics:
            if r.get("first_debuff_double"):
                return True
        return False

    @property
    def heal_on_kill(self):
        total = 0
        for r in self.relics:
            total += r.get("heal_on_kill", 0)
        return total

    @property
    def low_hp_damage_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("low_hp_damage_mult", 1.0)
        return total

    @property
    def execute_bonus_pct(self):
        total = 0
        for r in self.relics:
            total += r.get("execute_bonus_pct", 0)
        return total

    @property
    def second_wind_heal_pct(self):
        total = 0
        for r in self.relics:
            val = r.get("second_wind_heal_pct", 0)
            if val > total:
                total = val
        return total

    @property
    def def_reduction(self):
        total = 0
        for r in self.relics:
            total += r.get("def_reduction", 0)
        return total

    @property
    def defend_shield_mult(self):
        total = 1.0
        for r in self.relics:
            total *= r.get("defend_shield_mult", 1.0)
        return total

    @property
    def defend_hp_cost(self):
        total = 0
        for r in self.relics:
            total += r.get("defend_hp_cost", 0)
        return total

    def calc_dr(self, enemy_level):
        return calc_dr(self.defense, enemy_level)

    def is_weapon_affinity(self):
        if not self.weapon:
            return False
        return self.weapon.get("weapon_type", "") in self.weapon_affinity

    def calc_damage(self):
        base = self.atk
        if self.is_weapon_affinity():
            base = int(base * self.damage_mult)
        return max(1, base + random.randint(-1, 2))

    def calc_crit(self):
        crit_total = self.crit_chance + self.crit / 100.0
        if random.random() < crit_total:
            return True
        return False

    def take_damage(self, raw_damage, enemy_level=1):
        shield = get_status(self.statuses, "shield")
        if shield:
            absorbed = min(shield["value"], raw_damage)
            shield["value"] -= absorbed
            raw_damage -= absorbed
            if shield["value"] <= 0:
                remove_status(self.statuses, "shield")

        dr = self.calc_dr(enemy_level)
        reduced = max(1, int(raw_damage * (1 - dr)))
        self.hp = max(0, self.hp - reduced)
        return reduced

    def heal(self, amount):
        before = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        return self.hp - before

    def restore_mp(self, amount):
        before = self.mp
        self.mp = min(self.mp + amount, self.max_mp)
        return self.mp - before

    def is_alive(self):
        return self.hp > 0

    def _equip_weapon(self, item):
        old = self.weapon
        self.weapon = item
        return old

    def _equip_armor(self, item):
        old = self.armor
        self.armor = item
        return old

    def _equip_accessory(self, item):
        if item.get("effect") in ("heal", "full_heal", "revive", "restore_mp", "buff_atk", "buff_def",
                                  "full_heal_small", "random_mushroom"):
            return None, "You can't equip consumables."
        old = self.accessory
        self.accessory = item
        if item.get("hp_bonus"):
            self.max_hp += item["hp_bonus"]
            self.hp = min(self.hp + item["hp_bonus"], self.max_hp)
        if item.get("mp_bonus"):
            self.max_mp += item["mp_bonus"]
            self.mp = min(self.mp + item["mp_bonus"], self.max_mp)
        if item.get("class_mp_bonus") and self.class_key == item.get("class_bonus"):
            self.max_mp += item["class_mp_bonus"]
            self.mp = min(self.mp + item["class_mp_bonus"], self.max_mp)
        if old:
            if old.get("hp_bonus"):
                self.max_hp -= old["hp_bonus"]
                self.hp = min(self.hp, self.max_hp)
            if old.get("mp_bonus"):
                self.max_mp -= old["mp_bonus"]
                self.mp = min(self.mp, self.max_mp)
            if old.get("class_mp_bonus") and self.class_key == old.get("class_bonus"):
                self.max_mp -= old["class_mp_bonus"]
                self.mp = min(self.mp, self.max_mp)
        return old, f"Equipped {item['name']}."

    EQUIP_HANDLERS = {
        "weapon": lambda self, item: (self._equip_weapon(item), f"Equipped {item['name']}."),
        "armor": lambda self, item: (self._equip_armor(item), f"Equipped {item['name']}."),
    }

    def equip(self, item):
        slot = item.get("type")
        if slot == "accessory":
            return self._equip_accessory(item)
        if slot == "relic":
            return self.equip_relic(item)
        handler = self.EQUIP_HANDLERS.get(slot)
        if handler:
            return handler(self, item)
        return None, "You can't equip that."

    def equip_relic(self, item):
        if item.get("type") != "relic":
            return None, "That's not a relic."
        if item.get("cursed") and any(
            r.get("name") == item.get("name") for r in self.relics
        ):
            return None, "You already have this relic equipped."
        self.relics.append(dict(item))
        return None, f"You equip the {item['name']}. You feel a dark presence seep into your soul..."

    def unequip_relic(self, index):
        if index < 0 or index >= len(self.relics):
            return None, "Invalid relic index."
        relic = self.relics[index]
        if relic.get("cursed"):
            return None, f"The {relic['name']} is cursed! It cannot be removed."
        removed = self.relics.pop(index)
        return removed, f"Unequipped {removed['name']}."

    def get_stats_display(self):
        from status import format_statuses, get_status
        weapon_name = self.weapon["name"] if self.weapon else "None"
        armor_name = self.armor["name"] if self.armor else "None"
        acc_name = self.accessory["name"] if self.accessory else "None"
        affinity = " [AFFINITY BONUS!]" if self.is_weapon_affinity() else ""
        dr = int(self.calc_dr(self.level) * 100)
        status_str = format_statuses(self.statuses)

        atk_up = get_status(self.statuses, "atk_up")
        atk_down = get_status(self.statuses, "atk_down")
        def_up = get_status(self.statuses, "def_up")
        def_down = get_status(self.statuses, "def_down")
        atk_buff = (atk_up.get("value", 0) if atk_up else 0) - (atk_down.get("value", 0) if atk_down else 0)
        def_buff = (def_up.get("value", 0) if def_up else 0) - (def_down.get("value", 0) if def_down else 0)
        atk_str = f"ATK: {self.atk}" + (f" ({self.atk - atk_buff:+d}{'+' if atk_buff >= 0 else ''}{atk_buff})" if atk_buff != 0 else "")
        def_str = f"DEF: {self.defense}" + (f" ({self.defense - def_buff:+d}{'+' if def_buff >= 0 else ''}{def_buff})" if def_buff != 0 else "")

        lines = [
            f"  {self.name} the {self.class_name} (Lv.{self.level})",
            f"  HP: {self.hp}/{self.max_hp}  MP: {self.mp}/{self.max_mp}",
            f"  {atk_str}  {def_str}  DR: {dr}%  Dodge: {self.dodge_chance}%",
            f"  SPD: {self.speed}  ACC: {self.accuracy}  Crit: {self.crit}%",
            f"  Lifesteal: {self.lifesteal}%  Thorns: {self.thorns}  Armor Pen: {self.armor_pen}%",
            f"  Regen: {self.regen_per_turn}/t  MP Regen: {self.mp_regen_per_turn}/t",
            f"  XP Mult: {self.xp_mult:.2f}x  Gold Mult: {self.gold_mult:.2f}x",
            f"  XP: {self.xp}/{self.xp_to_next_level()}  Gold: {self.gold}",
            f"  Weapon: {weapon_name}{affinity}",
            f"  Armor:  {armor_name}",
            f"  Accessory: {acc_name}",
        ]
        if self.relics:
            relic_names = []
            for i, r in enumerate(self.relics):
                tag = " [CURSED]" if r.get("cursed") and r.get("_curse_revealed") else ""
                relic_names.append(f"{r['name']}{tag}")
            lines.append(f"  Relics: {', '.join(relic_names)}")
        if status_str:
            lines.append(f"  Status: {status_str}")
        return "\n".join(lines)

    def to_dict(self):
        return {
            "name": self.name,
            "class_key": self.class_key,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "base_atk": self.base_atk,
            "base_def": self.base_def,
            "xp": self.xp,
            "level": self.level,
            "gold": self.gold,
            "weapon": self.weapon,
            "armor": self.armor,
            "accessory": self.accessory,
            "relics": self.relics,
            "inventory": self.inventory,
            "floor": self.floor,
            "x": self.x,
            "y": self.y,
            "explored": list(self.explored),
            "kills": self.kills,
            "revive_used": self.revive_used,
            "cooldowns": self.cooldowns,
            "statuses": self.statuses,
        }

    @classmethod
    def from_dict(cls, data):
        p = cls(data["name"], data["class_key"])
        p.hp = data["hp"]
        p.max_hp = data["max_hp"]
        p.mp = data.get("mp", 0)
        p.max_mp = data.get("max_mp", 0)
        p.base_atk = data["base_atk"]
        p.base_def = data["base_def"]
        p.xp = data["xp"]
        p.level = data["level"]
        p.gold = data["gold"]
        p.weapon = data.get("weapon")
        p.armor = data.get("armor")
        p.accessory = data.get("accessory")
        p.relics = data.get("relics", [])
        p.inventory = data.get("inventory", [])
        p.floor = data.get("floor", 1)
        p.x = data.get("x", 0)
        p.y = data.get("y", 0)
        p.explored = set(tuple(x) for x in data.get("explored", []))
        p.kills = data.get("kills", {})
        p.revive_used = data.get("revive_used", False)
        p.cooldowns = data.get("cooldowns", {k: 0 for k in p.abilities})
        p.statuses = data.get("statuses", data.get("status_effects_list", []))
        if not p.statuses and isinstance(data.get("status_effects"), dict):
            old = data["status_effects"]
            if old.get("buff_atk"):
                add_status(p.statuses, "atk_up", 9999, old["buff_atk"])
            if old.get("buff_def"):
                add_status(p.statuses, "def_up", 9999, old["buff_def"])
            if old.get("regen"):
                r = old["regen"]
                add_status(p.statuses, "regen", r.get("turns", 3), r.get("amount", 5))
        return p
