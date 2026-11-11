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
# Dungeons QuestieDB has no AreaID for yet use placeholder IDs from 200001 on; replace them with the
# real AreaID once QuestieDB knows the dungeon (so its quests are filed there).
# The Hall of Thanes, Ruins of Lordaeron, Excavation Site: Wetlands and City of Dalaran got real
# AreaIDs with the official WoW Forever release; QuestieDB's own dungeon table lists them now.
EXTRA_DUNGEONS = {
    200003: ("The Drowned City", 33),             # levels 35-40, Stranglethorn Vale
    200004: ("Krol'dok Stronghold", 16591),       # levels 40-45, Riverglades
    200005: ("Alcaz Prison", 15),                 # levels 48-53, Alcaz Island, Dustwallow Marsh
    200006: ("Blackmaw Hold", 16),                # levels 55-60, Azshara
    200007: ("Shaper's Terrace", 490),            # levels 58-60, Un'Goro Crater
}

# AreaID -> display name for zones whose name is missing from the source data.
ZONE_NAMES = {
}

# Extra (before, after) quest links that merge two chains into one storyline. QuestieDB marks
# each "before" quest here as a breadcrumb for its "after" quest (so the automatic linking skips
# it, by design, since a breadcrumb's target doesn't list it as a real requirement) - but in each
# case here it's actually how the quest is obtained at all, confirmed against the ForeverDungeonScout
# dungeon guide addon's hand-tested quest order.
LINK_QUESTS = [
    (495, 518),      # The Crown of Will (Melisara, Tarren Mill): same quest name, 3-step kill chain
    (638, 639),       # Trollbane -> Sigil of Strom (the Uldaman key sigils, Stromgarde/Hammerfall)
    (1198, 1200),     # In Search of Thaelrid -> Blackfathom Villainy (QuestieDB flags hasPrereq=true)
    (95663, 95682),   # Dragonmaw Rumors -> Open the Maw (Excavation Site: Wetlands, Horde)
    (95664, 98823),   # Elder Knowledge -> Earthen Echo (Excavation Site: Wetlands, Horde)
    # Paladin's "Orb of Althalaxx" chain (new to WoW Forever): QuestieDB has no prereq data for any
    # of these at all, but each quest's turn-in NPC/object is the next one's quest giver, confirming
    # the order: A Strange Artifact -> Advice From Stormwind -> A Second Opinion -> Earning Your
    # Salt -> It Must Be Destroyed -> Return to Delgren.
    (78088, 78089),
    (78089, 78090),
    (78090, 78091),
    (78091, 78092),
    (78092, 78093),
]

# Quests to leave out completely.
EXCLUDE_QUESTS = [
]
