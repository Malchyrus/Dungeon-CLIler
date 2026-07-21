import random
from room import Room, LORE_NOTES
from items import random_loot, random_artifact, roll_chest_tier
from constants import LOOT_GOLD_MIN_MULT, LOOT_GOLD_MAX_MULT
from enemies import spawn_enemy, spawn_boss, spawn_bonus_enemy, spawn_bonus_boss, spawn_gatekeeper
from npc import get_random_npc, get_celdric_npc
from player import MEMORY_FRAGMENTS


GRID_SIZE = 6
ROOM_COUNT_MIN = 12
ROOM_COUNT_MAX = 16


def _generate_grid(room_count, grid_size=GRID_SIZE):
    start_x = random.randint(1, grid_size - 2)
    start_y = random.randint(1, grid_size - 2)

    placed = {(start_x, start_y)}
    positions = [(start_x, start_y)]

    while len(placed) < room_count:
        cx, cy = random.choice(positions)
        dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and (nx, ny) not in placed:
                placed.add((nx, ny))
                positions.append((nx, ny))
                break

    return list(placed), (start_x, start_y)


def _find_farthest(rooms, start):
    farthest = start
    max_dist = 0
    for pos in rooms:
        dist = abs(pos[0] - start[0]) + abs(pos[1] - start[1])
        if dist > max_dist:
            max_dist = dist
            farthest = pos
    return farthest


def generate_dungeon(floor, ascension=0, variant=None):
    rooms = {}
    room_count = random.randint(ROOM_COUNT_MIN, ROOM_COUNT_MAX)

    room_list, start = _generate_grid(room_count)

    for x, y in room_list:
        rooms[(x, y)] = Room(x, y, "empty", floor)

    _fix_doors(rooms)

    start_room = rooms[start]
    start_room.room_type = "empty"
    start_room.description = "The entrance to the dungeon. Cold air rushes past you."
    start_room.cleared = True
    start_room.visited = True

    farthest = _find_farthest(room_list, start)

    total_enemy_gold = 0

    if floor < 5:
        rooms[farthest].room_type = "stairs"
        rooms[farthest].description = random.choice([
            "A spiral staircase descends into darkness below.",
            "Stone steps lead down. Cold air rises from the depths.",
            "A shaft in the floor reveals a ladder going deeper.",
        ])

        sx, sy = farthest
        adjacent_empty = []
        for dx, dy, direction in [(0, -1, "north"), (0, 1, "south"), (-1, 0, "west"), (1, 0, "east")]:
            nx, ny = sx + dx, sy + dy
            if (nx, ny) in rooms and rooms[(nx, ny)].room_type == "empty" and (nx, ny) != start:
                adjacent_empty.append(((nx, ny), direction))

        if adjacent_empty:
            (bx, by), entry_dir = random.choice(adjacent_empty)
            rooms[(bx, by)].room_type = "gatekeeper"
            rooms[(bx, by)].enemy = spawn_gatekeeper(floor, ascension)
            total_enemy_gold += rooms[(bx, by)].enemy.get("gold", 0)
            rooms[(bx, by)].description = random.choice([
                "A dark presence pervades this chamber. The air tastes of iron.",
                "This room radiates dread. Something powerful lurks here.",
                "The walls are scarred with claw marks. A guardian awaits.",
                "An oppressive force presses down on you. The way forward is guarded.",
            ])

            for d in rooms[farthest].doors:
                rooms[farthest].doors[d] = False
            rooms[farthest].doors[entry_dir] = True
            opposite = {"north": "south", "south": "north", "east": "west", "west": "east"}
            rooms[(bx, by)].doors[opposite[entry_dir]] = True

            for dx, dy, direction in [(0, -1, "north"), (0, 1, "south"), (-1, 0, "west"), (1, 0, "east")]:
                nx, ny = sx + dx, sy + dy
                if (nx, ny) in rooms and (nx, ny) != (bx, by):
                    rooms[(nx, ny)].doors[opposite[direction]] = False

            room_list = [(x, y) for (x, y) in room_list if (x, y) != (bx, by) and (x, y) != farthest]
        else:
            room_list = [(x, y) for (x, y) in room_list if (x, y) != farthest]

    if floor == 2:
        locked_candidates = [p for p in room_list if p != start and p != farthest and rooms[p].room_type == "empty"]
        if locked_candidates:
            locked_pos = random.choice(locked_candidates)
            rooms[locked_pos].room_type = "locked_door"
            rooms[locked_pos].description = random.choice([
                "A massive iron door with a skeleton-shaped keyhole seals the passage below.",
                "Iron bars block a staircase downward. A skeleton lock holds them shut.",
                "A reinforced door blocks the way. The keyhole is shaped like a skull.",
                "Ancient iron bars block a descending stairway. They radiate cold energy.",
            ])

    assignable = [p for p in room_list if p != start and rooms[p].room_type == "empty"]
    random.shuffle(assignable)

    idx = 0

    monster_count = min(len(assignable), random.randint(3, 5))
    for i in range(monster_count):
        if idx < len(assignable):
            pos = assignable[idx]
            rooms[pos].room_type = "monster"
            rooms[pos].enemy = spawn_enemy(floor, ascension, variant=variant)
            total_enemy_gold += rooms[pos].enemy.get("gold", 0)
            idx += 1

    treasure_count = min(len(assignable) - idx, 2)
    chest_types = ["equipment", "relic"]
    for i in range(treasure_count):
        if idx < len(assignable):
            pos = assignable[idx]
            rooms[pos].room_type = "treasure"
            chest_tier = roll_chest_tier(floor)
            rooms[pos].chest = {"type": chest_types[i], "tier": chest_tier}
            idx += 1

    total_enemy_gold += treasure_count * floor * (LOOT_GOLD_MIN_MULT + LOOT_GOLD_MAX_MULT) // 2

    npc_pool = ["merchant", "quest_giver", "lore", "trapped", "healer", "item_trader", "key_trader", "map_seeker"]
    npc_count = min(len(assignable) - idx, random.randint(1, 3))
    for i in range(npc_count):
        if idx < len(assignable):
            pos = assignable[idx]
            rooms[pos].room_type = "npc"
            npc_type = random.choice(npc_pool)
            rooms[pos].npc = get_random_npc(npc_type)
            idx += 1

    if floor >= 5:
        boss_count = min(len(assignable) - idx, 1)
        for i in range(boss_count):
            if idx < len(assignable):
                pos = assignable[idx]
                rooms[pos].room_type = "boss"
                rooms[pos].enemy = spawn_boss(floor, ascension)
                idx += 1

    if ascension >= 2:
        lore_positions = [p for p in assignable[idx:] if rooms[p].room_type == "empty"]
        random.shuffle(lore_positions)
        fragment_count = min(len(lore_positions), 2, len(MEMORY_FRAGMENTS))
        used_fragments = random.sample(MEMORY_FRAGMENTS, fragment_count)
        for i in range(fragment_count):
            rooms[lore_positions[i]].memory_fragment = used_fragments[i]

    for pos in room_list:
        if rooms[pos].room_type == "empty" and random.random() < 0.3:
            rooms[pos].lore_note = random.choice(LORE_NOTES)

    return rooms, start, farthest, total_enemy_gold


