# Storylines

**[Get it on CurseForge](https://www.curseforge.com/wow/addons/storylines-forever)**

A **WoW Forever** addon that brings retail's zone "Storylines" list to the classic world.

Each zone lists its quest chains (storylines). Each storyline shows how far you've got, and it
gets checked off and crossed out once you finish it. This shows you how many storylines each
zone has, which ones you skipped completely, and which quest in a chain you need next.

## Features

- **Zone list** grouped by Eastern Kingdoms, Kalimdor, Dungeons & Raids, Battlegrounds, Class Quests and
  Professions, with
  `completed / total` storylines per zone. An arrow marks the zone you're in. **Dungeons & Raids**
  lists every dungeon and raid (all 26 classic ones and WoW Forever's 9 new ones), each with the
  storylines that lead into it. Dungeons whose quests aren't known yet say "no quests yet".
- **Search** (top left of the window, or `/stl find <name>`): find zones, dungeons and raids,
  storylines and quests by name, and see which storyline and zone each quest belongs to. Click a
  result to open it.
- **Storyline list** for the selected zone, with a progress bar, level range, `done/total` count
  and a check mark plus strike-through for finished storylines.
- **Click a storyline** to see its quests in order, one branch at a time. When a quest opens
  several lines, they are shown as a tree: each line indented under the quest that opens it, and a
  line of several quests is one row you can open and close. Each quest shows
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
- **Class Quests**: your own class's quest chains (paladin tomes, warlock summons, druid forms…)
  under **Class Quests** in the zone list, and also in the zone or city where they start. You
  never see another class's quests.
- **Professions**: profession quests (Blacksmithing armor sets, cooking recipes, Gnome and Goblin
  Engineering…) under **Professions**, one entry per profession. Only the professions your
  character has learned are listed (an option shows them all), and quests show the skill they
  need ("needs Cooking 50").
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
  Each quest is reported once per session. The options choose chat, screen, both or off.
- **Chat messages** when you turn in a storyline quest (`Storyline progress: The Defias
  Brotherhood 5/8`) and when you finish a whole storyline or zone.
- **Right-click** a quest or storyline to ignore it, for a quest you can't get or a chain you don't
  care about. Ignored entries no longer count. Tick *Show ignored* to see them again.
- *Follow my zone* switches to your current zone automatically. If the world map is open, the
  window opens on the zone the map is showing.
- **Resizable window**: drag the bottom-right corner; the size and position are remembered.
- **Options** (Options → AddOns → Storylines, `/stl options`, or right-click the minimap button):
  - *Window*: scale, background opacity, text size, which side the details panel opens on, lock
    window, close with Escape, reset size and position.
  - *Lists*: hide completed, side quests, show ignored, follow my zone, hide gray quests, hide
    quests far above your level (storylines and side quests; started ones always stay), sort by level, name or progress,
    hide finished zones, show unlearned professions, show quest IDs.
  - *Notifications*: chat messages, reputation warnings, completion sound.
  - *Map*: minimap button, waypoints with TomTom or the game's map pin.
  - Clear ignored quests and reset all settings.
- Minimap button (click to open, right-click for options, drag to move) and an entry in the addon
  compartment menu.

## Installation

1. **[Download Storylines 0.3.1](https://github.com/VitalikRibiy/Storylines/raw/refs/heads/claude/wow-forever-story-tracker-vrrpsz/dist/Storylines-0.3.1.zip)**
   and unzip it. You get a folder called `Storylines`.
2. Move that folder into the `Interface\AddOns` folder of your WoW Forever installation.
   `Storylines.toc` must sit directly inside it (`Interface\AddOns\Storylines\Storylines.toc`).
3. Start the game (or `/reload`). On the character screen, under **AddOns**, make sure Storylines
   is enabled; tick **Load out of date AddOns** if it is marked out of date.

To package a new version after changing the code: commit, bump `## Version` in `Storylines.toc`,
and run `tools/package.sh` (writes `dist/Storylines-<version>.zip`).

## Usage

| Command | |
| --- | --- |
| `/storylines` or `/stl` | Open/close the window |
| `/stl zone <name>` or `/stl <name>` | Open a zone by name or the start of it, e.g. `/stl westf` |
| `/stl find <name>` | Find zones, dungeons, storylines and quests by name |
| `/stl options` | Open the settings |
| `/stl minimap` | Show/hide the minimap button |
| `/stl announce` | Turn the storyline progress messages on/off |
| `/stl repwarn` | Turn the reputation warnings on/off |
| `/stl reset` | Restore every ignored quest and storyline |
| `/stl help` | List the commands |

## Where the storylines come from

The game has no "storyline" data for these zones, so the addon builds storylines from the
WoW Forever quest database of [QuestieDB](https://github.com/Questie/QuestieDB). It uses the fully
merged database, exactly as Questie uses it in game: the original data plus Questie's corrections
and the quests, NPCs and changes that are new in WoW Forever (e.g. Zephras Isle and the new
dungeons). QuestieDB's own export tool produces it. Questie's list of unobtainable quests is
applied on top.

`tools/generate_data.py` turns that database into `Data/Storylines.lua` (the storylines) and
`Data/QuestDetails.lua` (objectives, quest givers with coordinates, quest types, XP, rewards and
requirements for the inspector). Quest types come from Questie's tag list; any quest set in a
dungeon, raid or battleground also gets that type.

1. It keeps normal zone quests, class quests and profession quests. It leaves out repeatable
   quests, placeholder quests and quests Questie marks as unobtainable. Class quests are filed
   under their class (only that class sees them); a WoW Forever quest without a class in the data
   but given only by one class's trainers counts as that class's quest. Profession quests are
   filed under their profession (only characters with that profession see them).
2. It links quests through their prerequisites, follow-up quests and child quests. Every
   connected group of two or more quests becomes one storyline. A quest that isn't linked to
   anything becomes a side quest.
3. Mutually exclusive quests (e.g. "pick one of these") count as a single step.
4. Alliance and Horde versions of the same chain stay separate storylines.
5. **Breadcrumbs**, optional quests that send you to another quest without that quest requiring
   them (e.g. *Sergra Darkthorn* → *Plainstrider Menace*), are listed as side quests. They are
   never a step of a storyline, so skipping them doesn't leave a storyline unfinished. Only quests
   that exclude each other ("pick one of these") are merged into one step.
6. It files each storyline under the zone that has most of its quests and orders the steps by
   prerequisites, one branch at a time. If you pick up its first quest in a different zone or city
   (e.g. Shadowfang Keep quests from Undercity), it is listed there too, with the zone it belongs
   to shown in grey. Group totals count each storyline once.
7. It names each storyline after its final quest, skipping generic names like "Return to …".

The current data has **489 storylines and 1,078 side quests across 48 zones, 35 dungeons and
raids, 3 battlegrounds, 9 classes and 12 professions**. 7 of WoW Forever's new dungeons have no quests in QuestieDB
yet. They are listed already and fill in when the data is regenerated after QuestieDB adds them.

Because the storylines are generated, some may be off: a few chains get merged or split, and
some names aren't great. You can correct these in `tools/overrides.py` (story names, zones,
extra links, excluded quests, dungeons QuestieDB doesn't list yet). Forever quests that QuestieDB
doesn't know yet are missing until it adds them; regenerating the data picks them up.

### Regenerating the data

```sh
python3 tools/generate_data.py            # updates QuestieDB (sparse checkout in tools/.cache) and rebuilds both data files
python3 tools/generate_data.py --questiedb ../QuestieDB   # or use an existing QuestieDB checkout
python3 tools/generate_data.py --report   # also prints every zone's storylines with their keys
python3 tools/show_story.py Westfall      # shows the quests of each storyline in a zone (or by quest ID)
```

### Releasing a new version

1. Describe the changes under a `## [x.y.z] - Unreleased` heading at the top of `CHANGELOG.md`.
2. Run `python3 tools/release.py x.y.z`. It sets the version in `Storylines.toc`, dates the
   changelog, runs the tests, commits and tags `vx.y.z`.
3. Push the commit and the tag: `git push origin <branch> vx.y.z`.

Pushing the tag runs the **Release** GitHub workflow. It tests the addon, builds the zip, creates a
GitHub release and uploads the version to CurseForge with its changelog section. It needs a
`CF_API_TOKEN` secret in the repository's Actions settings (the project ID is in `Storylines.toc`).
Versions before 1.0.0 (and `-alpha`/`-beta` versions) upload as beta; later ones use the
`CF_RELEASE_TYPE` variable (`release`). You can also start it by hand under Actions → Release,
with a release type override; by default that is a dry run.

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
