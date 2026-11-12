# Changelog

All notable changes to Storylines. The newest version is at the top.

## [1.0.3] - Unreleased

### Fixed
- **Linked 8 more quests into their storylines**: Vengeful Trail -> Shared Fury (Ashenvale,
  confirmed in-game after the earlier scan excluded it as ambiguous - the same NPC happens to both
  give and take in both quests), and 7 more found by re-running the handoff scan against
  QuestieDB's latest data: Your Final Reward -> Ill Tidings (Azshara), two pairs in Riverglades, a
  pair in Dustwallow Marsh, a Paladin side-chain, and one in the Blasted Lands.
- **Removed our hand-made Shaman "Call of Water" links** now that QuestieDB chains them natively -
  and more completely: it also starts two quests earlier than we had it, and turned out to be one
  straight line rather than three parallel waterskin fetches, which our own version had wrong.

### Changed
- **Updated to QuestieDB's latest data** (another batch of fixes and new quests, and much better
  NPC/turn-in data: "no turn-in known" dropped from 327 to 109). The data now has 557 storylines
  and 1,382 side quests, up from 546 and 1,409.

## [1.0.2] - 2026-11-11

### Fixed
- **A quest requiring the other faction's version of itself could never be completed.**
  QuestieDB sometimes lists a faction-shared step's Alliance and Horde requirements together, so a
  Horde quest could end up needing an Alliance-only quest first (or vice versa) - something no
  character could ever do. Such requirements are now dropped instead of permanently locking the
  quest.
- **Linked the Paladin's "Orb of Althalaxx" chain** (A Strange Artifact → ... → Return to Delgren):
  QuestieDB has no prerequisite data for it at all, but each quest's turn-in NPC is the next one's
  giver.
- **17 more quests linked into their storylines** by the same method - checking every quest with
  no chain data for one whose turn-in NPC/object is uniquely another such quest's own giver, then
  verifying each by hand: two more Paladin side-chains, a Shaman "Call of Water" chain, a Rogue
  Stromgarde Keep infiltration, and others in Durotar, Riverglades and Wetlands.
- **Shaper's Terrace** now has its quests (QuestieDB gave it a real AreaID, though it's not in
  QuestieDB's own dungeon table yet). 4 of WoW Forever's new dungeons still have none.

### Changed
- **Updated to QuestieDB's latest data**, which merged in a large batch of new quests. The data
  now has 546 storylines and 1,409 side quests across 51 zones, up from 537 and 1,037.

## [1.0.1] - 2026-11-09

### Fixed
- **Breadcrumb quests with their own real prerequisite were wrongly left as side quests.** A
  quest that only *optionally* leads into another (a "breadcrumb") was also losing its *own*
  requirement in the process, so quests genuinely gated behind an earlier one showed up as
  unrelated side quests instead of continuing that storyline. For example, Wetlands' "Report to
  Captain Stoutfist" (which needs "The Algaz Gauntlet" first) is a storyline again. This also
  means **Lightforge Iron and Morbent Fel** (Duskwood) were never actually split by WoW Forever's
  official release like 1.0.0's changelog said — that was this same bug. They're one 15-step
  "Morbent Fel" storyline again. The fix applies everywhere this pattern occurs, not just
  Wetlands: the data now has 533 storylines and 1,051 side quests, up from 529 and 1,096.
- **5 more quest chains linked**, found by checking which quests are genuinely needed to reach
  another even though QuestieDB has no formal requirement for it yet: Excavation Site: Wetlands'
  Dragonmaw Rumors → Open the Maw and Elder Knowledge → Earthen Echo (the pairs from the original
  report), plus The Crown of Will (Hillsbrad/Alterac), Trollbane → Sigil of Strom (the Uldaman key
  sigils), and Blackfathom Deeps' In Search of Thaelrid → Blackfathom Villainy. The data now has
  536 storylines and 1,043 side quests.

## [1.0.0] - 2026-11-06

### Changed
- **Quest data updated for WoW Forever's official release.** Regenerated from QuestieDB's current
  Forever database (previously the beta data).
  - **The Hall of Thanes, Ruins of Lordaeron, City of Dalaran and Excavation Site: Wetlands** now
    have their quests, and are no longer listed as "no quests yet". 5 new dungeons (The Drowned
    City, Krol'dok Stronghold, Alcaz Prison, Blackmaw Hold, Shaper's Terrace) still have none in
    QuestieDB and will fill in with a later update.
  - **Lightforge Iron and Morbent Fel** (Duskwood) are now two storylines instead of one, matching
    a correction in the official data; **Westfall's Morbent Fel line also gained an alternate
    starting quest.**
  - The data now has 529 storylines and 1,096 side quests across 50 zones, up from 489 and 1,078
    across 48 zones.

