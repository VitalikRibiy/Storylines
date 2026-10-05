#!/usr/bin/env python3
"""Sanity checks over the generated data (Data/Storylines.lua + Data/QuestDetails.lua).

Finds things that are probably wrong rather than proving correctness: steps out of order,
storylines that mix factions or zones, quests a character could never unlock, missing quest
givers, suspicious names, and so on. Prints a report; exits non-zero if hard errors are found.

Usage: python3 tools/validate_data.py [--all]   (--all prints every finding, not just examples)
"""
import argparse
import os
import sys
from collections import Counter, defaultdict

from lupa import lua51

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTION = {0: "both", 1: "Alliance", 2: "Horde"}


def load_data():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    ns = lua.eval("{}")
    load = lua.execute("return function(src, name) return assert(loadstring(src, name)) end")
    for name in ("Data/Storylines.lua", "Data/QuestDetails.lua"):
        with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
            load(fh.read(), "@" + name)("Storylines", ns)

    def py(value, top=False):
        if lua51.lua_type(value) == "table":
            keys = list(value.keys())
            # Positional rows may have nil holes (e.g. {name, level, faction, nil, classMask}); tables
            # keyed by IDs (e.g. alsoVia) stay dictionaries.
            if not top and keys and all(isinstance(k, int) and k > 0 for k in keys) and max(keys) <= 2 * len(keys) + 4:
                return [py(value[i]) if i in keys else None for i in range(1, max(keys) + 1)]
            return {k: py(v) for k, v in value.items()}
        return value

    return (py(ns.Quests, True), py(ns.Zones, True), py(ns.QuestDetails, True), py(ns.NPCs, True),
            py(ns.Objects, True))


