#!/usr/bin/env python3
"""Generate Storylines' quest data (Data/Storylines.lua) from the QuestieDB Forever database.

The quest database is QuestieDB's fully merged WoW Forever data (raw data plus inherited
corrections, the quests/NPCs new in Forever, trace and authored Forever corrections), produced
by QuestieDB's own export tool (see tools/questiedb_export.py).

Storylines are built automatically: quests are linked through their prerequisite /
next-in-chain / child-quest relations, every connected group of two or more quests
becomes one storyline, and the storyline is filed under the zone that holds most of
its quests. Quests that are not part of any chain are kept as "side quests".

Usage:
    python3 tools/generate_data.py            # update QuestieDB (cached checkout) and regenerate
    python3 tools/generate_data.py --offline  # use the cached checkout / downloads only
    python3 tools/generate_data.py --report   # also print a per-zone summary
    python3 tools/generate_data.py --questiedb /path/to/QuestieDB   # use an existing checkout

Hand-made fixes (story names, merges, exclusions) live in tools/overrides.py.
"""
import argparse
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import luatable  # noqa: E402
import overrides  # noqa: E402
import quest_details  # noqa: E402
import questiedb_export  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", ".cache")
OUTPUT = os.path.join(ROOT, "Data", "Storylines.lua")

QUESTIEDB_CHECKOUT = os.path.join(CACHE, "QuestieDB")
QUESTIE = "https://raw.githubusercontent.com/Questie/Questie/master/"
# Downloaded from Questie (the addon), which keeps these lists rather than QuestieDB.
SOURCES = {
    "blacklist": QUESTIE + "Database/Corrections/QuestieQuestBlacklist.lua",
    "tags": QUESTIE + "Database/Corrections/questTagInfoCorrections.lua",
}
# Read from the QuestieDB checkout, so they always match the exported database.
SUPPORT_FILES = {
    "areaToMap": "support/Forever/Zones/areaIdToUiMapId.lua",
    "mapToArea": "support/Forever/Zones/uiMapIdToAreaId.lua",
    "subZones": "support/Forever/Zones/subZoneToParentZone.lua",
    "dungeons": "support/Forever/Zones/dungeons.lua",
    "xp": "support/Forever/QuestXP/xpDB-classic.lua",
}

# QuestieDB quest field indexes (see QuestieDB src/meta/questMeta.lua)
NAME, LEVEL, RACES, CLASSES = 1, 5, 6, 7
PRE_GROUP, PRE_SINGLE, CHILDREN, EXCLUSIVE = 12, 13, 14, 16
ZONE, SKILL, NEXT, SPECIAL, PARENT, BREADCRUMB_FOR = 17, 18, 22, 24, 25, 27

ALLIANCE_RACES = (1 << 0) | (1 << 2) | (1 << 3) | (1 << 6) | (1 << 32)  # Human Dwarf NightElf Gnome Skyborne
HORDE_RACES = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 7) | (1 << 33)  # Orc Undead Tauren Troll Skyborne
ALL_CLASSES = 1503
CLASS_MASKS = {"Warrior": 1, "Paladin": 2, "Hunter": 4, "Rogue": 8, "Priest": 16, "Shaman": 64, "Mage": 128,
               "Warlock": 256, "Druid": 1024}
# Class quests are filed under one entry per class in the "Class Quests" group. These entries use
# made-up area IDs (CLASS_AREA_BASE + class bit) that cannot collide with real AreaIDs.
CLASS_AREA_BASE = 100000
CLASS_AREAS = {CLASS_AREA_BASE + mask: name for name, mask in CLASS_MASKS.items()}


def class_bits(mask):
    return [bit for bit in CLASS_MASKS.values() if mask & bit]

