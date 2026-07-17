import random
from data_loader import load_json
from player import MEMORY_FRAGMENTS

_rooms_data = load_json("rooms.json")
ROOM_TYPES = {k: v for k, v in _rooms_data.items() if k != "lore_notes"}
LORE_NOTES = _rooms_data["lore_notes"]


class Room:
    def __init__(self, x, y, room_type="empty", floor=1):
        self.x = x
        self.y = y
        self.room_type = room_type
        self.floor = floor
        self.description = random.choice(ROOM_TYPES[room_type]["description"])
        self.doors = {"north": False, "south": False, "east": False, "west": False}
        self.items = []
        self.enemy = None
        self.npc = None
        self.chest = None
        self.chest_opened = False
        self.cleared = False
        self.locked = None
        self.visited = False
        self.memory_fragment = None
        self.lore_note = None

    def get_available_directions(self):
        return [d for d, open_ in self.doors.items() if open_]

    def describe(self, show_commands=True, ascension=0):
        lines = [self.description]

        if self.lore_note and not self.memory_fragment:
            lines.append(f"\n  {self.lore_note}")

        if self.memory_fragment:
            lines.append(f"\n  {self.memory_fragment}")

        if self.items and not self.cleared:
            item_names = [i["name"] for i in self.items]
            lines.append(f"You see: {', '.join(item_names)}")

        if self.enemy and not self.cleared:
            lines.append(f"A {self.enemy['name']} blocks your path!")

        if self.room_type == "gatekeeper" and not self.cleared:
            terror_texts = [
                "A chilling aura presses against your skin. Something terrible guards the way.",
                "The air grows thick with dread. You feel your bones tremble.",
                "An ancient malice permeates this room. The guardian stirs.",
                "Goosebumps rise on your arms. Death lingers here.",
            ]
            lines.append(f"\n  {random.choice(terror_texts)}")

        if self.npc:
            lines.append(f"{self.npc['name']} is here.")

        if self.chest and not self.chest_opened:
            from constants import CHEST_TIER_NAMES
            tier = self.chest.get("tier", 1)
            tier_name = CHEST_TIER_NAMES.get(tier, "?")
            lines.append(f"A {tier_name} chest sits in the room.")

        if self.room_type == "stairs":
            lines.append("A staircase descends to the next floor.")

        if self.room_type == "locked_door":
            lines.append("An iron door seals the stairway down. A skeleton keyhole glows faintly.")

        if self.room_type == "gatekeeper":
            lines.append("A powerful presence blocks the path to the stairs. You must defeat it to proceed.")

        if self.room_type == "empty" and not self.cleared and not self.enemy:
            lines.append("The room is empty. You could search for scraps.")

        if show_commands:
            lines.append("")
            lines.append("  -- Available Actions --")
            dirs = self.get_available_directions()
            key_map = {"north": "W", "south": "S", "east": "D", "west": "A"}
            dir_str = "/".join(key_map.get(d, d[0].upper()) for d in dirs)
            if dirs:
                lines.append(f"  [{dir_str}] Move")
            if self.room_type == "stairs":
                lines.append(f"  [go down]   Descend to next floor")
            if self.room_type == "locked_door":
                lines.append(f"  [use skeleton key]  Open the sealed door (Floor 2.5)")
            if self.items and not self.cleared:
                lines.append("  [take all]  Pick up items")
                for item in self.items:
                    lines.append(f"               - {item['name']}")
            if self.chest and not self.chest_opened:
                lines.append("  [open chest] Open the chest (requires Chest Key)")
            if self.npc:
                npc_first = self.npc["name"].split()[0].lower()
                lines.append(f"  [talk {npc_first}] Talk to {self.npc['name']}")
            if self.enemy and not self.cleared:
                lines.append("  (Defeat the enemy to explore further)")
            if self.room_type == "empty" and not self.cleared and not self.enemy:
                lines.append("  [scavenge]  Search the room for scraps")
            lines.append("  [i] Inventory  [st] Stats  [map] Map  [save] Save")

        return "\n".join(lines)

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "room_type": self.room_type,
            "floor": self.floor,
            "description": self.description,
            "doors": dict(self.doors),
            "items": self.items,
            "enemy": self.enemy,
            "npc": self.npc,
            "chest": self.chest,
            "chest_opened": self.chest_opened,
            "cleared": self.cleared,
            "locked": self.locked,
            "visited": self.visited,
            "memory_fragment": self.memory_fragment,
            "lore_note": self.lore_note,
        }

    @classmethod
    def from_dict(cls, data):
        r = cls(data["x"], data["y"], data["room_type"], data.get("floor", 1))
        r.description = data.get("description", r.description)
        r.doors = data.get("doors", r.doors)
        r.items = data.get("items", [])
        r.enemy = data.get("enemy")
        r.npc = data.get("npc")
        r.chest = data.get("chest")
        r.chest_opened = data.get("chest_opened", False)
        r.cleared = data.get("cleared", False)
        r.locked = data.get("locked")
        r.visited = data.get("visited", False)
        r.memory_fragment = data.get("memory_fragment")
        r.lore_note = data.get("lore_note")
        return r
