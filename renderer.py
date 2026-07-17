import os
from player import CLASSES, LORE_ENTRIES, MEMORY_FRAGMENTS
from status import format_statuses


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_separator(char="=", length=50):
    print(char * length)


def print_header(text, char="="):
    print_separator(char)
    print(f"  {text}")
    print_separator(char)


def make_bar(current, maximum, length=20, fill="#", empty="-"):
    filled = int(current / maximum * length) if maximum > 0 else 0
    return f"[{fill * filled}{empty * (length - filled)}] {current}/{maximum}"


def print_combat_ui(player, enemy, intent=None):
    print()
    enemy_status = format_statuses(enemy.get("statuses", []))
    status_str = f"  [{enemy_status}]" if enemy_status else ""
    print(f"  {enemy['name']}  HP: {make_bar(enemy['hp'], enemy.get('max_hp', enemy['hp']))}{status_str}")

    if intent:
        if intent["type"] == "stunned":
            print(f"  Intent: Stunned (cannot act)")
        elif intent["type"] == "ability":
            abil = intent["ability"]
            print(f"  Intent: {abil.get('name', 'Skill')} ({abil.get('type', 'special')})")
        else:
            print(f"  Intent: Basic Attack")

    player_status = format_statuses(player.statuses)
    pstatus_str = f"  [{player_status}]" if player_status else ""
    print(f"  {player.name}     HP: {make_bar(player.hp, player.max_hp)}{pstatus_str}")
    print(f"  {' ' * len(player.name)}  MP: {make_bar(player.mp, player.max_mp)}")
    extra_stats = f"SPD: {player.speed}  ACC: {player.accuracy}  Crit: {player.crit}%"
    if player.lifesteal > 0:
        extra_stats += f"  LS: {player.lifesteal}%"
    if player.thorns > 0:
        extra_stats += f"  Thorns: {player.thorns}"
    print(f"  {' ' * len(player.name)}  {extra_stats}")
    print()
    print("  [a] Attack  [d] Defend  [i] Inspect  [u] Use  [r] Run")

    available = player.get_available_abilities()
    if available:
        for key, ab in available.items():
            cd = player.cooldowns.get(key, 0)
            mp_cost = ab.get("mp_cost", 0)
            status = ""
            if cd > 0:
                status = f" (CD:{cd})"
            elif player.mp < mp_cost:
                status = " (NO MP)"
            print(f"  [{key[0]}] {ab['name']}{status}")


def print_shop_ui(player, npc, shop_items):
    print_header(f"  {npc['name']}'s Shop")
    print(f"  Your Gold: {player.gold}")
    print()
    for i, item in enumerate(shop_items, 1):
        itype = item.get("type", "")
        if itype == "weapon":
            stat = f"ATK+{item.get('atk', 0)}"
        elif itype == "armor":
            stat = f"DEF+{item.get('def', 0)}"
        else:
            stat = item.get("description", "")[:30]
        print(f"  {i}. {item['name']:<20} {stat:<20} {item['buy_price']}g")
    print()
    print("  Type: buy <number> to purchase")
    print("  Type: sell to browse and sell from inventory")
    print("  Type: leave to exit shop")


def _build_map_grid(rooms, player_pos, min_x, max_x, min_y, max_y, explored=None, fog_of_war=False):
    grid = []
    for y in range(min_y, max_y + 1):
        row_cells = []
        for x in range(min_x, max_x + 1):
            pos = (x, y)
            if pos == player_pos:
                row_cells.append("@")
            elif pos in rooms:
                if explored is not None and pos not in explored:
                    if fog_of_war:
                        connected = _is_connected(rooms, player_pos, pos)
                        if connected:
                            row_cells.append("?")
                        else:
                            row_cells.append(None)
                    else:
                        row_cells.append(None)
                else:
                    row_cells.append(_room_symbol(rooms[pos]))
            else:
                row_cells.append(None)
        grid.append(row_cells)
    return grid


def _is_connected(rooms, player_pos, target_pos):
    px, py = player_pos
    tx, ty = target_pos
    dx = tx - px
    dy = ty - py
    if abs(dx) + abs(dy) != 1:
        return False
    room = rooms.get(player_pos)
    if not room:
        return False
    if dx == 1:
        return room.doors.get("east", False)
    elif dx == -1:
        return room.doors.get("west", False)
    elif dy == 1:
        return room.doors.get("south", False)
    elif dy == -1:
        return room.doors.get("north", False)
    return False


