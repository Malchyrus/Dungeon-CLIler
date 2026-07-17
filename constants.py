GRID_SIZE = 6
ROOM_COUNT_MIN = 12
ROOM_COUNT_MAX = 16
BONUS_ROOM_COUNT_MIN = 6
BONUS_ROOM_COUNT_MAX = 8

MAX_INVENTORY = 20

XP_BASE = 10
XP_PER_LEVEL = 25
HP_PER_LEVEL = 5
MP_PER_LEVEL = 3
ATK_PER_LEVEL = 1
DEF_PER_LEVEL = 1
LEVEL_UP_HEAL = 10
LEVEL_UP_MP_HEAL = 5

DODGE_BASE = 10
DODGE_CAP = 50
DODGE_ROGUE_BONUS = 5

ESCAPE_CHANCE = 0.5

HEAL_BAR_LENGTH = 20
SEPARATOR_LENGTH = 50

GAMMA = 0.6
CHAR_ASPECT = 2.0

CELDRIC_PRICE_FRACTION = 0.9

ARMOR_DR_K = 3
ARMOR_DR_CAP = 0.8

SPEED_BASE = 10
SPEED_EXTRA_TURN_DIFF = 4
SPEED_EXTRA_TURN_CHANCE_PER_POINT = 0.15
SPEED_EXTRA_TURN_BASE_CHANCE = 0.15
SPEED_EXTRA_TURN_CAP = 0.75
SPEED_DODGE_PER_POINT = 2
SPEED_DODGE_CAP = 15

ACCURACY_BASE = 100
SKILL_ACCURACY_CAP = 90

ASCENSION_HP_MULT = {0: 1.0, 1: 0.9, 2: 0.8}
ASCENSION_MP_MULT = {0: 1.0, 1: 0.95, 2: 0.85}

LOOT_GOLD_MIN_MULT = 3
LOOT_GOLD_MAX_MULT = 8
LOOT_CONSUMABLE_CHANCE = 0.3
LOOT_WEAPON_CHANCE = 0.5
LOOT_ARMOR_CHANCE = 0.65
LOOT_EMPTY_CHANCE = 1.0

MONSTER_COUNT_MIN = 3
MONSTER_COUNT_MAX = 5
TREASURE_COUNT_MIN = 1
TREASURE_COUNT_MAX = 3
NPC_COUNT_MIN = 1
NPC_COUNT_MAX = 3

ROOM_TYPES_WEIGHT_EMPTY = 0.3

LEVEL_REQ_WARRIOR = [1, 1, 3, 5, 7]
LEVEL_REQ_ROGUE = [1, 1, 3, 5, 7]
LEVEL_REQ_MAGE = [1, 1, 3, 5, 7]
LEVEL_REQ_PALADIN = [1, 1, 3, 5, 7]

ABILITY_COOLDOWNS = {
    "war_cry": 4,
    "shield_bash": 3,
    "cleave": 3,
    "battle_stance": 5,
    "execute": 6,
    "backstab": 4,
    "poison_dagger": 3,
    "smoke_bomb": 4,
    "steal": 3,
    "assassinate": 7,
    "fireball": 3,
    "ice_shield": 4,
    "lightning": 3,
    "heal": 5,
    "arcane_blast": 6,
    "holy_smite": 3,
    "bless": 5,
    "divine_shield": 4,
    "lay_on_hands": 6,
    "retribution": 5,
}

CHEST_TIER_NAMES = {
    1: "Common",
    2: "Uncommon",
    3: "Rare",
    4: "Epic",
    5: "Legendary",
    6: "Mythic",
}

CHEST_TIER_TABLE = {
    1: [0.65, 0.25, 0.07, 0.025, 0.004, 0.001],
    2: [0.35, 0.35, 0.18, 0.08, 0.03, 0.01],
    3: [0.12, 0.30, 0.32, 0.16, 0.08, 0.02],
    4: [0.04, 0.16, 0.30, 0.30, 0.14, 0.06],
    5: [0.01, 0.08, 0.22, 0.32, 0.26, 0.11],
}

BONUS_CHEST_TIER_PROBS = [0.005, 0.03, 0.12, 0.28, 0.35, 0.215]

RELIC_TIER_TABLE = {
    1: [0.65, 0.25, 0.07, 0.025, 0.004, 0.001],
    2: [0.40, 0.32, 0.18, 0.07, 0.025, 0.005],
    3: [0.20, 0.30, 0.28, 0.15, 0.055, 0.015],
    4: [0.08, 0.20, 0.30, 0.25, 0.12, 0.05],
    5: [0.03, 0.10, 0.25, 0.30, 0.22, 0.10],
}

BONUS_RELIC_TIER_PROBS = [0.01, 0.05, 0.15, 0.28, 0.32, 0.19]

LOOT_BAG_DROP_CHANCE = 0.4
KEY_DROP_CHANCE = 0.3
KEY_FROM_BAG_CHANCE = 0.25

LOOT_BAG_TIER_TABLE = {
    1: [0.55, 0.25, 0.12, 0.055, 0.025],
    2: [0.40, 0.30, 0.18, 0.08, 0.04],
    3: [0.25, 0.30, 0.25, 0.13, 0.07],
    4: [0.15, 0.25, 0.28, 0.20, 0.12],
    5: [0.08, 0.18, 0.28, 0.26, 0.20],
}

BONUS_LOOT_BAG_TIER_PROBS = [0.05, 0.12, 0.22, 0.30, 0.31]

LOOT_BAG_TIER_NAMES = {
    1: "Common",
    2: "Rare",
    3: "Epic",
    4: "Legendary",
    5: "Mythic",
}

LOOT_BAG_TIER_GOLD = {
    1: (2, 5),
    2: (3, 7),
    3: (4, 9),
    4: (5, 11),
    5: (6, 14),
}

LOOT_BAG_TIER_CONTENTS = {
    1: {"consumable": 0.35, "weapon": 0.10, "armor": 0.05, "accessory": 0.00, "relic": 0.00},
    2: {"consumable": 0.40, "weapon": 0.12, "armor": 0.08, "accessory": 0.02, "relic": 0.00},
    3: {"consumable": 0.45, "weapon": 0.15, "armor": 0.10, "accessory": 0.04, "relic": 0.01},
    4: {"consumable": 0.50, "weapon": 0.18, "armor": 0.12, "accessory": 0.06, "relic": 0.03},
    5: {"consumable": 0.55, "weapon": 0.20, "armor": 0.15, "accessory": 0.08, "relic": 0.05},
}

RELIC_TIER_NAMES = {
    1: "Common",
    2: "Uncommon",
    3: "Rare",
    4: "Epic",
    5: "Legendary",
    6: "Mythic",
}

RELIC_CURSE_CHANCE = 0.20