# Reputation names used to tell same-named storylines apart (e.g. the two "Khan Hratha" chains).
FACTION_NAMES = {
    21: "Booty Bay", 47: "Ironforge", 54: "Gnomeregan Exiles", 59: "Thorium Brotherhood", 68: "Undercity",
    69: "Darnassus", 72: "Stormwind", 76: "Orgrimmar", 81: "Thunder Bluff", 87: "Bloodsail Buccaneers",
    92: "Gelkis Clan", 93: "Magram Clan", 169: "Steamwheedle Cartel", 270: "Zandalar Tribe", 349: "Ravenholdt",
    369: "Gadgetzan", 470: "Ratchet", 471: "Wildhammer Clan", 529: "Argent Dawn", 530: "Darkspear Trolls",
    576: "Timbermaw Hold", 577: "Everlook", 609: "Cenarion Circle", 729: "Frostwolf Clan", 730: "Stormpike Guard",
    749: "Hydraxian Waterlords", 889: "Warsong Outriders", 890: "Silverwing Sentinels", 910: "Brood of Nozdormu",
}

# Zone list groups shown in the addon.
EASTERN_KINGDOMS, KALIMDOR, DUNGEONS, BATTLEGROUNDS, CLASS_QUESTS = 1, 2, 3, 4, 5
KALIMDOR_AREAS = {14, 15, 16, 17, 141, 148, 215, 331, 357, 361, 400, 405, 406, 440, 490, 493, 618, 1377,
                  1637, 1638, 1657}
BATTLEGROUND_AREAS = {2597, 3277, 3358}

# Placeholder markers in internal quest names. Case-sensitive on purpose: real quests such as
# "Test of Faith" or "Poor Old Blanchy" must not match. (Questie's blacklist handles the rest.)
JUNK_NAME = re.compile(r"(UNUSED|DEPRECATED|<\s*(NYI|TXT|CHANGE)|\[PH\]|^ZZ|\bTEST\b|\(old\))")


# --------------------------------------------------------------------------- sources

def fetch(key, offline, checkout=None):
    if key in SUPPORT_FILES:
        with open(os.path.join(checkout, SUPPORT_FILES[key]), encoding="utf-8") as fh:
            return fh.read()
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, os.path.basename(SOURCES[key]))
    if not offline or not os.path.exists(path):
        if offline:
            sys.exit("Missing cached source %s; run without --offline" % path)
        print("Downloading", SOURCES[key], file=sys.stderr)
        with urllib.request.urlopen(SOURCES[key], timeout=60) as resp, open(path, "wb") as fh:
            fh.write(resp.read())
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_named_area_table(text, name):
    """Parse one of the ZoneDB.private.* long-string tables plus the area names in its comments."""
    body = luatable.extract_long_strings(text)["ZoneDB.private." + name]
    names = {}
    for m in re.finditer(r"\[(\d+)\]\s*=\s*(\d+),\s*--\s*(.+)", body):
        names[int(m.group(1))] = m.group(3).strip()
    return luatable.parse(body), names


def load_dungeons(text):
    dungeons = {}
    pattern = re.compile(r'\[(\d+)\]\s*=\s*\{"([^"]+)",(nil|\{[\d,\s]*\}),(\d+),')
    for m in pattern.finditer(text):
        alts = [int(x) for x in re.findall(r"\d+", m.group(3))] if m.group(3) != "nil" else []
        dungeons[int(m.group(1))] = {"name": m.group(2), "alts": alts, "parent": int(m.group(4))}
    return dungeons


def load_blacklist(text):
    """Quests Questie hides on Classic Era (removed, unobtainable or placeholder quests)."""
    start = text.index("function QuestieQuestBlacklist:Load()")
    end = text.index("if Questie.IsSoD", start)
    return {int(x) for x in re.findall(r"\[(\d+)\]\s*=\s*true", text[start:end])}


# --------------------------------------------------------------------------- helpers

def ids(value):
    return [v for v in (luatable.as_list(value) or []) if isinstance(v, int)]


def faction_of(races):
    """0 = both factions, 1 = Alliance only, 2 = Horde only."""
    races = races or 0
    if races == 0:
        return 0
    a, h = races & ALLIANCE_RACES, races & HORDE_RACES
    if a and not h:
        return 1
    if h and not a:
        return 2
    return 0


