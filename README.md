# Storylines

A **WoW Forever** addon that brings retail's zone "Storylines" list to the classic world.

Each zone lists its quest chains (storylines). Each storyline shows how far you've got, and it
gets checked off and crossed out once you finish it. This shows you how many storylines each
zone has, which ones you skipped completely, and which quest in a chain you need next.

## Features

- **Zone list** grouped by Eastern Kingdoms, Kalimdor, Dungeons & Raids and Battlegrounds, with
  `completed / total` storylines per zone. An arrow marks the zone you're in.
- **Storyline list** for the selected zone, with a progress bar, level range, `done/total` count
  and a check mark plus strike-through for finished storylines.
- **Click a storyline** to see its quests in order, one branch at a time. Each quest shows
  whether it's completed, in your quest log, ready to turn in, **available** to pick up now,
  waiting for a level, or still locked behind earlier quests. This uses each quest's real
  requirements, the same way the game decides.
- **Inspector**: click a storyline or quest to open a details panel next to the window.
  - *Storyline*: zone, level range, progress, XP left, the quest types it includes, where it
    starts (or the quest to continue with), and every quest in it.
  - *Quest*: level and required level, quest type, status, objectives, quest giver and turn-in
    NPC with map coordinates, rewards (XP for your level, reputation, items with tooltips), and
    the quests it requires and leads to. Click through these to move along the chain.
  - Click a location to place a map waypoint (or a TomTom waypoint if you use TomTom).
- **Quest levels are colored by difficulty**, the same way the game does it: red, orange,
  yellow, green and gray, relative to your character's level.
- **Quest type icons** for Dungeon, Raid, Elite, PvP and Escort quests, on quests and on the
  storylines that contain them.
- **Side quests**: quests that aren't part of any chain, listed separately with their own counter.
- Only shows quests your **faction and race** can actually do.
- **Reputation requirements**: quests that need a reputation you don't have are marked
  ("needs Honored") in the list. Storylines that contain such a quest get a ⚠ icon, and
  hovering the storyline lists which quests need what. The details panel shows a red **warning box** with the
  requirement, your current standing and how much reputation you still need. It appears even
  if earlier quests are still missing, so you know before you travel there. A storyline's
  overview lists every quest in it that your reputation is too low for. You also get a
  **warning** in chat and as red on-screen text:
  - when you talk to a quest giver who has a storyline quest your reputation is too low for (the
    game itself just hides those quests): *"James Halloran has [Young Crocolisk Skins] for you, but
    your reputation is not high enough: Requires Honored with Ironforge (you are Friendly +1,200)."*
  - when you turn in a quest whose follow-up needs more reputation.
  Each quest is reported once per session. `/stl repwarn` turns these warnings off.
- **Chat messages** when you turn in a storyline quest (`Storyline progress: The Defias
  Brotherhood 5/8`) and when you finish a whole storyline or zone.
- **Right-click** a quest or storyline to ignore it, for a quest you can't get or a chain you don't
  care about. Ignored entries no longer count. Tick *Show ignored* to see them again.
- *Follow my zone* switches to your current zone automatically. If the world map is open, the
  window opens on the zone the map is showing.
- Minimap button (drag it to move) and an entry in the addon compartment menu.

## Installation

1. Download this repository (Code → Download ZIP) and extract it.
2. Rename the extracted folder to `Storylines` and move it into the `Interface\AddOns` folder of
   your WoW Forever installation. `Storylines.toc` must sit directly inside that folder.
3. Restart the game or `/reload`.

## Usage

| Command | |
| --- | --- |
| `/storylines` or `/stl` | Open/close the window |
| `/stl zone <name>` or `/stl <name>` | Open a zone by name or the start of it, e.g. `/stl westf` |
| `/stl minimap` | Show/hide the minimap button |
| `/stl announce` | Turn the storyline progress messages on/off |
| `/stl repwarn` | Turn the reputation warnings on/off |
| `/stl reset` | Restore every ignored quest and storyline |
| `/stl help` | List the commands |

## Where the storylines come from

The game has no "storyline" data for classic zones, so the addon builds storylines from the
quest database of [QuestieDB](https://github.com/Questie/QuestieDB), which has a dedicated WoW
Forever data set. It also uses [Questie](https://github.com/Questie/Questie)'s list of
unobtainable quests.

`tools/generate_data.py` turns that database into `Data/Storylines.lua` (the storylines) and
`Data/QuestDetails.lua` (objectives, quest givers with coordinates, quest types, XP and rewards
for the inspector). Quest types come from Questie's tag list; any quest set in a dungeon, raid
or battleground also gets that type.

1. It keeps normal zone quests. It leaves out repeatable, class and profession quests,
   placeholder quests and quests Questie marks as unobtainable.
2. It links quests through their prerequisites, follow-up quests and child quests. Every
   connected group of two or more quests becomes one storyline. A quest that isn't linked to
   anything becomes a side quest.
3. Mutually exclusive quests (e.g. "pick one of these") count as a single step.
4. Alliance and Horde versions of the same chain stay separate storylines.
5. It files each storyline under the zone that has most of its quests and orders the steps by
   prerequisites, then by quest level.
6. It names each storyline after its final quest, skipping generic names like "Return to …".

The current data has **438 storylines and 456 side quests across 72 zones**.

Because the storylines are generated, some may be off: a few chains get merged or split, and
some names aren't great. You can correct these in `tools/overrides.py` (story names, zones,
extra links, excluded quests). QuestieDB doesn't have quests for Forever's new zones yet. Once
it does, regenerating the data adds them.

### Regenerating the data

```sh
python3 tools/generate_data.py            # downloads the latest QuestieDB data and rebuilds both data files
python3 tools/generate_data.py --report   # also prints every zone's storylines with their keys
python3 tools/show_story.py Westfall      # shows the quests of each storyline in a zone (or by quest ID)
```

### Tests

`tools/test_addon.py` loads the addon in Lua 5.1 with a mocked game API. It checks zone
detection, progress tracking, faction/race filtering, completion messages, level colors,
quest types, the inspector and the UI.

```sh
pip install lupa
python3 tools/test_addon.py
```

## Credits

Quest data: the [Questie](https://github.com/Questie/Questie) team and the
[QuestieDB](https://github.com/Questie/QuestieDB) project.
