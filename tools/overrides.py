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
    # Found by scanning every quest with no chain data at all for one whose turn-in NPC/object is
    # another such quest's own giver (and that NPC/object gives out no other quest), then checking
    # each candidate's objective text and surroundings by hand before trusting it.
    (79970, 81762),   # Aeonas the Vindicated -> Some Good News (Paladin, Cathedral of Light)
    (81762, 81764),   # Some Good News -> The Mysterious Merchant (Paladin)
    (81764, 81765),   # The Mysterious Merchant -> Elrick, Paladin of the Silver Hand
    (91859, 91860),   # A Curious Pair -> A Grim Fate (Paladin, the Earthen Ring travelers)
    (91860, 91861),   # A Grim Fate -> Into Fenris Keep (Paladin)
    (87318, 88757),   # Hearts of the Lost -> Accessories of the Lost (Wetlands, "Essene Villard")
    (88757, 88758),   # Accessories of the Lost -> Sentiments of the Lost (Wetlands)
    (94618, 94992),   # Wheeler's Fleeing Steeds -> Rescue Roundup (Riverglades)
    (94912, 94914),   # Child of Nature -> Moonglade (Druid)
    (95772, 95795),   # Songblade Search -> Fallen in the Fen (Excavation Site: Wetlands)
    (96783, 96784),   # A Way In -> Master of Disguise (Rogue, Stromgarde Keep infiltration)
    (96784, 96785),   # Master of Disguise -> Ain't No Telling (Rogue)
    (96876, 2161),    # Ukor's Lost Pack -> A Peon's Burden (Durotar)
    # The Shaman "Call of Water" chain: the three waterskins are parallel steps that all feed into
    # the vial delivery, which continues in a straight line from there.
    (94497, 94501),   # fill the Brown Waterskin -> Bring the Vial of Purest Water
    (94499, 94501),   # fill the Red Waterskin -> Bring the Vial of Purest Water
    (94500, 94501),   # fill the Blue Waterskin -> Bring the Vial of Purest Water
    (94501, 94502),   # Bring the Vial of Purest Water -> Drink the Water Sapta
    (94502, 94503),   # Drink the Water Sapta -> Speak to the Minor Manifestation of Water
    (94503, 94505),   # Speak to the Minor Manifestation of Water -> Bring the Shard of Water
    # Confirmed in-game: both quests are started AND finished by the same NPC (Maseara
    # Autumnmoon), with no QuestieDB chain data at all, so the earlier handoff-based scan
    # couldn't tell this apart from two independent quests given by the same NPC.
    (98417, 98418),   # Vengeful Trail -> Shared Fury (Ashenvale, Forest Song)
]

# Quests to leave out completely.
EXCLUDE_QUESTS = [
]
