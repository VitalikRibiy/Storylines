#!/usr/bin/env python3
"""Debug helper: print the steps of generated storylines. Usage: show_story.py <zone name or story key>..."""
import os
import re
import signal
import sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # allow piping into head
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
text = open(os.path.join(ROOT, "Data", "Storylines.lua"), encoding="utf-8").read()
quests = {int(m.group(1)): (m.group(2), int(m.group(3)), int(m.group(4)))
          for m in re.finditer(r'^\[(\d+)\]=\{"((?:[^"\\]|\\.)*)",(-?\d+),(\d+)', text, re.M)}
zone = None
for line in text.splitlines():
    m = re.match(r'\[(\d+)\]=\{name="([^"]+)"', line)
    if m:
        zone = m.group(2)
        continue
    m = re.match(r'\{"((?:[^"\\]|\\.)*)",\{(.*?)\}(?:,"((?:[^"\\]|\\.)*)")?\},$', line)
    if not m:
        continue
    steps = re.findall(r"\{[\d,]+\}|\d+", m.group(2))
    ids = [int(x) for x in re.findall(r"\d+", m.group(2))]
    if any(a == zone or (a.isdigit() and int(a) in ids) for a in sys.argv[1:]):
        horde = (" | Horde: " + m.group(3)) if m.group(3) else ""
        print("%s :: %s%s (%d steps)" % (zone, m.group(1), horde, len(steps)))
        for st in steps:
            alts = [int(x) for x in re.findall(r"\d+", st)]
            print("    " + " / ".join("%d %s [%d]%s" % (q, quests[q][0], quests[q][1], " AH"[quests[q][2]]) for q in alts))
