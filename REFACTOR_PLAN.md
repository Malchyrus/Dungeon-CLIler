# REFACTOR_PLAN.md — Full Refactoring Plan

## Phase 0: Bug Fixes (do first)

| ID | File | Bug | Fix |
|---|---|---|---|
| P0-1 | `player.py:518-542` | `status_effects` not saved — buffs vanish on load | Add to `to_dict()`/`from_dict()` |
| P0-2 | `player.py:280-289 vs 325-334` | `MEMORY_FRAGMENTS` duplicated as `LORE_ENTRIES["memory"]` | Delete duplicate, reference one source |
| P0-3 | `main.py:126-138` | Cascading ascension mults (0.9 × 0.8 = 0.72) | Use `elif` or flat multiplier |
| P0-4 | `enemies.py:168` | DEF scaled by `enemy_hp_mult` (copy-paste bug) | Remove DEF scaling or add `enemy_def_mult` |

## Phase 1: Foundation (new shared modules)

| ID | New File | Purpose |
|---|---|---|
| P1-1 | `data_loader.py` | Single `load_json()` with caching. Replaces 3 duplicate `_load()` functions |
| P1-2 | `constants.py` | All 40+ magic numbers as named constants |
| P1-3 | `directions.py` | Shared direction/WASD/compass mappings (used by main, room, dungeon) |

## Phase 2: Data Extraction (move hardcoded content to JSON)

| ID | From | To | Content |
|---|---|---|---|
| P2-1 | `player.py:4-203` | `data/classes.json` | CLASSES dict (200 lines of stats + narrative) |
| P2-2 | Various | `data/config.json` | Tunable gameplay values (loot rates, XP curve) |
| P2-3 | `room.py:4-103` | `data/rooms.json` | ROOM_TYPES + LORE_NOTES (100 lines) |
| P2-4 | `player.py:206-334` | `data/narrative.json` | WISH_OUTCOMES, TRUE_ENDING, LORE_ENTRIES |

## Phase 3: NPC OOP

| ID | File | Change |
|---|---|---|
| P3-1 | `npc_types.py` (new) | Base class + 8 subclasses |
| P3-2 | `npc.py` | Replace 8-branch if/elif with dict |
| P3-3 | `main.py` | Delete 7 `*_mode()` methods, use `_wrap_npc().interact()` |

## Phase 4: enemies.py

| ID | Change |
|---|---|
| P4-1 | Extract `_spawn_from_pool()` — deduplicate 4 spawn functions |
| P4-2 | Convert ability dispatch to dict-based |

## Phase 5: combat.py

| ID | Change |
|---|---|
| P5-1 | Break `combat_round()` into sub-functions |
| P5-2 | Convert 135-line ability if/elif to dict dispatch |
| P5-3 | Unify `use_item_in_combat()` with `inventory.py:use_item()` |

## Phase 6: inventory.py

| ID | Change |
|---|---|
| P6-1 | Replace 6-branch `use_item()` if/elif with dict |
| P6-2 | Replace `show_inventory()` display branching with formatter dict |

## Phase 7: player.py

| ID | Change |
|---|---|
| P7-1 | Load CLASSES from JSON |
| P7-2 | Extract `_apply_level_up()` |
| P7-3 | Fix MEMORY_FRAGMENTS duplication |
| P7-4 | Replace `equip()` if/elif with slot handler dict |

## Phase 8: renderer.py

| ID | Change |
|---|---|
| P8-1 | Replace `_room_symbol()` if/elif with dict |
| P8-2 | Extract `make_bar()` helper |
| P8-3 | Extract `_calc_map_bounds()` helper |
| P8-4 | Move late import to top-level |

## Phase 9: dungeon.py

| ID | Change |
|---|---|
| P9-1 | Extract `_generate_grid()` |
| P9-2 | Extract `_find_farthest()` |
| P9-3 | Extract `_assign_rooms()` |

## Phase 10: save_load.py

| ID | Change |
|---|---|
| P10-1 | Atomic writes |
| P10-2 | Add try/except on load |
| P10-3 | Add schema version |
| P10-4 | Deduplicate filepath construction |

## Phase 11: main.py

| ID | Change |
|---|---|
| P11-1 | Command dispatch → dict-based |
| P11-2 | Extract main_menu logic |
| P11-3 | Extract `combat_encounter()` into combat.py |
| P11-4 | Remove dead code |
| P11-5 | Remove `sys.path.insert` hack |

## Phase 12: block_photo.py

| ID | Change |
|---|---|
| P12-1 | Extract `_color_to_index()` helper |
| P12-2 | Remove dead `BLOCK_RAMP` constant |
| P12-3 | Make gamma a parameter |
| P12-4 | Add image error handling |

## Execution Order
```
Phase 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12
```
