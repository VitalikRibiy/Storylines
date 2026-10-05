# CurseForge project text

Copy these fields into the CurseForge project form. The description is Markdown (pick
"Markdown" as the description format in the form).

## Project name

Storylines

## Summary

Retail-style zone storylines for WoW Forever: every quest chain in each zone, dungeon, class and profession, with your progress, quest details and the quests you skipped.

## Description

**Storylines** brings retail's zone "Storylines" list to World of Warcraft: Forever.

Every zone lists its quest chains. Each storyline shows how far you've got, and it is checked off and crossed out when you finish it. You can see how many storylines a zone has, which ones you skipped completely, and which quest to pick up next.

Storylines knows every WoW Forever quest, including the ones Forever added (Zephras Isle, the new dungeons and Forever's new quests in the old zones).

### Features

- **Zone list** grouped by Eastern Kingdoms, Kalimdor, Dungeons & Raids, Battlegrounds, Class Quests and Professions, with completed / total storylines for each.
- **Every dungeon and raid**, including WoW Forever's new ones, with the storylines that lead into it.
- **Class Quests**: your own class's quest chains. You never see another class's quests.
- **Professions**: profession quests for the professions you have learned, with the skill level they need (e.g. "needs Cooking 50").
- **Storylines per zone** with progress, level range and quest-type icons (dungeon, raid, elite, PvP, escort).
- **Quests in order, branch by branch.** Each quest shows whether it is completed, in your quest log, ready to turn in, available to pick up now, waiting for a level, or locked behind earlier quests.
- **Quest levels colored by difficulty**, like the quest log (red, orange, yellow, green, gray).
- **Details panel** for a storyline (where it starts, XP left, all quests) or a quest (objectives, quest giver and turn-in with coordinates, rewards, required and follow-up quests). Click a location to set a waypoint (TomTom or the game's map pin).
- **Reputation requirements.** Quests that need more reputation than you have are marked, and you get a warning with how much reputation you still need, in the details and when you talk to the quest giver.
- **Side quests** that are not part of any chain, with their own counter.
- **Resizable window**: drag the bottom-right corner.
- **Options** (Options → AddOns → Storylines): window scale, background opacity, text size, lock window; hide completed, gray or far-too-high quests; sort by level, name or progress; hide finished zones; show quest IDs; notification settings and more.
- **Chat messages** and a sound for storyline progress and completed storylines.
- Right-click to **ignore** a quest or storyline that doesn't apply to you.
- Minimap button (right-click for options), addon compartment entry and `/stl` command.

### Commands

- `/stl` opens or closes the window.
- `/stl <zone>` opens a zone (the start of the name is enough, e.g. `/stl westf`).
- `/stl options` opens the settings.
- `/stl reset` restores ignored quests and storylines.
- `/stl help` lists every command.

### Where the storylines come from

The game has no storyline data for these zones, so Storylines builds them automatically from the WoW Forever quest database of [QuestieDB](https://github.com/Questie/QuestieDB) (by the [Questie](https://github.com/Questie/Questie) team). Quests are grouped into chains through their prerequisites. Some chains may be grouped or named imperfectly, and Forever quests the database doesn't know yet (for example most quests of Forever's new dungeons) are added in later updates. Please report anything that looks wrong.

### Feedback

Storylines is in beta until version 1.0. Bug reports and suggestions are welcome on [GitHub](https://github.com/VitalikRibiy/Storylines). A screenshot of any Lua error helps a lot.