def generate_bonus_floor(ascension=0):
    rooms = {}
    room_count = random.randint(6, 8)

    room_list, start = _generate_grid(room_count)

    for x, y in room_list:
        rooms[(x, y)] = Room(x, y, "empty", 2)

    _fix_doors(rooms)

    start_room = rooms[start]
    start_room.room_type = "empty"
    start_room.description = "You descend into the sealed depths. The air is thick with ancient power."
    start_room.cleared = True
    start_room.visited = True

    farthest = _find_farthest(room_list, start)

    rooms[farthest].room_type = "stairs"
    rooms[farthest].description = "A staircase descends to the floor below. The sealed guardian's power fades."

    assignable = [p for p in room_list if p != start and p != farthest]
    random.shuffle(assignable)

    idx = 0
    monster_count = min(len(assignable), random.randint(3, 4))
    for i in range(monster_count):
        if idx < len(assignable):
            pos = assignable[idx]
            rooms[pos].room_type = "monster"
            rooms[pos].enemy = spawn_bonus_enemy(ascension)
            idx += 1

    treasure_count = min(len(assignable) - idx, 2)
    chest_types = ["equipment", "relic"]
    for i in range(treasure_count):
        if idx < len(assignable):
            pos = assignable[idx]
            rooms[pos].room_type = "treasure"
            chest_tier = roll_chest_tier(5, is_bonus=True)
            rooms[pos].chest = {"type": chest_types[i], "tier": chest_tier}
            idx += 1

    if idx < len(assignable):
        pos = assignable[idx]
        rooms[pos].room_type = "boss"
        rooms[pos].enemy = spawn_bonus_boss(ascension)
        idx += 1

    for pos in room_list:
        if rooms[pos].room_type == "empty" and random.random() < 0.4:
            rooms[pos].lore_note = random.choice(LORE_NOTES)

    return rooms, start


def place_celdric(rooms):
    npc_rooms = [pos for pos, room in rooms.items() if room.room_type == "npc"]
    if npc_rooms:
        pos = random.choice(npc_rooms)
        rooms[pos].npc = get_celdric_npc()
        return pos
    empty_rooms = [pos for pos, room in rooms.items() if room.room_type == "empty" and room.visited is False]
    if empty_rooms:
        pos = random.choice(empty_rooms)
        rooms[pos].room_type = "npc"
        rooms[pos].npc = get_celdric_npc()
        return pos
    return None


def _fix_doors(rooms):
    for pos, room in rooms.items():
        x, y = pos
        for dx, dy, direction in [(0, -1, "north"), (0, 1, "south"), (-1, 0, "west"), (1, 0, "east")]:
            nx, ny = x + dx, y + dy
            if (nx, ny) in rooms:
                room.doors[direction] = True
            else:
                room.doors[direction] = False
