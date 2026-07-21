#!/usr/bin/env python3
"""
DUNGEON CRAWL - Fantasy Dungeon Crawler
"""

import sys
import os
import random

from player import Player, CLASSES, WISH_OUTCOMES, TRUE_ENDING, MEMORY_FRAGMENTS
from dungeon import generate_dungeon, generate_bonus_floor, place_celdric
from room import Room
from combat import combat_round, use_item_in_combat, _get_enemy_intent
from enemies import get_loot
from items import random_loot
from data_loader import load_json
from inventory import add_item, use_item, drop_item, show_inventory
from save_load import save_game, load_game, has_save, delete_save
from npc_types import wrap_npc
from constants import CELDRIC_PRICE_FRACTION
from renderer import (
    clear_screen, print_separator, print_header,
    print_combat_ui, print_dungeon_map, print_minimap,
    print_class_selection, print_death_screen, print_victory_screen,
    print_wish_screen, print_wish_outcome, print_true_ending,
    print_lore_menu, print_world_lore, print_class_lore,
    print_memory_fragments, print_ascension_unlock,
)


class Game:
    def __init__(self):
        self.player = None
        self.rooms = {}
        self.running = True
        self.current_room = None
        self.ascension = 0
        self.lore_entries = []
        self.pre_generated_floors = {}
        self.floor_gold_totals = {}
        self.floor_variants = {}
        self.celdric_floor = None
        self.celdric_price = 0
        self.bonus_floor = None
        self.has_key = False
        self.on_bonus_floor = False

    def run(self):
        while self.running:
            self.main_menu()

    def main_menu(self):
        clear_screen()
        print()
        print_header("DUNGEON CRAWL")
        print()
        has_save_file = has_save()

        if self.ascension > 0:
            print(f"  Ascension {self.ascension}")
            print()

        if has_save_file:
            print("  1. New Game")
            print("  2. Continue")
            print("  3. Delete Save")
            if self.ascension >= 2:
                print("  4. Lore Menu")
                print("  5. Quit")
            else:
                print("  4. Quit")
        else:
            print("  1. New Game")
            if self.ascension >= 2:
                print("  2. Lore Menu")
                print("  3. Quit")
            else:
                print("  2. Quit")
        print()

        choice = input("  > ").strip()

        if choice == "1":
            self.new_game()
        elif choice == "2":
            if has_save_file:
                self.load_game()
            elif self.ascension >= 2:
                self.show_lore_menu()
            else:
                self.running = False
        elif choice == "3":
            if has_save_file:
                delete_save()
                print("  Save deleted.")
                input("  Press Enter...")
            elif self.ascension >= 2:
                self.running = False
        elif choice == "4":
            if has_save_file:
                if self.ascension >= 2:
                    self.show_lore_menu()
                else:
                    self.running = False
        elif choice == "5" and has_save_file and self.ascension >= 2:
            self.running = False
        elif choice == "q":
            self.running = False

    def new_game(self):
        print_class_selection(self.ascension)

        while True:
            choice = input("  > ").strip()
            if choice in ("1", "2", "3", "4"):
                class_keys = ["warrior", "rogue", "mage", "paladin"]
                class_key = class_keys[int(choice) - 1]
                break
            print("  Invalid choice. Enter 1-4.")

        name = input("\n  Enter your name: ").strip()
        if not name:
            name = CLASSES[class_key]["name"]

        self.player = Player(name, class_key)

        if self.ascension >= 2:
            self.player.hp = int(self.player.hp * 0.8)
            self.player.max_hp = int(self.player.max_hp * 0.8)
            self.player.mp = int(self.player.mp * 0.85)
            self.player.max_mp = int(self.player.max_mp * 0.85)
        elif self.ascension >= 1:
            self.player.hp = int(self.player.hp * 0.9)
            self.player.max_hp = int(self.player.max_hp * 0.9)
            self.player.mp = int(self.player.mp * 0.95)
            self.player.max_mp = int(self.player.max_mp * 0.95)

        self.pre_generated_floors = {}
        self.floor_gold_totals = {}
        self.floor_variants = {}
        self.bonus_floor = None
        self.has_key = False
        self.on_bonus_floor = False

        rooms1, start1, _, gold1 = generate_dungeon(1, self.ascension)
        self.pre_generated_floors[1] = (rooms1, start1)
        self.floor_gold_totals[1] = gold1

        variant2 = random.choice(["standard", "alt"])
        self.floor_variants[2] = variant2
        rooms2, start2, locked_pos2, gold2 = generate_dungeon(2, self.ascension, variant=variant2)
        self.pre_generated_floors[2] = (rooms2, start2)
        self.floor_gold_totals[2] = gold2

        self.celdric_floor = random.choice([1, 2])
        cumulative_gold = sum(self.floor_gold_totals[f] for f in range(1, self.celdric_floor + 1))
        self.celdric_price = int(cumulative_gold * CELDRIC_PRICE_FRACTION)

        celdric_rooms, celdric_start = self.pre_generated_floors[self.celdric_floor]
        place_celdric(celdric_rooms)

        self.start_floor(1)

    def start_floor(self, floor):
        self.player.floor = floor

        if self.on_bonus_floor and self.bonus_floor:
            self.rooms, start_pos = self.bonus_floor
        elif floor in self.pre_generated_floors:
            self.rooms, start_pos = self.pre_generated_floors[floor]
        else:
            variant = None
            if floor == 4:
                variant = random.choice(["standard", "alt"])
                self.floor_variants[floor] = variant
            elif floor in self.floor_variants:
                variant = self.floor_variants[floor]
            self.rooms, start_pos, _, _ = generate_dungeon(floor, self.ascension, variant=variant)
            self.pre_generated_floors[floor] = (self.rooms, start_pos)

        self.player.x, self.player.y = start_pos
        self.player.explored = set()
        self.player.explored.add(start_pos)
        self.current_room = self.rooms[start_pos]

        clear_screen()
        print()
        if self.on_bonus_floor:
            print_header("Floor 2.5 — The Sealed Depths")
            print()
            print("  You descend into the sealed passage. Ancient power pulses around you.")
        else:
            print_header(f"Floor {floor} Descends...")
            print()
            if floor == 1:
                print("  You descend into the dungeon. The air is thick and cold.")
            elif floor == 5:
                print("  The deepest floor. The dragon's presence shakes the walls.")
            else:
                print(f"  Floor {floor}. The dungeon grows more dangerous.")
        if self.ascension > 0:
            print(f"  [Ascension {self.ascension}]")
        print()
        input("  Press Enter...")

        self.game_loop()

    def game_loop(self):
        while self.running:
            room = self.rooms.get((self.player.x, self.player.y))
            if room is None:
                break

            self.current_room = room
            room.visited = True
            self.player.explored.add((self.player.x, self.player.y))

            if room.enemy and not room.cleared:
                result = self.combat_encounter()
                if result == "dead":
                    return
                if result == "victory":
                    room.cleared = True
                    room.enemy = None
                    continue

            if room.memory_fragment and self.ascension >= 2:
                key = f"memory_{MEMORY_FRAGMENTS.index(room.memory_fragment)}"
                if key not in self.lore_entries:
                    self.lore_entries.append(key)
                    clear_screen()
                    print()
                    print_header("Memory Fragment")
                    print()
                    print(f"  {room.memory_fragment}")
                    print()
                    print("  This memory is now recorded in your lore journal.")
                    input("  Press Enter...")
                    room.memory_fragment = None

            clear_screen()
            print()
            if self.on_bonus_floor:
                floor_label = "2.5"
            else:
                floor_label = str(self.player.floor)
            print(f"  Floor {floor_label} | {self.player.name} HP: {self.player.hp}/{self.player.max_hp} MP: {self.player.mp}/{self.player.max_mp} Gold: {self.player.gold}")
            print_separator("-")
            print()
            print(room.describe(ascension=self.ascension))

            if room.room_type != "gatekeeper" and not room.cleared:
                px, py = self.player.x, self.player.y
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    adj = self.rooms.get((px + dx, py + dy))
                    if adj and adj.room_type == "gatekeeper" and not adj.cleared:
                        terror_texts = [
                            "A chill runs down your spine. Something powerful lurks nearby.",
                            "The air tastes of iron. A dark presence is close.",
                            "Your bones tremble. Death waits in the adjacent chamber.",
                            "Goosebumps cover your skin. A guardian guards the way forward.",
                        ]
                        print(f"\n  {random.choice(terror_texts)}")
                        break

            print()
            print_minimap(self.rooms, (self.player.x, self.player.y),
                          self._get_display_explored(), floor_label)

            cmd = input("  > ").strip().lower()
            if not cmd:
                continue

            if cmd in ("q", "quit", "exit"):
                self.running = False
                break

            handled = self._dispatch_command(cmd)
            if handled is False:
                break
            if handled is None:
                print(f"  Unknown command: {cmd}. Type 'help' for commands.")
                input("  Press Enter...")

    def _dispatch_command(self, cmd):
        simple = {
            "h": self.show_help,
            "help": self.show_help,
            "i": self.show_inventory_menu,
            "inventory": self.show_inventory_menu,
            "stats": self.show_stats,
            "st": self.show_stats,
            "map": self.show_map,
            "save": self.do_save,
            "save game": self.do_save,
            "scavenge": self.do_scavenge,
            "leave": lambda: (print("  You're not in a shop."), input("  Press Enter...")),
            "look": lambda: None,
        }

        if cmd in simple:
            simple[cmd]()
            return True

        if cmd.startswith("go ") or cmd in ("w", "a", "s", "d", "n", "e", "north", "south", "east", "west", "down"):
            self.do_move(cmd)
            return True
        if cmd.startswith("take "):
            self.do_take(cmd[5:])
            return True
        if cmd.startswith("open ") and "chest" in cmd:
            self.do_open_chest()
            return True
        if cmd.startswith("equip "):
            self.do_equip(cmd[6:])
            return True
        if cmd.startswith("use "):
            self.do_use(cmd[4:])
            return True
        if cmd.startswith("drop "):
            self.do_drop(cmd[5:])
            return True
        if cmd.startswith("talk "):
            self.do_talk(cmd[5:])
            return True

        return None

    def do_move(self, cmd):
        direction_map = {
            "w": "north", "a": "west", "s": "south", "d": "east",
            "n": "north", "e": "east",
            "north": "north", "south": "south", "east": "east", "west": "west",
        }

        if cmd.startswith("go "):
            direction = cmd[3:].strip()
        else:
            direction = direction_map.get(cmd, cmd)

        if direction == "down":
            if self.current_room.room_type == "stairs":
                gatekeeper_alive = False
                for pos, rm in self.rooms.items():
                    if rm.room_type == "gatekeeper" and not rm.cleared:
                        gatekeeper_alive = True
                        break
                if gatekeeper_alive:
                    clear_screen()
                    print()
                    print_header("The Way is Blocked")
                    print()
                    print("  A dark presence seals the stairs. You must defeat the guardian first.")
                    input("  Press Enter...")
                    return
                clear_screen()
                print()
                print_header("Descending deeper...")
                print()
                if self.on_bonus_floor:
                    self.on_bonus_floor = False
                    self.bonus_floor = None
                    input("  Press Enter...")
                    self.start_floor(3)
                    return
                next_floor = self.player.floor + 1
                if next_floor > 5:
                    print("  You've cleared all floors! But wait... something awaits below.")
                    input("  Press Enter...")
                    self.do_final_victory()
                    return
                input("  Press Enter...")
                self.start_floor(next_floor)
                return
            elif self.current_room.room_type == "locked_door":
                clear_screen()
                print()
                print_header("The Sealed Door")
                print()
                if self.has_key:
                    print("  The iron door groans as it swings open.")
                    print("  Behind it, a staircase descends into darkness.")
                    print("  The sealed depths await...")
                    input("  Press Enter...")
                    self.has_key = False
                    self.on_bonus_floor = True
                    self.bonus_floor = generate_bonus_floor(self.ascension)
                    self.start_floor(2)
                    return
                else:
                    print("  The iron door is sealed shut. You need a skeleton key.")
                    input("  Press Enter...")
            else:
                print("  There are no stairs here.")
                input("  Press Enter...")
                return

        if direction not in direction_map:
            print(f"  Invalid direction: {direction}")
            input("  Press Enter...")
            return

        direction = direction_map[direction]

        if not self.current_room.doors.get(direction):
            print(f"  You can't go {direction}. There's no exit that way.")
            input("  Press Enter...")
            return

        dx, dy = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[direction]
        nx, ny = self.player.x + dx, self.player.y + dy

        if (nx, ny) not in self.rooms:
            print("  You can't go that way.")
            input("  Press Enter...")
            return

        target_room = self.rooms[(nx, ny)]
        if target_room.locked:
            print(f"  The door is locked with a {target_room.locked} lock.")
            has_key = any(
                k.get("key_type") == target_room.locked
                for k in self.player.inventory
                if k.get("type") == "key"
            )
            if has_key:
                choice = input(f"  Use a {target_room.locked} key? (y/n) > ").strip().lower()
                if choice == "y":
                    for i, item in enumerate(self.player.inventory):
                        if item.get("type") == "key" and item.get("key_type") == target_room.locked:
                            self.player.inventory.pop(i)
                            print(f"  The {target_room.locked} key crumbles as the lock opens!")
                            target_room.locked = None
                            break
                else:
                    input("  Press Enter...")
                    return
            else:
                print("  You don't have the right key.")
                input("  Press Enter...")
                return

        self.player.x, self.player.y = nx, ny
        self.player.explored.add((nx, ny))

    def do_take(self, item_name):
        room = self.current_room
        if item_name.lower() == "all":
            if not room.items:
                print("  Nothing to take here.")
                input("  Press Enter...")
                return
            taken = []
            for item in list(room.items):
                success, msg = add_item(self.player, item)
                if success:
                    room.items.remove(item)
                    taken.append(item["name"])
                else:
                    print(f"  {msg}")
                    break
            if taken:
                print(f"  Picked up: {', '.join(taken)}")
            input("  Press Enter...")
            return

        found = None
        for item in room.items:
            if item_name.lower() in item["name"].lower():
                found = item
                break

        if found:
            success, msg = add_item(self.player, found)
            if success:
                room.items.remove(found)
            print(f"  {msg}")
        else:
            print(f"  No item called '{item_name}' here.")
        input("  Press Enter...")

    def do_scavenge(self):
        room = self.current_room
        if room.room_type != "empty" or room.enemy:
            print("  There's nothing to scavenge here.")
            input("  Press Enter...")
            return
        if room.cleared:
            print("  You've already searched this room.")
            input("  Press Enter...")
            return

        room.cleared = True
        clear_screen()
        print()
        print("  You search the room carefully...")
        print()

        roll = random.random()
        if roll < 0.10:
            gold = random.randint(2, 8 + self.player.floor * 2)
            self.player.gold += gold
            print(f"  You find {gold} gold hidden in the cracks!")
        elif roll < 0.50:
            data = load_json("items.json")
            scav_items = [v for v in data["consumables"].values() if v.get("scavenge_item")]
            if scav_items:
                item = dict(random.choice(scav_items))
                success, msg = add_item(self.player, item)
                if success:
                    print(f"  You find a {item['name']}! ({msg})")
                else:
                    print(f"  You find a {item['name']} but... {msg}")
            else:
                print("  You find nothing of value.")
        elif roll < 0.65:
            print("  You find some loose change. +3 gold.")
            self.player.gold += 3
        else:
            print("  You search thoroughly but find nothing useful.")

        print()
        input("  Press Enter...")

    def do_open_chest(self):
        room = self.current_room
        if not room.chest:
            print("  There's no chest here.")
            input("  Press Enter...")
            return

        if room.chest_opened:
            print("  You already opened this chest.")
            input("  Press Enter...")
            return

        has_key = any(
            k.get("type") == "key" and k.get("key_type") == "chest"
            for k in self.player.inventory
        )
        if not has_key:
            from constants import CHEST_TIER_NAMES
            tier_name = CHEST_TIER_NAMES.get(room.chest.get("tier", 1), "?")
            print(f"  The {tier_name} chest is locked. You need a Chest Key.")
            input("  Press Enter...")
            return

        for i, item in enumerate(self.player.inventory):
            if item.get("type") == "key" and item.get("key_type") == "chest":
                self.player.inventory.pop(i)
                break

        room.chest_opened = True
        chest_type = room.chest["type"]
        chest_tier = room.chest["tier"]

        if chest_type == "equipment":
            from items import random_equipment_chest
            loot = random_equipment_chest(self.player.floor, chest_tier, self.player)
        else:
            from items import random_relic_chest
            loot = random_relic_chest(self.player.floor, chest_tier)

        from constants import CHEST_TIER_NAMES
        tier_name = CHEST_TIER_NAMES.get(chest_tier, "?")
        print()
        print(f"  You unlock the {tier_name} chest...")
        for item in loot:
            if item.get("type") == "gold":
                gold = int(item["value"] * self.player.gold_mult)
                self.player.gold += gold
                print(f"  Found {gold} gold!")
            else:
                success, msg = add_item(self.player, item)
                print(f"  Found: {item['name']}! ({msg})")
                if self.player.double_item_chance > 0 and random.random() < self.player.double_item_chance:
                    success2, msg2 = add_item(self.player, item)
                    print(f"  Double loot! Found another: {item['name']}! ({msg2})")
        print()
        input("  Press Enter...")

    def _resolve_inventory_item(self, query):
        if not query:
            return None
        try:
            idx = int(query) - 1
            grouped = {}
            for item in self.player.inventory:
                key = item.get("name", "Unknown")
                if key not in grouped:
                    grouped[key] = item
            items = list(grouped.values())
            if 0 <= idx < len(items):
                return items[idx]
        except ValueError:
            pass
        for item in self.player.inventory:
            if query.lower() in item["name"].lower():
                return item
        return None

    def do_equip(self, item_name):
        found = self._resolve_inventory_item(item_name)
        if not found:
            print(f"  You don't have '{item_name}'.")
            input("  Press Enter...")
            return

        if found.get("type") not in ("weapon", "armor", "accessory", "relic"):
            print(f"  You can't equip {found['name']}.")
            input("  Press Enter...")
            return

        if found.get("type") == "relic":
            _, msg = self.player.equip_relic(found)
            for i, item in enumerate(self.player.inventory):
                if item.get("name") == found["name"]:
                    self.player.inventory.pop(i)
                    break
            print(f"  {msg}")
            input("  Press Enter...")
            return

        old, msg = self.player.equip(found)
        if old:
            add_item(self.player, old)
            for i, item in enumerate(self.player.inventory):
                if item.get("name") == found["name"]:
                    self.player.inventory.pop(i)
                    break
        else:
            if "can't equip" in str(msg):
                print(f"  {msg}")
                input("  Press Enter...")
                return
            for i, item in enumerate(self.player.inventory):
                if item.get("name") == found["name"]:
                    self.player.inventory.pop(i)
                    break

        print(f"  {msg}")
        input("  Press Enter...")

    def do_use(self, item_name):
        found = self._resolve_inventory_item(item_name)
        if not found:
            print(f"  You don't have '{item_name}'.")
            input("  Press Enter...")
            return

        if found.get("name", "").lower() == "skeleton key":
            if self.current_room.room_type == "locked_door":
                print("  You insert the skeleton key into the lock.")
                print("  The iron door groans as it swings open!")
                print("  Behind it, a staircase descends into the sealed depths.")
                self.has_key = True
                for i, item in enumerate(self.player.inventory):
                    if item.get("name", "").lower() == "skeleton key":
                        self.player.inventory.pop(i)
                        break
                input("  Press Enter...")
                return
            else:
                print("  There's no lock here to use this key on.")
                input("  Press Enter...")
                return

        if found.get("type") == "key" and found.get("key_type") == "chest":
            room = self.current_room
            if room.chest and not room.chest_opened:
                self.do_open_chest()
                return
            else:
                print("  There's no locked chest here.")
                input("  Press Enter...")
                return

        msg = use_item(self.player, found)
        print(f"  {msg}")
        input("  Press Enter...")

    def do_drop(self, item_name):
        found = self._resolve_inventory_item(item_name)
        if not found:
            print(f"  You don't have '{item_name}'.")
            input("  Press Enter...")
            return

        msg = drop_item(self.player, found)
        print(f"  {msg}")
        input("  Press Enter...")

    def do_talk(self, target):
        room = self.current_room
        if not room.npc:
            print("  There's nobody here to talk to.")
            input("  Press Enter...")
            return

        npc = room.npc
        name_lower = npc["name"].lower()
        if target.lower() not in name_lower and target.lower() != "npc":
            print(f"  {npc['name']} is here. Type 'talk {npc['name'].split()[0].lower()}' to talk.")
            input("  Press Enter...")
            return

        clear_screen()
        print()
        print_header(f"  {npc['name']}")
        print()

        npc_obj = wrap_npc(npc)
        npc_obj.interact(self.player, self)

        print()
        input("  Press Enter...")

    def combat_encounter(self):
        enemy = self.current_room.enemy
        if not enemy:
            return "victory"

        self.player._second_wind_used = False
        self.player._first_debuff_used = False

        clear_screen()
        print()
        print_header("COMBAT!")
        print(f"  A {enemy['name']} appears!")
        print(f"  {enemy.get('description', '')}")
        input("  Press Enter...")

        intent = _get_enemy_intent(enemy)

        first_turn = True
        extra_turn_pending = False
        while self.player.is_alive() and enemy["hp"] > 0:
            clear_screen()
            print()
            print_combat_ui(self.player, enemy, intent)
            print()

            cmd = input("  > ").strip().lower()

            action_result = None

            if cmd in ("a", "attack", ""):
                action_result = ("attack", None)
            elif cmd in ("d", "defend"):
                action_result = ("defend", None)
            elif cmd in ("i", "inspect"):
                clear_screen()
                print()
                print(self._inspect_enemy(enemy, intent))
                input("  Press Enter...")
                continue
            elif cmd in ("r", "run"):
                if random.random() < 0.5:
                    print("  You escaped!")
                    input("  Press Enter...")
                    return "escaped"
                else:
                    print("  Failed to escape!")
                    raw = enemy["atk"] + random.randint(-1, 2)
                    reduced = max(1, raw - self.player.defense)
                    self.player.hp = max(0, self.player.hp - reduced)
                    print(f"  The {enemy['name']} hits you for {reduced} as you try to flee!")
                    input("  Press Enter...")
                    continue
            elif cmd == "u":
                clear_screen()
                print(show_inventory(self.player))
                print()
                item_name = input("  Use which item? (name or #) > ").strip()
                try:
                    idx = int(item_name) - 1
                    grouped = {}
                    for item in self.player.inventory:
                        key = item.get("name", "Unknown")
                        if key not in grouped:
                            grouped[key] = item
                    item_list = list(grouped.values())
                    if 0 <= idx < len(item_list):
                        item = item_list[idx]
                        if item.get("type") == "consumable":
                            messages, used = use_item_in_combat(self.player, item)
                            for msg in messages:
                                print(f"  {msg}")
                        else:
                            print("  You can only use consumables in combat.")
                    else:
                        print("  Invalid selection.")
                except ValueError:
                    found = None
                    for item in self.player.inventory:
                        if item_name.lower() in item["name"].lower():
                            found = item
                            break
                    if found and found.get("type") == "consumable":
                        messages, _ = use_item_in_combat(self.player, found)
                        for msg in messages:
                            print(f"  {msg}")
                    else:
                        print("  Invalid item or can't use in combat.")
                input("  Press Enter...")
                continue
            elif cmd in [k[0] for k in self.player.abilities.keys()]:
                ability_key = None
                for k in self.player.abilities:
                    if cmd == k[0] or cmd == k:
                        ability_key = k
                        break
                if ability_key:
                    action_result = ("ability", ability_key)
                else:
                    print("  Invalid ability.")
                    input("  Press Enter...")
                    continue
            else:
                print("  Invalid command. [a]ttack, [d]efend, [u]se item, [r]un")
                input("  Press Enter...")
                continue

            if action_result:
                act, abil = action_result
                is_extra = extra_turn_pending
                messages, _, intent, extra_turn = combat_round(
                    self.player, enemy, act, abil, is_extra_turn=is_extra, intent=intent
                )
                for msg in messages:
                    print(f"  {msg}")

                if extra_turn:
                    extra_turn_pending = True
                    print("  --- EXTRA TURN! ---")
                    input("  Press Enter...")
                    continue

                extra_turn_pending = False
                input("  Press Enter...")

            self._tick_cooldowns()

            if not self.player.is_alive():
                if self.player.revive_used or self._try_revive():
                    self.player.hp = self.player.max_hp // 2
                    print("  The Holy Grail revives you!")
                    input("  Press Enter...")
                else:
                    print_death_screen(self.player)
                    input("  Press Enter...")
                    return "dead"

            first_turn = False

        if enemy["hp"] <= 0:
            return self._combat_victory(enemy)

        return "victory"

    def _try_revive(self):
        for i, item in enumerate(self.player.inventory):
            if item.get("effect") == "revive" and not self.player.revive_used:
                self.player.revive_used = True
                self.player.inventory.pop(i)
                return True
        return False

    def _inspect_enemy(self, enemy, intent):
        from status import format_statuses
        from constants import ARMOR_DR_K, ARMOR_DR_CAP
        lines = [
            f"  === {enemy['name']} ===",
            f"  {enemy.get('description', '')}",
            f"  HP: {enemy['hp']}/{enemy.get('max_hp', enemy['hp'])}  ATK: {enemy['atk']}  DEF: {enemy.get('def', 0)}",
            f"  SPD: {enemy.get('speed', 10)}  ACC: {enemy.get('accuracy', 100)}  CRIT: {int(enemy.get('crit', 0) * 100)}%",
        ]
        regen = enemy.get("passive_regen", 0)
        if regen > 0:
            lines.append(f"  Passive Regen: {regen}/turn")
        first = enemy.get("first_strike", False)
        if first:
            lines.append(f"  First Strike: Double damage on first attack")
        statuses = format_statuses(enemy.get("statuses", []))
        if statuses:
            lines.append(f"  Status: {statuses}")
        lines.append("")
        lines.append("  Abilities:")
        for key, abil in enemy.get("abilities", {}).items():
            acc = abil.get("accuracy", 100)
            atype = abil.get("type", "special")
            val = abil.get("value", 0)
            scale = abil.get("dmg_scale", 0)
            hits = abil.get("hits", 1)
            desc = f"{abil.get('name', key)} [{atype}] (ACC:{acc}%)"
            if atype in ("damage", "drain") and val > 0 and scale > 0:
                raw = val + int(enemy["atk"] * scale)
                dr = min(ARMOR_DR_CAP, self.player.defense / (self.player.defense + ARMOR_DR_K * enemy.get("level", 1))) if self.player.defense > 0 else 0.0
                est = max(1, int(raw * (1 - dr)))
                if hits > 1:
                    desc += f" ({val}+{int(scale*100)}% ATK = ~{est}x{hits})"
                else:
                    desc += f" ({val}+{int(scale*100)}% ATK = ~{est})"
            elif val > 0 and scale > 0:
                desc += f" ({val}+{int(scale*100)}% ATK)"
            elif val > 0:
                desc += f" (val:{val})"
            if hits > 1 and atype in ("damage", "multi"):
                desc += f" x{hits} hits"
            threshold = abil.get("threshold", 0)
            if threshold > 0:
                desc += f" [<{int(threshold*100)}% HP]"
            lines.append(f"    - {desc}")
        lines.append("")
        if intent:
            if intent["type"] == "stunned":
                lines.append("  Intent: Stunned (cannot act)")
            elif intent["type"] == "ability":
                abil = intent["ability"]
                atype = abil.get("type", "special")
                val = abil.get("value", 0)
                scale = abil.get("dmg_scale", 0)
                hits = abil.get("hits", 1)
                intent_line = f"  Intent: {abil.get('name', 'Skill')}"
                if atype in ("damage", "drain") and val > 0:
                    raw = val + int(enemy["atk"] * scale) if scale > 0 else val
                    dr = min(ARMOR_DR_CAP, self.player.defense / (self.player.defense + ARMOR_DR_K * enemy.get("level", 1))) if self.player.defense > 0 else 0.0
                    est = max(1, int(raw * (1 - dr)))
                    if hits > 1:
                        intent_line += f" (~{est * hits} total)"
                    else:
                        intent_line += f" (~{est})"
                elif atype == "heal":
                    intent_line += f" (heals {val})"
                elif atype == "buff":
                    intent_line += f" (buffs +{val})"
                elif atype == "debuff":
                    intent_line += f" (debuffs -{val})"
                elif atype == "stun":
                    intent_line += f" (stun {val}t)"
                lines.append(intent_line)
            else:
                raw = enemy["atk"]
                dr = min(ARMOR_DR_CAP, self.player.defense / (self.player.defense + ARMOR_DR_K * enemy.get("level", 1))) if self.player.defense > 0 else 0.0
                est = max(1, int(raw * (1 - dr)))
                lines.append(f"  Intent: Basic Attack (~{est})")
        return "\n".join(lines)

    def _tick_cooldowns(self):
        for k in self.player.cooldowns:
            if self.player.cooldowns[k] > 0:
                self.player.cooldowns[k] -= 1

    def _combat_victory(self, enemy):
        print()
        print(f"  You defeated the {enemy['name']}!")
        xp = int(enemy.get("xp", 0) * self.player.xp_mult)
        self.player.xp += xp
        print(f"  Gained {xp} XP!")

        if self.player.heal_on_kill > 0:
            healed = self.player.heal(self.player.heal_on_kill)
            if healed > 0:
                print(f"  Kill restores {healed} HP!")

        key = enemy.get("key", "unknown")
        self.player.kills[key] = self.player.kills.get(key, 0) + 1

        loot = get_loot(enemy, self.player.floor)
        for item in loot:
            if item.get("type") == "gold":
                gold = int(item["value"] * self.player.gold_mult)
                self.player.gold += gold
                print(f"  Found {gold} gold!")
            else:
                success, msg = add_item(self.player, item)
                print(f"  Found: {item['name']}!")

        level_msgs = self.player.check_level_up()
        for msg in level_msgs:
            print(f"  {msg}")

        if enemy.get("boss") and self.current_room.room_type == "boss":
            if self.player.floor == 5:
                input("  Press Enter...")
                self.do_final_victory()
                return "victory"
            elif self.on_bonus_floor:
                print()
                print("  The Sealed Guardian falls! The sealed depths are conquered!")
                print("  The path to Floor 3 is now clear.")

        if enemy.get("gatekeeper"):
            print()
            print("  The guardian falls! The path to the stairs is now clear.")
            from items import random_gatekeeper_loot
            gatekeeper_loot = random_gatekeeper_loot(self.player.floor, self.player)
            print("  The guardian drops a treasure:")
            for item in gatekeeper_loot:
                if item.get("type") == "gold":
                    gold = int(item["value"] * self.player.gold_mult)
                    self.player.gold += gold
                    print(f"    {gold} gold!")
                else:
                    success, msg = add_item(self.player, item)
                    print(f"    {item['name']}! ({msg})")

        input("  Press Enter...")
        return "victory"

    def do_final_victory(self):
        self.running = False
        print_victory_screen(self.player, self.ascension)

        print()
        print_header("The Grail of Valdris")
        print()
        print("  The dragon falls. The dungeon trembles.")
        print("  You stand before the Grail of Valdris.")
        print('  It whispers: "Make your wish."')
        print()
        print("  1. Make your wish")
        if self.ascension >= 2:
            print("  2. DESTROY THE GRAIL")
        print()

        while True:
            choice = input("  > ").strip()
            if choice == "1":
                self.do_wish()
                break
            elif choice == "2" and self.ascension >= 2:
                self.do_destroy_grail()
                break
            elif choice == "3" and self.ascension >= 2:
                print("  The Grail grows impatient...")
            else:
                print("  The Grail waits...")

    def do_wish(self):
        wish_key = CLASSES[self.player.class_key]["wish_id"]
        outcome = WISH_OUTCOMES[self.player.class_key]

        print_wish_outcome(outcome)

        if self.ascension == 0:
            self.ascension = 1
            print_ascension_unlock(1)
            self.lore_entries.append("world_1")
            self.lore_entries.append("world_2")
            self.lore_entries.append(f"class_{self.player.class_key}")
        elif self.ascension == 1:
            self.ascension = 2
            print_ascension_unlock(2)
            self.lore_entries.append("world_3")
            self.lore_entries.append("world_4")

        save_game(self.player, self.rooms, self.ascension, self.lore_entries)
        self.running = False
        print("  The cycle continues...")
        input("  Press Enter...")

    def do_destroy_grail(self):
        print_true_ending(TRUE_ENDING)

        self.ascension = 0
        self.lore_entries = []
        delete_save()
        self.running = False
        print("  The cycle is broken. The game has ended.")
        print("  Start a new game to play again.")
        input("  Press Enter...")

    def show_lore_menu(self):
        while True:
            print_lore_menu(self.lore_entries, self.ascension)
            choice = input("  > ").strip()

            if choice == "0":
                break
            elif choice == "1":
                print_world_lore(self.lore_entries)
            elif choice == "2":
                print_class_lore(self.player.class_key if self.player else "warrior", self.lore_entries)
            elif choice == "3" and self.ascension >= 2:
                print_memory_fragments(self.lore_entries)

    def show_inventory_menu(self):
        clear_screen()
        print()
        print(show_inventory(self.player))
        print()
        print("  Commands: equip <name/number>, use <name/number>, drop <name/number>")
        cmd = input("  > ").strip().lower()
        if cmd.startswith("equip "):
            self.do_equip(cmd[6:])
        elif cmd.startswith("use "):
            self.do_use(cmd[4:])
        elif cmd.startswith("drop "):
            self.do_drop(cmd[5:])

    def show_stats(self):
        clear_screen()
        print()
        print_header("Player Stats")
        print()
        print(self.player.get_stats_display())
        print()
        if self.on_bonus_floor:
            print(f"  Floor: 2.5 (The Sealed Depths)")
        else:
            print(f"  Floor: {self.player.floor}")
        print(f"  Kills: {self.player.kills}")
        if self.ascension > 0:
            print(f"  Ascension: {self.ascension}")
        print()
        input("  Press Enter...")

    def _get_display_explored(self):
        explored = set(self.player.explored)
        if self.player.accessory and self.player.accessory.get("effect") == "map_reveal":
            return set(self.rooms.keys())
        px, py = self.player.x, self.player.y
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = px + dx, py + dy
            room = self.rooms.get((nx, ny))
            if room and room.room_type == "gatekeeper" and not room.cleared:
                explored.add((nx, ny))
        return explored

    def show_map(self):
        clear_screen()
        print()
        floor_label = "2.5" if self.on_bonus_floor else str(self.player.floor)
        print_dungeon_map(self.rooms, (self.player.x, self.player.y),
                          self._get_display_explored(), floor_label)
        print()
        input("  Press Enter...")

    def show_help(self):
        clear_screen()
        print()
        print_header("Commands")
        print()
        print("  MOVEMENT: W/A/S/D (or go north/south/east/west)")
        print("            go down (on stairs)")
        print("  LOOK:     look")
        print("  TAKE:     take <item>")
        print("  SCAVENGE: scavenge (search empty rooms)")
        print("  OPEN:     open chest")
        print("  EQUIP:    equip <item>")
        print("  USE:      use <item>")
        print("  DROP:     drop <item>")
        print("  INVENTORY:i")
        print("  STATS:    st")
        print("  MAP:      map")
        print("  TALK:     talk <npc>")
        print("  BUY/SELL: talk <merchant> then buy/sell")
        print("  SAVE:     save")
        print("  HELP:     help")
        print("  QUIT:     quit")
        print()
        input("  Press Enter...")

    def do_save(self):
        filepath = save_game(self.player, self.rooms, self.ascension, self.lore_entries)
        print(f"  Game saved to {filepath}")
        input("  Press Enter...")

    def load_game(self):
        result = load_game()
        if result is None:
            print("  No save file found.")
            input("  Press Enter...")
            return
        self.player, self.rooms, self.ascension, self.lore_entries = result
        self.pre_generated_floors = {}
        self.floor_gold_totals = {}
        self.bonus_floor = None
        self.has_key = False
        self.on_bonus_floor = False
        self.start_floor(self.player.floor)


if __name__ == "__main__":
    game = Game()
    game.run()
