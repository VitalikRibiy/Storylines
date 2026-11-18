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
# New WoW Forever zones consistently lag behind on QuestieDB's own ZONE tagging for their quests,
# even once everything else (prereqs, NPC locations) is in: without this they vanish ("no zone")
# instead of becoming storylines. Verified by checking each quest's own quest-giver/turn-in NPC's
# actual spawn location, not just the quest text.
ZONE_OVERRIDES = {
    # Shen'dralas, AreaID 16651
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
    93574: 16651,   # Corpsefeeder's Carapace

    # Mount Hyjal, AreaID 616
    90487: 616,   # Ancient Allies
    90647: 616,   # The Staff of the Mountain
    90750: 616,   # More Work?
    90854: 616,   # Leather for Inclement Weather
    90865: 616,   # Eyes of the Watchers
    91696: 616,   # Open Season
    91697: 616,   # Meet the Elders
    91698: 616,   # Barkskin Breakout
    91754: 616,   # Rub Some Dirt In It
    91755: 616,   # Leaves to Ligatures
    91770: 616,   # Bark Bite
    91883: 616,   # Spear of the Skylord
    91923: 616,   # Celastrus the Bitter
    92008: 616,   # Premiere Parts
    92009: 616,   # Crate Expectations
    92011: 616,   # Rubble Rummage
    92016: 616,   # Rootwork
    92017: 616,   # Cleansing Winds
    92100: 616,   # Anywhere But Here
    92102: 616,   # Praise
    92111: 616,   # Of Friend and Fur
    92147: 616,   # Highfeather Helper
    92169: 616,   # Paying Back the Pact
    92171: 616,   # Taking to New Heights
    92317: 616,   # Stolen Life
    92328: 616,   # Siegecraft
    92329: 616,   # Drum Up Trouble
    92335: 616,   # Ashes of the Legion Ascent
    92433: 616,   # Now We're Cooking
    92500: 616,   # A Bit of the Sky
    92533: 616,   # Twisted Tools
    92594: 616,   # Kindling, Kinda
    92612: 616,   # Aid from Moonglade
    92833: 616,   # Ve'han's Fall
    92959: 616,   # The Dying Ancients
    92960: 616,   # Siphoned Ephemeral Essence
    93127: 616,   # Summit Sentries
    93407: 616,   # A Thorn in the Paw
    93422: 616,   # Blackthorne Blackout
    93444: 616,   # Bait the Beast
    93521: 616,   # Challenger of the Gods
    93547: 616,   # A Thorny Solution
    93567: 616,   # Ends Meet
    93584: 616,   # Cult Closure
    93615: 616,   # Kits and Cats
    93617: 616,   # Prey and Predator
    93747: 616,   # Violence Into Verdure
    93759: 616,   # The Bounty of Nature
    93773: 616,   # The Pact
    93825: 616,   # Barkbound Blessings
    93826: 616,   # Deal Dread to Deadwood
    93827: 616,   # Windswept Wards
    93828: 616,   # Herbs of the Hollow
    93830: 616,   # Water of Hyjal
    93831: 616,   # Sweetpaw Jam
    93833: 616,   # Wicked Wisdom
    93834: 616,   # Burrow Beetles
    93848: 616,   # Work Well Done
    93925: 616,   # Beads for Brerufa
    93952: 616,   # Balance Through Strength
    94479: 616,   # One Person's Trash
    94504: 616,   # Barkskin Beginnings
    95006: 616,   # Stolen Power
    95316: 616,   # The Experimental Method
    95317: 616,   # Notation, Notation, Notation
    95318: 616,   # Taste of Ash
    95319: 616,   # Crystalline Collection
    95320: 616,   # A Curious Question
    95378: 616,   # The Hydra's Head
    95379: 616,   # A Revenge So Sweet
    95380: 616,   # A Prolific Source
    95568: 616,   # Seeds for a New Season
    95569: 616,   # Hope for Hatchlings
    95611: 616,   # Rites of Respect
    95766: 616,   # Fine Feathered Friend
    95793: 616,   # Stemming the Demon Tide
    96003: 616,   # Drawing Down the Malevolent
    96025: 616,   # As the Crow Flies
    96131: 616,   # An Oldstone But An Old Friend
    96145: 616,   # Past Wing and Claw
    96209: 616,   # The Ancient, Orokai
    96252: 616,   # Tarnished Treasures
    96255: 616,   # Amalgamated Marrow
    96262: 616,   # Prickly Pinecones
    96296: 616,   # Fetid Corruption
    96301: 616,   # Power Wash
    96302: 616,   # Arch Absolution
    96303: 616,   # Memory Mist
    96321: 616,   # The Dying God
    96322: 616,   # A Revenge Now Bitter
    96435: 616,   # A Fitting End
    96550: 616,   # Battle Recall
    96558: 616,   # Soldier's Solace
    96666: 616,   # Burrow Bonding
    96796: 616,   # Woods Workshop
    96830: 616,   # Farsight Guided
    96833: 616,   # Venom Maws
    96930: 616,   # The Capricious Corvid
    96931: 616,   # Heading Up the Mountain
    96939: 616,   # The Balance of Life and Death
    96957: 616,   # Bone Sweet Bone
    96959: 616,   # Blademaster's Bonfires
    96964: 616,   # A Clever Creature
    96971: 616,   # To Outfox a Demon
    96978: 616,   # Violent Venison
    96979: 616,   # Sacred Refreshment
    96983: 616,   # Yashiro's Windwalk
    96991: 616,   # Trail Assist
    97009: 616,   # Maerion's Misery
    97010: 616,   # Blind Vengeance
    99670: 616,   # Return to Jereman

    # Riverglades, AreaID 16591
    94961: 16591,   # Biting the Hand
    94968: 16591,   # Eye of Mugg
    94972: 16591,   # Tome of Twilight
    94973: 16591,   # Krol'dok Moulding
    94974: 16591,   # Key Ingredients
    94975: 16591,   # A Token of Vengeance
    94980: 16591,   # Krol'dok Moulding
    94981: 16591,   # Key Ingredients
    94982: 16591,   # Eye of Mugg
    94983: 16591,   # Twilight Mementos
    94984: 16591,   # Tome of Twilight
    94997: 16591,   # Lingering Essence
    94998: 16591,   # Curios of Curiosity
    95120: 16591,   # WANTED: Old Rot-Chum
    95122: 16591,   # Unchecked Expansion
    95123: 16591,   # A Blast Ye Scurvy Dogs!
    95124: 16591,   # Admiral Lamora
    95260: 16591,   # Terrors From the Deep
    95261: 16591,   # It Takes Guts
    95288: 16591,   # Smuggler's Paradise
    95294: 16591,   # Smuggler's Bargain
    95296: 16591,   # Shipping and Handling
    95312: 16591,   # Coming to Collect
    95321: 16591,   # Tazzik's Dues
    95322: 16591,   # Get the Goods
    95325: 16591,   # We've Been Robbed!
    95326: 16591,   # The Big Payback
    95327: 16591,   # All's Well That Ends Well
    95383: 16591,   # Shipping and Handling
    95472: 16591,   # Consolation Prize
    95792: 16591,   # Clear 'em Out
    95934: 16591,   # Proof of Profit
    96063: 16591,   # Gaseous Gold
    96067: 16591,   # Rock 'em and Sock 'em

    # Zephras Isle, AreaID 16593 (only the copies actually given there: "The Great Outdoors" /
    # "The Adventurer" / "Camping 101" are a repeatable series with a separate, zoneless copy at
    # many camps across both old and new zones; only Zephras Isle's own copies are fixed here).
    93797: 16593,   # Boughs in the Wind
    96101: 16593,   # The Great Outdoors
    96638: 16593,   # The Adventurer
    96646: 16593,   # Camping 101: Cooking
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
