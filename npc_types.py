from items import get_item, random_artifact
from npc import get_shop_inventory, get_sell_price
from inventory import add_item, drop_item
from renderer import print_shop_ui


class NPC:
    def __init__(self, npc_dict):
        self.data = npc_dict
        self.name = npc_dict["name"]

    def get_dialogue(self, key, default="..."):
        return self.data.get("dialogue", {}).get(key, default)

    def interact(self, player, game):
        raise NotImplementedError


class MerchantNPC(NPC):
    def interact(self, player, game):
        shop_items = get_shop_inventory(self.data)
        print(f"  {self.get_dialogue('greeting')}")
        print()

        while True:
            print_shop_ui(player, self.data, shop_items)
            cmd = input("\n  > ").strip().lower()

            if cmd in ("leave", "exit", "q"):
                print(f"\n  {self.get_dialogue('farewell')}")
                break

            if cmd.startswith("buy "):
                try:
                    idx = int(cmd[4:].strip()) - 1
                    if 0 <= idx < len(shop_items):
                        item = shop_items[idx]
                        if player.gold >= item["buy_price"]:
                            player.gold -= item["buy_price"]
                            add_item(player, item)
                            print(f"  Bought {item['name']} for {item['buy_price']}g!")
                        else:
                            print(f"  {self.get_dialogue('no_gold')}")
                    else:
                        print("  Invalid item number.")
                except ValueError:
                    print("  Usage: buy <number>")

            elif cmd == "sell":
                if not player.inventory:
                    print("  Your inventory is empty.")
                else:
                    print()
                    grouped = {}
                    for item in player.inventory:
                        key = item.get("name", "Unknown")
                        if key not in grouped:
                            grouped[key] = {"item": item, "count": 0}
                        grouped[key]["count"] += 1
                    for i, (name, info) in enumerate(grouped.items(), 1):
                        count = info["count"]
                        tag = f" x{count}" if count > 1 else ""
                        price = get_sell_price(self.data, info["item"])
                        print(f"  {i}. {name}{tag} ({price}g)")
                    print()
                    query = input("  Sell which? (number/name/cancel) > ").strip().lower()
                    if query in ("cancel", "c", "back", ""):
                        continue
                    found = None
                    try:
                        idx = int(query) - 1
                        items = list(grouped.values())
                        if 0 <= idx < len(items):
                            found = items[idx]["item"]
                    except ValueError:
                        for inv_item in player.inventory:
                            if query in inv_item["name"].lower():
                                found = inv_item
                                break
                    if found:
                        price = get_sell_price(self.data, found)
                        player.gold += price
                        drop_item(player, found)
                        print(f"  Sold {found['name']} for {price}g!")
                    else:
                        print("  You don't have that item.")

            elif cmd.startswith("sell "):
                query = cmd[5:].strip()
                found = None
                try:
                    idx = int(query) - 1
                    if 0 <= idx < len(player.inventory):
                        found = player.inventory[idx]
                except ValueError:
                    for inv_item in player.inventory:
                        if query.lower() in inv_item["name"].lower():
                            found = inv_item
                            break
                if found:
                    price = get_sell_price(self.data, found)
                    player.gold += price
                    drop_item(player, found)
                    print(f"  Sold {found['name']} for {price}g!")
                else:
                    print("  You don't have that item.")


class QuestGiverNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")
        print()
        quest = self.data.get("quest", {})
        if quest:
            print(f"  Quest: {self.data['dialogue'].get('quest', 'No quest available.')}")
            quest_type = quest.get("type")
            if quest_type == "kill":
                target = quest.get("target", "")
                needed = quest.get("amount", 1)
                killed = player.kills.get(target, 0)
                print(f"  Progress: {killed}/{needed} {target}s slain")
                if killed >= needed:
                    print(f"  {self.name}: \"{self.data['dialogue'].get('quest_complete', 'Well done!')}\"")
                    reward_id = quest.get("reward")
                    if reward_id:
                        reward = get_item(reward_id)
                        if reward:
                            add_item(player, reward)
                            print(f"  Reward: {reward['name']}!")
            elif quest_type == "fetch":
                target = quest.get("target", "")
                has_item = any(
                    i.get("name", "").lower().replace(" ", "_") == target or
                    i.get("name", "").lower() == target.replace("_", " ")
                    for i in player.inventory
                )
                if has_item:
                    print(f"  {self.name}: \"{self.data['dialogue'].get('quest_complete', 'Well done!')}\"")
                    reward_id = quest.get("reward")
                    if reward_id:
                        reward = get_item(reward_id)
                        if reward:
                            add_item(player, reward)
                            print(f"  Reward: {reward['name']}!")
                else:
                    print(f"  Still searching for the {target.replace('_', ' ')}...")
        print()
        print(f"  {self.name}: \"{self.data['dialogue'].get('no_quest', 'Be careful out there.')}]\"")


class TrappedNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")
        print()
        print(f"  {self.name}: \"{self.get_dialogue('lore')}\"")
        print()

        while True:
            print("  -- What do you do? --")
            print("  1. [Rescue] Free the adventurer")
            print("  2. [Trade]  Offer a Health Potion for an item")
            print("  3. [Info]   Ask for dungeon tips")
            print("  4. [Leave]  Walk away")
            print()

            choice = input("  > ").strip().lower()

            if choice in ("1", "rescue"):
                print()
                print(f"  {self.name}: \"{self.get_dialogue('rescue')}\"")
                reward_id = self.data.get("reward_item", "health_potion")
                reward = get_item(reward_id)
                if reward:
                    add_item(player, reward)
                    print(f"  They give you: {reward['name']}!")
                print()
                print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                game.current_room.npc = None
                break

            elif choice in ("2", "trade"):
                print()
                trade_want = self.data.get("trade_want", "health_potion")
                has_potion = any(
                    i.get("name", "").lower() == trade_want.replace("_", " ")
                    or i.get("name", "").lower() == trade_want
                    for i in player.inventory
                )
                if has_potion:
                    print(f"  {self.name}: \"{self.get_dialogue('trade_accept')}\"")
                    trade_item_id = self.data.get("trade_item", "silver_key")
                    trade_item = get_item(trade_item_id)
                    if trade_item:
                        add_item(player, trade_item)
                        print(f"  They give you: {trade_item['name']}!")
                    for i, item in enumerate(player.inventory):
                        want = trade_want.replace("_", " ")
                        if want in item.get("name", "").lower() or item.get("name", "").lower() == want:
                            player.inventory.pop(i)
                            break
                else:
                    print(f"  {self.name}: \"{self.get_dialogue('trade_refuse')}\"")
                    print(f"  (You need a Health Potion to trade)")

            elif choice in ("3", "info"):
                print()
                print(f"  {self.name}: \"{self.get_dialogue('hint')}\"")
                print()
                print(f"  {self.name}: \"{self.get_dialogue('lore')}\"")

            elif choice in ("4", "leave"):
                print()
                print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                break

            else:
                print("  Invalid choice. Enter 1-4.")


class KeySellerNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")
        print()
        print(f"  {self.name}: \"{self.get_dialogue('lore')}\"")
        print()

        already_has = any(
            item.get("name", "").lower() == "skeleton key"
            for item in player.inventory
        )

        if already_has:
            print(f"  {self.name}: \"{self.get_dialogue('already_bought')}\"")
            print()
            print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
            return

        price = game.celdric_price
        print(f"  The Skeleton Key costs {price} gold.")
        print(f"  (Total enemy gold on this floor: {game.floor_gold_totals.get(player.floor, '???')} gold)")
        print()

        has_enough = player.gold >= price

        if has_enough:
            print(f"  1. Buy the Skeleton Key ({price}g)")
        else:
            print(f"  You need {price} gold. You have {player.gold} gold.")
        print(f"  2. Leave")
        print()

        while True:
            choice = input("  > ").strip()
            if choice == "1" and has_enough:
                player.gold -= price
                skeleton_key = {"name": "Skeleton Key", "type": "key", "key_type": "skeleton",
                                "description": "A key shaped like a skeleton. It radiates cold energy."}
                add_item(player, skeleton_key)
                print()
                print(f"  {self.name}: \"{self.get_dialogue('sell_success')}\"")
                print()
                print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                break
            elif choice == "2":
                print()
                print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                break
            else:
                if not has_enough:
                    print(f"  {self.name}: \"{self.get_dialogue('sell_fail')}\"")
                else:
                    print("  Invalid choice. Enter 1 or 2.")


class HealerNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")
        print()

        cost_per_hp = self.data.get("heal_cost_per_hp", 2)
        missing_hp = player.max_hp - player.hp
        heal_cost = missing_hp * cost_per_hp

        while True:
            print(f"  HP: {player.hp}/{player.max_hp}  Gold: {player.gold}")
            print(f"  Missing HP: {missing_hp}  Cost to heal: {heal_cost}g")
            print()

            if missing_hp <= 0:
                print(f"  {self.name}: \"{self.get_dialogue('heal_fail')}\"")
                input("  Press Enter...")
                break

            print(f"  1. Heal to full ({heal_cost}g)")
            print(f"  2. Leave")
            print()

            choice = input("  > ").strip()
            if choice == "1":
                if player.gold >= heal_cost:
                    player.gold -= heal_cost
                    healed = player.heal(missing_hp)
                    print(f"  {self.name}: \"{self.get_dialogue('heal_success')}\"")
                    print(f"  Healed for {healed} HP!")
                    missing_hp = player.max_hp - player.hp
                    heal_cost = missing_hp * cost_per_hp
                else:
                    print(f"  {self.name}: \"{self.get_dialogue('heal_fail')}\"")
                    print(f"  You need {heal_cost}g but only have {player.gold}g.")
            elif choice == "2":
                print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                break


class ItemTraderNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")
        print()

        accepted_types = self.data.get("accepted_types", ["weapon", "accessory"])
        required_count = self.data.get("required_count", 2)

        while True:
            eligible = [i for i in player.inventory if i.get("type") in accepted_types]
            print(f"  Offer {required_count} items ({', '.join(accepted_types)}) for 1 random artifact.")
            print(f"  You have {len(eligible)} eligible item(s).")
            print()

            if len(eligible) < required_count:
                print(f"  {self.name}: \"{self.get_dialogue('trade_fail')}\"")
                print()
                print(f"  1. Leave")
                choice = input("  > ").strip()
                if choice == "1":
                    print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                break

            print("  Eligible items:")
            for i, item in enumerate(eligible):
                stat = ""
                if item.get("type") == "weapon":
                    stat = f" ATK+{item.get('atk', 0)}"
                elif item.get("type") == "accessory":
                    bonuses = []
                    if item.get("atk_bonus"):
                        bonuses.append(f"ATK+{item['atk_bonus']}")
                    if item.get("def_bonus"):
                        bonuses.append(f"DEF+{item['def_bonus']}")
                    if item.get("hp_bonus"):
                        bonuses.append(f"HP+{item['hp_bonus']}")
                    stat = f" ({', '.join(bonuses)})" if bonuses else ""
                print(f"    {i+1}. {item['name']}{stat}")
            print()

            print(f"  1. Trade {required_count} items for 1 artifact")
            print(f"  2. Leave")
            print()

            choice = input("  > ").strip()
            if choice == "1":
                picks = []
                for p in range(required_count):
                    pick = input(f"  Pick item #{p+1} (number): ").strip()
                    try:
                        idx = int(pick) - 1
                        if 0 <= idx < len(eligible) and eligible[idx] not in picks:
                            picks.append(eligible[idx])
                        else:
                            print("  Invalid selection.")
                            break
                    except ValueError:
                        print("  Invalid input.")
                        break
                else:
                    for pick in picks:
                        drop_item(player, pick)
                    artifact = random_artifact()
                    if artifact:
                        add_item(player, artifact)
                        print(f"  {self.name}: \"{self.get_dialogue('trade_success')}\"")
                        print(f"  You receive: {artifact['name']}!")
                    print()
                    print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                    break
            elif choice == "2":
                print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
                break


class MapSeekerNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")
        print()
        print(f"  {self.name}: \"{self.get_dialogue('quest')}\"")
        print()

        total_rooms = len(game.rooms)
        explored_count = len([pos for pos in game.rooms if pos in player.explored])
        enemy_rooms = [room for room in game.rooms.values()
                       if room.room_type in ("monster", "boss")]
        uncleared_enemies = [room for room in enemy_rooms if not room.cleared]
        chests = [room for room in game.rooms.values()
                  if room.room_type in ("treasure", "mimic") and not room.chest_opened]

        is_complete = len(uncleared_enemies) == 0 and len(chests) == 0

        print(f"  Floor {player.floor} Status:")
        print(f"    Rooms explored: {explored_count}/{total_rooms}")
        print(f"    Enemies remaining: {len(uncleared_enemies)}")
        print(f"    Chests unopened: {len(chests)}")
        print()

        if is_complete:
            print(f"  {self.name}: \"{self.get_dialogue('quest_complete')}\"")
            print()
            artifact = random_artifact()
            if artifact:
                add_item(player, artifact)
                print(f"  Reward: {artifact['name']}!")
        else:
            print(f"  {self.name}: \"{self.get_dialogue('quest_incomplete')}\"")
            remaining = len(uncleared_enemies) + len(chests)
            print(f"  {remaining} room(s) still need clearing.")

        print()
        print(f"  {self.name}: \"{self.get_dialogue('farewell')}\"")
        input("  Press Enter...")


class LoreNPC(NPC):
    def interact(self, player, game):
        for key in ("greeting", "lore", "hint"):
            dialogue = self.get_dialogue(key)
            print(f"  {self.name}: \"{dialogue}\"")
            print()
            if key == "lore":
                lore_key = f"lore_{self.name.lower().replace(' ', '_')}"
                if lore_key not in game.lore_entries:
                    game.lore_entries.append(lore_key)
                    print("  [Lore entry recorded]")
                    print()


class FallbackNPC(NPC):
    def interact(self, player, game):
        print(f"  {self.name}: \"{self.get_dialogue('greeting')}\"")


NPC_TYPES = {
    "merchant": MerchantNPC,
    "quest_giver": QuestGiverNPC,
    "trapped": TrappedNPC,
    "key_seller": KeySellerNPC,
    "healer": HealerNPC,
    "item_trader": ItemTraderNPC,
    "map_seeker": MapSeekerNPC,
    "lore": LoreNPC,
}


def wrap_npc(npc_dict):
    cls = NPC_TYPES.get(npc_dict.get("type"), FallbackNPC)
    return cls(npc_dict)