def _render_grid(rooms, grid, min_x, min_y):
    lines = []
    for gy, row_cells in enumerate(grid):
        y = min_y + gy
        row_str = ""
        for gx, cell in enumerate(row_cells):
            x = min_x + gx
            has_room = cell is not None
            if has_room:
                row_str += f" {cell} "
            else:
                row_str += "   "

            if gx < len(row_cells) - 1:
                next_has_room = row_cells[gx + 1] is not None
                if has_room and next_has_room:
                    room = rooms.get((x, y))
                    if room and room.doors.get("east"):
                        row_str += "-"
                    else:
                        row_str += " "
                else:
                    row_str += " "
        lines.append(("row", row_str))

        if gy < len(grid) - 1:
            col_str = ""
            for gx, cell in enumerate(row_cells):
                x = min_x + gx
                has_room = cell is not None
                next_has_room = grid[gy + 1][gx] is not None
                if has_room and next_has_room:
                    room = rooms.get((x, y))
                    v = "|" if room and room.doors.get("south") else " "
                else:
                    v = " "
                col_str += f"  {v}"
                if gx < len(row_cells) - 1:
                    col_str += " "
            lines.append(("col", col_str))

    return lines


def _grid_width(lines):
    return max(len(c) for _, c in lines) if lines else 0


def _calc_map_bounds(center, radius=2, min_val=0, max_val=5):
    return (
        max(min_val, center[0] - radius),
        min(max_val, center[0] + radius),
        max(min_val, center[1] - radius),
        min(max_val, center[1] + radius),
    )


def print_dungeon_map(rooms, player_pos, explored, floor):
    print_header(f"  Floor {floor} Map")

    min_x = max(0, min(k[0] for k in explored) - 1)
    max_x = min(5, max(k[0] for k in explored) + 1)
    min_y = max(0, min(k[1] for k in explored) - 1)
    max_y = min(5, max(k[1] for k in explored) + 1)

    grid = _build_map_grid(rooms, player_pos, min_x, max_x, min_y, max_y, explored=explored)
    lines = _render_grid(rooms, grid, min_x, min_y)

    print()
    for _, content in lines:
        print(content)

    print()
    print("    W ")
    print("  A<>D")
    print("    S ")
    print()
    print("  Legend: @=You  E=Enemy  $=Treasure  !=Mimic  S=Shop")
    print("         N=NPC  T=Trap  >=Stairs  B=Boss  L=Locked Door")


def print_minimap(rooms, player_pos, explored, floor):
    min_x, max_x, min_y, max_y = _calc_map_bounds(player_pos)

    grid = _build_map_grid(rooms, player_pos, min_x, max_x, min_y, max_y, explored, fog_of_war=True)
    lines = _render_grid(rooms, grid, min_x, min_y)

    print()
    print(f"  [Mini-map]  Floor {floor}")
    for _, content in lines:
        print(content)

    print()
    print("    W ")
    print("  A<>D")
    print("    S ")


ROOM_SYMBOLS = {
    "monster": "E",
    "treasure": "$",
    "mimic": "!",
    "shop": "S",
    "npc": "N",
    "trap": "T",
    "stairs": ">",
    "boss": "B",
    "gatekeeper": "B",
    "locked_door": "L",
}


def _room_symbol(room):
    return ROOM_SYMBOLS.get(room.room_type, ".")


def print_class_selection(ascension=0):
    clear_screen()
    print()
    print_header("DUNGEON CRAWL")
    print()
    if ascension > 0:
        print(f"  ASCENSION {ascension} - The cycle continues.")
        print(f"  Enemies are stronger. You are weaker.")
        if ascension >= 2:
            print(f"  Memories of past cycles haunt you.")
        print()
    print("  A dark dungeon stretches before you.")
    print("  Five floors deep. An ancient dragon guards the bottom.")
    print("  Many have entered. None have returned.")
    print()
    print_header("Choose Your Hero", "-")
    print()
    print("  1. WARRIOR - High HP, heavy armor, axes (1.5x dmg)")
    print(f"     Wish: \"{CLASSES['warrior']['wish']}\"")
    print(f"     Abilities: War Cry, Shield Bash, Cleave, Battle Stance, Execute")
    print()
    print("  2. ROGUE   - High ATK, daggers (1.5x dmg + crits)")
    print(f"     Wish: \"{CLASSES['rogue']['wish']}\"")
    print(f"     Abilities: Backstab, Poison Blade, Smoke Bomb, Steal, Assassinate")
    print()
    print("  3. MAGE    - Spells, staffs (1.5x dmg), ranged magic")
    print(f"     Wish: \"{CLASSES['mage']['wish']}\"")
    print(f"     Abilities: Fireball, Ice Shield, Heal, Lightning Bolt, Mana Shield")
    print()
    print("  4. PALADIN - Balanced, holy swords (1.5x dmg)")
    print(f"     Wish: \"{CLASSES['paladin']['wish']}\"")
    print(f"     Abilities: Holy Smite, Bless, Lay on Hands, Retribution, Divine Shield")
    print()
    print_separator("-", 50)
    print()


