#!/usr/bin/env python3
"""Generate Storylines' quest data (Data/Storylines.lua) from the QuestieDB Forever database.

Storylines are built automatically: quests are linked through their prerequisite /
next-in-chain / child-quest relations, every connected group of two or more quests
becomes one storyline, and the storyline is filed under the zone that holds most of
its quests. Quests that are not part of any chain are kept as "side quests".

Usage:
    python3 tools/generate_data.py            # download sources (cached) and regenerate
    python3 tools/generate_data.py --offline  # use the cached sources only
    python3 tools/generate_data.py --report   # also print a per-zone summary

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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", ".cache")
OUTPUT = os.path.join(ROOT, "Data", "Storylines.lua")

QUESTIEDB = "https://raw.githubusercontent.com/Questie/QuestieDB/master/"
QUESTIE = "https://raw.githubusercontent.com/Questie/Questie/master/"
SOURCES = {
    "quests": QUESTIEDB + "data/Forever/foreverQuestDB.lua",
    "areaToMap": QUESTIEDB + "support/Forever/Zones/areaIdToUiMapId.lua",
    "mapToArea": QUESTIEDB + "support/Forever/Zones/uiMapIdToAreaId.lua",
    "subZones": QUESTIEDB + "support/Forever/Zones/subZoneToParentZone.lua",
    "dungeons": QUESTIEDB + "support/Forever/Zones/dungeons.lua",
    "blacklist": QUESTIE + "Database/Corrections/QuestieQuestBlacklist.lua",
    "tags": QUESTIE + "Database/Corrections/questTagInfoCorrections.lua",
    "npcs": QUESTIEDB + "data/Forever/foreverNpcDB.lua",
    "objects": QUESTIEDB + "data/Forever/foreverObjectDB.lua",
    "items": QUESTIEDB + "data/Forever/foreverItemDB.lua",
    "xp": QUESTIEDB + "support/Forever/QuestXP/xpDB-classic.lua",
}

# QuestieDB quest field indexes (see QuestieDB src/meta/questMeta.lua)
NAME, LEVEL, RACES, CLASSES = 1, 5, 6, 7
PRE_GROUP, PRE_SINGLE, CHILDREN, EXCLUSIVE = 12, 13, 14, 16
ZONE, SKILL, NEXT, SPECIAL, PARENT, BREADCRUMB_FOR = 17, 18, 22, 24, 25, 27

ALLIANCE_RACES = (1 << 0) | (1 << 2) | (1 << 3) | (1 << 6) | (1 << 32)  # Human Dwarf NightElf Gnome Skyborne
HORDE_RACES = (1 << 1) | (1 << 4) | (1 << 5) | (1 << 7) | (1 << 33)  # Orc Undead Tauren Troll Skyborne
ALL_CLASSES = 1503

# Zone list groups shown in the addon.
EASTERN_KINGDOMS, KALIMDOR, DUNGEONS, BATTLEGROUNDS = 1, 2, 3, 4
KALIMDOR_AREAS = {14, 15, 16, 17, 141, 148, 215, 331, 357, 361, 400, 405, 406, 440, 490, 493, 618, 1377,
                  1637, 1638, 1657}
BATTLEGROUND_AREAS = {2597, 3277, 3358}

# Placeholder markers in internal quest names. Case-sensitive on purpose: real quests such as
# "Test of Faith" or "Poor Old Blanchy" must not match. (Questie's blacklist handles the rest.)
JUNK_NAME = re.compile(r"(UNUSED|DEPRECATED|<\s*(NYI|TXT|CHANGE)|\[PH\]|^ZZ|\bTEST\b|\(old\))")


# --------------------------------------------------------------------------- sources

def fetch(key, offline):
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

def build(offline):
    quest_text = fetch("quests", offline)
    quests = luatable.parse(luatable.extract_long_strings(quest_text)["QuestieDB.questData"])

    area_to_map, area_names = load_named_area_table(fetch("areaToMap", offline), "areaIdToUiMapId")
    map_to_area, _ = load_named_area_table(fetch("mapToArea", offline), "uiMapIdToAreaId")
    sub_text = fetch("subZones", offline)
    sub_override, _ = load_named_area_table(sub_text, "subZoneToParentZoneOverride")
    sub_main, _ = load_named_area_table(sub_text, "subZoneToParentZone")
    sub_to_parent = dict(sub_main)
    sub_to_parent.update(sub_override)
    dungeons = load_dungeons(fetch("dungeons", offline))
    blacklist = load_blacklist(fetch("blacklist", offline)) | set(overrides.EXCLUDE_QUESTS)

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
        elif q.get(CLASSES) and q.get(CLASSES) & ALL_CLASSES != ALL_CLASSES:
            reason = "class quest"
        elif q.get(SKILL):
            reason = "profession quest"
        elif zone <= 0:
            reason = "no zone (sort %d)" % zone
        else:
            resolved = resolve_zone(zone)
            if resolved is None:
                reason = "unknown zone %d" % zone
            else:
                kept[qid] = {"name": name, "level": q.get(LEVEL) or 0, "zone": resolved,
                             "races": q.get(RACES) or 0, "raw": q}
        if reason:
            skipped[reason.split(" (")[0]] += 1

    # ---- link quests into chains
    uf = UnionFind()
    prereqs = defaultdict(set)  # quest -> quests that must come before it
    exclusive = defaultdict(set)
    breadcrumbs = set()
    lead_ins = {}  # breadcrumb quest -> the quest it leads to (kept as separate storylines/side quests)
    for qid, k in kept.items():
        q = k["raw"]
        uf.find(qid)
        if q.get(BREADCRUMB_FOR) and q.get(BREADCRUMB_FOR) in kept:
            breadcrumbs.add(qid)  # optional lead-in, never a required story step
            continue
        for p in ids(q.get(PRE_SINGLE)) + ids(q.get(PRE_GROUP)):
            if p in kept and p != qid and kept[p]["raw"].get(BREADCRUMB_FOR) != qid:
                prereqs[qid].add(p)
        nxt = q.get(NEXT)
        if nxt in kept and nxt != qid:
            target = kept[nxt]["raw"]
            if qid in ids(target.get(PRE_SINGLE)) + ids(target.get(PRE_GROUP)):
                prereqs[nxt].add(qid)
            else:
                # "Next in chain" without the target requiring this quest: an optional breadcrumb that
                # leads to another chain (e.g. Sergra Darkthorn -> Plainstrider Menace). Not a story step.
                lead_ins[qid] = nxt
        if q.get(PARENT) in kept:
            prereqs[qid].add(q[PARENT])
        for c in ids(q.get(CHILDREN)):
            if c in kept:
                prereqs[c].add(qid)
        for e in ids(q.get(EXCLUSIVE)):
            # Alliance and Horde versions of a quest are exclusive too; keep their chains apart.
            if e in kept and e != qid and faction_of(q.get(RACES)) + faction_of(kept[e]["races"]) != 3:
                exclusive[qid].add(e)
                exclusive[e].add(qid)

    for qid in list(prereqs):
        if qid in breadcrumbs:
            del prereqs[qid]
            continue
        prereqs[qid] = {p for p in prereqs[qid] if p not in breadcrumbs}
        for p in prereqs[qid]:
            uf.union(p, qid)
    for qid, others in exclusive.items():
        if qid in breadcrumbs:
            continue
        for e in others:
            if e not in breadcrumbs:
                uf.union(qid, e)
    for a, b in overrides.LINK_QUESTS:
        if a in kept and b in kept:
            uf.union(a, b)
            prereqs[b].add(a)

    groups = defaultdict(list)
    for qid in kept:
        if qid not in breadcrumbs:
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

    npcs = luatable.parse(luatable.extract_long_strings(fetch("npcs", offline))["QuestieDB.npcData"])
    objects = luatable.parse(luatable.extract_long_strings(fetch("objects", offline))["QuestieDB.objectData"])

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
        zone_votes = Counter(kept[q]["zone"] for q in members)
        top = max(zone_votes.values())
        # Prefer an open-world zone over a dungeon when tied (chains usually start outside).
        zone = sorted((z for z, c in zone_votes.items() if c == top),
                      key=lambda z: (z in dungeons, min(q for q in members if kept[q]["zone"] == z)))[0]
        story_key = min(members)
        zone = overrides.STORY_ZONE.get(story_key, zone)
        ordered, finals = ordered_steps(members)
        # Also list it where you pick it up, if that is another zone or city (e.g. Undercity for
        # Shadowfang Keep quests, Mulgore for a chain that continues in The Barrens).
        start_zones = {giver_zone(q) for q in ordered[0]} - {None, zone}
        if len(ordered) == 1:
            zones[zone]["side"].append(ordered[0])
            for other in start_zones:
                zones[other]["alsoSide"].append(ordered[0])
            continue
        zones[zone]["stories"].append({"key": story_key, "steps": ordered,
                                       "name": story_name(story_key, ordered, finals, kept)})
        for other in start_zones:
            zones[other]["also"].append(story_key)

    return {"kept": kept, "zones": zones, "dungeons": dungeons, "area_names": area_names,
            "area_to_map": area_to_map, "map_to_area": map_to_area, "skipped": skipped,
            "breadcrumbs": breadcrumbs, "quests": quests, "prereqs": prereqs, "resolve_zone": resolve_zone,
            "lead_ins": lead_ins}


GENERIC_PREFIX = re.compile(r"^(Return to|Report to|Report back|Speak (with|to)|Talk to|Seek out|Back to|"
                            r"Meet|Find |Visit|Deliver|Delivery|Journey to|Travel to|An? Message|The Message|"
                            r"A Letter|Letter|Note to|Errand)", re.I)


def story_name(key, ordered, finals, kept):
    if key in overrides.STORY_NAMES:
        return overrides.STORY_NAMES[key]
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


def write_lua(kept, zones, dungeons, area_names, area_to_map, stats):
    used = used_quests(zones)

    def zone_name(area):
        if area in dungeons:
            return dungeons[area]["name"]
        return overrides.ZONE_NAMES.get(area) or area_names.get(area) or ("Zone %d" % area)

    def step_lua(step):
        return str(step[0]) if len(step) == 1 else "{" + ",".join(map(str, step)) + "}"

    lines = [
        "-- AUTO GENERATED by tools/generate_data.py from the QuestieDB Forever database. Do not edit by hand;",
        "-- put fixes in tools/overrides.py and regenerate.",
        "-- %d storylines and %d side quests in %d zones." % stats,
        "local _, ns = ...",
        "",
        "-- [questID] = { name, questLevel, faction (0 both / 1 Alliance / 2 Horde), {raceIDs} or nil }",
        "ns.Quests = {",
    ]
    for qid in sorted(used):
        k = kept[qid]
        races = race_list(k["races"])
        extra = (",{" + ",".join(map(str, races)) + "}") if races else ""
        lines.append("[%d]={%s,%d,%d%s}," % (qid, lua_str(k["name"]), k["level"], faction_of(k["races"]), extra))
    lines += [
        "}",
        "",
        "-- [areaID] = { name, uiMapID, group (1 Eastern Kingdoms / 2 Kalimdor / 3 Dungeons & Raids / 4 Battlegrounds),",
        "--              parent areaID (dungeons), stories = { {name, {steps}} }, side = {steps},",
        "--              also = {story keys of storylines filed elsewhere that start here}, alsoSide = {steps} }",
        "-- A step is a questID, or a table of mutually exclusive questIDs (any one of them completes the step).",
        "ns.Zones = {",
    ]
    for area in sorted(zones, key=zone_name):
        z = zones[area]
        is_dungeon = area in dungeons
        ui_map = 0 if is_dungeon else area_to_map.get(area, 0)
        parent = dungeons[area]["parent"] if is_dungeon else 0
        if area in BATTLEGROUND_AREAS:
            group = BATTLEGROUNDS
        elif is_dungeon:
            group = DUNGEONS
        else:
            group = KALIMDOR if area in KALIMDOR_AREAS else EASTERN_KINGDOMS
        lines.append("[%d]={name=%s,uiMap=%d,group=%d,parent=%d," % (
            area, lua_str(zone_name(area)), ui_map, group, parent))
        lines.append("stories={")
        stories = sorted(z["stories"], key=lambda s: (min(kept[q]["level"] for st in s["steps"] for q in st), s["key"]))
        for s in stories:
            lines.append("{%s,{%s}}," % (lua_str(s["name"]), ",".join(step_lua(st) for st in s["steps"])))
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
    args = ap.parse_args()

    ctx = build(args.offline)
    kept, zones, dungeons, area_names = ctx["kept"], ctx["zones"], ctx["dungeons"], ctx["area_names"]
    area_to_map, skipped, breadcrumbs = ctx["area_to_map"], ctx["skipped"], ctx["breadcrumbs"]
    n_stories = sum(len(z["stories"]) for z in zones.values())
    n_side = sum(len(z["side"]) for z in zones.values())
    write_lua(kept, zones, dungeons, area_names, area_to_map, (n_stories, n_side, len(zones)))
    print("Wrote %s: %d storylines, %d side quests, %d zones (%d breadcrumbs left out)" % (
        os.path.relpath(OUTPUT, ROOT), n_stories, n_side, len(zones), len(breadcrumbs)))
    print("Skipped quests:", dict(skipped))
    quest_details.write(ctx, lambda key: fetch(key, args.offline), used_quests(zones))
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