def race_list(races):
    """Explicit race IDs when a quest is limited to part of a faction, else None."""
    races = races or 0
    if races == 0 or races in (ALLIANCE_RACES, HORDE_RACES, ALLIANCE_RACES | HORDE_RACES):
        return None
    # Classic masks without the Forever-only races still mean "whole faction".
    if races & ~(ALLIANCE_RACES | HORDE_RACES) == 0 and races | (1 << 32) | (1 << 33) in (
        ALLIANCE_RACES | (1 << 33), HORDE_RACES | (1 << 32), ALLIANCE_RACES | HORDE_RACES,
    ):
        return None
    return [bit + 1 for bit in range(64) if races & (1 << bit)]


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


# --------------------------------------------------------------------------- ordering

def chain_order(count, deps, sort_key):
    """Topological order of steps 0..count-1 that finishes one branch before starting the next.

    Prerequisites always come first. Among the steps that are ready, a successor of the most
    recently placed step wins (depth-first), otherwise the lowest sort_key. Cycles in the data
    are broken by placing the lowest remaining step.
    """
    succ = defaultdict(set)
    for step, pre in deps.items():
        for p in pre:
            succ[p].add(step)
    waiting = {step: set(deps.get(step, ())) for step in range(count)}
    ready = {step for step in range(count) if not waiting[step]}
    placed, order = set(), []
    while len(order) < count:
        if not ready:  # cycle
            ready.add(min((s for s in range(count) if s not in placed), key=sort_key))
        pick = None
        for prev in reversed(order):
            candidates = [s for s in succ[prev] if s in ready]
            if candidates:
                pick = min(candidates, key=sort_key)
                break
        if pick is None:
            pick = min(ready, key=sort_key)
        ready.discard(pick)
        placed.add(pick)
        order.append(pick)
        for nxt in succ[pick]:
            waiting[nxt].discard(pick)
            if not waiting[nxt] and nxt not in placed:
                ready.add(nxt)
    return order


def longest_path_depths(count, deps):
    """Number of prerequisite steps on the longest path to each step (cycle-safe)."""
    depth = {}

    def visit(step, stack):
        if step in depth:
            return depth[step]
        if step in stack:
            return 0
        depth[step] = 1 + max([visit(p, stack | {step}) for p in deps.get(step, ())] or [-1])
        return depth[step]

    for step in range(count):
        visit(step, frozenset())
    return depth


# --------------------------------------------------------------------------- build