### Fixed
- **Crafting order writs** ("Craftsman's Writ: ...", new in the official release) no longer show
  up as unplaced side quests; they aren't tied to any real zone.

## [0.5.2] - 2026-10-05

### Added
- **Storyline branches as a tree.** When a quest opens several lines, each line is listed
  indented under it with a guide line, in the storyline list and in the details panel. For
  example, after **Goblin Invaders** you see **Shredding Machines** and **The Elder Crone**'s
  chain as two separate branches.
  - A line of several quests is **one row you can open and close** ("The Elder Crone ... The
    Flying Machine Airport (6 quests) 2/6"). The line you are on starts open, the others closed.
  - Where lines join again, the list steps back out. Lines that aren't for your faction or class
    don't count.
  - Turn it off in the options ("Show storyline branches as a tree") for a flat list.

### Fixed
- **Short side quests are listed next to the quest that unlocks them**, not at the end of the
  storyline. For example, **Shredding Machines** now comes right after **Goblin Invaders** in
  "The Flying Machine Airport" (Thunder Bluff), before the long Elder Crone chain. 19 storylines
  are affected, e.g. Battle of Hillsbrad, Raene's Cleansing, Northshire Valley and The Fate of
  Zephras.

## [0.5.1] - 2026-10-05

### Added
- **Search.** Type in the box at the top left of the window (or `/stl find <name>`) to find
  zones, dungeons and raids, storylines and quests by name. Each quest shows its storyline and
  zone; click a result to open it.

### Fixed
- **Storylines are listed in another zone only if you start them there.** Durotar's **Burning
  Blade Medallion** no longer shows in Tirisfal Glades unless you are an Undead warlock, who
  starts it there.
- **"Pick one" steps with a version for each starting zone show your own version.** For example,
  Undead warlocks see Piercing the Veil (Tirisfal Glades) and Orc and Troll warlocks see Vile
  Familiars (Durotar). Shaman's **Call of Earth** shows in Mulgore for Tauren and in Durotar for
  Orcs and Trolls.

## [0.5.0] - 2026-10-04

### Added
- **Options page** under Options → AddOns → Storylines. Open it with `/stl options` or by
  right-clicking the minimap button.
  - **Window:** scale, background opacity, text size, which side the details panel opens on,
    lock window, close with Escape, and reset size and position.
  - **Lists:** hide completed, side quests, show ignored and follow my zone, plus the new list
    options below.
  - **Notifications:** chat messages, reputation warnings (chat, screen, both or off) and the
    storyline-complete sound.
  - **Map:** show the minimap button, and use TomTom or the game's map pin for waypoints.
  - **Clear ignored** quests and storylines, and **reset to defaults**.
- **Resizable window.** Drag the bottom-right corner. The size and position are remembered.
- **Professions.** Profession quests have their own **Professions** group, one entry per
  profession (Blacksmithing, Cooking, Engineering…). Only the professions you have learned are
  listed; an option shows them all. Quests show the skill they need, e.g. "needs Cooking 50".
- **Hide gray (too low level) quests** and **hide quests far above your level.** Both apply to
  storylines and side quests. The ones you have started are always shown.
- **Sort storylines** by level, name or progress.
- **Hide finished zones** in the zone list.
- **Show quest IDs** next to quest names.

### Changed
- The storyline-complete sound has its own setting, so it can play without chat messages.

### Fixed
- **Quests for several classes** (e.g. **The Forging of Quel'Serrar** for warriors and paladins) no
  longer show another class's name next to them. They are listed as your own class's quests.

## [0.4.0] - 2026-10-04

### Added
- **All of WoW Forever's quests.** Storylines now knows every WoW Forever quest, including the
  ones Forever added, instead of only the original quests.
  - New zone: **Zephras Isle** with its storylines, including **The Fate of Zephras**.
  - **All of Forever's new dungeons** are in the zone list: Ruins of Lordaeron, The Hall of Thanes,
    City of Dalaran, Excavation Site: Wetlands, The Drowned City, Krol'dok Stronghold, Alcaz Prison,
    Blackmaw Hold and Shaper's Terrace. Most have no known quests yet ("no quests yet"); they fill
    in with a later update.
  - Forever's new quests in existing zones (Elwynn Forest, Dun Morogh, Westfall, Tirisfal Glades,
    Durotar, Mulgore and more).
- **Class Quests.** Your own class's quest chains (paladin tomes, warlock summons, druid forms…)
  appear under **Class Quests** in the zone list and in the zone or city where they start.
  You never see another class's quests.

### Changed
- **Quest data follows WoW Forever:** levels, races, rewards and requirements now match Forever.
  For example, The Defias Brotherhood gives 200 Stormwind reputation in Forever, and "Young
  Crocolisk Skins" no longer shows a wrong Honored with Ironforge requirement.
- **Breadcrumbs are side quests.** Optional quests that only send you to another quest are no
  longer steps of a storyline, so skipping them never leaves a storyline unfinished.
- **Storylines shared by both factions are named for your faction.** For example, Alliance
  players no longer see a Horde quest name.
- **Same-named storylines in one zone are told apart** by quest giver, reputation or level, e.g.
  "Khan Hratha (Magram Clan)" and "Khan Hratha (Gelkis Clan)".

### Fixed
- **Dungeons and battlegrounds were missing from the zone list.** Wailing Caverns, The Deadmines,
  The Stockade, Scarlet Monastery, Zul'Farrak and others had only side quests of their own and
  weren't shown. They're now listed, and a dungeon also lists the storylines that lead into it
  (e.g. **Leaders of the Fang** under Wailing Caverns, **The Defias Brotherhood** under The
  Deadmines).
- **Every classic dungeon and raid is listed**, including Onyxia's Lair and Blackwing Lair, which
  were missing. Quests are also filed under a dungeon when you kill or loot their targets only
  there.
- **Dire Maul** is listed once instead of once per wing.
- **Deeprun Tram** is listed under Eastern Kingdoms instead of Dungeons & Raids.
- **The Ashenvale Hunt** lead-ins and similar "pick one" breadcrumbs are no longer merged into
  other storylines.
- **"Proving Grounds"** (Alterac Valley, Stormpike Guard) is no longer shown to Horde players.
- **Forever class-trainer quests** (e.g. "Sparring Match") are no longer shown to every class,
  only to the class that gets them.

## [0.3.1] - 2026-10-04

### Fixed
- **Isha Awak** (The Barrens) no longer starts with The Hunter's Way and Sergra Darkthorn. These
  breadcrumbs aren't required for it.
- **Quests are now also listed where you pick them up**, e.g. Undercity's dungeon quests (The Book
  of Ur, Hearts of Zeal, Into The Scarlet Monastery…). The zone they belong to is shown in grey.