def step_ids(step):
    return step if isinstance(step, list) else [step]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="list every finding")
    args = ap.parse_args()
    quests, zones, details, npcs, objects = load_data()

    findings = defaultdict(list)  # category -> [text]
    errors = set()  # categories that are hard errors

    def add(category, text, error=False):
        findings[category].append(text)
        if error:
            errors.add(category)

    def qname(qid):
        q = quests.get(qid)
        return "%s (%d)" % (q[0] if q else "?", qid)

    def faction(qid):
        return quests[qid][2] if qid in quests else 0

    def compatible(a, b):
        return faction(a) == 0 or faction(b) == 0 or faction(a) == faction(b)

    story_of, side_of = {}, {}
    all_stories = []
    for area, zone in zones.items():
        for story in zone.get("stories") or []:
            name, steps = story[0], story[1]
            horde_name = story[2] if len(story) > 2 else name
            all_stories.append((area, zone["name"], name, steps, horde_name))
            for step in steps:
                for qid in step_ids(step):
                    if qid in story_of:
                        add("quest in two storylines", "%s: %s and %s" % (qname(qid), story_of[qid], name), True)
                    story_of[qid] = name
        for step in zone.get("side") or []:
            for qid in step_ids(step):
                side_of[qid] = zone["name"]
                if qid in story_of:
                    add("quest both side quest and storyline step", qname(qid), True)

    # ---- per-quest checks
    for qid, q in quests.items():
        name, level = q[0], q[1]
        if not name or name.startswith("Quest #"):
            add("missing quest name", str(qid), True)
        if level is None or level <= 0:
            add("quest level 0 or missing", qname(qid))
        d = details.get(qid)
        if d is None:
            add("no details", qname(qid), True)
            continue
        req_level = d[0] or 0
        if level and req_level > level:
            add("required level above quest level", "%s: requires %d, quest level %d" % (qname(qid), req_level, level))
        giver_kind, giver_id = d[3], d[4]
        if giver_kind == 0:
            add("no quest giver known", qname(qid))
        elif giver_kind == 1 and giver_id in npcs:
            npc = npcs[giver_id]
            if len(npc) < 5 or npc[3] is None:
                add("quest giver without coordinates", "%s from %s" % (qname(qid), npc[0]))
        elif giver_kind == 2 and giver_id in objects and (len(objects[giver_id]) < 4 or objects[giver_id][2] is None):
            add("quest giver without coordinates", "%s from object %s" % (qname(qid), objects[giver_id][0]))
        if d[5] == 0:
            add("no turn-in known", qname(qid))
        pre_all = d[10] or []
        pre_any = d[11] or []
        # A quest some character can never unlock: a required quest that its faction can't do.
        if faction(qid) != 0:
            bad = [p for p in pre_all if not compatible(qid, p)]
            if bad:
                add("requires a quest of the other faction (never available)",
                    "%s (%s) requires %s" % (qname(qid), FACTION[faction(qid)],
                                             ", ".join("%s %s" % (qname(p), FACTION[faction(p)]) for p in bad)), True)
            if pre_any and not any(compatible(qid, p) for p in pre_any):
                add("requires one of quests of the other faction (never available)",
                    "%s (%s) needs one of %s" % (qname(qid), FACTION[faction(qid)], ", ".join(qname(p) for p in pre_any)),
                    True)
        if qid in pre_all or qid in pre_any:
            add("quest requires itself", qname(qid), True)
        if qid not in story_of and qid not in side_of:
            # Steps listed only through "alsoSide" in another zone are fine.
            pass
        mn = d[12] or []
        if mn and len(mn) == 2 and mn[1] > 42999:
            add("impossible reputation requirement", "%s needs %d" % (qname(qid), mn[1]), True)

    # ---- prerequisite cycles
    pre = {qid: set((details.get(qid) or [None] * 12)[10] or []) for qid in quests}
    state = {}

    def visit(qid, path):
        if state.get(qid) == 1:
            cyc = path[path.index(qid):] + [qid]
            add("prerequisite cycle", " -> ".join(qname(x) for x in cyc), True)
            return
        if state.get(qid) == 2:
            return
        state[qid] = 1
        for p in pre.get(qid, ()):
            if p in pre:
                visit(p, path + [qid])
        state[qid] = 2

    for qid in quests:
        visit(qid, [])

    # ---- per-storyline checks
    names_by_zone = defaultdict(Counter)  # (zone, faction) -> names that faction sees
    for area, zone_name, name, steps, horde_name in all_stories:
        ids = [qid for step in steps for qid in step_ids(step)]
        for side, shown in ((1, name), (2, horde_name)):
            if any(faction(q) in (0, side) for q in ids):
                names_by_zone[(zone_name, FACTION[side])][shown] += 1
        position = {}
        for i, step in enumerate(steps):
            for qid in step_ids(step):
                position[qid] = i
        # every prerequisite inside the storyline must come before the quest
        for qid in ids:
            d = details.get(qid) or []
            for p in (d[10] if len(d) > 10 else []) or []:
                if p in position and position[p] >= position[qid]:
                    add("step before its prerequisite", "%s / %s: %s is listed before %s" % (
                        zone_name, name, qname(qid), qname(p)), True)
        factions = {faction(q) for q in ids} - {0}
        if len(factions) > 1:
            # Fine if each faction has its own alternative in the same step; suspicious otherwise.
            mixed = [s for s in steps if len({faction(q) for q in step_ids(s)} - {0}) > 1]
            if len(mixed) < len(steps):
                add("storyline mixes Alliance-only and Horde-only quests", "%s / %s" % (zone_name, name))
        levels = [quests[q][1] for q in ids if quests[q][1] and quests[q][1] > 0]
        if levels and max(levels) - min(levels) >= 20:
            add("storyline spans 20+ levels", "%s / %s: levels %d-%d" % (zone_name, name, min(levels), max(levels)))
        # Length as one character sees it: steps with a quest for their faction and class.
        def seen(side, cls):
            def ok(q):
                row = quests[q]
                mask = row[4] if len(row) > 4 else None
                return faction(q) in (0, side) and (not mask or mask & cls)
            return sum(1 for step in steps if any(ok(q) for q in step_ids(step)))
        longest = max(seen(side, cls) for side in (1, 2) for cls in (1, 2, 4, 8, 16, 64, 128, 256, 1024))
        if longest > 25:
            add("very long storyline (25+ steps for one character)", "%s / %s: up to %d of %d steps" % (
                zone_name, name, longest, len(steps)))
        lower = name.lower()
        if lower.startswith(("return to", "report to", "speak with", "talk to", "back to")):
            add("generic storyline name", "%s / %s" % (zone_name, name))
    for (zone_name, side), counter in names_by_zone.items():
        for name, count in counter.items():
            if count > 1:
                add("same storyline name twice in one zone for one faction",
                    "%s / %s (%dx, %s)" % (zone_name, name, count, side))

    # ---- zones
    for area, zone in zones.items():
        if not (zone.get("stories") or zone.get("side") or zone.get("also") or zone.get("alsoSide")):
            add("empty zone", zone["name"])
        if zone["group"] in (1, 2) and not zone.get("uiMap"):
            add("zone without map ID (current-zone detection falls back to the name)", zone["name"])

    # ---- report
    total = sum(len(v) for v in findings.values())
    print("Checked %d quests, %d storylines, %d zones: %d findings in %d categories (%d hard-error categories)\n" % (
        len(quests), len(all_stories), len(zones), total, len(findings), len(errors)))
    for category in sorted(findings, key=lambda c: (c not in errors, -len(findings[c]))):
        items = findings[category]
        print("%s %s: %d" % ("ERROR" if category in errors else "note ", category, len(items)))
        for text in (items if args.all else items[:6]):
            print("        " + text)
        if not args.all and len(items) > 6:
            print("        ... %d more" % (len(items) - 6))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
