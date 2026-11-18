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
    92914: "The Pylons of Shen'dralas",  # automatic name was "Not on Squealing Terms", a side branch
}

# Storyline key -> AreaID to file it under (when the automatic zone is wrong).
STORY_ZONE = {
}

# Quest ID -> AreaID to use instead of the quest's own zone.
ZONE_OVERRIDES = {
    # Shen'dralas (new WoW Forever zone, AreaID 16651): QuestieDB has no ZONE field yet for this
    # chain, even though every quest giver is physically in Shen'dralas. Without this they vanish
    # ("no zone") instead of becoming a storyline.
    92914: 16651,   # Strange Pylons
    96010: 16651,   # Fragments of the Pylons
    96018: 16651,   # Powering the Pylons
    93016: 16651,   # A Brief History Lesson
    93394: 16651,   # Meeting the Magister
    93341: 16651,   # Forlorn Gardens
    93362: 16651,   # What They've Done to My Peonies
    93594: 16651,   # Word of the Woods
    93404: 16651,   # Rot and Regret
    93601: 16651,   # Passing the Blame
    93604: 16651,   # Agamaggan's Blood
    93606: 16651,   # Not on Squealing Terms
    93450: 16651,   # Phantasmal Problems
    93546: 16651,   # Spectral Iron Ore
    96060: 16651,   # Tempered Expectations
    99257: 16651,   # A Heart of Crystal
    99258: 16651,   # Mana Mania
    93568: 16651,   # Partially Digested Collar
    93609: 16651,   # Forlorn Necklace
    93644: 16651,   # Tattered Journal
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
# Shaper's Terrace has quests under a real AreaID (16985) too, but isn't in QuestieDB's own
# dungeon table yet, so it stays here with that AreaID instead of a placeholder.
EXTRA_DUNGEONS = {
    200003: ("The Drowned City", 33),             # levels 35-40, Stranglethorn Vale
    200004: ("Krol'dok Stronghold", 16591),       # levels 40-45, Riverglades
    200005: ("Alcaz Prison", 15),                 # levels 48-53, Alcaz Island, Dustwallow Marsh
    200006: ("Blackmaw Hold", 16),                # levels 55-60, Azshara
    16985: ("Shaper's Terrace", 490),             # levels 58-60, Un'Goro Crater
}

# AreaID -> display name for zones whose name is missing from the source data.
ZONE_NAMES = {
}

# Extra (before, after) quest links that merge two chains into one storyline, for cases
# QuestieDB has no prerequisite data for at all (confirmed by hand: the ForeverDungeonScout
# dungeon guide addon's hand-tested order, matching turn-in NPCs/objects, or in-game testing).
# QuestieDB keeps improving its own quest relation data - most of the links found this way end up
# here only until QuestieDB adds the real data itself; check new entries against it before adding.
LINK_QUESTS = [
    (495, 518),      # The Crown of Will (Melisara, Tarren Mill): same quest name, 3-step kill chain
    (638, 639),       # Trollbane -> Sigil of Strom (the Uldaman key sigils, Stromgarde/Hammerfall)
    (1198, 1200),     # In Search of Thaelrid -> Blackfathom Villainy (QuestieDB flags hasPrereq=true)
    (79970, 81762),   # Aeonas the Vindicated -> Some Good News (Paladin, Cathedral of Light)
    (81762, 81764),   # Some Good News -> The Mysterious Merchant (Paladin)
    (81764, 81765),   # The Mysterious Merchant -> Elrick, Paladin of the Silver Hand
    (94912, 94914),   # Child of Nature -> Moonglade (Druid)
    (96876, 2161),    # Ukor's Lost Pack -> A Peon's Burden (Durotar)
    (96438, 79939),   # Battle at the Mannoroc Coven -> The Broken Hammer (Paladin)
]

# Quests to leave out completely.
EXCLUDE_QUESTS = [
]
