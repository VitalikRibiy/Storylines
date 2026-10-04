"""Hand-made corrections applied by generate_data.py.

Storylines are generated automatically, so this is where to fix the cases the
automatic grouping gets wrong. Storylines are identified by their *key*: the lowest
quest ID in the chain (shown in brackets by `generate_data.py --report`).
"""

# Storyline key -> display name (when the automatic name is poor).
STORY_NAMES = {
    6: "Northshire Valley",  # automatic name would be "Grape Manifest"
    8286: "The Scepter of the Shifting Sands",  # the Ahn'Qiraj opening chain (31 steps)
    92514: "The Fate of Zephras",  # Zephras Isle main storyline; automatic name was Horde-only
}

# Storyline key -> AreaID to file it under (when the automatic zone is wrong).
STORY_ZONE = {
}

# Quest ID -> AreaID to use instead of the quest's own zone.
ZONE_OVERRIDES = {
}

# AreaID -> AreaID, applied while resolving a quest's zone (e.g. sub-areas missing from QuestieDB).
ZONE_REMAP = {
    25: 1584,  # Blackrock Mountain -> Blackrock Depths
}

# Dungeons new in WoW Forever that QuestieDB's dungeon table does not list yet:
# AreaID -> (name, AreaID of the zone it is in).
EXTRA_DUNGEONS = {
    16611: ("Ruins of Lordaeron", 85),   # levels 15-20, Tirisfal Glades
    16919: ("The Hall of Thanes", 1537),  # levels 13-18, inside Ironforge
}

# AreaID -> display name for zones whose name is missing from the source data.
ZONE_NAMES = {
}

# Extra (before, after) quest links that merge two chains into one storyline.
LINK_QUESTS = [
]

# Quests to leave out completely.
EXCLUDE_QUESTS = [
]
