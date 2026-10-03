# CurseForge project text

Copy these fields into the CurseForge project form. The description is Markdown (pick
"Markdown" as the description format in the form).

## Project name

Storylines

## Summary

Retail-style zone storylines for WoW Forever: every quest chain in each zone, with your progress, quest details, and which quests you skipped.

## Description

**Storylines** brings retail's zone "Storylines" list to World of Warcraft: Forever.

Every zone lists its quest chains. Each storyline shows how far you've got, and it is checked off and crossed out when you finish it. You can see how many storylines a zone has, which ones you skipped completely, and which quest to pick up next.

### Features

- **Zone list** for Eastern Kingdoms, Kalimdor, Dungeons & Raids and Battlegrounds, with completed / total storylines for each zone.
- **Storylines per zone** with progress, level range and quest-type icons (dungeon, raid, elite, PvP, escort).
- **Quests in order, branch by branch.** Each quest shows whether it is completed, in your quest log, ready to turn in, available to pick up now, waiting for a level, or locked behind earlier quests.
- **Quest levels colored by difficulty**, like the quest log (red, orange, yellow, green, gray).
- **Details panel** for a storyline (where it starts, XP left, all quests) or a quest (objectives, quest giver and turn-in with coordinates, rewards, required and follow-up quests). Click a location to set a map waypoint (TomTom supported).
- **Reputation requirements.** Quests that need more reputation than you have are marked. You get a warning with how much reputation you still need, both in the details and when you talk to the quest giver.
- **Side quests** that are not part of any chain, with their own counter.
- **Chat messages** for storyline progress and completed storylines.
- Right-click to **ignore** a quest or storyline that doesn't apply to you.
- Minimap button, addon compartment entry and `/stl` command.

### Commands

- `/stl` opens or closes the window.
- `/stl <zone>` opens a zone (the start of the name is enough, e.g. `/stl westf`).
- `/stl minimap`, `/stl announce`, `/stl repwarn` toggle the minimap button, progress messages and reputation warnings.
- `/stl reset` restores ignored quests and storylines.

### Where the storylines come from

The game has no storyline data for these zones, so Storylines builds them automatically from the WoW Forever quest database of [QuestieDB](https://github.com/Questie/QuestieDB) (by the [Questie](https://github.com/Questie/Questie) team). Quests are grouped into chains through their prerequisites. Some chains may be grouped or named imperfectly, and quests from Forever's new zones will be added when the database includes them. Please report anything that looks wrong.

### Feedback

This is a new addon. Bug reports and suggestions are welcome on [GitHub](https://github.com/VitalikRibiy/Storylines). A screenshot of any Lua error helps a lot.