## [0.3.0] - 2026-10-03

### Added
- **Quest availability.** Each quest shows whether you can pick it up now, need a higher level,
  or must finish earlier quests first, based on its real requirements.
- **Reputation requirements.**
  - Quests that need more reputation are marked ("needs Honored") in the list.
  - The details panel shows a warning with how much reputation you still need.
  - Storylines containing such quests get a ⚠ icon.
  - You're warned in chat and on screen when you talk to a quest giver, or turn in a quest, whose
    quest your reputation is too low for. `/stl repwarn` turns these warnings off.
- `/stl` accepts the start of a zone name (e.g. `/stl westf`).

### Changed
- **Storyline steps are listed one branch at a time** instead of interleaving separate branches.

### Fixed
- **31 real quests were missing**, e.g. the Thousand Needles "Test of Faith" chain, "Poor Old
  Blanchy" and "Heroes of Old".
- **Expanding Dungeons & Raids or Battlegrounds** is now remembered after `/reload`.
- **Difficulty colors and XP** update when you level up.
- **The zone list** scrolls to your zone when the window opens.
- **Faster refreshes** while the window is open.

## [0.2.0] - 2026-10-03

### Added
- **Details panel.** Click a storyline or quest to see:
  - storyline overview: levels, progress, XP left, where it starts;
  - quest details: objectives, quest giver and turn-in with coordinates and map waypoints
    (TomTom supported), rewards, and the quests it requires and leads to.
- **Quest levels colored by difficulty**, like the quest log.
- **Quest type icons** for dungeon, raid, elite, PvP and escort quests.

## [0.1.0] - 2026-10-03

### Added
- **First release.**
  - A zone list with completed / total storylines per zone.
  - Each zone's storylines, with progress, crossed out when finished.
  - Side quests.
  - Faction and race filtering.
  - Chat messages for storyline progress.
  - Right-click to ignore a quest or storyline.
  - Minimap button and addon compartment entry.
  - `/stl` command.