def print_wish_screen(player, can_destroy=False):
    clear_screen()
    print()
    print_header("The Grail of Valdris")
    print()
    print("  You stand before the Grail. It pulses with power.")
    print('  It whispers: "Make your wish."')
    print()
    wish = CLASSES[player.class_key]["wish"]
    print(f"  1. {wish}")
    if can_destroy:
        print("  2. DESTROY THE GRAIL")
    print()


def print_wish_outcome(lines):
    clear_screen()
    print()
    print_header("The Grail Speaks")
    print()
    for line in lines:
        print(f"  {line}")
    print()
    input("  Press Enter...")


def print_true_ending(lines):
    clear_screen()
    print()
    for line in lines:
        print(f"  {line}")
    print()
    input("  Press Enter...")


def print_lore_menu(lore_entries_found, ascension):
    clear_screen()
    print()
    print_header("Chronicles of Valdris")
    print()
    print("  1. World Lore")
    print("  2. Class Lore")
    if ascension >= 2:
        print(f"  3. Memory Fragments ({len([e for e in lore_entries_found if e.startswith('memory_')])}/8)")
    print()
    print("  0. Back")
    print()


def print_world_lore(lore_entries_found):
    clear_screen()
    print()
    print_header("World Lore")
    print()
    entries = LORE_ENTRIES["world"]
    for i, entry in enumerate(entries, 1):
        key = f"world_{i}"
        if key in lore_entries_found:
            print(f"  {i}. {entry['title']}")
            print(f"     {entry['text']}")
            print()
        else:
            print(f"  {i}. ???")
            print()
    print("  Press Enter to go back.")
    input("  > ")


def print_class_lore(player_class, lore_entries_found):
    clear_screen()
    print()
    print_header("Class Lore")
    print()
    class_map = {"warrior": 0, "rogue": 1, "mage": 2, "paladin": 3}
    idx = class_map.get(player_class, 0)
    entry = LORE_ENTRIES["class"][idx]
    key = f"class_{player_class}"
    if key in lore_entries_found:
        print(f"  {entry['title']}")
        print(f"  {entry['text']}")
    else:
        print("  ???")
    print()
    print("  Press Enter to go back.")
    input("  > ")


def print_memory_fragments(lore_entries_found):
    clear_screen()
    print()
    print_header("Memory Fragments")
    print()
    count = 0
    for i in range(8):
        key = f"memory_{i}"
        if key in lore_entries_found:
            print(f"  Fragment {i + 1}:")
            print(f"  {MEMORY_FRAGMENTS[i]}")
            print()
            count += 1
    if count == 0:
        print("  No memory fragments found yet.")
    print("  Press Enter to go back.")
    input("  > ")


def print_death_screen(player):
    clear_screen()
    print()
    print_header("YOU HAVE FALLEN")
    print()
    print(f"  {player.name} the {player.class_name} has perished.")
    print(f"  Reached floor {player.floor}, level {player.level}.")
    print(f"  Enemies slain: {sum(player.kills.values())}")
    print()
    print("  The dungeon claims another soul...")
    print()


def print_victory_screen(player, ascension):
    clear_screen()
    print()
    print_header("VICTORY!")
    print()
    print(f"  {player.name} the {player.class_name} has conquered the dungeon!")
    print(f"  The Elder Dragon is defeated!")
    print(f"  Final Level: {player.level}")
    print(f"  Enemies Slain: {sum(player.kills.values())}")
    print()
    if ascension == 0:
        print("  But something awaits beyond victory...")
        print("  The Grail. It calls to you.")
    elif ascension == 1:
        print("  The cycle continues...")
        print("  But you are beginning to remember.")
    print()


def print_ascension_unlock(new_ascension):
    clear_screen()
    print()
    print_header("ASCENSION UNLOCKED")
    print()
    if new_ascension == 1:
        print("  The Grail has granted your wish.")
        print("  But the wish was never what you wanted.")
        print("  The cycle begins again.")
        print()
        print("  ASCENSION 1 UNLOCKED")
        print("  Enemies will be stronger. You will be weaker.")
        print("  But you will remember more.")
    elif new_ascension == 2:
        print("  The Grail has granted your wish again.")
        print("  The same wish. The same outcome. The same regret.")
        print("  But this time... you remember.")
        print()
        print("  ASCENSION 2 UNLOCKED")
        print("  A new option awaits at the Grail.")
        print("  Destroy it. End the cycle.")
    print()
    input("  Press Enter...")