def build(offline, questiedb=None):
    checkout = questiedb_export.ensure_checkout(questiedb or QUESTIEDB_CHECKOUT, offline or bool(questiedb))
    combined = questiedb_export.export(checkout, offline)
    quests = questiedb_export.load(combined, "quests")
    npcs = questiedb_export.load(combined, "npcs")
    objects = questiedb_export.load(combined, "objects")

    def get(key):
        return fetch(key, offline, checkout)

    # Quests that exist in QuestieDB's raw data; the rest were added for WoW Forever.
    with open(os.path.join(checkout, "data", "Forever", "foreverQuestDB.lua"), encoding="utf-8") as fh:
        raw_ids = set(luatable.parse(luatable.extract_long_strings(fh.read())["QuestieDB.questData"]))

    def inferred_classes(qid, q):
        """Class mask for a quest added in Forever that has none yet but is only given by trainers of
        one class (e.g. the warrior trainer's "Sparring Match"). Classic quests are left alone: some
        trainers give quests that every class can do (e.g. "Morrowgrain Research")."""
        if qid in raw_ids:
            return None
        titles = {(npcs.get(g) or {}).get(14) for g in ids((q.get(2) or {}).get(1))}
        if len(titles) == 1:
            title = next(iter(titles)) or ""
            if title.endswith(" Trainer") and title[:-len(" Trainer")] in CLASS_MASKS:
                return CLASS_MASKS[title[:-len(" Trainer")]]
        return None

    area_to_map, area_names = load_named_area_table(get("areaToMap"), "areaIdToUiMapId")
    map_to_area, _ = load_named_area_table(get("mapToArea"), "uiMapIdToAreaId")
    sub_text = get("subZones")
    sub_override, _ = load_named_area_table(sub_text, "subZoneToParentZoneOverride")
    sub_main, _ = load_named_area_table(sub_text, "subZoneToParentZone")
    sub_to_parent = dict(sub_main)
    sub_to_parent.update(sub_override)
    dungeons = load_dungeons(get("dungeons"))
    for area, (name, parent) in overrides.EXTRA_DUNGEONS.items():
        dungeons.setdefault(area, {"name": name, "alts": [], "parent": parent})
    blacklist = load_blacklist(get("blacklist")) | set(overrides.EXCLUDE_QUESTS)

    # Area names: "Sub -> Parent" comments name both ends.
    for area, comment in list(area_names.items()):
        if "->" in comment:
            area_names[area] = comment.split("->")[0].strip()
            parent_name = comment.split("->")[1].strip()
            target = area_to_map.get(area)
            for parent_area, ui_map in map_to_area.items():
                if ui_map == target:
                    area_names.setdefault(parent_area, parent_name)

    zone_areas = set(map_to_area.values())  # one AreaID per native zone/city map
    dungeon_alias = {}
    for did, d in dungeons.items():
        for alt in d["alts"]:
            dungeon_alias[alt] = did

    def resolve_zone(area):
        seen = set()
        while area not in seen:
            seen.add(area)
            area = overrides.ZONE_REMAP.get(area, area)
            if area in dungeon_alias:
                area = dungeon_alias[area]
            if area in dungeons or area in zone_areas:
                return area
            if area in sub_to_parent and sub_to_parent[area] != area:
                area = sub_to_parent[area]
                continue
            break
        return None

    # ---- pick the quests that belong in zone storylines
    kept = {}
    skipped = Counter()
    for qid, q in quests.items():
        name = q.get(NAME)
        zone = q.get(ZONE) or 0
        if qid in overrides.ZONE_OVERRIDES:
            zone = overrides.ZONE_OVERRIDES[qid]
        reason = None
        if not name or JUNK_NAME.search(name):
            reason = "placeholder"
        elif qid in blacklist:
            reason = "blacklisted"
        elif (q.get(SPECIAL) or 0) & 1:  # repeatable (2 = escort/exploration, still a story quest)
            reason = "repeatable"
        elif q.get(SKILL):
            reason = "profession quest"
        else:
            classes = (q.get(CLASSES) or inferred_classes(qid, q) or ALL_CLASSES) & ALL_CLASSES
            classes = classes if classes != ALL_CLASSES and class_bits(classes) else 0
            if classes:
                # Class quests live under their class (shown only to that class), wherever they happen.
                resolved = CLASS_AREA_BASE + class_bits(classes)[0]
            elif zone <= 0:
                resolved, reason = None, "no zone (sort %d)" % zone
            else:
                resolved = resolve_zone(zone)
        if reason is None:
            if resolved is None:
                reason = "unknown zone %d" % zone
            else:
                races = q.get(RACES) or 0
                if not races:
                    # No faction in the data: if every quest giver is friendly to one faction only,
                    # it is that faction's quest (e.g. the Stormpike Guard's "Proving Grounds").
                    friendly = {(npcs.get(g) or {}).get(13) for g in ids((q.get(2) or {}).get(1))}
                    races = {frozenset(["A"]): ALLIANCE_RACES, frozenset(["H"]): HORDE_RACES}.get(
                        frozenset(friendly), 0)
                kept[qid] = {"name": name, "level": q.get(LEVEL) or 0, "zone": resolved,
                             "races": races, "classes": classes, "raw": q}
        if reason:
            skipped[reason.split(" (")[0]] += 1

    # ---- link quests into chains
    uf = UnionFind()
    prereqs = defaultdict(set)  # quest -> quests that must come before it
    exclusive = defaultdict(set)  # quest -> its real alternatives (mutually exclusive quests)

    def required_by(target, qid):
        raw = kept[target]["raw"]
        return qid in ids(raw.get(PRE_SINGLE)) + ids(raw.get(PRE_GROUP))

    # Breadcrumbs: optional quests that send you to another quest without that quest requiring them,
    # either marked as such or linked only as "next in chain" (e.g. Sergra Darkthorn -> Plainstrider
    # Menace). They are listed as side quests and never become a step of any storyline, so they
    # can't make a storyline look unfinished.
    lead_ins = {}  # breadcrumb quest -> the quest it leads to
    for qid, k in kept.items():
        q = k["raw"]
        for target in (q.get(BREADCRUMB_FOR), q.get(NEXT)):
            if target in kept and target != qid and not required_by(target, qid):
                lead_ins.setdefault(qid, target)

    # Exclusive quests are alternatives only when they exclude each other ("pick one of these").
    # A one-sided exclusion just makes a breadcrumb unavailable once you start its target.
    for qid, k in kept.items():
        for e in ids(k["raw"].get(EXCLUSIVE)):
            # Alliance and Horde versions of a quest are exclusive too; keep their chains apart.
            if (e in kept and e != qid and qid in ids(kept[e]["raw"].get(EXCLUSIVE))
                    and faction_of(k["races"]) + faction_of(kept[e]["races"]) != 3):
                exclusive[qid].add(e)
                exclusive[e].add(qid)
    # A quest that is an alternative to a breadcrumb is a breadcrumb too (e.g. the three
    # "The Ashenvale Hunt" lead-ins).
    changed = True
    while changed:
        changed = False
        for qid in list(lead_ins):
            for e in exclusive.get(qid, ()):
                if e not in lead_ins:
                    lead_ins[e] = lead_ins[qid]
                    changed = True

    for qid, k in kept.items():
        q = k["raw"]
        uf.find(qid)
        if qid in lead_ins:
            continue  # breadcrumbs only join their alternatives (below)
        for p in ids(q.get(PRE_SINGLE)) + ids(q.get(PRE_GROUP)):
            if p in kept and p != qid:
                prereqs[qid].add(p)  # a real requirement, even if p is someone else's breadcrumb
        if q.get(PARENT) in kept and q[PARENT] not in lead_ins:
            prereqs[qid].add(q[PARENT])
        for c in ids(q.get(CHILDREN)):
            if c in kept and c not in lead_ins:
                prereqs[c].add(qid)

    for qid in list(prereqs):
        for p in prereqs[qid]:
            uf.union(p, qid)
    for qid, others in exclusive.items():
        for e in others:
            if (qid in lead_ins) == (e in lead_ins):
                uf.union(qid, e)
    for a, b in overrides.LINK_QUESTS:
        if a in kept and b in kept:
            uf.union(a, b)
            prereqs[b].add(a)

    groups = defaultdict(list)
    for qid in kept:
        groups[uf.find(qid)].append(qid)

    # ---- turn every group into ordered steps
    def ordered_steps(members):
        members = set(members)
        # Mutually exclusive quests in the same chain are one step with alternatives.
        step_of = {}
        steps = []
        for qid in sorted(members, key=lambda x: (kept[x]["level"], x)):
            if qid in step_of:
                continue
            alts = sorted({qid} | {e for e in exclusive.get(qid, ()) if e in members and e not in step_of},
                          key=lambda x: (faction_of(kept[x]["races"]), x))
            for a in alts:
                step_of[a] = len(steps)
            steps.append(alts)
        # Prerequisites of each step, as step indexes.
        deps = defaultdict(set)
        for qid in members:
            for p in prereqs.get(qid, ()):
                if p in members and step_of[p] != step_of[qid]:
                    deps[step_of[qid]].add(step_of[p])
        order = chain_order(len(steps), deps, lambda s: (min(kept[q]["level"] for q in steps[s]), min(steps[s])))
        depth = longest_path_depths(len(steps), deps)
        # Ends of the chain (no later step depends on them), deepest first: used for the story name.
        needed = set().union(*deps.values()) if deps else set()
        finals = sorted((s for s in range(len(steps)) if s not in needed),
                        key=lambda s: (-depth[s], -max(kept[q]["level"] for q in steps[s]), steps[s][0]))
        return [steps[s] for s in order], [steps[s] for s in finals]

    def giver_zone(qid):
        """Open-world zone (not a dungeon) where the quest is picked up, or None."""
        started = kept[qid]["raw"].get(2) or {}
        for index, db, zone_field, spawn_field in ((1, npcs, 9, 7), (2, objects, 5, 4)):
            for gid in ids(started.get(index)):
                record = db.get(gid)
                if not record:
                    continue
                spawns = record.get(spawn_field) or {}
                area = record.get(zone_field) if record.get(zone_field) in spawns else next(iter(sorted(spawns)), None)
                zone = resolve_zone(area) if area else None
                if zone and zone not in dungeons:
                    return zone
        return None

    zones = defaultdict(lambda: {"stories": [], "side": [], "also": [], "alsoSide": []})
    for members in groups.values():
        # A storyline belongs under a class only if all of it is class quests; a zone chain with a
        # class step (e.g. the warlock "Vile Familiars" leading into Durotar's chain) stays in the zone.
        voters = [q for q in members if not kept[q]["classes"]] or members
        zone_votes = Counter(kept[q]["zone"] for q in voters)
        top = max(zone_votes.values())
        # Prefer an open-world zone over a dungeon when tied (chains usually start outside).
        zone = sorted((z for z, c in zone_votes.items() if c == top),
                      key=lambda z: (z in dungeons, min(q for q in voters if kept[q]["zone"] == z)))[0]
        story_key = min(members)
        zone = overrides.STORY_ZONE.get(story_key, zone)
        ordered, finals = ordered_steps(members)
        # Also list it where you pick it up, if that is another zone or city (e.g. Undercity for
        # Shadowfang Keep quests, Mulgore for a chain that continues in The Barrens).
        start_zones = {giver_zone(q) for q in ordered[0]} - {None, zone}
        if zone in CLASS_AREAS:
            # A class storyline several classes can do is listed under each of those classes. (A zone
            # storyline that merely contains a class step, e.g. a class letter, stays in its zone.)
            for q in members:
                for bit in class_bits(kept[q]["classes"]):
                    start_zones.add(CLASS_AREA_BASE + bit)
            start_zones.discard(zone)
        if len(ordered) == 1:
            zones[zone]["side"].append(ordered[0])
            for other in start_zones:
                zones[other]["alsoSide"].append(ordered[0])
            continue
        name_alliance, name_horde = story_names(story_key, ordered, finals, kept)
        zones[zone]["stories"].append({"key": story_key, "steps": ordered, "name": name_alliance,
                                       "names": {1: name_alliance, 2: name_horde}})
        for other in start_zones:
            zones[other]["also"].append(story_key)

    disambiguate_names(zones, kept, npcs)

    return {"kept": kept, "zones": zones, "dungeons": dungeons, "area_names": area_names,
            "area_to_map": area_to_map, "map_to_area": map_to_area, "skipped": skipped, "quests": quests, "prereqs": prereqs, "resolve_zone": resolve_zone,
            "lead_ins": lead_ins, "npcs": npcs, "objects": objects,
            "items": lambda: questiedb_export.load(combined, "items"), "fetch": get,
            "source": "QuestieDB " + questiedb_export.commit_info(checkout)}


