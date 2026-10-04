# Changelog

All notable changes to Storylines. The newest version is at the top.

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