GENERIC_PREFIX = re.compile(r"^(Return to|Report to|Report back|Speak (with|to)|Talk to|Seek out|Back to|"
                            r"Meet|Find |Visit|Deliver|Delivery|Journey to|Travel to|An? Message|The Message|"
                            r"A Letter|Letter|Note to|Errand)", re.I)


def story_names(key, ordered, finals, kept):
    """(name for Alliance players, name for Horde players).

    A storyline shared by both factions is named from the steps each faction actually sees, so
    Alliance players never get a Horde-only quest name (e.g. "Exploring the Horde")."""
    if key in overrides.STORY_NAMES:
        return overrides.STORY_NAMES[key], overrides.STORY_NAMES[key]
    names = []
    for side in (1, 2):
        def visible(steps):
            out = [[q for q in step if faction_of(kept[q]["races"]) in (0, side)] for step in steps]
            return [step for step in out if step]
        seen = visible(ordered)
        names.append(story_name(seen, visible(finals), kept) if seen else None)
    alliance, horde = names
    return alliance or horde, horde or alliance


def disambiguate_names(zones, kept, npcs):
    """Two storylines with the same name for the same faction in one zone (e.g. two "A Donation of
    Runecloth" in Orgrimmar) get the quest giver of their first quest, or their levels, appended."""
    def giver(story, side):
        for step in story["steps"]:
            for q in step:
                if faction_of(kept[q]["races"]) in (0, side):
                    for npc in ids(((kept[q]["raw"].get(2) or {}).get(1))):
                        if npc in npcs and npcs[npc].get(1):
                            return npcs[npc][1]
                    return None
        return None

    def reputation(story, side):
        totals = Counter()
        for step in story["steps"]:
            for q in step:
                if faction_of(kept[q]["races"]) in (0, side):
                    for pair in luatable.as_list(kept[q]["raw"].get(26)) or []:
                        pair = luatable.as_list(pair)
                        if pair and len(pair) >= 2 and pair[0] in FACTION_NAMES and (pair[1] or 0) > 0:
                            totals[pair[0]] += pair[1]
        return FACTION_NAMES[totals.most_common(1)[0][0]] if totals else None

    def levels(story, side):
        lv = [kept[q]["level"] for step in story["steps"] for q in step
              if faction_of(kept[q]["races"]) in (0, side) and kept[q]["level"] > 0]
        return ("level %d" % min(lv)) if lv and min(lv) == max(lv) else ("levels %d-%d" % (min(lv), max(lv)) if lv else None)

    for zone in zones.values():
        for side in (1, 2):
            by_name = defaultdict(list)
            for story in zone["stories"]:
                if any(faction_of(kept[q]["races"]) in (0, side) for step in story["steps"] for q in step):
                    by_name[story["names"][side]].append(story)
            for name, group in by_name.items():
                if len(group) < 2:
                    continue
                for describe in (giver, reputation, levels):
                    labels = [describe(story, side) for story in group]
                    if None not in labels and len(set(labels)) == len(labels):
                        for story, label in zip(group, labels):
                            story["names"][side] = "%s (%s)" % (name, label)
                        break


def story_name(ordered, finals, kept):
    # Prefer the end of the longest branch; fall back past "Return to ..." style names.
    for qid in [s[0] for s in finals] + [s[0] for s in reversed(ordered)]:
        name = kept[qid]["name"]
        if not GENERIC_PREFIX.search(name):
            return re.sub(r"\s*\((Part|Pt\.?) ?[IVX\d]+\)$|\s+(Part|Pt\.?) ?[IVX\d]+$", "", name)
    return kept[ordered[0][0]]["name"]


# --------------------------------------------------------------------------- output

def used_quests(zones):
    used = set()
    for z in zones.values():
        for story in z["stories"]:
            for step in story["steps"]:
                used.update(step)
        for step in z["side"]:
            used.update(step)
    return used


def write_lua(kept, zones, dungeons, area_names, area_to_map, stats, source):
    used = used_quests(zones)

    def zone_name(area):
        if area in CLASS_AREAS:
            return CLASS_AREAS[area]
        if area in dungeons:
            return dungeons[area]["name"]
        return overrides.ZONE_NAMES.get(area) or area_names.get(area) or ("Zone %d" % area)

    def step_lua(step):
        return str(step[0]) if len(step) == 1 else "{" + ",".join(map(str, step)) + "}"

    lines = [
        "-- AUTO GENERATED by tools/generate_data.py from the merged QuestieDB Forever database (%s)." % source,
        "-- Do not edit by hand;",
        "-- put fixes in tools/overrides.py and regenerate.",
        "-- %d storylines and %d side quests in %d zones." % stats,
        "local _, ns = ...",
        "",
        "-- [questID] = { name, questLevel, faction (0 both / 1 Alliance / 2 Horde), {raceIDs} or nil,",
        "--               class bitmask (class quests only: 1 Warrior, 2 Paladin, 4 Hunter, 8 Rogue, 16 Priest,",
        "--               64 Shaman, 128 Mage, 256 Warlock, 1024 Druid) }",
        "ns.Quests = {",
    ]
    for qid in sorted(used):
        k = kept[qid]
        races = race_list(k["races"])
        extra = (",{" + ",".join(map(str, races)) + "}") if races else ""
        if k.get("classes"):
            extra = (extra or ",nil") + ",%d" % k["classes"]
        lines.append("[%d]={%s,%d,%d%s}," % (qid, lua_str(k["name"]), k["level"], faction_of(k["races"]), extra))
    lines += [
        "}",
        "",
        "-- [areaID] = { name, uiMapID, group (1 Eastern Kingdoms / 2 Kalimdor / 3 Dungeons & Raids / 4 Battlegrounds /",
        "--              5 Class Quests: one entry per class, keyed 100000 + class bit, with classFile),",
        "--              parent areaID (dungeons), stories = { {name, {steps}, name for Horde if different} },",
        "--              side = {steps},",
        "--              also = {story keys of storylines filed elsewhere that start here}, alsoSide = {steps} }",
        "-- A step is a questID, or a table of mutually exclusive questIDs (any one of them completes the step).",
        "ns.Zones = {",
    ]
    for area in sorted(zones, key=zone_name):
        z = zones[area]
        is_dungeon = area in dungeons
        ui_map = 0 if is_dungeon or area in CLASS_AREAS else area_to_map.get(area, 0)
        parent = dungeons[area]["parent"] if is_dungeon else 0
        class_file = ""
        if area in CLASS_AREAS:
            group = CLASS_QUESTS
            class_file = ',classFile="%s"' % CLASS_AREAS[area].upper()
        elif area in BATTLEGROUND_AREAS:
            group = BATTLEGROUNDS
        elif is_dungeon:
            group = DUNGEONS
        else:
            group = KALIMDOR if area in KALIMDOR_AREAS else EASTERN_KINGDOMS
        lines.append("[%d]={name=%s,uiMap=%d,group=%d,parent=%d%s," % (
            area, lua_str(zone_name(area)), ui_map, group, parent, class_file))
        lines.append("stories={")
        stories = sorted(z["stories"], key=lambda s: (min(kept[q]["level"] for st in s["steps"] for q in st), s["key"]))
        for s in stories:
            alliance, horde = s["names"][1], s["names"][2]
            lines.append("{%s,{%s}%s}," % (lua_str(alliance), ",".join(step_lua(st) for st in s["steps"]),
                                           "," + lua_str(horde) if horde != alliance else ""))
        lines.append("},")
        side = sorted(z["side"], key=lambda st: (kept[st[0]]["level"], st[0]))
        lines.append("side={%s}," % ",".join(step_lua(st) for st in side))
        if z["also"]:
            lines.append("also={%s}," % ",".join(str(k) for k in sorted(z["also"])))
        if z["alsoSide"]:
            also_side = sorted(z["alsoSide"], key=lambda st: (kept[st[0]]["level"], st[0]))
            lines.append("alsoSide={%s}," % ",".join(step_lua(st) for st in also_side))
        lines.append("},")
    lines.append("}")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="use cached sources only")
    ap.add_argument("--report", action="store_true", help="print a per-zone summary")
    ap.add_argument("--questiedb", metavar="PATH", help="use an existing QuestieDB checkout as is")
    args = ap.parse_args()

    ctx = build(args.offline, args.questiedb)
    kept, zones, dungeons, area_names = ctx["kept"], ctx["zones"], ctx["dungeons"], ctx["area_names"]
    area_to_map, skipped, lead_ins = ctx["area_to_map"], ctx["skipped"], ctx["lead_ins"]
    n_stories = sum(len(z["stories"]) for z in zones.values())
    n_side = sum(len(z["side"]) for z in zones.values())
    write_lua(kept, zones, dungeons, area_names, area_to_map, (n_stories, n_side, len(zones)), ctx["source"])
    print("Wrote %s: %d storylines, %d side quests, %d zones (%d breadcrumbs kept out of the chains they lead to)" % (
        os.path.relpath(OUTPUT, ROOT), n_stories, n_side, len(zones), len(lead_ins)))
    print("Skipped quests:", dict(skipped))
    quest_details.write(ctx, used_quests(zones))
    if args.report:
        def name(a):
            return dungeons[a]["name"] if a in dungeons else area_names.get(a, str(a))
        for area in sorted(zones, key=name):
            z = zones[area]
            print("\n== %s (%d) — %d stories, %d side" % (name(area), area, len(z["stories"]), len(z["side"])))
            for s in sorted(z["stories"], key=lambda s: -len(s["steps"])):
                print("   %-45s %3d steps  [%d]" % (s["name"], len(s["steps"]), s["key"]))


if __name__ == "__main__":
    main()
